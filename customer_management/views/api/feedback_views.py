"""
用户反馈ViewSet
"""
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import SuccessResponse, ErrorResponse
from customer_management.models.feedback import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    """反馈序列化器"""
    user_name = serializers.CharField(source='user.name', read_only=True)
    handler_name = serializers.CharField(source='handler.name', read_only=True)
    
    class Meta:
        model = Feedback
        fields = '__all__'
        read_only_fields = ['user', 'handler', 'handled_at']


class FeedbackViewSet(CustomModelViewSet):
    """
    用户反馈ViewSet
    
    提供反馈的创建、查询、处理等功能
    """
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type', 'status', 'priority']
    search_fields = ['title', 'content']
    ordering_fields = ['create_datetime', 'priority', 'status']
    
    # 只返回JSON，不渲染HTML模板
    from rest_framework.renderers import JSONRenderer
    renderer_classes = [JSONRenderer]
    ordering = ['-create_datetime']
    
    def get_queryset(self):
        """根据用户角色过滤反馈数据"""
        user = self.request.user
        queryset = Feedback.objects.select_related('user', 'handler')
        
        # 普通用户只能看到自己的反馈
        # 管理员可以看到所有反馈
        if not user.is_superuser:
            user_role = getattr(user, 'role_level', None)
            if user_role not in ['HQ', 'BRANCH']:
                queryset = queryset.filter(user=user)
        
        return queryset
    
    def perform_create(self, serializer):
        """创建反馈时自动设置用户"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def handle(self, request, pk=None):
        """处理反馈"""
        feedback = self.get_object()
        
        # 检查权限：只有管理员可以处理反馈
        user_role = getattr(request.user, 'role_level', None)
        if user_role not in ['HQ', 'BRANCH'] and not request.user.is_superuser:
            return ErrorResponse(msg="您没有权限处理反馈")
        
        reply = request.data.get('reply', '')
        status = request.data.get('status', 'resolved')
        
        if not reply:
            return ErrorResponse(msg="请填写回复内容")
        
        feedback.reply = reply
        feedback.status = status
        feedback.handler = request.user
        feedback.handled_at = timezone.now()
        feedback.save()
        
        return SuccessResponse(
            data=FeedbackSerializer(feedback).data,
            msg="反馈处理成功"
        )
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """关闭反馈"""
        feedback = self.get_object()
        
        # 用户可以关闭自己的反馈
        if feedback.user != request.user:
            user_role = getattr(request.user, 'role_level', None)
            if user_role not in ['HQ', 'BRANCH'] and not request.user.is_superuser:
                return ErrorResponse(msg="您没有权限关闭此反馈")
        
        feedback.status = 'closed'
        feedback.save()
        
        return SuccessResponse(msg="反馈已关闭")
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取反馈统计"""
        user = request.user
        
        # 根据用户角色统计
        if user.is_superuser or getattr(user, 'role_level', None) in ['HQ', 'BRANCH']:
            # 管理员看所有反馈统计
            queryset = Feedback.objects.all()
        else:
            # 普通用户看自己的反馈统计
            queryset = Feedback.objects.filter(user=user)
        
        # 按状态统计
        pending_count = queryset.filter(status='pending').count()
        processing_count = queryset.filter(status='processing').count()
        resolved_count = queryset.filter(status='resolved').count()
        closed_count = queryset.filter(status='closed').count()
        
        # 按类型统计
        bug_count = queryset.filter(type='bug').count()
        feature_count = queryset.filter(type='feature').count()
        improvement_count = queryset.filter(type='improvement').count()
        other_count = queryset.filter(type='other').count()
        
        return SuccessResponse(data={
            'by_status': {
                'pending': pending_count,
                'processing': processing_count,
                'resolved': resolved_count,
                'closed': closed_count,
            },
            'by_type': {
                'bug': bug_count,
                'feature': feature_count,
                'improvement': improvement_count,
                'other': other_count,
            },
            'total': queryset.count()
        })
