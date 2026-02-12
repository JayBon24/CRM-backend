"""
Tab3 AI 会话域模型。

用于支持：
1) 多会话管理（新建/切换/重命名/置顶/删除）
2) 结构化消息存储（文本/卡片/操作结果）
3) 写操作确认链路（待确认动作）
"""
from django.db import models

from dvadmin.utils.models import CoreModel, SoftDeleteModel


class AIConversation(CoreModel, SoftDeleteModel):
    """AI 会话元数据。"""

    user_id = models.IntegerField(
        verbose_name="用户ID",
        help_text="会话归属用户ID",
        db_index=True,
    )
    title = models.CharField(
        max_length=200,
        verbose_name="会话标题",
        help_text="会话标题",
        default="新会话",
    )
    pinned = models.BooleanField(
        default=False,
        verbose_name="是否置顶",
        help_text="会话是否置顶",
        db_index=True,
    )
    last_message_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="最后消息时间",
        help_text="最后一条消息时间",
        db_index=True,
    )

    class Meta:
        db_table = "ai_conversation"
        verbose_name = "AI会话"
        verbose_name_plural = "AI会话"
        ordering = ["-pinned", "-last_message_time", "-create_datetime"]
        indexes = [
            models.Index(fields=["user_id", "-last_message_time"], name="ai_conv_user_lastmsg_idx"),
            models.Index(fields=["user_id", "-pinned"], name="ai_conv_user_pinned_idx"),
        ]


class AIMessage(CoreModel, SoftDeleteModel):
    """AI 会话消息。"""

    ROLE_CHOICES = (
        ("user", "用户"),
        ("assistant", "助手"),
        ("system", "系统"),
    )
    MESSAGE_TYPE_CHOICES = (
        ("text", "文本"),
        ("card", "卡片"),
        ("action_result", "操作结果"),
        ("scope_hint", "范围提示"),
        ("error", "错误"),
    )

    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name="messages",
        db_constraint=False,
        verbose_name="会话",
        help_text="所属会话",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="assistant",
        verbose_name="角色",
        help_text="消息角色",
        db_index=True,
    )
    message_type = models.CharField(
        max_length=30,
        choices=MESSAGE_TYPE_CHOICES,
        default="text",
        verbose_name="消息类型",
        help_text="消息类型",
        db_index=True,
    )
    content_json = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="消息内容",
        help_text="结构化消息内容",
    )
    tool_trace = models.JSONField(
        default=list,
        blank=True,
        verbose_name="工具轨迹",
        help_text="工具调用轨迹",
    )

    class Meta:
        db_table = "ai_message"
        verbose_name = "AI消息"
        verbose_name_plural = "AI消息"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["conversation", "id"], name="ai_msg_conv_id_idx"),
            models.Index(fields=["conversation", "message_type"], name="ai_msg_conv_type_idx"),
        ]


class AIPendingAction(CoreModel, SoftDeleteModel):
    """待确认动作（草稿卡片 -> 确认执行）。"""

    STATUS_CHOICES = (
        ("pending", "待确认"),
        ("cancelled", "已取消"),
        ("executed", "已执行"),
        ("expired", "已过期"),
        ("approval_pending", "审批中"),
        ("failed", "执行失败"),
    )
    RISK_LEVEL_CHOICES = (
        ("low", "低风险"),
        ("high", "高风险"),
    )

    operation_id = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="操作ID",
        help_text="对外幂等操作ID",
    )
    user_id = models.IntegerField(
        verbose_name="用户ID",
        help_text="动作归属用户ID",
        db_index=True,
    )
    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name="pending_actions",
        db_constraint=False,
        null=True,
        blank=True,
        verbose_name="会话",
        help_text="所属会话",
    )
    action_type = models.CharField(
        max_length=64,
        verbose_name="动作类型",
        help_text="如 followup_create",
    )
    risk_level = models.CharField(
        max_length=16,
        choices=RISK_LEVEL_CHOICES,
        default="low",
        verbose_name="风险等级",
        help_text="低风险或高风险",
    )
    entity_type = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name="实体类型",
        help_text="如 customer/followup",
    )
    entity_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="实体ID",
        help_text="关联实体ID",
    )
    draft_payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="草稿负载",
        help_text="待确认草稿内容",
    )
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="状态",
        help_text="动作状态",
        db_index=True,
    )
    expire_at = models.DateTimeField(
        verbose_name="过期时间",
        help_text="超过该时间不允许确认",
        db_index=True,
    )
    last_idempotency_key = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name="最后幂等键",
        help_text="防重复提交",
    )
    result_json = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="执行结果",
        help_text="执行结果负载",
    )

    class Meta:
        db_table = "ai_pending_action"
        verbose_name = "AI待确认动作"
        verbose_name_plural = "AI待确认动作"
        ordering = ["-create_datetime"]
        indexes = [
            models.Index(fields=["operation_id"], name="ai_pend_opid_idx"),
            models.Index(fields=["user_id", "status"], name="ai_pend_user_status_idx"),
            models.Index(fields=["conversation", "status"], name="ai_pend_conv_status_idx"),
        ]
