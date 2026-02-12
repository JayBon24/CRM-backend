"""
智能内容提取服务
用于从提取的文本内容中智能识别和映射到模板占位符字段
"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SmartContentExtractor:
    """智能内容提取器"""
    
    def __init__(self):
        # 定义字段映射规则
        self.field_patterns = {
            # 原告信息
            'plaintiff_name': [
                r'原告[：:]\s*([^\s，,。\n]+)',
                r'申请人[：:]\s*([^\s，,。\n]+)',
                r'起诉人[：:]\s*([^\s，,。\n]+)',
                r'原告方[：:]\s*([^\s，,。\n]+)',
                r'([^\s，,。\n]+)\s*作为原告',
                r'([^\s，,。\n]+)\s*起诉'
            ],
            'plaintiff_address': [
                r'原告地址[：:]\s*([^\n]+)',
                r'申请人地址[：:]\s*([^\n]+)',
                r'原告住所[：:]\s*([^\n]+)',
                r'原告住址[：:]\s*([^\n]+)',
                r'住址[：:]\s*([^\n]+)',
                r'地址[：:]\s*([^\n]+)'
            ],
            'plaintiff_credit_code': [
                r'原告统一社会信用代码[：:]\s*([A-Z0-9]{18})',
                r'申请人统一社会信用代码[：:]\s*([A-Z0-9]{18})',
                r'信用代码[：:]\s*([A-Z0-9]{18})',
                r'社会信用代码[：:]\s*([A-Z0-9]{18})',
                r'统一社会信用代码[：:]\s*([A-Z0-9]{18})'
            ],
            'plaintiff_legal_representative': [
                r'原告法定代表人[：:]\s*([^\s，,。\n]+)',
                r'申请人法定代表人[：:]\s*([^\s，,。\n]+)',
                r'法定代表人[：:]\s*([^\s，,。\n]+)',
                r'法人代表[：:]\s*([^\s，,。\n]+)'
            ],
            
            # 被告信息
            'defendant_name': [
                r'被告[：:]\s*([^\s，,。\n]+)',
                r'被申请人[：:]\s*([^\s，,。\n]+)',
                r'被起诉人[：:]\s*([^\s，,。\n]+)',
                r'被告方[：:]\s*([^\s，,。\n]+)',
                r'([^\s，,。\n]+)\s*作为被告',
                r'起诉\s*([^\s，,。\n]+)'
            ],
            'defendant_address': [
                r'被告地址[：:]\s*([^\n]+)',
                r'被申请人地址[：:]\s*([^\n]+)',
                r'被告住所[：:]\s*([^\n]+)',
                r'被告住址[：:]\s*([^\n]+)'
            ],
            'defendant_credit_code': [
                r'被告统一社会信用代码[：:]\s*([A-Z0-9]{18})',
                r'被申请人统一社会信用代码[：:]\s*([A-Z0-9]{18})'
            ],
            'defendant_legal_representative': [
                r'被告法定代表人[：:]\s*([^\s，,。\n]+)',
                r'被申请人法定代表人[：:]\s*([^\s，,。\n]+)'
            ],
            
            # 案件信息
            'case_number': [
                r'案件编号[：:]\s*([^\s，,。\n]+)',
                r'案号[：:]\s*([^\s，,。\n]+)',
                r'编号[：:]\s*([^\s，,。\n]+)'
            ],
            'case_name': [
                r'案件名称[：:]\s*([^\n]+)',
                r'案由[：:]\s*([^\n]+)',
                r'纠纷性质[：:]\s*([^\n]+)'
            ],
            'case_type': [
                r'案件类型[：:]\s*([^\s，,。\n]+)',
                r'诉讼类型[：:]\s*([^\s，,。\n]+)',
                r'纠纷类型[：:]\s*([^\s，,。\n]+)'
            ],
            'jurisdiction': [
                r'管辖法院[：:]\s*([^\n]+)',
                r'受理法院[：:]\s*([^\n]+)',
                r'法院[：:]\s*([^\n]+)'
            ],
            
            # 金额信息
            'contract_amount': [
                r'合同金额[：:]\s*([0-9,，.]+)\s*元',
                r'争议金额[：:]\s*([0-9,，.]+)\s*元',
                r'诉讼标的[：:]\s*([0-9,，.]+)\s*元',
                r'金额[：:]\s*([0-9,，.]+)\s*元',
                r'([0-9,，.]+)\s*元'
            ],
            'lawyer_fee': [
                r'律师费[：:]\s*([0-9,，.]+)\s*元',
                r'代理费[：:]\s*([0-9,，.]+)\s*元',
                r'法律服务费[：:]\s*([0-9,，.]+)\s*元'
            ],
            
            # 时间信息
            'contract_date': [
                r'合同签订日期[：:]\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)',
                r'签订日期[：:]\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)',
                r'合同日期[：:]\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)'
            ],
            'dispute_date': [
                r'纠纷发生日期[：:]\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)',
                r'争议发生日期[：:]\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)',
                r'纠纷时间[：:]\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)'
            ],
            'filing_date': [
                r'起诉日期[：:]\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)',
                r'立案日期[：:]\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)',
                r'提交日期[：:]\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)'
            ]
        }
    
    def extract_from_content(self, content: str) -> Dict[str, Any]:
        """从内容中提取字段信息"""
        extracted_data = {}
        
        # 清理内容，去除多余空白
        content = re.sub(r'\s+', ' ', content)
        
        for field, patterns in self.field_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value and value not in ['无', '暂无', '待定', '未知']:
                        extracted_data[field] = value
                        break
        
        # 处理金额字段，转换为数字
        if 'contract_amount' in extracted_data:
            try:
                amount_str = extracted_data['contract_amount'].replace(',', '').replace('，', '')
                extracted_data['contract_amount'] = float(amount_str)
            except ValueError:
                extracted_data['contract_amount'] = 0.0
        
        if 'lawyer_fee' in extracted_data:
            try:
                fee_str = extracted_data['lawyer_fee'].replace(',', '').replace('，', '')
                extracted_data['lawyer_fee'] = float(fee_str)
            except ValueError:
                extracted_data['lawyer_fee'] = 0.0
        
        # 处理日期字段，转换为标准格式
        date_fields = ['contract_date', 'dispute_date', 'filing_date']
        for field in date_fields:
            if field in extracted_data:
                extracted_data[field] = self._normalize_date(extracted_data[field])
        
        logger.info(f"从内容中提取到字段: {list(extracted_data.keys())}")
        return extracted_data
    
    def _normalize_date(self, date_str: str) -> str:
        """标准化日期格式"""
        try:
            # 处理 "2024年1月1日" 格式
            if '年' in date_str and '月' in date_str and '日' in date_str:
                year = re.search(r'(\d{4})年', date_str)
                month = re.search(r'(\d{1,2})月', date_str)
                day = re.search(r'(\d{1,2})日', date_str)
                
                if year and month and day:
                    return f"{year.group(1)}-{month.group(1).zfill(2)}-{day.group(1).zfill(2)}"
        except Exception as e:
            logger.warning(f"日期格式化失败: {date_str}, 错误: {e}")
        
        return date_str
    
    def merge_with_case_data(self, case_data: Dict[str, Any], extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """将提取的数据与案例数据合并，提取的数据优先级更高"""
        merged_data = case_data.copy()
        
        # 更新提取到的字段
        for key, value in extracted_data.items():
            if value:  # 只有当提取到的值不为空时才更新
                merged_data[key] = value
                logger.info(f"更新字段 {key}: {value}")
        
        return merged_data


# 创建全局实例
smart_extractor = SmartContentExtractor()


