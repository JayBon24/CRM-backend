"""
AI服务模块 - 只使用真实AI模型，异常时直接返回错误
"""

import json
import os
from typing import Dict, Any, List
from django.conf import settings

# 不再使用模拟AI服务
MOCK_AI_AVAILABLE = False

# 导入错误消息处理
try:
    from .error_messages import get_user_friendly_error_message
except ImportError:
    def get_user_friendly_error_message(error: str) -> str:
        return f"AI服务暂时不可用：{error}"

# 导入直接LangChain AI服务
try:
    from .direct_langchain_ai_service import (
        generate_document_with_langchain,
        generate_all_documents_with_langchain,
        ai_chat_with_langchain,
        test_langchain_connection,
        get_best_available_model
    )
    LANGCHAIN_AI_AVAILABLE = True
except ImportError:
    LANGCHAIN_AI_AVAILABLE = False


def deepseek_ai(prompt: str, documents: List[str] = None, templates: List[str] = None) -> Dict[str, Any]:
    """
    调用DeepSeek-R1大模型API

    Args:
        prompt: 提示词
        documents: 文档列表
        templates: 模板列表

    Returns:
        AI响应结果
    """
    import requests
    
    # 从环境变量获取API密钥
    api_key = os.getenv('DEEPSEEK_API_KEY', '')
    
    if not api_key:
        return {
            "success": False,
            "error": "DeepSeek API密钥未配置",
            "content": "请配置DEEPSEEK_API_KEY环境变量"
        }
    
    # 构建请求数据
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的法律文书生成助手，请根据用户的要求生成高质量的法律文书。"
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 4000
    }
    
    try:
        # 发送请求
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=data,
            timeout=30
        )
        
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            return {
                "success": True,
                "content": content,
                "usage": result.get('usage', {})
            }
        elif response.status_code == 401:
            return {
                "success": False,
                "error": "API密钥无效",
                "content": "请检查DeepSeek API密钥是否正确"
            }
        elif response.status_code == 402:
            return {
                "success": False,
                "error": "账户余额不足",
                "content": "DeepSeek账户余额不足，请充值后重试"
            }
        elif response.status_code == 429:
            return {
                "success": False,
                "error": "请求频率过高",
                "content": "请求过于频繁，请稍后再试"
            }
        else:
            return {
                "success": False,
                "error": f"API调用失败: {response.status_code}",
                "content": f"DeepSeek API返回错误: {response.text}"
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "请求超时",
            "content": "AI服务响应超时，请稍后再试"
        }
    except requests.exceptions.ConnectionError as e:
        print(f"DeepSeek API连接错误: {e}")
        return {
            "success": False,
            "error": f"DeepSeek API连接错误: {str(e)}",
            "content": f"无法连接到DeepSeek API: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"未知错误: {str(e)}",
            "content": f"AI服务调用失败: {str(e)}"
        }


def load_template_files() -> List[Dict[str, str]]:
    """加载模板文件"""
    templates = []
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    
    if not os.path.exists(template_dir):
        return templates

    for filename in os.listdir(template_dir):
        filepath = os.path.join(template_dir, filename)
        if os.path.isfile(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    templates.append({
                        "name": filename,
                        "content": f.read()
                    })
            except Exception as e:
                print(f"读取模板文件 {filename} 失败: {e}")
    
    return templates


def generate_document_with_ai(case_data: Dict[str, Any], document_type: str) -> Dict[str, Any]:
    """
    使用AI生成单个法律文书
    只使用真实AI服务，异常时直接返回错误
    """
    # 使用LangChain AI服务
    if LANGCHAIN_AI_AVAILABLE:
        try:
            print("使用LangChain AI服务生成文档")
            result = generate_document_with_langchain(case_data, document_type)
            if result.get('success', False):
                return result
            else:
                # 直接返回错误，不进行降级
                error_msg = f"LangChain AI服务失败: {result.get('error', '未知错误')}"
                print(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'content': f"生成文档失败: {result.get('error', '未知错误')}"
                }
        except Exception as e:
            # 直接返回异常，不进行降级
            error_msg = f"LangChain AI服务异常: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'content': f"生成文档失败: {str(e)}"
            }
    
    # 尝试使用DeepSeek API
    try:
        print("使用DeepSeek API生成文档")
        # 构建提示词
        prompt = f"""请根据以下案例信息生成{document_type}：

案例信息：
- 案号：{case_data.get('case_number', '')}
- 案件名称：{case_data.get('case_name', '')}
- 案件类型：{case_data.get('case_type', '')}
- 管辖法院：{case_data.get('jurisdiction', '')}
- 拟稿人：{case_data.get('draft_person', '')}

被告信息：
- 被告名称：{case_data.get('defendant_name', '')}
- 被告信用代码：{case_data.get('defendant_credit_code', '')}
- 被告地址：{case_data.get('defendant_address', '')}

原告信息：
- 原告名称：{case_data.get('plaintiff_name', '')}
- 原告信用代码：{case_data.get('plaintiff_credit_code', '')}
- 原告地址：{case_data.get('plaintiff_address', '')}

费用信息：
- 合同金额：{case_data.get('contract_amount', 0)}
- 律师费：{case_data.get('lawyer_fee', 0)}

请生成专业的{document_type}，要求格式规范、内容完整、逻辑清晰。"""

        # 调用AI生成
        result = deepseek_ai(prompt)
        
        # 如果API调用成功，直接返回结果
        if result.get('success', False):
            return {
                'success': True,
                'content': result['content'],
                'document_name': document_type
            }
        else:
            # 直接返回错误，不进行降级
            error_msg = f"DeepSeek API失败: {result.get('error', '未知错误')}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'content': f"生成文档失败: {result.get('error', '未知错误')}"
            }
            
    except Exception as e:
        # 直接返回异常，不进行降级
        error_msg = f"DeepSeek API异常: {str(e)}"
        print(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'content': f"生成文档失败: {str(e)}"
        }
    
    # 如果所有AI服务都不可用
    return {
        'success': False,
        'error': '所有AI服务都不可用',
        'content': '抱歉，AI服务暂时不可用，请检查配置后重试。'
    }


