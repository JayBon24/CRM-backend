# -*- coding: utf-8 -*-
"""
提醒消息模型
用于存储公海回收提醒和跟进提醒等消息
"""
from django.db import models
from dvadmin.utils.models import CoreModel, SoftDeleteModel
from dvadmin.system.models import Users


class ReminderMessage(CoreModel, SoftDeleteModel):
    """提醒消息模型"""

    REMINDER_TYPE_CHOICES = [
        ('recycle_warning', '公海回收提醒'),
        ('followup_reminder', '跟进提醒'),
        ('other', '其他'),
    ]

    reminder_type = models.CharField(
        max_length=50,
        choices=REMINDER_TYPE_CHOICES,
        verbose_name="提醒类型",
        help_text="提醒类型：recycle_warning(公海回收提醒)、followup_reminder(跟进提醒)"
    )

    title = models.CharField(
        max_length=200,
        verbose_name="提醒标题",
        help_text="提醒标题"
    )

    content = models.TextField(
        verbose_name="提醒内容",
        help_text="提醒内容"
    )

    # 关联信息
    related_type = models.CharField(
        max_length=50,
        verbose_name="关联类型",
        help_text="关联类型：customer(客户)",
        null=True,
        blank=True
    )

    related_id = models.IntegerField(
        verbose_name="关联对象ID",
        help_text="关联对象ID（如客户ID）",
        null=True,
        blank=True
    )

    # 接收人（总所账号）
    recipient = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name='received_reminders',
        verbose_name="接收人",
        help_text="接收提醒的用户（总所账号）",
        null=True,
        blank=True,
        db_constraint=False
    )

    # 是否已读
    is_read = models.BooleanField(
        default=False,
        verbose_name="是否已读",
        help_text="是否已读",
        db_index=True
    )

    # 已读时间
    read_time = models.DateTimeField(
        verbose_name="已读时间",
        help_text="已读时间",
        null=True,
        blank=True
    )

    # 额外数据（JSON格式）
    extra_data = models.JSONField(
        verbose_name="额外数据",
        help_text="额外数据（JSON格式，如客户名称、经办人信息等）",
        null=True,
        blank=True,
        default=dict
    )

    class Meta:
        db_table = "reminder_message"
        verbose_name = "提醒消息"
        verbose_name_plural = "提醒消息"
        ordering = ['-create_datetime']
        indexes = [
            models.Index(fields=['recipient', 'is_read'], name='reminder_me_recipie_7807e6_idx'),
            models.Index(fields=['reminder_type', 'is_read'], name='reminder_me_reminde_c80c5c_idx'),
            models.Index(fields=['create_datetime'], name='reminder_me_create__3e06ae_idx'),
        ]

    def __str__(self):
        return f"{self.title} - {self.recipient.name if self.recipient else '未知'}"
