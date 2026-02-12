"""
AI 对话相关的序列化器
"""
from rest_framework import serializers


class AIChatSerializer(serializers.Serializer):
    """AI 对话请求序列化器"""
    message = serializers.CharField(
        required=True, 
        help_text="用户消息",
        max_length=5000
    )
    context_type = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="上下文类型（如：case, customer）"
    )
    context_id = serializers.IntegerField(
        required=False, 
        allow_null=True,
        help_text="上下文ID"
    )
    uploaded_files = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        help_text="上传的文件列表（文件路径或URL）"
    )
    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="对话ID（用于多轮对话）"
    )


class AIChatResponseSerializer(serializers.Serializer):
    """AI 对话响应序列化器"""
    response = serializers.CharField(help_text="AI响应内容")
    conversation_id = serializers.IntegerField(
        required=False,
        help_text="对话ID"
    )
    suggestions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        help_text="建议操作列表"
    )
    model_name = serializers.CharField(
        required=False,
        help_text="使用的AI模型名称"
    )

