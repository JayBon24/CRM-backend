from django.db import models

from dvadmin.system.models import Users
from dvadmin.utils.models import CoreModel

from .approval import ApprovalTask
from .customer import Customer


class TransferLog(CoreModel):
    STATUS_CHOICES = (
        ("pending", "待审批"),
        ("completed", "已完成"),
        ("rejected", "已驳回"),
    )

    customer = models.ForeignKey(
        to=Customer,
        on_delete=models.CASCADE,
        related_name="transfer_logs",
        verbose_name="关联客户",
        db_constraint=False,
    )
    from_user = models.ForeignKey(
        to=Users,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transfer_from_logs",
        verbose_name="转出人",
        db_constraint=False,
    )
    to_user = models.ForeignKey(
        to=Users,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transfer_to_logs",
        verbose_name="转入人",
        db_constraint=False,
    )
    transfer_reason = models.CharField(max_length=200, verbose_name="转交原因", null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", verbose_name="状态")
    approval_task = models.ForeignKey(
        to=ApprovalTask,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transfer_logs",
        verbose_name="审批任务",
        db_constraint=False,
    )

    class Meta:
        db_table = "customer_transfer_log"
        verbose_name = "转交日志"
        verbose_name_plural = "转交日志"

    def __str__(self):
        return f"{self.customer} {self.from_user}→{self.to_user}"
