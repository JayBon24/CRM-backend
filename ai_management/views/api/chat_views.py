"""
AI 对话视图（控制器）
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.request_util import get_request_user
from ai_management.serializers import AIChatSerializer, AIChatResponseSerializer
from ai_management.services.chat_service import AIChatService


class AIChatViewSet(CustomModelViewSet):
    """AI 对话视图集"""
    
    # 添加空的 queryset 以满足 DRF 要求（此 ViewSet 不使用数据库模型）
    queryset = None
    permission_classes = []
    
    # 禁用 Swagger 文档生成（避免因无 queryset 导致错误）
    swagger_schema = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_service = AIChatService()
    
    @action(detail=False, methods=['post'], url_path='chat')
    def chat(self, request):
        """
        AI 对话接口
        
        POST /api/ai/chat/chat/
        """
        serializer = AIChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            message = serializer.validated_data.get('message')
            context_type = serializer.validated_data.get('context_type')
            context_id = serializer.validated_data.get('context_id')
            uploaded_files = serializer.validated_data.get('uploaded_files', [])
            conversation_id = serializer.validated_data.get('conversation_id')
            
            # 获取当前用户
            user = get_request_user(request)
            user_id = user.id if user and hasattr(user, 'id') else None
            
            # 调用服务层
            result = self.chat_service.chat(
                message=message,
                context_type=context_type,
                context_id=context_id,
                uploaded_files=uploaded_files,
                user_id=user_id,
                conversation_id=conversation_id
            )
            
            return DetailResponse(data=result)
            
        except Exception as e:
            return ErrorResponse(msg=f"AI对话失败: {str(e)}")
    
    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        """
        获取对话历史
        
        GET /api/ai/chat/history/
        """
        try:
            user = get_request_user(request)
            user_id = user.id if user and hasattr(user, 'id') else None
            
            if not user_id:
                return ErrorResponse(msg="请先登录")
            
            # TODO: 从数据库获取对话历史
            # from ai_management.models import AIChatHistory
            # histories = AIChatHistory.objects.filter(user_id=user_id).order_by('-create_datetime')[:20]
            # data = [{
            #     'id': h.id,
            #     'message': h.message,
            #     'response': h.response,
            #     'create_datetime': h.create_datetime,
            # } for h in histories]
            
            return DetailResponse(data=[])
            
        except Exception as e:
            return ErrorResponse(msg=f"获取对话历史失败: {str(e)}")

