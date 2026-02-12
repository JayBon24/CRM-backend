from django.db import models

from dvadmin.system.models import Users
from dvadmin.utils.models import CoreModel

from .customer import Customer


class VisitRecord(CoreModel):
    LOCATION_STATUS_CHOICES = (
        ("success", "定位成功"),
        ("fail", "定位失败"),
        ("denied", "拒绝"),
        ("offline", "离线"),
    )

    customer = models.ForeignKey(
        to=Customer,
        on_delete=models.CASCADE,
        related_name="visits",
        verbose_name="关联客户",
        db_constraint=False,
    )
    visit_time = models.DateTimeField(verbose_name="拜访时间")
    duration = models.IntegerField(verbose_name="拜访时长（分钟）", default=0)
    location_status = models.CharField(max_length=32, choices=LOCATION_STATUS_CHOICES, verbose_name="定位状态")
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="经度")
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="纬度")
    address = models.CharField(max_length=255, verbose_name="拜访地址", null=True, blank=True)
    participants = models.JSONField(default=list, blank=True, null=True, verbose_name="参与人员")
    attachments = models.JSONField(default=list, blank=True, null=True, verbose_name="附件")
    created_by = models.ForeignKey(
        to=Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visit_creators",
        verbose_name="创建人",
        db_constraint=False,
    )

    class Meta:
        db_table = "customer_visit_record"
        verbose_name = "拜访记录"
        verbose_name_plural = "拜访记录"

    def __str__(self):
        return f"{self.customer} - {self.visit_time}"
