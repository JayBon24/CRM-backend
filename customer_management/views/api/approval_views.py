"""
审批管理ViewSet
"""
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import SuccessResponse, ErrorResponse, DetailResponse
from customer_management.models.approval import ApprovalTask, ApprovalHistory
from customer_management.serializers.admin import ApprovalTaskSerializer, ApprovalHistorySerializer
from customer_management.services.approval_service import ApprovalService


class ApprovalViewSet(CustomModelViewSet):
    """
    审批管理ViewSet
    
    提供审批任务的查询、审批、驳回等功能
    """
    queryset = ApprovalTask.objects.all()
    serializer_class = ApprovalTaskSerializer
    permission_classes = [IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['approval_type', 'status', 'applicant']
    search_fields = ['related_customer__name']
    ordering_fields = ['create_datetime', 'status']
    ordering = ['-create_datetime']
    
    # 只返回JSON，不渲染HTML模板
    from rest_framework.renderers import JSONRenderer
    renderer_classes = [JSONRenderer]
    
    def get_queryset(self):
        """根据用户角色和tab参数过滤审批数据"""
        user = self.request.user
        queryset = ApprovalTask.objects.select_related(
            'applicant', 'related_customer', 'creator'
        ).prefetch_related('histories')
        
        # 如果用户未认证，返回空查询集
        if not user or not user.is_authenticated:
            return queryset.none()
        
        # 根据tab参数过滤
        tab = self.request.query_params.get('tab', 'pending')
        
        if tab == 'pending':
            # 待我审批：当前审批角色匹配用户角色，且状态为pending
            user_role = getattr(user, 'role_level', None)
            if user_role:
                queryset = queryset.filter(
                    current_approver_role=user_role,
                    status='pending'
                )
            else:
                return queryset.none()
        elif tab == 'my':
            # 我发起的：申请人是当前用户
            queryset = queryset.filter(applicant=user)
        elif tab == 'processed':
            # 已处理：在审批历史中有当前用户的审批记录
            queryset = queryset.filter(
                histories__approver=user
            ).distinct()
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """通过审批"""
        approval = self.get_object()
        comment = request.data.get('comment', '')
        
        if approval.status != 'pending':
            return ErrorResponse(msg="该审批已处理")
        
        # 检查当前用户是否有权限审批
        user_role = getattr(request.user, 'role_level', None)
        if approval.current_approver_role != user_role:
            return ErrorResponse(msg="您没有权限审批此任务")
        
        try:
            # 使用审批服务处理审批
            result = ApprovalService.approve_task(
                task=approval,
                approver=request.user,
                comment=comment
            )
            
            if result['success']:
                return SuccessResponse(
                    data=ApprovalTaskSerializer(approval).data,
                    msg=result['message']
                )
            else:
                return ErrorResponse(msg=result['message'])
                
        except Exception as e:
            return ErrorResponse(msg=f"审批失败: {str(e)}")
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """驳回审批"""
        approval = self.get_object()
        comment = request.data.get('comment', '')
        
        if approval.status != 'pending':
            return ErrorResponse(msg="该审批已处理")
        
        if not comment:
            return ErrorResponse(msg="驳回时必须填写原因")
        
        # 检查当前用户是否有权限审批
        user_role = getattr(request.user, 'role_level', None)
        if approval.current_approver_role != user_role:
            return ErrorResponse(msg="您没有权限审批此任务")
        
        try:
            # 使用审批服务处理驳回
            result = ApprovalService.reject_task(
                task=approval,
                approver=request.user,
                comment=comment
            )
            
            if result['success']:
                return SuccessResponse(
                    data=ApprovalTaskSerializer(approval).data,
                    msg=result['message']
                )
            else:
                return ErrorResponse(msg=result['message'])
                
        except Exception as e:
            return ErrorResponse(msg=f"驳回失败: {str(e)}")
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """获取审批历史"""
        approval = self.get_object()
        
        histories = ApprovalHistory.objects.filter(
            approval_task=approval
        ).select_related('approver').order_by('create_datetime')
        
        serializer = ApprovalHistorySerializer(histories, many=True)
        
        return SuccessResponse(data=serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取审批统计"""
        user = request.user
        user_role = getattr(user, 'role_level', None)
        
        # 待我审批数量
        pending_count = ApprovalTask.objects.filter(
            current_approver_role=user_role,
            status='pending'
        ).count()
        
        # 我发起的数量
        my_count = ApprovalTask.objects.filter(
            applicant=user
        ).count()
        
        # 已处理数量
        processed_count = ApprovalTask.objects.filter(
            histories__approver=user
        ).distinct().count()
        
        return SuccessResponse(data={
            'pending_count': pending_count,
            'my_count': my_count,
            'processed_count': processed_count
        })
