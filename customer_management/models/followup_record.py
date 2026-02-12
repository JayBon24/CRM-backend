"""
跟进记录模型
"""
from django.db import models
from django.utils import timezone
from dvadmin.utils.models import CoreModel, SoftDeleteModel


class FollowupRecord(CoreModel, SoftDeleteModel):
    """跟进记录模型"""
    
    # 跟进方式选项
    METHOD_CHOICES = [
        ('PHONE', '电话'),
        ('WECHAT', '微信'),
        ('EMAIL', '邮件'),
        ('VISIT', '拜访'),
        ('OTHER', '其他'),
    ]

    # 定位状态选项
    LOCATION_STATUS_CHOICES = [
        ('success', '成功'),
        ('fail', '失败'),
        ('denied', '拒绝授权'),
        ('offline', '无网络'),
    ]
    
    # 基本信息
    client_id = models.IntegerField(
        verbose_name="客户ID",
        help_text="客户ID",
        db_index=True
    )
    user_id = models.IntegerField(
        verbose_name="跟进人ID",
        help_text="跟进人ID",
        db_index=True
    )
    
    # 跟进内容
    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default='PHONE',
        verbose_name="跟进方式",
        help_text="跟进方式"
    )
    method_other = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="其他跟进方式",
        help_text="跟进方式为其他时填写"
    )
    summary = models.TextField(
        verbose_name="跟进摘要",
        help_text="跟进摘要",
        null=True,
        blank=True
    )
    conclusion = models.TextField(
        verbose_name="关键结论",
        help_text="关键结论",
        null=True,
        blank=True
    )
    content = models.TextField(
        verbose_name="跟进内容",
        help_text="跟进内容"
    )
    duration = models.IntegerField(
        verbose_name="洽谈时长（分钟）",
        help_text="洽谈时长（分钟）",
        null=True,
        blank=True
    )

    # 跟进地点与定位
    location_status = models.CharField(
        max_length=20,
        choices=LOCATION_STATUS_CHOICES,
        default='success',
        verbose_name="定位状态",
        help_text="定位状态",
        null=True,
        blank=True
    )
    lng = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        verbose_name="经度",
        help_text="经度",
        null=True,
        blank=True
    )
    lat = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        verbose_name="纬度",
        help_text="纬度",
        null=True,
        blank=True
    )
    address = models.CharField(
        max_length=500,
        verbose_name="跟进地点",
        help_text="跟进地点",
        null=True,
        blank=True
    )

    # 参与人员与附件
    internal_participants = models.JSONField(
        verbose_name="内部参与人员",
        help_text="内部参与人员（用户ID列表）",
        default=list,
        blank=True
    )
    customer_participants = models.JSONField(
        verbose_name="客户方参与人员",
        help_text="客户方参与人员（自定义列表）",
        default=list,
        blank=True
    )
    attachments = models.JSONField(
        verbose_name="附件列表",
        help_text="附件列表（JSON）",
        default=list,
        blank=True
    )
    
    # 时间信息
    followup_time = models.DateTimeField(
        verbose_name="跟进时间",
        help_text="跟进时间",
        default=timezone.now,
        db_index=True
    )
    next_followup_time = models.DateTimeField(
        verbose_name="下次跟进时间",
        help_text="下次跟进时间",
        null=True,
        blank=True,
        db_index=True
    )
    
    class Meta:
        db_table = "followup_record"
        verbose_name = "跟进记录"
        verbose_name_plural = "跟进记录"
        ordering = ['-followup_time']
        indexes = [
            models.Index(fields=['client_id', 'followup_time']),
            models.Index(fields=['user_id', 'followup_time']),
        ]
    
    def __str__(self):
        return f"跟进记录 - {self.followup_time}"
