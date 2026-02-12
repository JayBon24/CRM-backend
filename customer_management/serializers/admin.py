from rest_framework import serializers

from customer_management.models import (
    ApprovalTask,
    ApprovalHistory,
    FollowupRecord,
    VisitRecord,
    Contract,
    RecoveryPayment,
    LegalFee,
    TransferLog,
)


class ApprovalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalHistory
        fields = "__all__"


class ApprovalTaskSerializer(serializers.ModelSerializer):
    histories = ApprovalHistorySerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalTask
        fields = "__all__"
        read_only_fields = ["approval_chain", "current_step", "status", "histories"]


class FollowupRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowupRecord
        fields = "__all__"


class VisitRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitRecord
        fields = "__all__"


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = "__all__"


class RecoveryPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecoveryPayment
        fields = "__all__"


class LegalFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalFee
        fields = "__all__"


class TransferLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransferLog
        fields = "__all__"
