"""
腾讯OCR服务封装
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any, Dict

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from application import dispatch
try:
    from dvadmin.system.models import SystemConfig
except Exception:  # pragma: no cover
    SystemConfig = None

try:
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.ocr.v20181119 import ocr_client, models
except Exception:  # pragma: no cover - 避免依赖缺失导致导入失败
    credential = None
    ocr_client = None
    models = None

logger = logging.getLogger(__name__)


class TencentOCRService:
    """腾讯OCR服务（名片/通用识别）"""

    def __init__(self):
        self.config = self._load_config()
        self.secret_id = self.config.get('SECRET_ID', '')
        self.secret_key = self.config.get('SECRET_KEY', '')
        self.region = self.config.get('REGION', 'ap-beijing')
        self.enabled = bool(self.secret_id and self.secret_key and credential and ocr_client and models)

        if not self.enabled:
            logger.warning("腾讯OCR配置不完整或SDK不可用，将使用模拟模式")

    def _load_config(self) -> Dict[str, Any]:
        config = getattr(settings, 'TENCENT_OCR_CONFIG', {}) or {}
        use_system_config = config.get('USE_SYSTEM_CONFIG', True)
        secret_id = config.get('SECRET_ID', '')
        secret_key = config.get('SECRET_KEY', '')
        region = config.get('REGION', 'ap-beijing')

        # 优先从系统配置读取（兼容不同的 key 形态）
        if use_system_config:
            if not secret_id or secret_id == '1318395246':  # 排除明显错误的默认值
                system_secret_id = self._get_system_config_value(
                    ["tencent_ocr_secret_id", "tencent_ocr.secret_id"]
                )
                if system_secret_id:
                    secret_id = system_secret_id
            if not secret_key or secret_key.startswith('AKID') and len(secret_key) < 50:  # SecretKey应该更长
                system_secret_key = self._get_system_config_value(
                    ["tencent_ocr_secret_key", "tencent_ocr.secret_key"]
                )
                if system_secret_key:
                    secret_key = system_secret_key
            if not region or region == 'ap-beijing':
                system_region = self._get_system_config_value(
                    ["tencent_ocr_region", "tencent_ocr.region"]
                )
                if system_region:
                    region = system_region

        # 兜底读取环境变量/配置文件
        secret_id = secret_id or getattr(settings, 'TENCENT_OCR_SECRET_ID', '') or config.get('SECRET_ID', '')
        secret_key = secret_key or getattr(settings, 'TENCENT_OCR_SECRET_KEY', '') or config.get('SECRET_KEY', '')
        region = region or getattr(settings, 'TENCENT_OCR_REGION', '') or config.get('REGION', 'ap-beijing')

        # 清理非法值，避免 SDK 触发 latin-1 编码错误
        if not self._is_valid_secret_id(secret_id):
            logger.warning("OCR配置 SECRET_ID 无效或包含非ASCII字符")
            secret_id = ""
        if not self._is_valid_secret_key(secret_key):
            logger.warning("OCR配置 SECRET_KEY 无效或包含非ASCII字符")
            secret_key = ""

        # 调试日志：记录配置读取情况（不记录完整密钥）
        logger.info(f"OCR配置加载: SECRET_ID长度={len(secret_id) if secret_id else 0}, "
                   f"SECRET_KEY长度={len(secret_key) if secret_key else 0}, REGION={region}")

        return {
            'SECRET_ID': secret_id,
            'SECRET_KEY': secret_key,
            'REGION': region,
        }

    def _get_system_config_value(self, keys):
        """从系统配置获取值，先通过 dispatch，再直查 SystemConfig。"""
        for key in keys:
            try:
                value = dispatch.get_system_config_values(key)
            except Exception:
                value = None
            if value:
                return value
        if SystemConfig:
            for key in keys:
                try:
                    value = SystemConfig.objects.filter(key=key).values_list("value", flat=True).first()
                    if value:
                        return value
                except Exception:
                    continue
        return None

    def _is_valid_secret_id(self, value: str) -> bool:
        if not value:
            return False
        try:
            value.encode("ascii")
        except Exception:
            return False
        # SecretId 通常以 AKID 开头，长度要求放宽，避免误判
        return value.startswith("AKID")

    def _is_valid_secret_key(self, value: str) -> bool:
        if not value:
            return False
        try:
            value.encode("ascii")
        except Exception:
            return False
        # SecretKey 长度放宽到 >= 32
        return len(value) >= 32

    def _file_to_base64(self, image_file: UploadedFile) -> str:
        image_file.seek(0)
        return base64.b64encode(image_file.read()).decode('utf-8')

    def _build_client(self):
        # 验证配置
        if not self.secret_id or not self.secret_key:
            raise ValueError(f"OCR配置不完整: SECRET_ID={'已设置' if self.secret_id else '未设置'}, "
                           f"SECRET_KEY={'已设置' if self.secret_key else '未设置'}")
        
        # 验证SecretId格式（通常以AKID开头）
        if not self.secret_id.startswith('AKID') and len(self.secret_id) < 20:
            logger.warning(f"SECRET_ID格式可能不正确: {self.secret_id[:10]}... (长度: {len(self.secret_id)})")
        
        cred = credential.Credential(self.secret_id, self.secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = "ocr.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        return ocr_client.OcrClient(cred, self.region, client_profile)

    def recognize_business_card(self, image_file: UploadedFile) -> Dict[str, Any]:
        if not self.enabled:
            logger.warning("OCR服务未启用，使用模拟模式")
            return self._mock_business_card()

        try:
            # 记录配置信息（不记录完整密钥）
            logger.info(f"开始名片OCR识别: SECRET_ID前10位={self.secret_id[:10] if self.secret_id else 'N/A'}, "
                       f"SECRET_KEY长度={len(self.secret_key) if self.secret_key else 0}, REGION={self.region}")
            
            client = self._build_client()
            req = models.BusinessCardOCRRequest()
            req.ImageBase64 = self._file_to_base64(image_file)
            resp = client.BusinessCardOCR(req)
            data = json.loads(resp.to_json_string())
            return self._parse_business_card(data)
        except Exception as exc:
            logger.error(f"名片OCR识别失败: {exc}")
            logger.error(f"配置信息: SECRET_ID长度={len(self.secret_id) if self.secret_id else 0}, "
                        f"SECRET_KEY长度={len(self.secret_key) if self.secret_key else 0}, "
                        f"SECRET_ID前10位={self.secret_id[:10] if self.secret_id else 'N/A'}")
            return {"success": False, "error": str(exc)}

    def recognize_general(self, image_file: UploadedFile) -> Dict[str, Any]:
        if not self.enabled:
            return self._mock_general()

        try:
            client = self._build_client()
            req = models.GeneralBasicOCRRequest()
            req.ImageBase64 = self._file_to_base64(image_file)
            resp = client.GeneralBasicOCR(req)
            data = json.loads(resp.to_json_string())
            return self._parse_general(data)
        except Exception as exc:
            logger.error(f"通用OCR识别失败: {exc}")
            return {"success": False, "error": str(exc)}

    def _parse_business_card(self, data: Dict[str, Any]) -> Dict[str, Any]:
        infos = data.get("BusinessCardInfos") or []
        mapping = {
            "姓名": "name",
            "公司": "company",
            "职称": "position",
            "电话": "phone",
            "手机": "mobile",
            "邮箱": "email",
            "地址": "address",
            "网站": "website",
            "微信": "wechat",
            "QQ": "qq",
        }
        result = {key: "" for key in mapping.values()}
        raw_text_parts = []
        for item in infos:
            name = item.get("Name")
            value = item.get("Value", "")
            raw_text_parts.append(value)
            key = mapping.get(name)
            if key:
                result[key] = value
        result["rawText"] = "\n".join([part for part in raw_text_parts if part])
        result["success"] = True
        return result

    def _parse_general(self, data: Dict[str, Any]) -> Dict[str, Any]:
        texts = data.get("TextDetections") or []
        raw_text = "\n".join([item.get("DetectedText", "") for item in texts if item.get("DetectedText")])
        return {
            "success": True,
            "rawText": raw_text,
            "extractedFields": self._extract_fields(raw_text),
        }

    def _extract_fields(self, text: str) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}
        if not text:
            return fields

        contract_match = re.search(r"(合同编号|合同号)[:：]?\s*([A-Za-z0-9\-]+)", text)
        if contract_match:
            fields["contractNo"] = contract_match.group(2)

        amount_match = re.search(r"(金额|合同金额|价款)[:：]?\s*([0-9,\.]+)", text)
        if amount_match:
            fields["amount"] = amount_match.group(2)

        date_match = re.search(r"(\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?)", text)
        if date_match:
            fields["date"] = date_match.group(1)

        party_a = re.search(r"(甲方|委托方)[:：]?\s*([^\n]+)", text)
        if party_a:
            fields["partyA"] = party_a.group(2).strip()

        party_b = re.search(r"(乙方|受托方)[:：]?\s*([^\n]+)", text)
        if party_b:
            fields["partyB"] = party_b.group(2).strip()

        case_no = re.search(r"(案号|案件编号)[:：]?\s*([A-Za-z0-9\-]+)", text)
        if case_no:
            fields["caseNo"] = case_no.group(2)

        plaintiff = re.search(r"(原告)[:：]?\s*([^\n]+)", text)
        if plaintiff:
            fields["plaintiffName"] = plaintiff.group(2).strip()

        defendant = re.search(r"(被告)[:：]?\s*([^\n]+)", text)
        if defendant:
            fields["defendantName"] = defendant.group(2).strip()

        return fields

    def _mock_business_card(self) -> Dict[str, Any]:
        return {
            "success": True,
            "name": "张三",
            "company": "示例科技有限公司",
            "position": "销售经理",
            "phone": "010-88888888",
            "mobile": "13800000000",
            "email": "zhangsan@example.com",
            "address": "北京市朝阳区示例路88号",
            "website": "https://example.com",
            "wechat": "zhangsan",
            "qq": "123456",
            "rawText": "张三\n示例科技有限公司\n销售经理\n13800000000",
        }

    def _mock_general(self) -> Dict[str, Any]:
        return {
            "success": True,
            "rawText": "合同编号: HT20240101\n合同金额: 100000\n日期: 2024-01-01",
            "extractedFields": {
                "contractNo": "HT20240101",
                "amount": "100000",
                "date": "2024-01-01",
            },
        }
