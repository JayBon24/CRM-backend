import re
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from dvadmin.system.models import Users, Dept
from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.import_export import import_to_data, get_excel_header
from customer_management.models import Customer, ApprovalTask
from customer_management.serializers import CustomerSerializer, CustomerImportTemplateSerializer, ApprovalTaskSerializer
from customer_management.services.customer_service import CustomerService
from customer_management.services.approval_service import ApprovalService
from case_management.models import CaseManagement


class AdminCustomerViewSet(CustomModelViewSet):
    queryset = Customer.objects.filter(is_deleted=False)
    serializer_class = CustomerSerializer
    import_serializer_class = CustomerImportTemplateSerializer  # 模板导出带案件名/编号/状态且状态为中文
    export_serializer_class = CustomerSerializer
    export_field_label = {
        "name": "客户名称",
        "contact_person": "联系人",
        "contact_phone": "联系电话",
        "contact_email": "联系邮箱",
        "address": "地址",
        "client_grade": "客户等级",
        "source_channel": "来源渠道",
        "status": "客户状态",
        "sales_stage": "销售阶段",
        "handler_names": "经办人",
        "owner_user_name": "经办人(主)",
        "collection_category": "催收类别",
        "recycle_risk_level": "回收风险等级",
    }
    import_field_dict = {
        "name": "客户名称",
        "contact_person": "联系人",
        "contact_phone": "联系电话",
        "contact_email": "联系邮箱",
        "address": "地址",
        "client_grade": {
            "title": "客户等级",
            "choices": {"data": {"A": "A", "B": "B", "C": "C", "D": "D"}},
        },
        "source_channel": {
            "title": "来源渠道",
            "choices": {
                "data": {
                    "电话来访": "电话来访",
                    "网络咨询": "网络咨询",
                    "朋友推荐": "朋友推荐",
                    "老客户介绍": "老客户介绍",
                    "展会活动": "展会活动",
                    "其他": "其他",
                }
            },
        },
        "status": {
            "title": "客户状态",
            "choices": {
                "data": {
                    "公海": Customer.STATUS_PUBLIC_POOL,
                    "商机": Customer.STATUS_FOLLOW_UP,
                    "跟进": Customer.STATUS_FOLLOW_UP,
                    "交案": Customer.STATUS_CASE,
                    "回款": Customer.STATUS_PAYMENT,
                    "赢单": Customer.STATUS_WON,
                }
            },
        },
        "case_name": "案件名称（交案/回款/赢单必填）",
        "case_number": "案件编号（可选，若不填将自动生成）",
        "case_stage": {
            "title": "案件阶段",
            "choices": {
                "data": {
                    "交案": CaseManagement.SALES_STAGE_CASE,
                    "回款": CaseManagement.SALES_STAGE_PAYMENT,
                    "赢单": CaseManagement.SALES_STAGE_WON,
                    "商机": CaseManagement.SALES_STAGE_BLANK,
                    "跟进": CaseManagement.SALES_STAGE_MEETING,
                    "公海": CaseManagement.SALES_STAGE_PUBLIC,
                }
            },
        },
        "owner_user": {
            "title": "经办人（多个用逗号/分号分隔）",
            "display": "owner_user_names",
            "choices": {"queryset": Users.objects.filter(is_active=True), "values_name": "name"},
        },
    }

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["name", "credit_code", "status", "sales_stage", "owner_user", "handlers"]
    search_fields = ["name", "contact_person", "contact_phone", "credit_code"]
    ordering_fields = ["id", "name"]
    ordering = ["-id"]

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return queryset.none()
        # 角色层级 HQ 或 数据范围 全所(HQ) 均视为全所，可见全部客户
        if getattr(user, "role_level", None) == "HQ" or getattr(user, "org_scope", None) == "HQ":
            return queryset
        if user.role_level == "BRANCH":
            # 优先使用 branch_id，没有则使用 dept_id（与 miniapp/crm 视图保持一致）
            branch_id = getattr(user, 'branch_id', None) or user.dept_id
            if branch_id:
                return queryset.filter(branch_id=branch_id)
            return queryset.none()
        if user.role_level == "TEAM":
            # 优先使用 team_id，没有则使用 dept_id（与 miniapp/crm 视图保持一致）
            team_id = getattr(user, 'team_id', None) or user.dept_id
            if team_id:
                return queryset.filter(team_id=team_id)
            return queryset.none()
        return queryset.filter(handlers=user)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        customer = self.get_object()
        handler_ids = request.data.get("handler_ids") or request.data.get("owner_user_ids")
        owner_id = request.data.get("owner_user_id")
        if not handler_ids and not owner_id:
            return Response({"detail": "handler_ids or owner_user_id required"}, status=status.HTTP_400_BAD_REQUEST)
        if handler_ids:
            if isinstance(handler_ids, str):
                handler_ids = [item for item in handler_ids.split(",") if str(item).strip()]
            if not isinstance(handler_ids, (list, tuple)):
                handler_ids = [handler_ids]
            handler_ids = [int(x) for x in handler_ids if str(x).isdigit()]
        if not handler_ids and owner_id:
            handler_ids = [owner_id]
        if not handler_ids:
            return Response({"detail": "handler_ids required"}, status=status.HTTP_400_BAD_REQUEST)

        owner_user = Users.objects.filter(id=handler_ids[0]).first()
        if not owner_user:
            return Response({"detail": "owner user not found"}, status=status.HTTP_404_NOT_FOUND)

        CustomerService.set_handlers(customer, handler_ids, primary_id=handler_ids[0], mode="replace")
        serializer = self.get_serializer(customer)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def claim(self, request, pk=None):
        customer = self.get_object()
        task = ApprovalService.create_task(
            applicant=request.user,
            approval_type="LEAD_CLAIM",
            customer=customer,
            related_data={"requested_owner_id": request.user.id},
        )
        serializer = ApprovalTaskSerializer(task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        customer = self.get_object()
        target_user_ids = request.data.get("to_owner_ids") or request.data.get("to_user_id")
        if not target_user_ids:
            return Response({"detail": "to_owner_ids required"}, status=status.HTTP_400_BAD_REQUEST)
        if isinstance(target_user_ids, str):
            target_user_ids = [item for item in target_user_ids.split(",") if str(item).strip()]
        if not isinstance(target_user_ids, (list, tuple)):
            target_user_ids = [target_user_ids]
        target_user_ids = [int(x) for x in target_user_ids if str(x).isdigit()]
        if not target_user_ids:
            return Response({"detail": "to_owner_ids required"}, status=status.HTTP_400_BAD_REQUEST)

        target_users = list(Users.objects.filter(id__in=target_user_ids))
        if not target_users:
            return Response({"detail": "target user not found"}, status=status.HTTP_404_NOT_FOUND)

        task = ApprovalService.create_task(
            applicant=request.user,
            approval_type="HANDOVER",
            customer=customer,
            related_data={"to_owner_ids": target_user_ids},
        )
        serializer = ApprovalTaskSerializer(task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        customer = self.get_object()
        status_value = request.data.get("status")
        if status_value not in dict(Customer.STATUS_CHOICES):
            return Response({"detail": "invalid status"}, status=status.HTTP_400_BAD_REQUEST)
        CustomerService.update_status(customer, status_value)
        serializer = self.get_serializer(customer)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        status_counts = {key: 0 for key, _ in Customer.STATUS_CHOICES}
        stage_counts = {key: 0 for key, _ in Customer.SALES_STAGE_CHOICES}
        for customer in queryset:
            status_counts[customer.status] += 1
            stage_counts[customer.sales_stage] += 1
        return Response({"status_counts": status_counts, "sales_stage_counts": stage_counts})

    @action(detail=False, methods=["post"])
    def batch_assign(self, request):
        """批量分配经办人"""
        customer_ids = request.data.get("customer_ids", [])
        handler_ids = request.data.get("handler_ids") or request.data.get("owner_user_ids")
        owner_user_id = request.data.get("owner_user_id")

        if not customer_ids:
            return Response({"detail": "customer_ids required"}, status=status.HTTP_400_BAD_REQUEST)
        if not handler_ids and not owner_user_id:
            return Response({"detail": "handler_ids or owner_user_id required"}, status=status.HTTP_400_BAD_REQUEST)
        if handler_ids:
            if isinstance(handler_ids, str):
                handler_ids = [item for item in handler_ids.split(",") if str(item).strip()]
            if not isinstance(handler_ids, (list, tuple)):
                handler_ids = [handler_ids]
            handler_ids = [int(x) for x in handler_ids if str(x).isdigit()]
        if not handler_ids and owner_user_id:
            handler_ids = [owner_user_id]
        if not handler_ids:
            return Response({"detail": "handler_ids required"}, status=status.HTTP_400_BAD_REQUEST)

        owner_user = Users.objects.filter(id=handler_ids[0]).first()
        if not owner_user:
            return Response({"detail": "owner user not found"}, status=status.HTTP_404_NOT_FOUND)

        customers = Customer.objects.filter(id__in=customer_ids, is_deleted=False)
        count = 0
        for customer in customers:
            CustomerService.set_handlers(customer, handler_ids, primary_id=handler_ids[0], mode="replace")
            count += 1

        return Response({
            "detail": f"Successfully assigned {count} customers",
            "count": count
        })

    @action(detail=False, methods=["post"])
    def batch_delete(self, request):
        """批量删除客户"""
        customer_ids = request.data.get("customer_ids", [])
        
        if not customer_ids:
            return Response({"detail": "customer_ids required"}, status=status.HTTP_400_BAD_REQUEST)
        
        count = Customer.objects.filter(
            id__in=customer_ids, 
            is_deleted=False
        ).update(is_deleted=True)
        
        return Response({
            "detail": f"Successfully deleted {count} customers",
            "count": count
        })

    @action(detail=False, methods=["post"])
    def batch_export(self, request):
        """批量导出客户"""
        customer_ids = request.data.get("customer_ids", [])
        
        if not customer_ids:
            # 如果没有指定ID，导出当前筛选结果
            customers = self.filter_queryset(self.get_queryset())
        else:
            customers = Customer.objects.filter(
                id__in=customer_ids, 
                is_deleted=False
            )
        
        serializer = self.get_serializer(customers, many=True)
        
        return Response({
            "detail": "Export data generated",
            "count": customers.count(),
            "data": serializer.data
        })

    @action(detail=False, methods=["post"])
    def batch_claim(self, request):
        """批量申领客户"""
        customer_ids = request.data.get("customer_ids", [])
        
        if not customer_ids:
            return Response({"detail": "customer_ids required"}, status=status.HTTP_400_BAD_REQUEST)
        
        tasks = []
        for customer_id in customer_ids:
            customer = Customer.objects.filter(
                id=customer_id, 
                is_deleted=False,
                status="PUBLIC_POOL"
            ).first()
            
            if customer:
                task = ApprovalService.create_task(
                    applicant=request.user,
                    approval_type="LEAD_CLAIM",
                    customer=customer,
                    related_data={"requested_owner_id": request.user.id},
                )
                tasks.append(task)
        
        return Response({
            "detail": f"Created {len(tasks)} approval tasks",
            "count": len(tasks),
            "tasks": ApprovalTaskSerializer(tasks, many=True).data
        }, status=status.HTTP_201_CREATED)

    @action(methods=["get", "post"], detail=False)
    @transaction.atomic
    def import_data(self, request, *args, **kwargs):
        """
        自定义导入：支持客户基础信息 + 案件阶段（交案/回款/赢单需要填写案件）
        """
        # GET 仍然复用父类模板导出能力
        if request.method == "GET":
            # 动态构建经办人下拉，附带层级路径
            def build_dept_path(dept_obj: Dept):
                names = []
                current = dept_obj
                while current:
                    names.append(current.name)
                    current = current.parent
                return "/".join(reversed(names))

            user_choices = {}
            for user in Users.objects.filter(is_active=True).select_related("dept"):
                dept_path = build_dept_path(user.dept) if hasattr(user, "dept") and user.dept else "未分组"
                label = f"{dept_path} - {user.name or user.username or user.id}"
                user_choices[label] = user.id

            self.import_field_dict["owner_user"] = {
                "title": "经办人（可多选，多个用逗号/分号分隔；或选层级-姓名）",
                "display": "owner_user_names",
                "choices": {"data": user_choices},
            }
            return super().import_data(request, *args, **kwargs)

        queryset = self.filter_queryset(self.get_queryset())
        # 获取多对多字段
        m2m_fields = [
            ele.name
            for ele in queryset.model._meta.get_fields()
            if hasattr(ele, "many_to_many") and ele.many_to_many is True
        ]
        file_url = request.data.get("url")
        import_field_dict = {"id": "更新主键(勿改)", **self.import_field_dict}
        data = import_to_data(file_url, import_field_dict, m2m_fields)

        def _is_update_template(url: str) -> bool:
            if not url:
                return False
            try:
                header = get_excel_header(url)
                return bool(header and "更新主键(勿改)" in header)
            except Exception:
                return False

        is_update_template = _is_update_template(file_url)
        delete_missing = bool(request.data.get("delete_missing"))
        if delete_missing and not is_update_template:
            raise ValidationError("删除未在 Excel 中的账号仅支持批量更新模板")

        created_count = 0
        updated_count = 0
        keep_ids = set()

        # 映射案源阶段到状态
        stage_status_map = {
            CaseManagement.SALES_STAGE_CASE: CaseManagement.STATUS_CASE,
            CaseManagement.SALES_STAGE_PAYMENT: CaseManagement.STATUS_PAYMENT,
            CaseManagement.SALES_STAGE_WON: CaseManagement.STATUS_WON,
            CaseManagement.SALES_STAGE_MEETING: CaseManagement.STATUS_FOLLOW_UP,
            CaseManagement.SALES_STAGE_BLANK: CaseManagement.STATUS_FOLLOW_UP,
            CaseManagement.SALES_STAGE_PUBLIC: CaseManagement.STATUS_PUBLIC_POOL,
        }

        update_mode = is_update_template or delete_missing or any(ele.get("id") for ele in data)

        def _is_blank(value) -> bool:
            if value is None:
                return True
            if isinstance(value, str):
                return value.strip() == ""
            return False

        def _to_clean_text(value) -> str:
            if value is None:
                return ""
            if isinstance(value, float):
                # Excel 数字单元格可能是 13800138000.0
                if value.is_integer():
                    return str(int(value))
                return str(value).strip()
            if isinstance(value, int):
                return str(value)
            return str(value).strip()

        def _normalize_name(value) -> str:
            return _to_clean_text(value).strip()

        def _normalize_phone(value) -> str:
            text = _to_clean_text(value)
            # 仅保留数字，避免空格/短横线等导致匹配失败
            text = re.sub(r"\\D", "", text)
            return text

        def _parse_int(value):
            text = _to_clean_text(value)
            return int(text) if text.isdigit() else None

        # 预取一次用户，避免经办人 N+1
        active_users = list(Users.objects.filter(is_active=True).values("id", "name", "username"))
        user_by_id = {str(u["id"]): u for u in active_users}
        user_by_name = {}
        user_by_username = {}
        for u in active_users:
            if u.get("name"):
                user_by_name[str(u["name"]).strip()] = u
            if u.get("username"):
                user_by_username[str(u["username"]).strip()] = u

        def _resolve_user_id(token: str):
            if not token:
                return None
            token = token.strip()
            if not token:
                return None
            if token.isdigit():
                u = user_by_id.get(token)
                return u["id"] if u else None
            if " - " in token:
                token = token.split(" - ", 1)[1].strip()
            u = user_by_name.get(token) or user_by_username.get(token)
            return u["id"] if u else None

        # 预取客户：id -> instance、(name, phone) -> [instance...]
        id_values = [_parse_int(ele.get("id")) for ele in data]
        id_values = [v for v in id_values if v]
        customer_by_id = {}
        if id_values:
            for c in queryset.filter(id__in=list(set(id_values))):
                customer_by_id[c.id] = c

        pair_candidates = []
        if update_mode:
            for ele in data:
                if _parse_int(ele.get("id")):
                    continue
                name = _normalize_name(ele.get("name"))
                phone = _normalize_phone(ele.get("contact_phone"))
                if name and phone:
                    pair_candidates.append((name, phone))

        customer_by_pair = {}
        if pair_candidates:
            names = list({n for n, _ in pair_candidates})
            phones = list({p for _, p in pair_candidates})
            for c in queryset.filter(name__in=names, contact_phone__in=phones).only("id", "name", "contact_phone"):
                key = (_normalize_name(c.name), _normalize_phone(c.contact_phone))
                customer_by_pair.setdefault(key, []).append(c)

        for row_index, ele in enumerate(data, start=2):
            case_name = _to_clean_text(ele.pop("case_name", ""))
            case_number_input = _to_clean_text(ele.pop("case_number", ""))
            raw_case_stage = _to_clean_text(ele.pop("case_stage", ""))
            case_stage = raw_case_stage or ""
            # 解析经办人：支持多值（逗号/分号）、“层级路径 - 姓名”、纯数字ID、或姓名/用户名
            owner_raw = ele.get("owner_user")
            handler_ids = []
            if owner_raw:
                owner_text = _to_clean_text(owner_raw)
                parts = [p.strip() for p in re.split(r"[，,；;、]+", owner_text) if str(p).strip()]
                if not parts and owner_text.strip():
                    parts = [owner_text.strip()]
                for item in parts:
                    uid = _resolve_user_id(item)
                    if uid:
                        handler_ids.append(uid)
                handler_ids = list(dict.fromkeys(handler_ids))

            if handler_ids:
                ele["owner_user"] = handler_ids[0]
                primary_user = user_by_id.get(str(handler_ids[0]))
                ele["owner_user_name"] = (
                    (primary_user.get("name") or primary_user.get("username")) if primary_user else None
                )
            else:
                ele["owner_user"] = None
                ele["owner_user_name"] = None
            raw_status_text = _to_clean_text(ele.get("status"))
            cn_status_map = {
                "公海": Customer.STATUS_PUBLIC_POOL,
                "商机": Customer.STATUS_FOLLOW_UP,
                "跟进": Customer.STATUS_FOLLOW_UP,
                "交案": Customer.STATUS_CASE,
                "回款": Customer.STATUS_PAYMENT,
                "赢单": Customer.STATUS_WON,
            }
            status_value = cn_status_map.get(raw_status_text, raw_status_text)

            # 如果传中文，做一次兼容映射
            cn_stage_map = {
                "交案": CaseManagement.SALES_STAGE_CASE,
                "回款": CaseManagement.SALES_STAGE_PAYMENT,
                "赢单": CaseManagement.SALES_STAGE_WON,
                "商机": CaseManagement.SALES_STAGE_BLANK,
                "跟进": CaseManagement.SALES_STAGE_MEETING,
                "公海": CaseManagement.SALES_STAGE_PUBLIC,
            }
            if case_stage in cn_stage_map:
                case_stage = cn_stage_map[case_stage]
            # 如果未填写案件阶段，但状态是交案/回款/赢单，则同步
            status_to_stage = {
                Customer.STATUS_CASE: CaseManagement.SALES_STAGE_CASE,
                Customer.STATUS_PAYMENT: CaseManagement.SALES_STAGE_PAYMENT,
                Customer.STATUS_WON: CaseManagement.SALES_STAGE_WON,
            }
            if not case_stage and status_value in status_to_stage:
                case_stage = status_to_stage[status_value]

            # 规则：
            # - 无案件时（未填案件阶段）：客户状态仅允许 公海/跟进/商机；并根据客户状态映射销售阶段
            # - 有案件时（填了案件阶段）：优先使用案件阶段，客户状态同步为对应的案件状态
            if not case_stage:
                if status_value in [Customer.STATUS_CASE, Customer.STATUS_PAYMENT, Customer.STATUS_WON]:
                    raise ValidationError(f"第{row_index}行：有案件的客户请填写案件阶段；无案件客户状态仅填 公海/跟进/商机")
                if not status_value:
                    raise ValidationError(f"第{row_index}行：未填写案件阶段时，客户状态必填（公海/跟进/商机）")
                if status_value == Customer.STATUS_PUBLIC_POOL:
                    ele["status"] = Customer.STATUS_PUBLIC_POOL
                    ele["sales_stage"] = Customer.SALES_STAGE_PUBLIC
                else:
                    # raw=商机 -> BLANK；其他跟进 -> MEETING
                    if raw_status_text == "商机":
                        ele["status"] = Customer.STATUS_FOLLOW_UP
                        ele["sales_stage"] = Customer.SALES_STAGE_BLANK
                    else:
                        ele["status"] = Customer.STATUS_FOLLOW_UP
                        ele["sales_stage"] = Customer.SALES_STAGE_MEETING
            else:
                # 有案件：客户状态跟随案件阶段
                ele["status"] = stage_status_map.get(case_stage, status_value or Customer.STATUS_FOLLOW_UP)
                ele["sales_stage"] = case_stage

            instance = None
            if update_mode:
                row_id = _parse_int(ele.get("id"))
                if not row_id:
                    name = _normalize_name(ele.get("name"))
                    phone = _normalize_phone(ele.get("contact_phone"))
                    if not name:
                        raise ValidationError(f"第{row_index}行：客户名称不能为空")
                    # 允许联系电话为空：按“新建”处理
                    if phone:
                        matches = customer_by_pair.get((name, phone), [])
                        if len(matches) > 1:
                            raise ValidationError(f"第{row_index}行：手机号与客户名称匹配到多条记录，请先保证唯一")
                        instance = matches[0] if matches else None
                        if instance:
                            ele["id"] = instance.id
                else:
                    instance = customer_by_id.get(row_id)
                    if not instance:
                        raise ValidationError(f"第{row_index}行：更新主键 {row_id} 不存在，请确认没有删改该列")
            else:
                row_id = _parse_int(ele.get("id"))
                if row_id:
                    instance = customer_by_id.get(row_id)

            try:
                if instance is None and not ele.get("client_category"):
                    ele["client_category"] = "construction"
                # 导入场景自行处理经办人，避免 serializer 内部 set_handlers + 同步案件导致导入变慢
                ele.pop("handler_ids", None)
                serializer = self.import_serializer_class(
                    instance,
                    data=ele,
                    context={"request": request},
                    partial=bool(instance),
                )
                serializer.is_valid(raise_exception=True)
                customer = serializer.save()
            except ValidationError as e:
                raise ValidationError(f"第{row_index}行校验失败：{e.detail if hasattr(e, 'detail') else str(e)}")
            if handler_ids:
                CustomerService.set_handlers(
                    customer,
                    handler_ids,
                    primary_id=handler_ids[0],
                    mode="replace",
                    sync_cases=False,
                )
            created_count += 1 if instance is None else 0
            updated_count += 1 if instance is not None else 0
            keep_ids.add(customer.id)

            # 仅在交案/回款/赢单需要创建或更新案件
            need_case = case_stage in [
                CaseManagement.SALES_STAGE_CASE,
                CaseManagement.SALES_STAGE_PAYMENT,
                CaseManagement.SALES_STAGE_WON,
            ]
            if not need_case:
                continue
            if not case_name:
                case_name = f"{customer.name}-导入案件"

            case = CaseManagement.objects.filter(
                customer=customer, case_name=case_name, is_deleted=False
            ).first()
            if not case:
                # 生成一个简单的案件编号
                case_number = case_number_input or f"CUST{customer.id}-{timezone.now().strftime('%Y%m%d%H%M%S%f')[:18]}"
                case = CaseManagement.objects.create(
                    customer=customer,
                    case_name=case_name,
                    case_number=case_number,
                    case_type="导入",
                    case_status="导入",
                    sales_stage=case_stage or CaseManagement.SALES_STAGE_CASE,
                    status=stage_status_map.get(case_stage, CaseManagement.STATUS_CASE),
                    owner_user=customer.owner_user,
                    owner_user_name=customer.owner_user_name,
                )
                try:
                    case.handlers.set(handler_ids or list(customer.handlers.values_list("id", flat=True)))
                except Exception:
                    pass
            else:
                case.sales_stage = case_stage or case.sales_stage
                case.status = stage_status_map.get(case_stage, case.status)
                if case_number_input:
                    case.case_number = case_number_input
                if customer.owner_user and case.owner_user_id != customer.owner_user_id:
                    case.owner_user = customer.owner_user
                    case.owner_user_name = customer.owner_user_name
                case.save(update_fields=["sales_stage", "status", "owner_user", "owner_user_name", "case_number", "update_datetime"])
                try:
                    case.handlers.set(handler_ids or list(customer.handlers.values_list("id", flat=True)))
                except Exception:
                    pass

        deleted_count = 0
        if delete_missing and data:
            if keep_ids:
                to_delete = queryset.exclude(id__in=keep_ids)
                to_delete = self.filter_queryset_for_import_delete(to_delete)
                deleted_count = to_delete.update(is_deleted=True)

        return Response(
            {
                "detail": f"导入完成，新增 {created_count} 条，更新 {updated_count} 条，删除 {deleted_count} 条",
                "created": created_count,
                "updated": updated_count,
                "deleted": deleted_count,
            },
            status=status.HTTP_200_OK,
        )
