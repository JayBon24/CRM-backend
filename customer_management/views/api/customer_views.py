from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, SuccessResponse, ErrorResponse
from customer_management.models import Customer, ApprovalTask
from customer_management.serializers import CustomerSerializer
from customer_management.mixins import RoleBasedFilterMixin
from customer_management.services.customer_service import CustomerService
from customer_management.services.approval_service import ApprovalService
from dvadmin.system.models import Users


class CustomerViewSet(RoleBasedFilterMixin, CustomModelViewSet):
    """
    客户管理ViewSet
    
    自动根据用户角色过滤数据范围：
    - HQ（总所管理）：查看全所数据
    - BRANCH（分所管理）：查看本分所数据
    - TEAM（团队管理）：查看本团队数据
    - SALES（销售）：仅查看本人负责的客户
    """
    queryset = Customer.objects.filter(is_deleted=False)
    serializer_class = CustomerSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["name", "credit_code", "status", "client_grade", "client_category"]
    search_fields = ["name", "contact_person", "contact_phone", "credit_code"]
    ordering_fields = ["id", "name", "create_datetime"]
    ordering = ["-id"]

    permission_classes = []
    extra_filter_class = []
    
    # 只返回JSON，不渲染HTML模板
    from rest_framework.renderers import JSONRenderer
    renderer_classes = [JSONRenderer]
    
    @action(detail=False, methods=['get'], url_path='public-pool')
    def public_pool(self, request):
        """
        获取公海客户列表
        GET /admin-api/customer/customers/public-pool
        """
        try:
            # 获取查询参数
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('pageSize', 20))
            keyword = request.query_params.get('keyword')
            grade = request.query_params.get('grade')
            
            # 查询公海客户
            queryset = Customer.objects.filter(
                is_deleted=False,
                status=Customer.STATUS_PUBLIC_POOL
            )
            
            # 关键词搜索
            if keyword:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(name__icontains=keyword) | 
                    Q(contact_phone__icontains=keyword) |
                    Q(contact_person__icontains=keyword)
                )
            
            # 客户等级筛选
            if grade:
                queryset = queryset.filter(client_grade=grade)
            
            # 排序
            queryset = queryset.order_by('-create_datetime')
            
            # 分页
            total = queryset.count()
            start = (page - 1) * page_size
            end = start + page_size
            customers = queryset[start:end]
            
            # 序列化
            rows = []
            for customer in customers:
                rows.append({
                    'id': customer.id,
                    'name': customer.name,
                    'contact_person': customer.contact_person,
                    'contact_phone': customer.contact_phone,
                    'address': customer.address,
                    'client_grade': customer.client_grade,
                    'source_channel': customer.source_channel,
                    'remark': customer.remark,
                    'create_time': customer.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if customer.create_datetime else None,
                })
            
            return DetailResponse(data={
                'rows': rows,
                'total': total,
                'page': page,
                'pageSize': page_size
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ErrorResponse(msg=f"获取公海客户列表失败: {str(e)}")
    
    @action(detail=True, methods=['post'])
    def claim(self, request, pk=None):
        """
        申领公海客户
        POST /admin-api/customer/customers/{id}/claim
        """
        try:
            user = request.user
            
            # 权限检查：只有 SALES 和 TEAM 可以申领
            role_level = getattr(user, 'role_level', None)
            if role_level in ['HQ', 'BRANCH']:
                return ErrorResponse(msg="管理角色不能申领客户，请使用分配功能")
            
            customer = self.get_object()
            
            # 检查客户状态
            if customer.status != Customer.STATUS_PUBLIC_POOL:
                return ErrorResponse(msg="只能申领公海客户")
            
            # 创建审批任务
            reason = request.data.get('reason', '')
            related_data = {
                'customer_id': str(customer.id),
                'name': customer.name,
                'reason': reason
            }
            
            task = ApprovalService.create_task(
                applicant=user,
                approval_type='LEAD_CLAIM',
                customer=customer,
                related_data=related_data
            )
            
            return DetailResponse(data={
                'approval_id': task.id,
                'status': 'pending'
            }, msg='申领成功，等待审批')
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ErrorResponse(msg=f"申领客户失败: {str(e)}")
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """
        分配客户（管理权限）
        POST /admin-api/customer/customers/{id}/assign
        """
        try:
            user = request.user
            
            # 权限检查：只有管理角色可以分配
            role_level = getattr(user, 'role_level', None)
            if role_level not in ['HQ', 'BRANCH', 'TEAM']:
                return ErrorResponse(msg="只有管理角色可以分配客户")
            
            customer = self.get_object()
            
            handler_ids = request.data.get("handler_ids") or request.data.get("owner_user_ids")
            owner_user_id = request.data.get('owner_user_id')
            if not handler_ids and not owner_user_id:
                return ErrorResponse(msg="请指定经办人")
            if handler_ids:
                if isinstance(handler_ids, str):
                    handler_ids = [item for item in handler_ids.split(",") if str(item).strip()]
                if not isinstance(handler_ids, (list, tuple)):
                    handler_ids = [handler_ids]
                handler_ids = [int(x) for x in handler_ids if str(x).isdigit()]
            if not handler_ids and owner_user_id:
                handler_ids = [owner_user_id]

            try:
                owner_user = Users.objects.get(id=handler_ids[0])
            except Users.DoesNotExist:
                return ErrorResponse(msg="经办人不存在")

            CustomerService.set_handlers(customer, handler_ids, primary_id=handler_ids[0], mode="replace")
            
            return DetailResponse(data={
                'id': customer.id,
                'owner_user_id': customer.owner_user_id,
                'owner_user_name': customer.owner_user_name,
                'status': customer.status
            }, msg='分配成功')
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ErrorResponse(msg=f"分配客户失败: {str(e)}")
    
    @action(detail=True, methods=['post'])
    def recycle(self, request, pk=None):
        """
        回收客户到公海
        POST /admin-api/customer/customers/{id}/recycle
        """
        try:
            user = request.user
            
            # 权限检查：只有管理角色可以回收
            role_level = getattr(user, 'role_level', None)
            if role_level not in ['HQ', 'BRANCH', 'TEAM']:
                return ErrorResponse(msg="只有管理角色可以回收客户")
            
            customer = self.get_object()
            
            # 检查客户状态
            if customer.status == Customer.STATUS_PUBLIC_POOL:
                return ErrorResponse(msg="客户已在公海中")
            
            reason = request.data.get('reason', '')
            
            # 回收到公海
            customer.status = Customer.STATUS_PUBLIC_POOL
            customer.sales_stage = Customer.SALES_STAGE_PUBLIC
            customer.owner_user = None
            customer.owner_user_name = None
            try:
                customer.handlers.clear()
            except Exception:
                pass
            customer.remark = f"{customer.remark or ''}\n[回收原因: {reason}]" if reason else customer.remark
            customer.save()
            
            return DetailResponse(data={
                'id': customer.id,
                'status': customer.status
            }, msg='回收成功')
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ErrorResponse(msg=f"回收客户失败: {str(e)}")
