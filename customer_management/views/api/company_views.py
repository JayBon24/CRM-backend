# -*- coding: utf-8 -*-
"""
企业信息查询接口
提供统一社会信用代码自动识别功能
支持阿里云企业信息API对接
"""
import logging
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
import requests
import time

logger = logging.getLogger(__name__)

# 企业信息API配置（从settings读取，使用阿里云API）
ALI_COMPANY_API_ENABLED = getattr(settings, 'ALI_COMPANY_API_ENABLED', False)
ALI_COMPANY_API_URL = getattr(settings, 'ALI_COMPANY_API_URL', 'https://sdcombz.market.alicloudapi.com/company_normal/query')
ALI_COMPANY_APP_CODE = getattr(settings, 'ALI_COMPANY_APP_CODE', '')
COMPANY_API_CACHE_TIMEOUT = getattr(settings, 'COMPANY_API_CACHE_TIMEOUT', 3600)  # 缓存1小时
COMPANY_API_RATE_LIMIT = getattr(settings, 'COMPANY_API_RATE_LIMIT', 10)  # 每分钟最多10次请求

# 限流记录（简单内存限流，生产环境建议使用Redis）
_rate_limit_cache = {}
_rate_limit_window = 60  # 60秒窗口


def _check_rate_limit():
    """检查API调用频率限制"""
    current_time = time.time()
    # 清理过期记录
    _rate_limit_cache.clear()
    for key, timestamps in list(_rate_limit_cache.items()):
        _rate_limit_cache[key] = [t for t in timestamps if current_time - t < _rate_limit_window]
    
    # 检查当前窗口内的请求数
    if len(_rate_limit_cache.get('global', [])) >= COMPANY_API_RATE_LIMIT:
        return False
    
    # 记录本次请求
    if 'global' not in _rate_limit_cache:
        _rate_limit_cache['global'] = []
    _rate_limit_cache['global'].append(current_time)
    return True


