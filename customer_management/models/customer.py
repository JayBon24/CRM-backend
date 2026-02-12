from django.db import models

from dvadmin.system.models import Users
from dvadmin.utils.models import CoreModel, SoftDeleteModel


class Customer(CoreModel, SoftDeleteModel):
    STATUS_PUBLIC_POOL = "PUBLIC_POOL"
    STATUS_FOLLOW_UP = "FOLLOW_UP"
    STATUS_CASE = "CASE"
    STATUS_PAYMENT = "PAYMENT"
    STATUS_WON = "WON"
    STATUS_CHOICES = (
        (STATUS_PUBLIC_POOL, "公海"),
        (STATUS_FOLLOW_UP, "跟进"),
        (STATUS_CASE, "交案"),
        (STATUS_PAYMENT, "回款"),
        (STATUS_WON, "赢单"),
    )

    SALES_STAGE_PUBLIC = "PUBLIC_POOL"
    SALES_STAGE_BLANK = "BLANK"
    SALES_STAGE_MEETING = "MEETING"
    SALES_STAGE_CASE = "CASE"
    SALES_STAGE_PAYMENT = "PAYMENT"
    SALES_STAGE_WON = "WON"
    SALES_STAGE_CHOICES = (
        (SALES_STAGE_PUBLIC, "公海"),
        (SALES_STAGE_BLANK, "跟进-空白"),
        (SALES_STAGE_MEETING, "跟进-面谈"),
        (SALES_STAGE_CASE, "交案"),
        (SALES_STAGE_PAYMENT, "回款"),
        (SALES_STAGE_WON, "赢单"),
    )

    GRADE_CHOICES = (
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
        ("D", "D"),
    )
    CATEGORY_CHOICES = (
        ("construction", "建工"),
        ("material", "建材"),
    )
    SOURCE_CHOICES = (
        ("ai", "AI"),
        ("manual", "manual"),
    )

    RISK_LEVEL_CHOICES = (
        ("none", "无风险"),
        ("low", "低风险"),
        ("medium", "中风险"),
        ("high", "高风险"),
    )

    LOCATION_STATUS_CHOICES = (
        ("success", "定位成功"),
        ("fail", "定位失败"),
        ("denied", "拒绝"),
        ("offline", "离线"),
    )

    name = models.CharField(max_length=200, verbose_name="客户名称", help_text="客户名称")
    contact_person = models.CharField(max_length=100, verbose_name="联系人", help_text="联系人", null=True, blank=True)
    contact_phone = models.CharField(max_length=50, verbose_name="联系电话", help_text="联系电话", null=True, blank=True)
    contact_email = models.CharField(max_length=200, verbose_name="联系邮箱", help_text="联系邮箱", null=True, blank=True)
    address = models.CharField(max_length=500, verbose_name="地址", help_text="地址", null=True, blank=True)
    credit_code = models.CharField(max_length=100, verbose_name="统一社会信用代码", help_text="统一社会信用代码", null=True, blank=True)
    remark = models.TextField(verbose_name="备注", help_text="备注", null=True, blank=True)

    owner_user = models.ForeignKey(
        to=Users,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_customers",
        verbose_name="经办人",
        help_text="经办人",
        db_constraint=False,
    )
    owner_user_name = models.CharField(max_length=150, verbose_name="经办人姓名", null=True, blank=True)
    handlers = models.ManyToManyField(
        Users,
        through="customer_management.CustomerHandler",
        through_fields=("customer", "user"),
        related_name="handled_customers",
        blank=True,
        verbose_name="经办人列表",
    )
    team_id = models.IntegerField(null=True, blank=True, verbose_name="团队 ID", help_text="团队 ID", db_index=True)
    branch_id = models.IntegerField(null=True, blank=True, verbose_name="分所 ID", help_text="分所 ID", db_index=True)
    hq_id = models.IntegerField(null=True, blank=True, verbose_name="总部 ID", help_text="总部 ID", db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PUBLIC_POOL, verbose_name="生命周期状态")
    sales_stage = models.CharField(max_length=20, choices=SALES_STAGE_CHOICES, default=SALES_STAGE_PUBLIC, verbose_name="展业状态")
    client_category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, verbose_name="客户类别")
    client_grade = models.CharField(max_length=2, choices=GRADE_CHOICES, null=True, blank=True, verbose_name="客户等级")
    grade_source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default="ai", null=True, blank=True, verbose_name="客户等级来源")
    collection_category = models.CharField(max_length=64, null=True, blank=True, verbose_name="催收类别")
    collection_source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default="ai", null=True, blank=True, verbose_name="催收类别来源")
    source_channel = models.CharField(max_length=64, null=True, blank=True, verbose_name="来源渠道")
    referrer = models.CharField(max_length=64, null=True, blank=True, verbose_name="引荐人")
    valid_visit_count = models.IntegerField(default=0, verbose_name="有效拜访次数")
    followup_count = models.IntegerField(default=0, verbose_name="跟进次数")
    recycle_risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default="none", verbose_name="回收风险等级")
    recycle_deadline = models.DateField(null=True, blank=True, verbose_name="回收截止时间")
    last_deal_time = models.DateTimeField(null=True, blank=True, verbose_name="最后成交时间")
    location_status = models.CharField(max_length=32, choices=LOCATION_STATUS_CHOICES, null=True, blank=True, verbose_name="定位状态")
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="经度")
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="纬度")

    class Meta:
        db_table = "customer"
        verbose_name = "客户"
        verbose_name_plural = "客户"
        ordering = ["-id"]

    def __str__(self):
        return self.name

    def calculate_sales_stage(self):
        if self.status == self.STATUS_PUBLIC_POOL:
            return self.SALES_STAGE_PUBLIC
        if self.status == self.STATUS_FOLLOW_UP:
            return self.SALES_STAGE_MEETING if self.valid_visit_count > 0 else self.SALES_STAGE_BLANK
        if self.status == self.STATUS_CASE:
            return self.SALES_STAGE_CASE
        if self.status == self.STATUS_PAYMENT:
            return self.SALES_STAGE_PAYMENT
        if self.status == self.STATUS_WON:
            return self.SALES_STAGE_WON
        return self.sales_stage or self.SALES_STAGE_PUBLIC

    def save(self, *args, **kwargs):
        self.sales_stage = self.calculate_sales_stage()
        super().save(*args, **kwargs)

    class Meta:
        db_table = "customer"
        verbose_name = "客户"
        verbose_name_plural = "客户"
        ordering = ["-id"]

    def __str__(self):
        return self.name
