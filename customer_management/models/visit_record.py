"""
拜访记录模型
"""
from django.db import models
from dvadmin.utils.models import CoreModel, SoftDeleteModel


class VisitRecord(CoreModel, SoftDeleteModel):
    """拜访记录模型"""
    
    # 定位状态选项
    LOCATION_STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失败'),
        ('pending', '待定位'),
    ]
    
    # 基本信息
    client_id = models.IntegerField(
        verbose_name="客户ID",
        help_text="客户ID",
        db_index=True
    )
    user_id = models.IntegerField(
        verbose_name="拜访人ID",
        help_text="拜访人ID",
        db_index=True
    )
    
    # 拜访信息
    visit_time = models.DateTimeField(
        verbose_name="拜访时间",
        help_text="拜访时间",
        db_index=True
    )
    duration = models.IntegerField(
        verbose_name="洽谈时长（分钟）",
        help_text="洽谈时长（分钟）",
        null=True,
        blank=True
    )
    content = models.TextField(
        verbose_name="拜访内容",
        help_text="拜访内容",
        null=True,
        blank=True
    )
    
    # 定位信息
    location_status = models.CharField(
        max_length=20,
        choices=LOCATION_STATUS_CHOICES,
        default='pending',
        verbose_name="定位状态",
        help_text="定位状态"
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
        verbose_name="拜访地址",
        help_text="拜访地址",
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = "visit_record"
        verbose_name = "拜访记录"
        verbose_name_plural = "拜访记录"
        ordering = ['-visit_time']
        indexes = [
            models.Index(fields=['client_id', 'visit_time']),
            models.Index(fields=['user_id', 'visit_time']),
            models.Index(fields=['location_status']),
        ]
    
    def __str__(self):
        return f"拜访记录 - {self.visit_time}"
