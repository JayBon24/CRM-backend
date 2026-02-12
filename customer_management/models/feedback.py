"""
用户反馈模型
"""
from django.db import models
from dvadmin.system.models import Users
from dvadmin.utils.models import CoreModel


class Feedback(CoreModel):
    """用户反馈"""
    
    TYPE_CHOICES = (
        ('bug', '问题反馈'),
        ('feature', '功能建议'),
        ('improvement', '改进建议'),
        ('other', '其他'),
    )
    
    STATUS_CHOICES = (
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('resolved', '已解决'),
        ('closed', '已关闭'),
    )
    
    PRIORITY_CHOICES = (
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '紧急'),
    )
    
    user = models.ForeignKey(
        to=Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedbacks',
        verbose_name='反馈用户',
        db_constraint=False,
    )
    
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='other',
        verbose_name='反馈类型'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='标题'
    )
    
    content = models.TextField(
        verbose_name='反馈内容'
    )
    
    contact = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='联系方式'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='处理状态'
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name='优先级'
    )
    
    handler = models.ForeignKey(
        to=Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_feedbacks',
        verbose_name='处理人',
        db_constraint=False,
    )
    
    reply = models.TextField(
        null=True,
        blank=True,
        verbose_name='回复内容'
    )
    
    handled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='处理时间'
    )
    
    class Meta:
        db_table = 'customer_feedback'
        verbose_name = '用户反馈'
        verbose_name_plural = '用户反馈'
        ordering = ['-create_datetime']
    
    def __str__(self):
        return f"{self.title} - {self.user.name if self.user else '匿名'}"
