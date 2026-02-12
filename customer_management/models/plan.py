"""
客户计划模型（用于有效案源/办案计划/回款跟进）
"""
from django.db import models
from dvadmin.utils.models import CoreModel, SoftDeleteModel


class CustomerPlan(CoreModel, SoftDeleteModel):
    PLAN_TYPE_CHOICES = [
        ("effective_case", "有效案源"),
        ("case_plan", "办案计划"),
        ("payment_followup", "回款跟进"),
    ]

    STATUS_CHOICES = [
        ("pending", "待处理"),
        ("completed", "已完成"),
        ("cancelled", "已取消"),
    ]

    customer_id = models.IntegerField(
        verbose_name="客户ID",
        help_text="客户ID",
        db_index=True
    )
    plan_type = models.CharField(
        max_length=32,
        choices=PLAN_TYPE_CHOICES,
        verbose_name="计划类型",
        help_text="计划类型"
    )
    title = models.CharField(
        max_length=200,
        verbose_name="计划标题",
        help_text="计划标题"
    )
    time_points = models.JSONField(
        verbose_name="计划时间点",
        help_text="计划时间点列表",
        default=list,
        blank=True
    )
    remind_method = models.CharField(
        max_length=20,
        verbose_name="提醒方式",
        help_text="提醒方式",
        null=True,
        blank=True
    )
    remind_advance = models.IntegerField(
        verbose_name="提前提醒分钟数",
        help_text="提前提醒分钟数",
        null=True,
        blank=True
    )
    sync_to_schedule = models.BooleanField(
        default=True,
        verbose_name="同步到日程",
        help_text="同步到日程"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="计划状态",
        help_text="计划状态",
        db_index=True
    )
    extra_data = models.JSONField(
        verbose_name="扩展数据",
        help_text="扩展数据（有效案源字段等）",
        default=dict,
        blank=True
    )

    class Meta:
        db_table = "customer_plan"
        verbose_name = "客户计划"
        verbose_name_plural = "客户计划"
        ordering = ["-create_datetime"]
        indexes = [
            models.Index(fields=["customer_id", "plan_type"]),
            models.Index(fields=["status", "create_datetime"]),
        ]

    def __str__(self):
        return f"{self.customer_id} - {self.plan_type} - {self.title}"
