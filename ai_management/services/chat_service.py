"""
AI 对话服务
"""
from typing import Dict, Any, List, Optional
from ai_management.services.ai_service import AIService


class AIChatService:
    """AI 对话服务"""
    
    def __init__(self):
        """初始化对话服务"""
        self.ai_service = AIService()
    
    def chat(
        self,
        message: str,
        context_type: Optional[str] = None,
        context_id: Optional[int] = None,
        uploaded_files: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        处理 AI 对话请求
        
        Args:
            message: 用户消息
            context_type: 上下文类型（如：case, customer）
            context_id: 上下文ID
            uploaded_files: 上传的文件列表
            user_id: 用户ID
            conversation_id: 对话ID（用于多轮对话）
            
        Returns:
            AI 响应结果
        """
        # 构建上下文
        context = {}
        if context_type and context_id:
            context = {
                "type": context_type,
                "id": context_id
            }
        
        # 调用 AI 服务
        result = self.ai_service.chat(
            message=message,
            context=context,
            uploaded_files=uploaded_files or []
        )
        
        # TODO: 保存对话历史到数据库
        # if user_id:
        #     from ai_management.models import AIChatHistory
        #     AIChatHistory.objects.create(
        #         user_id=user_id,
        #         message=message,
        #         response=result.get('response', ''),
        #         context_type=context_type,
        #         context_id=context_id,
        #         model_name=result.get('model_name')
        #     )
        
        return result

