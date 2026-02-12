from rest_framework import serializers
from customer_management.models import Schedule, ScheduleReminder


class ScheduleReminderSerializer(serializers.ModelSerializer):
    """日程提醒序列化器"""
    
    class Meta:
        model = ScheduleReminder
        fields = [
            'id', 'remind_time', 'remind_method', 'is_sent',
            'sent_time', 'send_result', 'create_datetime'
        ]
        read_only_fields = ['id', 'create_datetime']


class ScheduleSerializer(serializers.ModelSerializer):
    """日程基础序列化器"""
    creator_info = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'title', 'description', 'schedule_type', 'other_type_content',
            'start_time', 'end_time', 'location', 'participants',
            'status', 'priority', 'is_all_day',
            'reminder_enabled', 'reminder_time', 'reminder_method',
            'related_type', 'related_id',
            'recurrence_rule', 'attachments', 'remark',
            'create_datetime', 'update_datetime', 'creator_info'
        ]
        read_only_fields = ['id', 'create_datetime', 'update_datetime']
    
    def get_creator_info(self, obj):
        """获取创建人信息"""
        if obj.creator:
            return {
                'id': obj.creator.id,
                'username': obj.creator.username,
                'name': getattr(obj.creator, 'name', obj.creator.username)
            }
        return None


class ScheduleListSerializer(serializers.ModelSerializer):
    """日程列表序列化器（简化版）"""
    creator_info = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'title', 'schedule_type', 'other_type_content', 'start_time', 'end_time',
            'location', 'status', 'priority', 'is_all_day',
            'related_type', 'related_id',
            'create_datetime', 'creator_info'
        ]
        read_only_fields = ['id', 'create_datetime']
    
    def get_creator_info(self, obj):
        """获取创建人信息"""
        if obj.creator:
            return {
                'id': obj.creator.id,
                'username': obj.creator.username,
                'name': getattr(obj.creator, 'name', obj.creator.username)
            }
        return None


class ScheduleDetailSerializer(serializers.ModelSerializer):
    """日程详情序列化器（包含关联信息）"""
    creator_info = serializers.SerializerMethodField(read_only=True)
    related_info = serializers.SerializerMethodField(read_only=True)
    reminders = ScheduleReminderSerializer(many=True, read_only=True)
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'title', 'description', 'schedule_type', 'other_type_content',
            'start_time', 'end_time', 'location', 'participants',
            'status', 'priority', 'is_all_day',
            'reminder_enabled', 'reminder_time', 'reminder_method',
            'related_type', 'related_id', 'related_info',
            'recurrence_rule', 'attachments', 'remark',
            'reminders',
            'create_datetime', 'update_datetime', 'creator_info'
        ]
        read_only_fields = ['id', 'create_datetime', 'update_datetime']
    
    def get_creator_info(self, obj):
        """获取创建人信息"""
        if obj.creator:
            return {
                'id': obj.creator.id,
                'username': obj.creator.username,
                'name': getattr(obj.creator, 'name', obj.creator.username)
            }
        return None
    
    def get_related_info(self, obj):
        """获取关联对象信息"""
        if not obj.related_type or not obj.related_id:
            return None
        
        try:
            if obj.related_type == 'case':
                from case_management.models import CaseManagement
                case = CaseManagement.objects.filter(id=obj.related_id, is_deleted=False).first()
                if case:
                    return {
                        'id': case.id,
                        'case_number': case.case_number,
                        'case_name': case.case_name,
                        'case_type': case.case_type
                    }
            elif obj.related_type == 'customer':
                from customer_management.models import Customer
                customer = Customer.objects.filter(id=obj.related_id, is_deleted=False).first()
                if customer:
                    return {
                        'id': customer.id,
                        'name': customer.name,
                        'contact_person': customer.contact_person
                    }
        except Exception:
            pass
        
        return None


class ScheduleCreateSerializer(serializers.ModelSerializer):
    """日程创建序列化器"""
    
    class Meta:
        model = Schedule
        fields = [
            'title', 'description', 'schedule_type', 'other_type_content',
            'start_time', 'end_time', 'location', 'participants',
            'status', 'priority', 'is_all_day',
            'reminder_enabled', 'reminder_time', 'reminder_method',
            'related_type', 'related_id',
            'recurrence_rule', 'attachments', 'remark'
        ]
    
    def validate(self, attrs):
        """验证数据"""
        # 验证结束时间必须大于开始时间
        if attrs.get('end_time') and attrs.get('start_time'):
            if attrs['end_time'] <= attrs['start_time']:
                raise serializers.ValidationError("结束时间必须大于开始时间")
        
        # 验证关联信息
        if attrs.get('related_type') and not attrs.get('related_id'):
            raise serializers.ValidationError("指定关联类型时必须提供关联对象ID")
        
        if attrs.get('related_id') and not attrs.get('related_type'):
            raise serializers.ValidationError("指定关联对象ID时必须提供关联类型")
        
        return attrs


class ScheduleUpdateSerializer(serializers.ModelSerializer):
    """日程更新序列化器"""
    
    class Meta:
        model = Schedule
        fields = [
            'title', 'description', 'schedule_type', 'other_type_content',
            'start_time', 'end_time', 'location', 'participants',
            'status', 'priority', 'is_all_day',
            'reminder_enabled', 'reminder_time', 'reminder_method',
            'related_type', 'related_id',
            'recurrence_rule', 'attachments', 'remark'
        ]
    
    def validate(self, attrs):
        """验证数据"""
        # 获取实例的当前值
        instance = self.instance
        start_time = attrs.get('start_time', instance.start_time if instance else None)
        end_time = attrs.get('end_time', instance.end_time if instance else None)
        
        # 验证结束时间必须大于开始时间
        if end_time and start_time:
            if end_time <= start_time:
                raise serializers.ValidationError("结束时间必须大于开始时间")
        
        return attrs


class CreateFromCustomerPlanSerializer(serializers.Serializer):
    """从客户计划创建日程的序列化器"""
    customer_id = serializers.IntegerField(required=True, help_text="客户ID")
    plan_title = serializers.CharField(max_length=200, required=True, help_text="计划标题")
    plan_time = serializers.DateTimeField(required=True, help_text="计划时间")
    plan_description = serializers.CharField(required=False, allow_blank=True, help_text="计划描述")
    reminder_time = serializers.IntegerField(default=60, help_text="提前提醒时间（分钟）")


class BatchDeleteSerializer(serializers.Serializer):
    """批量删除序列化器"""
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        help_text="要删除的日程ID列表"
    )


class UpdateStatusSerializer(serializers.Serializer):
    """更新状态序列化器"""
    status = serializers.ChoiceField(
        choices=Schedule.STATUS_CHOICES,
        required=True,
        help_text="状态：pending(待处理)、in_progress(进行中)、completed(已完成)、cancelled(已取消)"
    )


class SendSMSSerializer(serializers.Serializer):
    """发送短信序列化器"""
    phone = serializers.CharField(max_length=20, required=True, help_text="手机号")
    template_code = serializers.CharField(max_length=50, required=True, help_text="模板代码")
    params = serializers.JSONField(required=True, help_text="模板参数")


class SendEmailSerializer(serializers.Serializer):
    """发送邮件序列化器"""
    to = serializers.EmailField(required=True, help_text="收件人邮箱")
    subject = serializers.CharField(max_length=200, required=True, help_text="邮件主题")
    content = serializers.CharField(required=True, help_text="邮件内容")
    template = serializers.CharField(max_length=50, required=False, allow_blank=True, help_text="邮件模板")
