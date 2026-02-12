from django.db import models

from dvadmin.system.models import Users
from dvadmin.utils.models import CoreModel

from .customer import Customer


class Contract(CoreModel):
    STATUS_CHOICES = (
        ("pending", "待确认"),
        ("confirmed", "已确认"),
    )

    customer = models.ForeignKey(
        to=Customer,
        on_delete=models.CASCADE,
        related_name="contracts",
        verbose_name="关联客户",
        db_constraint=False,
    )
    case = models.ForeignKey(
        to="case_management.CaseManagement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_contracts",
        verbose_name="关联案件",
        db_constraint=False,
    )
    contract_no = models.CharField(max_length=64, verbose_name="合同编号")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="合同金额")
    term = models.CharField(max_length=64, verbose_name="合同期限", null=True, blank=True)
    service_type = models.CharField(max_length=64, verbose_name="服务类型", null=True, blank=True)
    client_subject = models.CharField(max_length=128, verbose_name="客户主体", null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", verbose_name="合同状态")
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="确认时间")
    confirmed_by = models.ForeignKey(
        to=Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_contracts",
        verbose_name="确认人",
        db_constraint=False,
    )
    attachments = models.JSONField(default=list, blank=True, null=True, verbose_name="附件")

    class Meta:
        db_table = "customer_contract"
        verbose_name = "客户合同"
        verbose_name_plural = "客户合同"

    def __str__(self):
        return self.contract_no


class RecoveryPayment(CoreModel):
    COLLECTION_CHOICES = (
        ("arbitration", "仲裁"),
        ("mediation", "调解"),
        ("litigation", "诉讼"),
    )

    customer = models.ForeignKey(
        to=Customer,
        on_delete=models.CASCADE,
        related_name="recovery_payments",
        verbose_name="关联客户",
        db_constraint=False,
    )
    pay_time = models.DateTimeField(verbose_name="回款时间")
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="回款金额")
    collection_category = models.CharField(max_length=32, choices=COLLECTION_CHOICES, verbose_name="催收类别")
    voucher_attachments = models.JSONField(default=list, blank=True, null=True, verbose_name="凭证附件")
    created_by = models.ForeignKey(
        to=Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_creators",
        verbose_name="创建人",
        db_constraint=False,
    )

    class Meta:
        db_table = "customer_recovery_payment"
        verbose_name = "回款记录"
        verbose_name_plural = "回款记录"

    def __str__(self):
        return f"{self.customer} - {self.amount}"


class LegalFee(CoreModel):
    customer = models.ForeignKey(
        to=Customer,
        on_delete=models.CASCADE,
        related_name="legal_fees",
        verbose_name="关联客户",
        db_constraint=False,
    )
    pay_time = models.DateTimeField(verbose_name="支付时间")
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="支付金额")
    voucher_attachments = models.JSONField(default=list, blank=True, null=True, verbose_name="凭证附件")
    created_by = models.ForeignKey(
        to=Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="legal_fee_creators",
        verbose_name="创建人",
        db_constraint=False,
    )

    class Meta:
        db_table = "customer_legal_fee"
        verbose_name = "律师费用"
        verbose_name_plural = "律师费用"

    def __str__(self):
        return f"{self.customer} - {self.amount}"
