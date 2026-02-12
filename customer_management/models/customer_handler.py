# -*- coding: utf-8 -*-
"""
客户经办人中间表。
表结构以迁移 0017_add_customer_handlers 为准，仅含 id/create_datetime/update_datetime/customer/user/is_primary/sort，
不继承 CoreModel，避免 INSERT 时出现表中不存在的 description 等列。
"""
from django.db import models

from dvadmin.system.models import Users


class CustomerHandler(models.Model):
    """客户-经办人多对多中间表（与迁移 0017 表结构一致）"""
    id = models.BigAutoField(primary_key=True, auto_created=True, serialize=False, verbose_name="ID")
    create_datetime = models.DateTimeField(auto_now_add=True, null=True, verbose_name="创建时间")
    update_datetime = models.DateTimeField(auto_now=True, null=True, verbose_name="更新时间")
    customer = models.ForeignKey(
        "customer_management.Customer",
        on_delete=models.CASCADE,
        related_name="customer_handler_links",
        db_constraint=False,
        verbose_name="客户",
    )
    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="customer_handler_links",
        db_constraint=False,
        verbose_name="经办人",
    )
    is_primary = models.BooleanField(default=False, verbose_name="是否主经办人")
    sort = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "customer_handler"
        verbose_name = "客户经办人"
        verbose_name_plural = verbose_name
        unique_together = ("customer", "user")
        ordering = ("sort", "id")

    def __str__(self):
        return f"{self.customer_id}-{self.user_id}"
