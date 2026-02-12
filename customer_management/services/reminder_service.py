from datetime import datetime, timedelta
from typing import List, Optional

from django.db.models import Q
from django.utils import timezone

from customer_management.models import Customer, FollowupRecord, VisitRecord, ReminderMessage
from dvadmin.system.models import Users
from customer_management.views.api.config_views import DEFAULT_CRM_CONFIG, get_crm_config


class ReminderService:
    """负责扫描并生成提醒消息的服务类。"""

    def __init__(self):
        self.config = get_crm_config() or DEFAULT_CRM_CONFIG or {}

    # --------- 公海回收提醒（无赢单天数） ----------
    def scan_recycle_reminders(self) -> int:
        """根据无赢单天数生成公海回收提醒，返回生成数量。"""
        no_won_days = self._get_no_won_days()
        if not no_won_days:
            return 0

        cutoff = timezone.now() - timedelta(days=no_won_days)
        candidates = Customer.objects.filter(
            is_deleted=False,
            status__in=[
                Customer.STATUS_PUBLIC_POOL,
                Customer.STATUS_FOLLOW_UP,
                Customer.STATUS_CASE,
                Customer.STATUS_PAYMENT,
            ],
        ).exclude(sales_stage=Customer.SALES_STAGE_WON)

        generated = 0
        for customer in candidates:
            last_touch = self._resolve_last_touch(customer)
            if last_touch and last_touch > cutoff:
                continue
            if self._exists_unread(customer, "recycle_warning"):
                continue
            for hq_user in self._get_hq_users():
                self._create_reminder(
                    recipient=hq_user,
                    customer=customer,
                    reminder_type="recycle_warning",
                    title=f"公海回收提醒：{customer.name}",
                    content=f"{customer.name} 已 {no_won_days} 天无赢单，请关注是否回收公海。",
                )
                generated += 1
        return generated

    # --------- 跟进提醒（超期未跟进） ----------
    def scan_followup_reminders(self) -> int:
        """根据配置扫描未跟进客户，生成提醒，返回生成数量。"""
        follow_cfg = self.config.get("followup_reminder") or {}
        if not follow_cfg.get("enabled", False):
            return 0
        days = follow_cfg.get("days", 15)
        if not days or days <= 0:
            return 0

        cutoff = timezone.now() - timedelta(days=days)
        candidates = Customer.objects.filter(
            is_deleted=False,
        ).exclude(status=Customer.STATUS_WON)

        generated = 0
        for customer in candidates:
            last_follow = self._resolve_last_followup(customer)
            last_time = last_follow or customer.create_datetime or customer.update_datetime
            if last_time and last_time > cutoff:
                continue
            if self._exists_unread(customer, "followup_reminder"):
                continue
            for hq_user in self._get_hq_users():
                self._create_reminder(
                    recipient=hq_user,
                    customer=customer,
                    reminder_type="followup_reminder",
                    title=f"跟进提醒：{customer.name}",
                    content=f"{customer.name} 已 {days} 天无跟进，请安排跟进。",
                )
                generated += 1
        return generated

    # --------- 内部辅助 ----------
    def _get_no_won_days(self) -> int:
        recycle_cfg = self.config.get("recycle_timeout") or {}
        return int(recycle_cfg.get("no_won_days") or 0)

    def _get_hq_users(self) -> List[Users]:
        # Users 模型没有 is_deleted 字段，只使用 is_active 过滤
        users = Users.objects.filter(is_active=True, role_level="HQ")
        if users.exists():
            return list(users)
        # 兜底：使用超级管理员
        fallback = Users.objects.filter(is_active=True, is_superuser=True)
        return list(fallback)

    def _resolve_last_followup(self, customer: Customer) -> Optional[datetime]:
        record = (
            FollowupRecord.objects.filter(client_id=customer.id, is_deleted=False)
            .order_by("-followup_time", "-create_datetime")
            .first()
        )
        if not record:
            return None
        if getattr(record, "followup_time", None):
            return record.followup_time
        return record.create_datetime

    def _resolve_last_visit(self, customer: Customer) -> Optional[datetime]:
        record = (
            VisitRecord.objects.filter(client_id=customer.id, is_deleted=False)
            .order_by("-visit_time", "-create_datetime")
            .first()
        )
        if not record:
            return None
        if getattr(record, "visit_time", None):
            return record.visit_time
        return record.create_datetime

    def _resolve_last_touch(self, customer: Customer) -> Optional[datetime]:
        points = [
            self._resolve_last_followup(customer),
            self._resolve_last_visit(customer),
            customer.update_datetime,
            customer.create_datetime,
        ]
        points = [p for p in points if p]
        return max(points) if points else None

    def _exists_unread(self, customer: Customer, reminder_type: str) -> bool:
        return ReminderMessage.objects.filter(
            reminder_type=reminder_type,
            related_type="customer",
            related_id=customer.id,
            is_read=False,
            is_deleted=False,
        ).exists()

    def _create_reminder(
        self,
        recipient: Users,
        customer: Customer,
        reminder_type: str,
        title: str,
        content: str,
    ) -> ReminderMessage:
        return ReminderMessage.objects.create(
            reminder_type=reminder_type,
            title=title,
            content=content,
            related_type="customer",
            related_id=customer.id,
            recipient=recipient,
            extra_data={
                "customer_name": customer.name,
                "customer_id": customer.id,
                "owner_user_id": customer.owner_user_id,
                "owner_user_name": customer.owner_user_name,
                "sales_stage": customer.sales_stage,
                "status": customer.status,
            },
        )
