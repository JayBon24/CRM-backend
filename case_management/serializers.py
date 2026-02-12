"""
案例管理序列化器
"""
from rest_framework import serializers
from .models import (
    CaseManagement, CaseDocument, DocumentTemplate, CaseFolder,
    RegulationConversation, RegulationMessage, CaseHandler
)
from dvadmin.system.models import Users


class CaseManagementSerializer(serializers.ModelSerializer):
    """案例管理序列化器"""
    handler_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    handlers = serializers.SerializerMethodField(read_only=True)
    handler_names = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = CaseManagement
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']

    def get_handlers(self, obj):
        users = getattr(obj, "handlers", None)
        if users is None:
            return []
        return [{"id": user.id, "name": user.name or user.username} for user in users.all()]

    def get_handler_names(self, obj):
        users = getattr(obj, "handlers", None)
        if users is None:
            return []
        return [user.name or user.username for user in users.all()]

    def create(self, validated_data):
        handler_ids = validated_data.pop("handler_ids", None)
        instance = super().create(validated_data)
        if handler_ids:
            handler_ids = [int(x) for x in handler_ids if str(x).isdigit()]
            handler_ids = list(dict.fromkeys(handler_ids))
            CaseHandler.objects.filter(case=instance).delete()
            links = []
            for idx, hid in enumerate(handler_ids):
                links.append(
                    CaseHandler(
                        case=instance,
                        user_id=hid,
                        is_primary=(idx == 0),
                        sort=idx,
                    )
                )
            if links:
                CaseHandler.objects.bulk_create(links, ignore_conflicts=True)
            primary_id = handler_ids[0] if handler_ids else None
            if primary_id:
                owner_user = Users.objects.filter(id=primary_id).first()
                if owner_user:
                    instance.owner_user = owner_user
                    instance.owner_user_name = owner_user.name or owner_user.username
                    instance.save(update_fields=["owner_user", "owner_user_name"])
        return instance

    def update(self, instance, validated_data):
        handler_ids = validated_data.pop("handler_ids", None)
        instance = super().update(instance, validated_data)
        if handler_ids is not None and handler_ids:
            handler_ids = [int(x) for x in handler_ids if str(x).isdigit()]
            handler_ids = list(dict.fromkeys(handler_ids))
            CaseHandler.objects.filter(case=instance).delete()
            links = []
            for idx, hid in enumerate(handler_ids):
                links.append(
                    CaseHandler(
                        case=instance,
                        user_id=hid,
                        is_primary=(idx == 0),
                        sort=idx,
                    )
                )
            if links:
                CaseHandler.objects.bulk_create(links, ignore_conflicts=True)
            primary_id = handler_ids[0] if handler_ids else None
            if primary_id:
                owner_user = Users.objects.filter(id=primary_id).first()
                if owner_user:
                    instance.owner_user = owner_user
                    instance.owner_user_name = owner_user.name or owner_user.username
                    instance.save(update_fields=["owner_user", "owner_user_name"])
        return instance


class CaseDocumentSerializer(serializers.ModelSerializer):
    """案例文档序列化器"""
    file_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = CaseDocument
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']
    
    def get_file_url(self, obj):
        """获取文件访问 URL"""
        return obj.file_url


class DocumentTemplateSerializer(serializers.ModelSerializer):
    """文档模板序列化器"""
    
    # 添加占位符信息的只读字段
    placeholder_summary = serializers.SerializerMethodField(read_only=True)
    placeholder_list = serializers.SerializerMethodField(read_only=True)
    # 添加文件 URL 字段
    file_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = DocumentTemplate
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']
    
    def get_placeholder_summary(self, obj):
        """获取占位符摘要信息"""
        if obj.placeholder_info:
            return {
                'total_placeholders': obj.placeholder_info.get('total_count', 0),
                'unique_placeholders': obj.placeholder_info.get('unique_count', 0),
                'categories': obj.placeholder_info.get('analysis', {}).get('by_category', {}),
                'with_defaults': len(obj.placeholder_info.get('analysis', {}).get('with_defaults', [])),
                'without_defaults': len(obj.placeholder_info.get('analysis', {}).get('without_defaults', []))
            }
        return None
    
    def get_placeholder_list(self, obj):
        """获取占位符列表"""
        if obj.placeholder_info and obj.placeholder_info.get('placeholders'):
            return obj.placeholder_info['placeholders']
        return []
    
    def get_file_url(self, obj):
        """获取文件访问 URL"""
        return obj.file_url


