"""
模拟AI服务模块
当DeepSeek API不可用时，提供模拟的AI响应
"""

from typing import Dict, Any, List


def mock_ai_response(prompt: str, documents: List[str] = None, templates: List[str] = None) -> Dict[str, Any]:
    """
    模拟AI响应
    
    Args:
        prompt: 用户输入的提示词
        documents: 上传的文档列表
        templates: 模板文件列表
    
    Returns:
        模拟的AI响应
    """
    
    # 根据提示词内容生成不同的模拟响应
    if "起诉状" in prompt or "起诉" in prompt:
        content = """民事起诉状

原告：张三
住所地：北京市朝阳区某某街道123号
联系电话：13800138000

被告：李四
住所地：上海市浦东新区某某路456号
联系电话：13900139000

诉讼请求：
1. 请求判令被告支付合同款人民币100,000元；
2. 请求判令被告支付逾期利息人民币5,000元；
3. 请求判令被告承担本案诉讼费用。

事实与理由：
原告与被告于2024年1月1日签订《货物买卖合同》，约定被告向原告购买货物，合同总金额为人民币100,000元，付款期限为2024年2月1日。合同签订后，原告按约履行了交货义务，但被告至今未支付合同款项。

根据《中华人民共和国民法典》相关规定，被告的行为已构成违约，应当承担相应的法律责任。

此致
某某人民法院

具状人：张三
2024年3月1日"""
    
    elif "答辩状" in prompt or "答辩" in prompt:
        content = """民事答辩状

答辩人：李四
住所地：上海市浦东新区某某路456号
联系电话：13900139000

被答辩人：张三
住所地：北京市朝阳区某某街道123号
联系电话：13800138000

答辩人就被答辩人提起的买卖合同纠纷一案，现答辩如下：

一、关于合同履行情况
答辩人认为，被答辩人提供的货物存在质量问题，不符合合同约定的质量标准。根据合同约定，被答辩人应当提供符合国家标准的合格产品，但实际交付的货物存在明显缺陷。

二、关于付款义务
由于被答辩人交付的货物存在质量问题，答辩人有权拒绝支付货款。根据《中华人民共和国民法典》相关规定，当一方当事人履行合同义务不符合约定时，对方当事人有权拒绝其相应的履行要求。

三、关于诉讼请求
被答辩人的诉讼请求缺乏事实和法律依据，请求法院驳回其全部诉讼请求。

此致
某某人民法院

答辩人：李四
2024年3月15日"""
    
    elif "代理词" in prompt or "代理" in prompt:
        content = """代理词

尊敬的审判长、审判员：

我作为原告张三的委托代理人，现就本案发表代理意见如下：

一、关于案件事实
1. 原、被告双方于2024年1月1日签订了《货物买卖合同》，该合同系双方真实意思表示，合法有效。
2. 原告已按合同约定履行了交货义务，被告应当按约支付货款。
3. 被告至今未支付货款，已构成违约。

二、关于法律适用
根据《中华人民共和国民法典》第五百七十七条之规定，当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。

三、关于诉讼请求
原告的诉讼请求有充分的事实和法律依据，请求法院支持原告的全部诉讼请求。

此致
某某人民法院

代理人：王律师
2024年3月20日"""
    
    else:
        content = f"""根据您提供的信息，我为您生成了以下法律文书：

{prompt}

请注意：
1. 以上内容为模拟生成，仅供参考
2. 实际使用时请根据具体案情进行修改
3. 建议咨询专业律师进行审核
4. 当前使用的是模拟AI服务，如需使用真实AI服务，请配置有效的DeepSeek API密钥

如需生成其他类型的法律文书，请提供更详细的要求。"""

    return {
        "success": True,
        "content": content,
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 500,
            "total_tokens": 600
        },
        "note": "当前使用模拟AI服务，请配置有效的DeepSeek API密钥以获得更好的体验"
    }


