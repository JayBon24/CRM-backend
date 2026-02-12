from django.db import transaction
from django.utils import timezone

from customer_management.models import Customer, CustomerHandler
from dvadmin.system.models import Users


class CustomerService:
    @classmethod
    def _get_primary_handler_id(cls, handler_ids, primary_id=None):
        if primary_id and primary_id in handler_ids:
            return primary_id
        return handler_ids[0] if handler_ids else None

    @classmethod
    def set_handlers(cls, customer: Customer, handler_ids, primary_id=None, mode="replace", sync_cases: bool = True):
        handler_ids = [int(h) for h in handler_ids if str(h).isdigit()]
        handler_ids = list(dict.fromkeys(handler_ids))
        if mode == "append":
            existing = list(customer.handlers.values_list("id", flat=True))
            for hid in existing:
                if hid not in handler_ids:
                    handler_ids.append(hid)

        primary_id = cls._get_primary_handler_id(handler_ids, primary_id)
        if mode == "replace":
            CustomerHandler.objects.filter(customer=customer).delete()
        # rebuild handlers（使用 customer_id/user_id 避免 MySQL 下 ignore_conflicts+ForeignKey 问题；先 delete 再 create 无重复，无需 ignore_conflicts）
        links = []
        for idx, hid in enumerate(handler_ids):
            links.append(
                CustomerHandler(
                    customer_id=customer.id,
                    user_id=hid,
                    is_primary=(hid == primary_id),
                    sort=idx,
                )
            )
        if links:
            CustomerHandler.objects.bulk_create(links)
        # update owner_user as primary (for team/branch)
        if primary_id:
            owner_user = Users.objects.filter(id=primary_id).first()
            if owner_user:
                customer.owner_user = owner_user
                customer.owner_user_name = owner_user.name or owner_user.username
                customer.team_id = cls._derive_team_id(owner_user)
                customer.branch_id = cls._derive_branch_id(owner_user)
        customer.save()
        if sync_cases:
            cls.sync_case_handlers(customer)
        return customer

    @classmethod
    def sync_case_handlers(cls, customer: Customer):
        try:
            from case_management.models import CaseHandler, CaseManagement
        except Exception:
            return
        handler_ids = list(customer.handlers.values_list("id", flat=True))
        cases = CaseManagement.objects.filter(customer=customer, is_deleted=False)
        for case in cases:
            if not handler_ids:
                CaseHandler.objects.filter(case=case).delete()
                continue
            CaseHandler.objects.filter(case=case).delete()
            links = []
            for idx, hid in enumerate(handler_ids):
                links.append(
                    CaseHandler(
                        case_id=case.id,
                        user_id=hid,
                        is_primary=(idx == 0),
                        sort=idx,
                    )
                )
            CaseHandler.objects.bulk_create(links)
    @staticmethod
    def _derive_team_id(user):
        """
        根据用户信息推导团队ID：
        1. 优先使用用户自身的 team_id（如果已配置）
        2. 如果没有 team_id，则使用 dept_id
        注意：此逻辑必须与查询逻辑保持一致（client_views.py 第392行）
        """
        return getattr(user, 'team_id', None) or getattr(user, 'dept_id', None)

    @staticmethod
    def _derive_branch_id(user):
        """
        根据用户信息推导分所ID：
        1. 如果 Users 表中显式配置了 branch_id，优先使用该字段；
        2. 如果角色是 BRANCH 且有 dept_id，则认为当前部门就是分所节点，直接返回 dept_id；
        3. 其他情况（如 TEAM/SALES）：使用部门的父级作为分所节点。
        """
        # 1. 优先使用用户自身的 branch_id（如果已配置）
        if getattr(user, "branch_id", None):
            return user.branch_id

        # 2. 分所角色：dept 本身就是分所节点
        role_level = getattr(user, "role_level", None)
        if role_level == "BRANCH" and getattr(user, "dept_id", None):
            return user.dept_id

        # 3. 其他情况：使用部门父级作为分所
        if not getattr(user, "dept", None):
            return None
        parent = getattr(user.dept, "parent", None)
        return parent.id if parent else None

    @classmethod
    def assign_customer(cls, customer, owner_user):
        with transaction.atomic():
            cls.set_handlers(customer, [owner_user.id], primary_id=owner_user.id, mode="replace")
            customer.status = Customer.STATUS_FOLLOW_UP
            customer.sales_stage = customer.calculate_sales_stage()
            customer.save()
        return customer

    @classmethod
    def transfer_customer(cls, customer, target_user):
        return cls.assign_customer(customer, target_user)

    @classmethod
    def update_status(cls, customer, status):
        customer.status = status
        customer.sales_stage = customer.calculate_sales_stage()
        if status == Customer.STATUS_WON and not customer.last_deal_time:
            customer.last_deal_time = timezone.now()
        customer.save()
        return customer

    @classmethod
    def record_visit(cls, customer, location_status=None):
        if location_status == "success":
            customer.valid_visit_count = max(customer.valid_visit_count + 1, 0)
        customer.sales_stage = customer.calculate_sales_stage()
        customer.save()
        return customer