def _query_company_api(company_name: str):
    """
    调用阿里云企业信息API查询统一社会信用代码
    如果未配置阿里云API，则返回None，提示需要配置API
    """
    if not ALI_COMPANY_API_ENABLED or not ALI_COMPANY_APP_CODE:
        # API未配置，返回None，让调用方处理错误提示
        logger.warning(f'阿里云企业信息API未配置，无法查询: {company_name}。请配置 ALI_COMPANY_API_ENABLED 和 ALI_COMPANY_APP_CODE')
        return None
    
    try:
        # 检查限流
        if not _check_rate_limit():
            logger.warning('企业信息API调用频率超限')
            return None
        
        # 阿里云API认证：使用AppCode在Header中认证
        headers = {
            'Authorization': f'APPCODE {ALI_COMPANY_APP_CODE}',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
        
        # 阿里云API参数：使用公司名称查询
        # 注意：该API使用POST方法，参数放在body中，而不是URL参数
        bodys = {
            'keyword': company_name
        }
        
        # 记录请求信息
        logger.info(f'调用阿里云企业信息API: URL={ALI_COMPANY_API_URL}, 公司名称={company_name}, 方法=POST')
        
        # 使用POST请求，参数编码后放在body中
        import urllib.parse
        post_data = urllib.parse.urlencode(bodys).encode('utf-8')
        
        response = requests.post(
            ALI_COMPANY_API_URL,
            headers=headers,
            data=post_data,
            timeout=10
        )
        
        # 记录响应信息
        logger.info(f'阿里云API响应: status_code={response.status_code}, url={response.url}')
        
        if response.status_code == 200:
            try:
                data = response.json()
                # 记录完整响应数据用于调试
                logger.info(f'阿里云API返回数据: {data}')
                
                # 阿里云API返回格式可能因API而异，需要根据实际返回格式解析
                # 常见格式：{"code": 200, "data": {...}} 或 {"success": true, "result": {...}}
                if isinstance(data, dict):
                    # 尝试多种可能的返回格式
                    result_data = None
                    
                    # 检查是否有错误信息（只有当msg不是"成功"时才认为是错误）
                    if 'msg' in data or 'message' in data or 'error' in data:
                        error_msg = data.get('msg') or data.get('message') or data.get('error', '')
                        # 只有当msg不是"成功"时才认为是错误
                        if error_msg and error_msg != '成功' and error_msg != 'success':
                            logger.warning(f'阿里云API返回错误信息: {error_msg}, 完整数据: {data}')
                            # 如果错误信息表明查询无结果，返回None
                            if '无结果' in str(error_msg) or '未找到' in str(error_msg) or '不存在' in str(error_msg):
                                return None
                    
                    # 尝试多种数据路径
                    if 'data' in data:
                        if isinstance(data['data'], (dict, list)):
                            result_data = data['data']
                        elif data.get('code') == 200:
                            result_data = data.get('data')
                    elif 'result' in data:
                        result_data = data.get('result')
                    elif 'Result' in data:
                        result_data = data.get('Result')
                    elif 'list' in data:
                        result_data = data.get('list')
                    elif 'items' in data:
                        result_data = data.get('items')
                    # 如果data本身就是结果（没有外层包装）
                    elif 'name' in data or 'creditCode' in data or 'credit_code' in data or 'CreditCode' in data:
                        result_data = data
                    
                    if result_data:
                        # 处理单个结果或结果列表
                        if isinstance(result_data, list) and len(result_data) > 0:
                            candidates = []
                            for item in result_data[:5]:  # 最多返回5个
                                if isinstance(item, dict):
                                    # 阿里云API返回的字段名：CreditNo, CompanyName, LegalPerson, CompanyAddress, CompanyStatus
                                    credit_code = item.get('CreditNo') or item.get('creditCode') or item.get('CreditCode') or item.get('credit_code') or item.get('unifiedSocialCreditCode') or item.get('socialCreditCode', '')
                                    if credit_code:  # 只添加有信用代码的结果
                                        candidates.append({
                                            'name': item.get('CompanyName') or item.get('name') or item.get('Name') or item.get('companyName') or item.get('enterpriseName', ''),
                                            'credit_code': credit_code,
                                            'legal_representative': item.get('LegalPerson') or item.get('legalPerson') or item.get('LegalPerson') or item.get('legal_representative') or item.get('legalRepresentative', ''),
                                            'address': item.get('CompanyAddress') or item.get('address') or item.get('Address') or item.get('regAddress', ''),
                                            'status': item.get('CompanyStatus') or item.get('status') or item.get('Status') or item.get('enterpriseStatus', '')
                                        })
                            if candidates:
                                logger.info(f'成功解析到 {len(candidates)} 个企业信息')
                                return candidates
                            else:
                                logger.warning(f'解析到列表但无有效信用代码，列表内容: {result_data[:2]}')
                        elif isinstance(result_data, dict):
                            # 单个结果
                            # 阿里云API返回的字段名：CreditNo, CompanyName, LegalPerson, CompanyAddress, CompanyStatus
                            # 优先查找CreditNo字段（阿里云API的标准字段名）
                            credit_code = result_data.get('CreditNo')
                            if not credit_code:
                                # 如果CreditNo不存在，尝试其他可能的字段名
                                credit_code = result_data.get('creditCode') or result_data.get('CreditCode') or result_data.get('credit_code') or result_data.get('unifiedSocialCreditCode') or result_data.get('socialCreditCode', '')
                            
                            # 调试日志：记录CreditNo字段的值
                            logger.info(f'解析单个结果，CreditNo字段值: {result_data.get("CreditNo")}, credit_code变量值: {credit_code}, 所有字段: {list(result_data.keys())}')
                            
                            if credit_code:
                                logger.info(f'成功解析到单个企业信息: {credit_code}')
                                return [{
                                    'name': result_data.get('CompanyName') or result_data.get('name') or result_data.get('Name') or result_data.get('companyName') or result_data.get('enterpriseName', ''),
                                    'credit_code': str(credit_code),  # 确保是字符串类型
                                    'legal_representative': result_data.get('LegalPerson') or result_data.get('legalPerson') or result_data.get('legal_representative') or result_data.get('legalRepresentative', ''),
                                    'address': result_data.get('CompanyAddress') or result_data.get('address') or result_data.get('Address') or result_data.get('regAddress', ''),
                                    'status': result_data.get('CompanyStatus') or result_data.get('status') or result_data.get('Status') or result_data.get('enterpriseStatus', '')
                                }]
                            else:
                                logger.warning(f'单个结果中未找到信用代码，CreditNo字段值: {result_data.get("CreditNo")}, 可用字段: {list(result_data.keys())}')
                    
                    # 如果没有找到数据，记录返回内容用于调试
                    logger.warning(f'阿里云API返回数据格式异常，无法解析: {data}')
                    return None
                else:
                    logger.warning(f'阿里云API返回格式异常，期望dict，实际: {type(data)}, 内容: {data}')
                    return None
            except ValueError as e:
                logger.error(f'阿里云API返回非JSON格式: {response.text[:500]}')
                return None
        elif response.status_code == 401:
            logger.error(f'阿里云API认证失败: AppCode可能无效')
            return None
        else:
            logger.error(f'阿里云API调用失败: HTTP {response.status_code}, {response.text}')
            return None
            
    except Exception as e:
        logger.error(f'阿里云企业信息API调用异常: {str(e)}', exc_info=True)
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_company_credit_code(request):
    """
    根据公司名称查询统一社会信用代码
    GET /api/crm/company/credit-code?company_name=xxx
    
    返回多个候选结果，供用户选择
    """
    try:
        company_name = request.query_params.get('company_name', '').strip()
        
        if not company_name:
            return ErrorResponse(msg='公司名称不能为空', code=4001)
        
        if len(company_name) < 2:
            return ErrorResponse(msg='公司名称至少需要2个字符', code=4001)
        
        # 检查缓存
        cache_key = f'company_credit_code:{company_name}'
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f'从缓存获取企业信息: {company_name}')
            return DetailResponse(data=cached_result)
        
        # 调用API查询
        candidates = _query_company_api(company_name)
        
        if candidates is None:
            # 检查是否是API未配置的情况
            if not ALI_COMPANY_API_ENABLED or not ALI_COMPANY_APP_CODE:
                return ErrorResponse(
                    msg='企业信息查询API未配置，请联系管理员配置阿里云企业信息API密钥后重试', 
                    code=4005
                )
            return ErrorResponse(msg='未获取到信用代码，请手动填写', code=4004)
        
        # 格式化返回数据
        result = {
            'company_name': company_name,
            'candidates': candidates,
            'count': len(candidates)
        }
        
        # 缓存结果
        cache_timeout = getattr(settings, 'COMPANY_API_CACHE_TIMEOUT', 3600)
        cache.set(cache_key, result, cache_timeout)
        
        return DetailResponse(data=result)
        
    except Exception as e:
        logger.error(f'查询统一社会信用代码失败: {str(e)}', exc_info=True)
        return ErrorResponse(msg=f'查询失败: {str(e)}', code=4000)
