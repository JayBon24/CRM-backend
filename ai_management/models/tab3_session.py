"""
Tab3 AI 会话模型：用于持久化 sessionId <-> thread_id 映射
"""
from django.db import models
from dvadmin.utils.models import CoreModel


class Tab3Session(CoreModel):
    """Tab3 AI 会话映射表"""
    session_id = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="会话ID",
        help_text="小程序端生成的会话ID（UUID）"
    )
    thread_id = models.CharField(
        max_length=64,
        verbose_name="Xpert Thread ID",
        help_text="XpertAI 平台的 thread_id"
    )
    user_id = models.IntegerField(
        verbose_name="用户ID",
        null=True,
        blank=True,
        help_text="关联的用户ID（可选）"
    )
    last_run_id = models.CharField(
        max_length=64,
        verbose_name="最后运行ID",
        null=True,
        blank=True,
        help_text="最后一次运行的 executionId（用于 resume/cancel）"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="是否活跃",
        help_text="会话是否仍在进行中"
    )
    conversation = models.ForeignKey(
        to="ai_management.AIConversation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tab3_sessions",
        db_constraint=False,
        verbose_name="会话归属",
        help_text="关联到 AIConversation"
    )
    
    class Meta:
        db_table = "lsl_tab3_session"
        verbose_name = "Tab3会话"
        verbose_name_plural = "Tab3会话"
        ordering = ['-update_datetime']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['user_id', '-create_datetime']),
            models.Index(fields=['is_active']),
            models.Index(fields=['conversation', '-create_datetime'], name='lsl_tab3_conv_ctime_idx'),
        ]
