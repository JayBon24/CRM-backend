from django.db import models

from dvadmin.system.models import Users
from dvadmin.utils.models import CoreModel

from .customer import Customer


class FollowupRecord(CoreModel):
    FOLLOWUP_TYPE_CHOICES = (
        ("phone", "电话"),
        ("wechat", "微信"),
        ("meeting", "面谈"),
        ("other", "其他"),
    )

    customer = models.ForeignKey(
        to=Customer,
        on_delete=models.CASCADE,
        related_name="followups",
        verbose_name="关联客户",
        db_constraint=False,
    )
    followup_type = models.CharField(max_length=32, choices=FOLLOWUP_TYPE_CHOICES, verbose_name="跟进方式")
    summary = models.TextField(verbose_name="跟进摘要", null=True, blank=True)
    conclusion = models.CharField(max_length=200, verbose_name="跟进结论", null=True, blank=True)
    attachments = models.JSONField(default=list, blank=True, null=True, verbose_name="附件")
    next_plan_at = models.DateTimeField(null=True, blank=True, verbose_name="下次计划时间")
    created_by = models.ForeignKey(
        to=Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="followup_creators",
        verbose_name="创建人",
        db_constraint=False,
    )

    class Meta:
        db_table = "customer_followup_record"
        verbose_name = "跟进记录"
        verbose_name_plural = "跟进记录"

    def __str__(self):
        return f"{self.customer} - {self.followup_type}"