class TemplateSortItemSerializer(serializers.Serializer):
    """单个模板排序项序列化器"""
    id = serializers.IntegerField(required=True, help_text="模板ID")
    sort_order = serializers.IntegerField(required=True, help_text="新的排序值")


class BatchSortSerializer(serializers.Serializer):
    """批量排序序列化器"""
    templates = TemplateSortItemSerializer(many=True, required=True, help_text="需要更新排序的模板列表")
    
    def validate_templates(self, value):
        """验证模板列表"""
        if not value:
            raise serializers.ValidationError("模板列表不能为空")
        
        # 检查是否有重复的ID
        ids = [item['id'] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("模板ID不能重复")
        
        return value


class DocumentPrintCountItemSerializer(serializers.Serializer):
    """单个文档打印数量项序列化器"""
    id = serializers.IntegerField(required=True, help_text="文档ID")
    print_count = serializers.IntegerField(
        required=True, 
        min_value=1, 
        max_value=99, 
        help_text="打印数量，范围：1-99"
    )
    is_selected = serializers.BooleanField(
        required=False,
        default=False,
        help_text="是否选中，默认为False（向后兼容）"
    )


class BatchUpdatePrintCountSerializer(serializers.Serializer):
    """批量更新打印数量序列化器"""
    documents = DocumentPrintCountItemSerializer(many=True, required=True, help_text="需要更新的文档列表")
    
    def validate_documents(self, value):
        """验证文档列表"""
        if not value:
            raise serializers.ValidationError("文档列表不能为空")
        
        # 检查是否有重复的ID
        ids = [item['id'] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("文档ID不能重复")
        
        return value


class ManualGenerateSerializer(serializers.Serializer):
    """人工生成文档序列化器 - 无强校验版本"""
    defendant_name = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="被告名称")
    defendant_credit_code = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="被告统一社会信用代码")
    defendant_address = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="被告所住地")
    defendant_legal_representative = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="被告法定代表人")
    plaintiff_name = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="原告名称")
    plaintiff_credit_code = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="原告统一社会信用代码")
    plaintiff_address = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="原告所住地")
    plaintiff_legal_representative = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="原告法定代表人")
    contract_amount = serializers.DecimalField(max_digits=20, decimal_places=2, required=False, allow_null=True, help_text="合同金额")
    lawyer_fee = serializers.DecimalField(max_digits=20, decimal_places=2, required=False, allow_null=True, help_text="律师费")
    
    # 诉讼信息字段
    litigation_request = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="诉讼请求")
    facts_and_reasons = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="事实与理由")
    jurisdiction = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="管辖法院")
    petitioner = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="具状人")
    filing_date = serializers.DateField(required=False, allow_null=True, help_text="起诉日期")


