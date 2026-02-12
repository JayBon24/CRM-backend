"""
检索相关的序列化器
"""
from rest_framework import serializers


class RegulationSearchSerializer(serializers.Serializer):
    """法规检索请求序列化器"""
    query = serializers.CharField(
        required=True,
        help_text="检索关键词",
        max_length=200
    )
    category = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="法规类别"
    )


class LegalSearchSerializer(serializers.Serializer):
    """法律检索请求序列化器"""
    query = serializers.CharField(
        required=True,
        help_text="检索关键词",
        max_length=200
    )
    search_type = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="检索类型"
    )

