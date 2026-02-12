"""
提示词构建工具
"""
from typing import Dict, Any, List, Optional


class PromptBuilder:
    """提示词构建器"""
    
    @staticmethod
    def build_chat_prompt(
        message: str,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        构建对话提示词
        
        Args:
            message: 用户消息
            context: 上下文信息
            history: 对话历史
            
        Returns:
            构建好的提示词
        """
        prompt = ""
        
        # 添加上下文信息
        if context:
            prompt += f"上下文信息：{context}\n\n"
        
        # 添加历史对话
        if history:
            prompt += "历史对话：\n"
            for h in history:
                prompt += f"用户：{h.get('user', '')}\n"
                prompt += f"助手：{h.get('assistant', '')}\n"
            prompt += "\n"
        
        # 添加当前消息
        prompt += f"用户：{message}\n助手："
        
        return prompt
    
    @staticmethod
    def build_document_prompt(
        document_type: str,
        case_data: Dict[str, Any],
        template_content: Optional[str] = None
    ) -> str:
        """
        构建文档生成提示词
        
        Args:
            document_type: 文档类型
            case_data: 案件数据
            template_content: 模板内容
            
        Returns:
            构建好的提示词
        """
        prompt = f"请根据以下信息生成{document_type}：\n\n"
        prompt += f"案件信息：{case_data}\n\n"
        
        if template_content:
            prompt += f"模板内容：\n{template_content}\n\n"
        
        prompt += "请生成完整的法律文书内容。"
        
        return prompt

