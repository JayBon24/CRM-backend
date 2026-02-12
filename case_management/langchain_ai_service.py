"""
使用LangChain和OpenRouter的AI服务
"""

import os
import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenRouter API配置（必须从环境变量读取，禁止硬编码）
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# 可用的免费模型列表（按优先级排序）
FREE_MODELS = [
    "deepseek/deepseek-r1:free",           # DeepSeek R1 - 推荐
    "google/gemma-2-9b-it:free",           # Google Gemma 2 9B - 备选
    "mistralai/mistral-7b-instruct:free",  # Mistral 7B - 备选
    "meta-llama/llama-3.1-8b-instruct:free",
    "meta-llama/llama-3.1-70b-instruct:free", 
    "microsoft/phi-3-mini-128k-instruct:free",
    "huggingface/zephyr-7b-beta:free"
]

# 付费模型列表（需要账户余额）
PAID_MODELS = [
    "deepseek/deepseek-chat",              # DeepSeek Chat - 付费
    "meta-llama/llama-3-8b-instruct",      # Meta Llama 3 8B
    "meta-llama/llama-3-8b-instruct:latest",
    "meta-llama/llama-3.1-8b-instruct",
    "meta-llama/llama-3.1-8b-instruct:latest",
    "meta-llama/llama-3.1-70b-instruct",
    "meta-llama/llama-3.1-70b-instruct:latest"
]

# 所有可用模型（免费优先，付费备选）
ALL_MODELS = FREE_MODELS + PAID_MODELS

# 初始化ChatOpenAI模型
def get_chat_model(model_name: str = None):
    """获取ChatOpenAI模型实例"""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY 未配置")

    if model_name is None:
        # 尝试获取最佳免费模型
        model_name = get_best_free_model()
    
    return ChatOpenAI(
        model=model_name,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        temperature=0.7,
        max_tokens=4000,
        timeout=30
    )

def load_template_files() -> List[Dict[str, str]]:
    """加载模板文件"""
    templates = []
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    
    if not os.path.exists(template_dir):
        logger.warning(f"模板目录不存在: {template_dir}")
        return templates
    
    template_files = [
        "1、起诉状（被告数量+3份）.docx",
        "2、法定代表人身份证明(5份).doc",
        "3、授权委托书（5份）.doc",
        "4、撤销授权（3份）.doc",
        "5、财产保全申请书（3份）.doc",
        "6、续封申请书（3份)-.doc",
        "7、解除财产保全申请书(3份).doc",
        "8、撤诉申请书(3份).doc",
        "9、诉前保全申请书（3份）.docx",
        "10、追加被告申请书（2份）-.doc",
        "11.（诉讼用）委托代理合同(1份).docx"
    ]
    
    for filename in template_files:
        file_path = os.path.join(template_dir, filename)
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                templates.append({
                    'name': filename,
                    'content': content
                })
                logger.info(f"成功加载模板: {filename}")
            else:
                logger.warning(f"模板文件不存在: {filename}")
        except Exception as e:
            logger.error(f"加载模板文件失败 {filename}: {e}")
    
    return templates

def generate_document_with_langchain(case_data: Dict[str, Any], document_type: str = "起诉状") -> Dict[str, Any]:
    """
    使用LangChain生成单个文档
    
    Args:
        case_data: 案例数据
        document_type: 文档类型
    
    Returns:
        生成结果
    """
    try:
        # 获取模型
        model = get_chat_model()
        
        # 构建提示词
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""你是一个专业的法律文书生成助手。请根据提供的案例信息，生成相应的法律文书。

要求：
1. 使用专业的法律语言和格式
2. 确保文书内容完整、准确
3. 根据案例信息填充所有必要字段
4. 保持文书的正式性和规范性

案例信息：
- 案号：{case_number}
- 案件名称：{case_name}
- 案件类型：{case_type}
- 管辖法院：{jurisdiction}
- 拟稿人：{draft_person}
- 被告名称：{defendant_name}
- 被告信用代码：{defendant_credit_code}
- 被告地址：{defendant_address}
- 原告名称：{plaintiff_name}
- 原告信用代码：{plaintiff_credit_code}
- 原告地址：{plaintiff_address}
- 合同金额：{contract_amount}
- 律师费：{lawyer_fee}

请生成{document_type}，要求内容完整、格式规范。"""),
            HumanMessage(content=f"请根据上述案例信息生成{document_type}")
        ])
        
        # 创建处理链
        chain = prompt | model | StrOutputParser()
        
        # 执行生成
        result = chain.invoke(case_data)
        
        return {
            'success': True,
            'content': result,
            'document_name': document_type,
            'template_name': f"{document_type}_模板"
        }
        
    except Exception as e:
        logger.error(f"生成文档失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'content': '',
            'document_name': document_type,
            'template_name': f"{document_type}_模板"
        }

def generate_all_documents_with_langchain(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用LangChain生成所有文档
    
    Args:
        case_data: 案例数据
    
    Returns:
        生成结果
    """
    try:
        # 文档类型列表
        document_types = [
            "起诉状",
            "法定代表人身份证明",
            "授权委托书",
            "撤销授权",
            "财产保全申请书",
            "续封申请书",
            "解除财产保全申请书",
            "撤诉申请书",
            "诉前保全申请书",
            "追加被告申请书",
            "委托代理合同"
        ]
        
        results = []
        success_count = 0
        
        for doc_type in document_types:
            logger.info(f"正在生成文档: {doc_type}")
            result = generate_document_with_langchain(case_data, doc_type)
            results.append(result)
            
            if result['success']:
                success_count += 1
                logger.info(f"成功生成文档: {doc_type}")
            else:
                logger.error(f"生成文档失败: {doc_type} - {result.get('error', '未知错误')}")
        
        return {
            'success': success_count > 0,
            'documents': results,
            'total_count': len(document_types),
            'success_count': success_count,
            'error_count': len(document_types) - success_count
        }
        
    except Exception as e:
        logger.error(f"批量生成文档失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'documents': [],
            'total_count': 0,
            'success_count': 0,
            'error_count': 0
        }