def load_template_files() -> List[str]:
    """
    加载模板文件夹中的所有模板文件
    
    Returns:
        模板文件内容列表
    """
    # 模拟模板文件内容
    templates = [
        """起诉状模板：

原告：[原告姓名]
住所地：[原告地址]
联系电话：[原告电话]

被告：[被告姓名]
住所地：[被告地址]
联系电话：[被告电话]

诉讼请求：
1. [诉讼请求1]
2. [诉讼请求2]
3. [诉讼请求3]

事实与理由：
[案件事实描述]

此致
[法院名称]

具状人：[原告姓名]
[日期]""",
        
        """答辩状模板：

答辩人：[被告姓名]
住所地：[被告地址]
联系电话：[被告电话]

被答辩人：[原告姓名]
住所地：[原告地址]
联系电话：[原告电话]

答辩人就[案件性质]一案，现答辩如下：

一、[答辩意见1]
二、[答辩意见2]
三、[答辩意见3]

此致
[法院名称]

答辩人：[被告姓名]
[日期]"""
    ]
    
    return templates


def generate_document_with_mock_ai(case_data: Dict[str, Any], document_type: str = "起诉状") -> Dict[str, Any]:
    """
    使用模拟AI生成法律文书
    
    Args:
        case_data: 案例数据
        document_type: 文书类型
    
    Returns:
        生成结果
    """
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

    # 加载模板文件
    templates = load_template_files()
    
    # 调用模拟AI生成
    result = mock_ai_response(prompt, templates=templates)
    
    return result


def generate_all_documents_with_mock_ai(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用模拟AI生成所有法律文书
    
    Args:
        case_data: 案例数据
    
    Returns:
        生成结果，包含所有文档
    """
    # 定义所有文档类型和对应的模板
    document_types = [
        {"name": "起诉状", "template": "1、起诉状（被告数量+3份）.docx"},
        {"name": "法定代表人身份证明", "template": "2、法定代表人身份证明(5份).doc"},
        {"name": "授权委托书", "template": "3、授权委托书（5份）.doc"},
        {"name": "撤销授权", "template": "4、撤销授权（3份）.doc"},
        {"name": "财产保全申请书", "template": "5、财产保全申请书（3份）.doc"},
        {"name": "续封申请书", "template": "6、续封申请书（3份)-.doc"},
        {"name": "解除财产保全申请书", "template": "7、解除财产保全申请书(3份).doc"},
        {"name": "撤诉申请书", "template": "8、撤诉申请书(3份).doc"},
        {"name": "诉前保全申请书", "template": "9、诉前保全申请书（3份）.docx"},
        {"name": "追加被告申请书", "template": "10、追加被告申请书（2份）-.doc"},
        {"name": "委托代理合同", "template": "11.（诉讼用）委托代理合同(1份).docx"}
    ]
    
    generated_documents = []
    
    for doc_type in document_types:
        try:
            # 生成单个文档
            result = generate_document_with_mock_ai(case_data, doc_type["name"])
            
            if result.get('success', False):
                generated_documents.append({
                    "document_name": doc_type["name"],
                    "template_name": doc_type["template"],
                    "content": result['content'],
                    "success": True
                })
            else:
                generated_documents.append({
                    "document_name": doc_type["name"],
                    "template_name": doc_type["template"],
                    "content": "",
                    "success": False,
                    "error": result.get('error', '生成失败')
                })
        except Exception as e:
            generated_documents.append({
                "document_name": doc_type["name"],
                "template_name": doc_type["template"],
                "content": "",
                "success": False,
                "error": str(e)
            })
    
    # 统计成功和失败的文档数量
    success_count = sum(1 for doc in generated_documents if doc['success'])
    total_count = len(generated_documents)
    
    return {
        "success": success_count > 0,
        "documents": generated_documents,
        "summary": {
            "total": total_count,
            "success": success_count,
            "failed": total_count - success_count
        }
    }


def ai_chat_with_mock_ai(message: str, uploaded_files: List[str] = None) -> Dict[str, Any]:
    """
    模拟AI对话功能，支持文档上传
    
    Args:
        message: 用户消息
        uploaded_files: 上传的文件内容列表
    
    Returns:
        模拟AI回复
    """
    # 加载模板文件
    templates = load_template_files()
    
    # 调用模拟AI对话
    result = mock_ai_response(message, documents=uploaded_files, templates=templates)
    
    return result
