from django.db import models
from django.utils import timezone

from dvadmin.system.models import Users
from dvadmin.utils.models import CoreModel

from .customer import Customer


class ApprovalTask(CoreModel):
    APPROVAL_TYPE_CHOICES = (
        ("LEAD_CLAIM", "申领线索"),
        ("LEAD_CREATE", "新增线索"),
        ("HANDOVER", "客户转交"),
    )
    STATUS_CHOICES = (
        ("pending", "待审批"),
        ("approved", "已通过"),
        ("rejected", "已驳回"),
    )

    approval_type = models.CharField(max_length=32, choices=APPROVAL_TYPE_CHOICES, verbose_name="审批类型")
    applicant = models.ForeignKey(
        to=Users,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approval_applications",
        verbose_name="申请人",
        db_constraint=False,
    )
    approval_chain = models.JSONField(default=list, verbose_name="审批链", help_text="按角色顺序排列的审批链")
    current_step = models.IntegerField(default=0, verbose_name="当前审批步骤")
    current_approver_role = models.CharField(max_length=32, null=True, blank=True, verbose_name="当前审批角色")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", verbose_name="审批状态")
    related_customer = models.ForeignKey(
        to=Customer,
        on_delete=models.CASCADE,
        related_name="approval_tasks",
        verbose_name="关联客户",
        db_constraint=False,
    )
    related_data = models.JSONField(null=True, blank=True, default=dict, verbose_name="关联数据")
    reject_reason = models.TextField(null=True, blank=True, verbose_name="驳回原因")

    class Meta:
        db_table = "customer_approval_task"
        verbose_name = "审批任务"
        verbose_name_plural = "审批任务"

    def __str__(self):
        return f"{self.approval_type} - {self.related_customer}"

    @property
    def next_role(self):
        if self.current_step < len(self.approval_chain):
            return self.approval_chain[self.current_step]
        return None


class ApprovalHistory(CoreModel):
    ACTION_CHOICES = (
        ("approve", "通过"),
        ("reject", "驳回"),
    )

    approval_task = models.ForeignKey(
        to=ApprovalTask,
        on_delete=models.CASCADE,
        related_name="histories",
        verbose_name="审批任务",
        db_constraint=False,
    )
    approver = models.ForeignKey(
        to=Users,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approval_histories",
        verbose_name="审批人",
        db_constraint=False,
    )
    approver_role = models.CharField(max_length=32, null=True, blank=True, verbose_name="审批角色")
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, verbose_name="审批动作")
    comment = models.TextField(null=True, blank=True, verbose_name="审批意见")
    approval_time = models.DateTimeField(default=timezone.now, verbose_name="审批时间")

    class Meta:
        db_table = "customer_approval_history"
        verbose_name = "审批历史"
        verbose_name_plural = "审批历史"

    def __str__(self):
        return f"{self.approval_task} - {self.action}"