def ai_chat_with_langchain(message: str, uploaded_files: List[str] = None) -> Dict[str, Any]:
    """
    使用LangChain进行AI对话
    
    Args:
        message: 用户消息
        uploaded_files: 上传的文件内容列表
    
    Returns:
        AI回复
    """
    try:
        # 获取模型
        model = get_chat_model()
        
        # 构建提示词
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""你是一个专业的法律助手，专门帮助律师处理案例管理和文书生成工作。

你的主要职责：
1. 回答法律相关问题
2. 帮助生成各种法律文书
3. 提供法律建议和指导
4. 协助案例管理工作

请用专业、准确、友好的语言回答用户的问题。如果用户需要生成法律文书，请提供详细的指导和建议。"""),
            HumanMessage(content=message)
        ])
        
        # 创建处理链
        chain = prompt | model | StrOutputParser()
        
        # 执行对话
        result = chain.invoke({"message": message})
        
        return {
            'success': True,
            'content': result
        }
        
    except Exception as e:
        logger.error(f"AI对话失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'content': f"抱歉，AI服务暂时不可用：{str(e)}"
        }

def test_langchain_connection() -> bool:
    """测试LangChain连接"""
    try:
        model = get_chat_model()
        result = model.invoke([HumanMessage(content="你好，请回复'连接成功'")])
        logger.info(f"LangChain连接测试成功: {result.content}")
        return True
    except Exception as e:
        logger.error(f"LangChain连接测试失败: {e}")
        return False

def test_free_models() -> Dict[str, Any]:
    """测试所有免费模型"""
    results = {}
    
    for model_name in FREE_MODELS:
        try:
            logger.info(f"测试模型: {model_name}")
            model = ChatOpenAI(
                model=model_name,
                openai_api_key=OPENROUTER_API_KEY,
                openai_api_base=OPENROUTER_BASE_URL,
                temperature=0.7,
                max_tokens=100,
                timeout=10
            )
            
            result = model.invoke([HumanMessage(content="你好，请简单回复")])
            results[model_name] = {
                'success': True,
                'response': result.content[:100] + "..." if len(result.content) > 100 else result.content
            }
            logger.info(f"模型 {model_name} 测试成功")
            
        except Exception as e:
            results[model_name] = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"模型 {model_name} 测试失败: {e}")
    
    return results

def get_best_free_model() -> str:
    """获取最佳可用的免费模型"""
    results = test_free_models()
    
    # 优先选择成功的免费模型
    for model_name, result in results.items():
        if result['success']:
            logger.info(f"选择免费模型: {model_name}")
            return model_name
    
    # 如果没有成功的免费模型，尝试付费模型
    logger.warning("没有找到可用的免费模型，尝试付费模型")
    paid_results = test_paid_models()
    
    for model_name, result in paid_results.items():
        if result['success']:
            logger.info(f"选择付费模型: {model_name}")
            return model_name
    
    # 如果都没有成功的模型，返回默认免费模型
    logger.warning("没有找到任何可用模型，使用默认免费模型")
    return FREE_MODELS[0]

def test_paid_models() -> Dict[str, Any]:
    """测试所有付费模型"""
    results = {}
    
    for model_name in PAID_MODELS:
        try:
            logger.info(f"测试付费模型: {model_name}")
            model = ChatOpenAI(
                model=model_name,
                openai_api_key=OPENROUTER_API_KEY,
                openai_api_base=OPENROUTER_BASE_URL,
                temperature=0.7,
                max_tokens=100,
                timeout=10
            )
            
            result = model.invoke([HumanMessage(content="你好，请简单回复")])
            results[model_name] = {
                'success': True,
                'response': result.content[:100] + "..." if len(result.content) > 100 else result.content
            }
            logger.info(f"付费模型 {model_name} 测试成功")
            
        except Exception as e:
            results[model_name] = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"付费模型 {model_name} 测试失败: {e}")
    
    return results

if __name__ == "__main__":
    # 测试连接
    print("测试LangChain连接...")
    if test_langchain_connection():
        print("✅ LangChain连接成功")
        
        # 测试文档生成
        print("\n测试文档生成...")
        test_case_data = {
            'case_number': '2024民初001',
            'case_name': '测试案例',
            'case_type': '民事纠纷',
            'jurisdiction': '北京市朝阳区人民法院',
            'draft_person': '张律师',
            'defendant_name': '李四',
            'defendant_credit_code': '91110000123456789X',
            'defendant_address': '北京市朝阳区某某街道123号',
            'plaintiff_name': '张三',
            'plaintiff_credit_code': '91110000987654321Y',
            'plaintiff_address': '上海市浦东新区某某路456号',
            'contract_amount': 100000.00,
            'lawyer_fee': 10000.00
        }
        
        result = generate_document_with_langchain(test_case_data, "起诉状")
        if result['success']:
            print("✅ 文档生成成功")
            print(f"内容预览: {result['content'][:200]}...")
        else:
            print(f"❌ 文档生成失败: {result.get('error', '未知错误')}")
    else:
        print("❌ LangChain连接失败")
