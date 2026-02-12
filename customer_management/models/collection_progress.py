"""
收款进度模型
"""
from django.db import models
from dvadmin.utils.models import CoreModel, SoftDeleteModel


class CollectionProgress(CoreModel, SoftDeleteModel):
    MODE_CHOICES = [
        ("average", "平均"),
        ("manual", "自选"),
    ]

    customer_id = models.IntegerField(
        verbose_name="客户ID",
        help_text="客户ID",
        db_index=True
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="总金额（万）",
        help_text="总金额（万）"
    )
    installment_count = models.IntegerField(
        verbose_name="期数",
        help_text="期数"
    )
    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default="average",
        verbose_name="分配模式",
        help_text="分配模式"
    )
    installments = models.JSONField(
        verbose_name="分期明细",
        help_text="分期明细（amount/time）",
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

    class Meta:
        db_table = "customer_collection_progress"
        verbose_name = "收款进度"
        verbose_name_plural = "收款进度"
        ordering = ["-create_datetime"]
        indexes = [
            models.Index(fields=["customer_id", "create_datetime"]),
        ]

    def __str__(self):
        return f"{self.customer_id} - {self.total_amount}"
