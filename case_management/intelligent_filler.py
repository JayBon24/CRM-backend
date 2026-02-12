"""
智能填充服务模块 - 使用DeepSeek大模型智能填充内容
"""

import json
import re
from typing import Dict, List, Any
import logging
from .ai_service import deepseek_ai

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntelligentFiller:
    """智能填充服务 - 使用大模型智能填充内容"""
    
    def __init__(self):
        """初始化智能填充服务"""
        pass
    
    def fill_template(self, template_markdown: str, case_elements: Dict) -> str:
        """
        智能填充Markdown模板内容
        
        Args:
            template_markdown: 模板Markdown内容
            case_elements: 案例要素信息
            
        Returns:
            填充后的Markdown内容
        """
        try:
            # 构建提示词
            prompt = self._build_fill_prompt(template_markdown, case_elements)
            
            # 调用DeepSeek API
            result = deepseek_ai(prompt)
            
            if result.get('success', False):
                return result['content']
            else:
                logger.error(f"AI填充失败: {result.get('error', '未知错误')}")
                return template_markdown  # 返回原模板
                
        except Exception as e:
            logger.error(f"智能填充失败: {e}")
            return template_markdown  # 返回原模板
    
    def fill_xml_template(self, template_xml: str, case_elements: Dict) -> str:
        """
        智能填充XML模板内容
        
        Args:
            template_xml: 模板XML内容
            case_elements: 案例要素信息
            
        Returns:
            填充后的XML内容
        """
        try:
            # 构建提示词
            prompt = self._build_xml_fill_prompt(template_xml, case_elements)
            
            # 调用DeepSeek API
            result = deepseek_ai(prompt)
            
            if result.get('success', False):
                return result['content']
            else:
                logger.error(f"AI填充失败: {result.get('error', '未知错误')}")
                return template_xml  # 返回原模板
                
        except Exception as e:
            logger.error(f"智能填充失败: {e}")
            return template_xml  # 返回原模板
    
    def fill_structured_template(self, template_content: str, case_elements: Dict, use_xml: bool = False) -> str:
        """
        智能填充结构化模板内容（支持Markdown和XML）
        
        Args:
            template_content: 模板内容
            case_elements: 案例要素信息
            use_xml: 是否使用XML格式
            
        Returns:
            填充后的内容
        """
        try:
            if use_xml:
                return self.fill_xml_template(template_content, case_elements)
            else:
                return self.fill_template(template_content, case_elements)
                
        except Exception as e:
            logger.error(f"智能填充失败: {e}")
            return template_content  # 返回原模板
    
    def _build_fill_prompt(self, template_markdown: str, case_elements: Dict) -> str:
        """
        构建Markdown填充提示词
        
        Args:
            template_markdown: 模板Markdown内容
            case_elements: 案例要素信息
            
        Returns:
            构建的提示词
        """
        prompt = f"""
你是一个专业的法律文档处理助手。请根据提供的案例要素信息，智能填充法律文书模板。

模板内容（Markdown格式）：
```
{template_markdown}
```

案例要素信息：
{json.dumps(case_elements, ensure_ascii=False, indent=2)}

请按照以下要求处理：
1. 仔细分析模板的结构和内容
2. 根据案例要素信息，智能填充模板中的空白部分
3. 保持原有的Markdown格式和结构
4. 确保填充的内容符合法律文书的规范
5. 如果某些信息缺失，请根据上下文合理推断或标注为"待补充"
6. 对于表格内容，确保数据完整且格式正确
7. 保留所有格式标记（如<size:>、<font:>、<indent:>等）
8. 保持原有的段落结构和缩进

请直接返回填充后的Markdown内容，不要添加任何解释。
"""
        return prompt
    
    def _build_xml_fill_prompt(self, template_xml: str, case_elements: Dict) -> str:
        """
        构建XML填充提示词
        
        Args:
            template_xml: 模板XML内容
            case_elements: 案例要素信息
            
        Returns:
            构建的提示词
        """
        prompt = f"""
你是一个专业的法律文档处理助手。请根据提供的案例要素信息，智能填充法律文书模板。

模板内容（XML格式）：
```xml
{template_xml}
```

案例要素信息：
{json.dumps(case_elements, ensure_ascii=False, indent=2)}

请按照以下要求处理：
1. 仔细分析XML模板的结构和内容
2. 根据案例要素信息，智能填充模板中的空白部分
3. 保持原有的XML格式和结构
4. 确保填充的内容符合法律文书的规范
5. 如果某些信息缺失，请根据上下文合理推断或标注为"待补充"
6. 对于表格内容，确保数据完整且格式正确
7. 保持原有的段落结构和属性

请直接返回填充后的XML内容，不要添加任何解释。
"""
        return prompt
    
    def extract_case_elements_from_data(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从案例数据中提取要素信息
        
        Args:
            case_data: 案例数据
            
        Returns:
            提取的案例要素信息
        """
        elements = {}
        
        # 基本信息
        elements['案件编号'] = case_data.get('case_number', '')
        elements['案件名称'] = case_data.get('case_name', '')
        elements['案件类型'] = case_data.get('case_type', '')
        elements['管辖法院'] = case_data.get('jurisdiction', '')
        elements['拟稿人'] = case_data.get('draft_person', '')
        elements['案件描述'] = case_data.get('case_description', '')
        elements['案件状态'] = case_data.get('status', 'draft')
        
        # 原告信息
        elements['原告名称'] = case_data.get('plaintiff_name', '待填写')
        elements['原告所住地'] = case_data.get('plaintiff_address', '待填写')
        elements['原告统一社会信用代码'] = case_data.get('plaintiff_credit_code', '待填写')
        elements['原告法定代表人'] = case_data.get('plaintiff_legal_representative', '待填写')
        
        # 被告信息
        elements['被告名称'] = case_data.get('defendant_name', '待填写')
        elements['被告所住地'] = case_data.get('defendant_address', '待填写')
        elements['被告统一社会信用代码'] = case_data.get('defendant_credit_code', '待填写')
        elements['被告法定代表人'] = case_data.get('defendant_legal_representative', '待填写')
        
        # 金额信息
        elements['合同金额'] = f"{case_data.get('contract_amount', 0)}元"
        elements['律师费'] = f"{case_data.get('lawyer_fee', 0)}元"
        elements['总金额'] = f"{float(case_data.get('contract_amount', 0)) + float(case_data.get('lawyer_fee', 0))}元"
        
        # 其他信息
        elements['创建日期'] = '2024年X月X日'
        elements['被告数量'] = '1'
        
        return elements
    
    def validate_filled_content(self, original_template: str, filled_content: str) -> Dict[str, Any]:
        """
        验证填充后的内容
        
        Args:
            original_template: 原始模板内容
            filled_content: 填充后的内容
            
        Returns:
            验证结果
        """
        validation_result = {
            'is_valid': True,
            'issues': [],
            'suggestions': []
        }
        
        try:
            # 检查内容长度
            if len(filled_content) < len(original_template) * 0.5:
                validation_result['issues'].append("填充内容过短，可能不完整")
                validation_result['is_valid'] = False
            
            # 检查是否包含"待填写"等占位符
            if "待填写" in filled_content or "待补充" in filled_content:
                validation_result['suggestions'].append("内容中包含未填充的占位符")
            
            # 检查格式标记是否完整
            original_format_tags = re.findall(r'<[^>]+>', original_template)
            filled_format_tags = re.findall(r'<[^>]+>', filled_content)
            
            if len(filled_format_tags) < len(original_format_tags) * 0.8:
                validation_result['issues'].append("格式标记可能丢失")
                validation_result['is_valid'] = False
            
            # 检查表格结构
            original_tables = original_template.count('|')
            filled_tables = filled_content.count('|')
            
            if filled_tables < original_tables * 0.8:
                validation_result['issues'].append("表格结构可能不完整")
                validation_result['is_valid'] = False
            
        except Exception as e:
            logger.error(f"验证填充内容失败: {e}")
            validation_result['is_valid'] = False
            validation_result['issues'].append(f"验证过程出错: {str(e)}")
        
        return validation_result

def fill_template_with_ai(template_content: str, case_elements: Dict, use_xml: bool = False) -> str:
    """
    使用AI填充模板的便捷函数
    
    Args:
        template_content: 模板内容
        case_elements: 案例要素信息
        use_xml: 是否使用XML格式
        
    Returns:
        填充后的内容
    """
    try:
        filler = IntelligentFiller()
        return filler.fill_structured_template(template_content, case_elements, use_xml)
    except Exception as e:
        logger.error(f"AI填充模板失败: {e}")
        return template_content

def extract_and_fill_template(template_content: str, case_data: Dict[str, Any], use_xml: bool = False) -> str:
    """
    提取案例要素并填充模板的便捷函数
    
    Args:
        template_content: 模板内容
        case_data: 案例数据
        use_xml: 是否使用XML格式
        
    Returns:
        填充后的内容
    """
    try:
        filler = IntelligentFiller()
        case_elements = filler.extract_case_elements_from_data(case_data)
        return filler.fill_structured_template(template_content, case_elements, use_xml)
    except Exception as e:
        logger.error(f"提取要素并填充模板失败: {e}")
        return template_content

