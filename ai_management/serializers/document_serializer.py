"""
文档生成相关的序列化器
"""
from rest_framework import serializers


class DocumentGenerateSerializer(serializers.Serializer):
    """文档生成请求序列化器"""
    case_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="案件ID（如果关联案件）"
    )
    document_type = serializers.CharField(
        required=True,
        help_text="文档类型（如：起诉状、答辩状等）"
    )
    template_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="模板ID（如果使用模板）"
    )
    case_data = serializers.DictField(
        required=False,
        help_text="案件数据（用于填充模板）"
    )


class DocumentGenerateResponseSerializer(serializers.Serializer):
    """文档生成响应序列化器"""
    document_id = serializers.IntegerField(help_text="生成的文档ID")
    document_name = serializers.CharField(help_text="文档名称")
    document_url = serializers.CharField(help_text="文档访问URL")
    success = serializers.BooleanField(help_text="是否生成成功")
    message = serializers.CharField(required=False, help_text="提示信息")


class DocumentExtractSerializer(serializers.Serializer):
    """Document extract request serializer."""
    url = serializers.CharField(required=True, help_text="File URL or path")
    file_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    force_ocr = serializers.BooleanField(required=False, default=False)
    ocr_all_pages = serializers.BooleanField(required=False, default=False)
    ocr_page_limit = serializers.IntegerField(required=False, default=0)