def generate_all_documents_with_ai(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据所有模板生成法律文书
    只使用真实AI服务，异常时直接返回错误
    """
    # 使用LangChain AI服务
    if LANGCHAIN_AI_AVAILABLE:
        try:
            print("使用LangChain AI服务生成所有文档")
            result = generate_all_documents_with_langchain(case_data)
            # 只要有文档生成成功就认为成功
            if result.get('success_count', 0) > 0:
                return result
            else:
                # 如果没有任何文档生成成功，返回错误
                error_msg = f"LangChain AI服务失败: 没有成功生成任何文档"
                print(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'documents': result.get('documents', []),
                    'total_count': result.get('total_count', 0),
                    'success_count': result.get('success_count', 0),
                    'error_count': result.get('error_count', 0)
                }
        except Exception as e:
            # 直接返回异常，不进行降级
            error_msg = f"LangChain AI服务异常: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'documents': [],
                'total_count': 0,
                'success_count': 0,
                'error_count': 0
            }
    
    # 如果LangChain不可用，返回错误
    return {
        'success': False,
        'error': 'LangChain AI服务不可用',
        'documents': [],
        'total_count': 0,
        'success_count': 0,
        'error_count': 0
    }


def ai_chat_with_documents(message: str, uploaded_files: List[str] = None) -> Dict[str, Any]:
    """
    使用AI进行对话
    只使用真实AI服务，异常时直接返回错误
    """
    # 使用LangChain AI服务
    if LANGCHAIN_AI_AVAILABLE:
        try:
            print("使用LangChain AI服务进行对话")
            result = ai_chat_with_langchain(message, uploaded_files)
            if result.get('success', False):
                return result
            else:
                # 直接返回错误，不进行降级
                error_msg = f"LangChain AI服务失败: {result.get('error', '未知错误')}"
                print(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'content': f"AI对话失败: {result.get('error', '未知错误')}"
                }
        except Exception as e:
            # 直接返回异常，不进行降级
            error_msg = f"LangChain AI服务异常: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'content': f"AI对话失败: {str(e)}"
            }
    
    # 如果LangChain不可用，返回错误
    return {
        'success': False,
        'error': 'LangChain AI服务不可用',
        'content': '抱歉，AI服务暂时不可用，请检查配置后重试。'
    }


def test_ai_services() -> Dict[str, Any]:
    """测试所有AI服务"""
    results = {}
    
    # 测试LangChain服务
    if LANGCHAIN_AI_AVAILABLE:
        try:
            results['langchain'] = {
                'available': True,
                'status': 'success' if test_langchain_connection() else 'failed'
            }
        except Exception as e:
            results['langchain'] = {
                'available': True,
                'status': 'error',
                'error': str(e)
            }
    else:
        results['langchain'] = {
            'available': False,
            'status': 'not_installed'
        }
    
    # 测试DeepSeek API
    try:
        test_result = deepseek_ai("你好，请简单回复")
        results['deepseek'] = {
            'available': True,
            'status': 'success' if test_result.get('success') else 'failed',
            'error': test_result.get('error') if not test_result.get('success') else None
        }
    except Exception as e:
        results['deepseek'] = {
            'available': True,
            'status': 'error',
            'error': str(e)
        }
    
    return results
