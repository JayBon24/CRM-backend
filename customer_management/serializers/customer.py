from rest_framework import serializers

from customer_management.models import Customer
from customer_management.services.customer_service import CustomerService
from case_management.models import CaseManagement


# 客户状态/案件阶段 -> 导出模板用中文标签
STATUS_TO_LABEL = {
    Customer.STATUS_PUBLIC_POOL: "公海",
    Customer.STATUS_FOLLOW_UP: "跟进",
    Customer.STATUS_CASE: "交案",
    Customer.STATUS_PAYMENT: "回款",
    Customer.STATUS_WON: "赢单",
}
SALES_STAGE_TO_LABEL = {
    CaseManagement.SALES_STAGE_PUBLIC: "公海",
    CaseManagement.SALES_STAGE_BLANK: "商机",
    CaseManagement.SALES_STAGE_MEETING: "跟进",
    CaseManagement.SALES_STAGE_CASE: "交案",
    CaseManagement.SALES_STAGE_PAYMENT: "回款",
    CaseManagement.SALES_STAGE_WON: "赢单",
}


class CustomerSerializer(serializers.ModelSerializer):
    handler_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    handlers = serializers.SerializerMethodField(read_only=True)
    handler_names = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ["id", "create_datetime", "update_datetime"]

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
            try:
                primary_id = handler_ids[0] if isinstance(handler_ids, (list, tuple)) and handler_ids else None
            except Exception:
                primary_id = None
            CustomerService.set_handlers(instance, handler_ids, primary_id=primary_id, mode="replace")
        return instance

    def update(self, instance, validated_data):
        handler_ids = validated_data.pop("handler_ids", None)
        instance = super().update(instance, validated_data)
        if handler_ids is not None and handler_ids:
            try:
                primary_id = handler_ids[0] if isinstance(handler_ids, (list, tuple)) and handler_ids else None
            except Exception:
                primary_id = None
            CustomerService.set_handlers(instance, handler_ids, primary_id=primary_id, mode="replace")
        return instance


class CustomerImportTemplateSerializer(CustomerSerializer):
    """用于案源批量更新模板导出：客户状态/案件阶段显示为中文，并带出案件名称、案件编号、案件阶段。"""

    class Meta(CustomerSerializer.Meta):
        model = Customer
        fields = "__all__"
        read_only_fields = ["id", "create_datetime", "update_datetime"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        handler_names = data.get("handler_names") or []
        if handler_names:
            data["owner_user_names"] = "；".join(str(name) for name in handler_names if str(name).strip())
        else:
            data["owner_user_names"] = data.get("owner_user_name") or ""
        # 客户状态列：显示中文（公海/商机/跟进/交案/回款/赢单），便于模板中显示与下拉一致
        data["status"] = STATUS_TO_LABEL.get(instance.status) or instance.status
        # 案件名称、案件编号、案件阶段：从该客户下第一个案件带出（交案/回款/赢单时必有）
        first_case = (
            CaseManagement.objects.filter(customer_id=instance.id, is_deleted=False)
            .order_by("id")
            .first()
        )
        if first_case:
            data["case_name"] = first_case.case_name or ""
            data["case_number"] = first_case.case_number or ""
            data["case_stage"] = SALES_STAGE_TO_LABEL.get(first_case.sales_stage) or first_case.sales_stage or ""
        else:
            data["case_name"] = ""
            data["case_number"] = ""
            data["case_stage"] = ""
        return data