class PlaceholderEditSerializer(serializers.Serializer):
    """占位符编辑序列化器"""
    placeholder_info = serializers.JSONField(help_text="占位符信息JSON数据")
    
    def validate_placeholder_info(self, value):
        """验证占位符信息格式"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("占位符信息必须是JSON对象")
        
        # 检查必要的字段
        required_fields = ['placeholders', 'analysis', 'total_count', 'unique_count']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"缺少必要字段: {field}")
        
        # 验证占位符列表格式
        placeholders = value.get('placeholders', [])
        if not isinstance(placeholders, list):
            raise serializers.ValidationError("占位符列表必须是数组")
        
        for placeholder in placeholders:
            if not isinstance(placeholder, dict):
                raise serializers.ValidationError("每个占位符必须是对象")
            if 'key' not in placeholder:
                raise serializers.ValidationError("占位符必须包含key字段")
        
        return value


class AIChatSerializer(serializers.Serializer):
    """AI对话序列化器"""
    message = serializers.CharField(help_text="用户消息")
    case_id = serializers.IntegerField(required=False, help_text="案例ID")
    files = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="上传的文件内容列表"
    )


class CaseFolderSerializer(serializers.ModelSerializer):
    """案件目录序列化器"""
    
    class Meta:
        model = CaseFolder
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']


class CaseDocumentDetailSerializer(serializers.ModelSerializer):
    """案件文档详细序列化器"""
    template_name = serializers.CharField(
        source='template.template_name',
        read_only=True,
        allow_null=True
    )
    folder_name = serializers.CharField(
        source='folder.folder_name',
        read_only=True,
        allow_null=True
    )
    file_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = CaseDocument
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']
    
    def get_file_url(self, obj):
        """获取文件访问 URL"""
        return obj.file_url


class DocumentUploadSerializer(serializers.Serializer):
    """文档上传序列化器"""
    folder_path = serializers.CharField(help_text="目标目录路径")
    file = serializers.FileField(help_text="上传的文件")
    document_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="文档显示名称（可选）"
    )


class DocumentMoveSerializer(serializers.Serializer):
    """文档移动序列化器"""
    target_folder_path = serializers.CharField(help_text="目标目录路径")


class DocumentRenameSerializer(serializers.Serializer):
    """文档重命名序列化器"""
    new_name = serializers.CharField(help_text="新名称")


class CheckGeneratedDocumentsSerializer(serializers.Serializer):
    """检查已生成文书序列化器"""
    template_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="模板ID列表"
    )
    folder_path = serializers.CharField(
        default='/case_documents',
        help_text="目录路径"
    )


class GenerateDocumentsSerializer(serializers.Serializer):
    """生成文书序列化器"""
    case_id = serializers.IntegerField(help_text="案件ID")
    template_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="模板ID列表"
    )
    folder_path = serializers.CharField(
        default='/case_documents',
        help_text="保存目录路径"
    )


class RegulationMessageSerializer(serializers.ModelSerializer):
    """法规检索消息序列化器"""
    
    class Meta:
        model = RegulationMessage
        fields = ['id', 'role', 'content', 'query', 'filters', 'response_time', 'related_regulations', 'create_datetime']
        read_only_fields = ['id', 'create_datetime']


class RegulationConversationSerializer(serializers.ModelSerializer):
    """法规检索对话序列化器"""
    messages = RegulationMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = RegulationConversation
        fields = [
            'id', 'user_id', 'title', 'message_count', 
            'last_message_time', 'is_pinned', 'messages',
            'create_datetime', 'update_datetime'
        ]
        read_only_fields = ['id', 'message_count', 'last_message_time', 'create_datetime', 'update_datetime']


class RegulationConversationListSerializer(serializers.ModelSerializer):
    """法规检索对话列表序列化器（不包含消息详情）"""
    first_message = serializers.SerializerMethodField()
    
    class Meta:
        model = RegulationConversation
        fields = [
            'id', 'user_id', 'title', 'message_count', 
            'last_message_time', 'is_pinned', 'first_message',
            'create_datetime', 'update_datetime'
        ]
        read_only_fields = ['id', 'message_count', 'last_message_time', 'create_datetime', 'update_datetime']
    
    def get_first_message(self, obj):
        """获取对话的第一条消息作为预览"""
        first_msg = obj.messages.filter(role='user').first()
        if first_msg:
            return {
                'content': first_msg.content[:100],  # 只返回前100字符
                'time': first_msg.create_datetime
            }
        return None
