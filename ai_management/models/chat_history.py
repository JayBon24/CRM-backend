"""
AI 对话历史模型
"""
from django.db import models
from dvadmin.utils.models import CoreModel


class AIChatHistory(CoreModel):
    """AI 对话历史"""
    user_id = models.IntegerField(verbose_name="用户ID", help_text="发起对话的用户ID")
    message = models.TextField(verbose_name="用户消息", help_text="用户发送的消息内容")
    response = models.TextField(verbose_name="AI响应", help_text="AI返回的响应内容")
    context_type = models.CharField(
        max_length=50, 
        verbose_name="上下文类型", 
        null=True, 
        blank=True,
        help_text="关联的业务类型，如：case（案件）、customer（客户）等"
    )
    context_id = models.IntegerField(
        verbose_name="上下文ID", 
        null=True, 
        blank=True,
        help_text="关联的业务ID"
    )
    model_name = models.CharField(
        max_length=100,
        verbose_name="使用的AI模型",
        null=True,
        blank=True,
        help_text="本次对话使用的AI模型名称"
    )
    
    class Meta:
        db_table = "ai_chat_history"
        verbose_name = "AI对话历史"
        verbose_name_plural = "AI对话历史"
        ordering = ['-create_datetime']
        indexes = [
            models.Index(fields=['user_id', '-create_datetime']),
            models.Index(fields=['context_type', 'context_id']),
        ]

