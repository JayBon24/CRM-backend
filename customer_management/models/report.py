from django.db import models
from dvadmin.utils.models import CoreModel


class Report(CoreModel):
    """报告模型"""
    
    # 报告类型
    REPORT_TYPE_CHOICES = [
        ('weekly', '周报'),
        ('monthly', '月报'),
        ('quarterly', '季报'),
        ('yearly', '年报'),
        ('custom', '自定义'),
    ]
    
    # 报告状态
    STATUS_CHOICES = [
        ('generating', '生成中'),
        ('completed', '已完成'),
        ('failed', '生成失败'),
    ]
    
    title = models.CharField(
        max_length=200,
        verbose_name="报告标题",
        help_text="报告标题"
    )
    type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        verbose_name="报告类型",
        help_text="报告类型"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='completed',
        verbose_name="状态",
        help_text="状态"
    )
    start_date = models.DateField(
        verbose_name="开始日期",
        help_text="开始日期"
    )
    end_date = models.DateField(
        verbose_name="结束日期",
        help_text="结束日期"
    )
    content = models.JSONField(
        verbose_name="报告内容",
        help_text="报告内容（JSON格式）",
        default=dict
    )
    
    class Meta:
        db_table = "report"
        verbose_name = "报告"
        verbose_name_plural = "报告"
        ordering = ['-create_datetime']
    
    def __str__(self):
        return f"{self.title} - {self.get_type_display()}"
