from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customer_management", "0007_followup_record_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerPlan",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False, verbose_name="Id", help_text="Id")),
                ("description", models.CharField(blank=True, help_text="描述", max_length=255, null=True, verbose_name="描述")),
                ("modifier", models.CharField(blank=True, help_text="修改人", max_length=255, null=True, verbose_name="修改人")),
                ("dept_belong_id", models.CharField(blank=True, help_text="数据归属部门", max_length=255, null=True, verbose_name="数据归属部门")),
                ("update_datetime", models.DateTimeField(auto_now=True, blank=True, help_text="修改时间", null=True, verbose_name="修改时间")),
                ("create_datetime", models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间", null=True, verbose_name="创建时间")),
                ("is_deleted", models.BooleanField(help_text="是否软删除", verbose_name="是否软删除", db_index=True)),
                ("customer_id", models.IntegerField(db_index=True, help_text="客户ID", verbose_name="客户ID")),
                ("plan_type", models.CharField(choices=[("effective_case", "有效案源"), ("case_plan", "办案计划"), ("payment_followup", "回款跟进")], help_text="计划类型", max_length=32, verbose_name="计划类型")),
                ("title", models.CharField(help_text="计划标题", max_length=200, verbose_name="计划标题")),
                ("time_points", models.JSONField(blank=True, default=list, help_text="计划时间点列表", verbose_name="计划时间点")),
                ("remind_method", models.CharField(blank=True, help_text="提醒方式", max_length=20, null=True, verbose_name="提醒方式")),
                ("remind_advance", models.IntegerField(blank=True, help_text="提前提醒分钟数", null=True, verbose_name="提前提醒分钟数")),
                ("sync_to_schedule", models.BooleanField(default=True, help_text="同步到日程", verbose_name="同步到日程")),
                ("status", models.CharField(choices=[("pending", "待处理"), ("completed", "已完成"), ("cancelled", "已取消")], db_index=True, default="pending", help_text="计划状态", max_length=20, verbose_name="计划状态")),
                ("extra_data", models.JSONField(blank=True, default=dict, help_text="扩展数据（有效案源字段等）", verbose_name="扩展数据")),
                ("creator", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_query_name="creator_query", to="system.Users", help_text="创建人", verbose_name="创建人", db_constraint=False)),
            ],
            options={
                "verbose_name": "客户计划",
                "verbose_name_plural": "客户计划",
                "db_table": "customer_plan",
                "ordering": ["-create_datetime"],
            },
        ),
        migrations.CreateModel(
            name="CollectionProgress",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False, verbose_name="Id", help_text="Id")),
                ("description", models.CharField(blank=True, help_text="描述", max_length=255, null=True, verbose_name="描述")),
                ("modifier", models.CharField(blank=True, help_text="修改人", max_length=255, null=True, verbose_name="修改人")),
                ("dept_belong_id", models.CharField(blank=True, help_text="数据归属部门", max_length=255, null=True, verbose_name="数据归属部门")),
                ("update_datetime", models.DateTimeField(auto_now=True, blank=True, help_text="修改时间", null=True, verbose_name="修改时间")),
                ("create_datetime", models.DateTimeField(auto_now_add=True, blank=True, help_text="创建时间", null=True, verbose_name="创建时间")),
                ("is_deleted", models.BooleanField(help_text="是否软删除", verbose_name="是否软删除", db_index=True)),
                ("customer_id", models.IntegerField(db_index=True, help_text="客户ID", verbose_name="客户ID")),
                ("total_amount", models.DecimalField(decimal_places=2, help_text="总金额（万）", max_digits=12, verbose_name="总金额（万）")),
                ("installment_count", models.IntegerField(help_text="期数", verbose_name="期数")),
                ("mode", models.CharField(choices=[("average", "平均"), ("manual", "自选")], default="average", help_text="分配模式", max_length=20, verbose_name="分配模式")),
                ("installments", models.JSONField(blank=True, default=list, help_text="分期明细（amount/time）", verbose_name="分期明细")),
                ("remind_method", models.CharField(blank=True, help_text="提醒方式", max_length=20, null=True, verbose_name="提醒方式")),
                ("remind_advance", models.IntegerField(blank=True, help_text="提前提醒分钟数", null=True, verbose_name="提前提醒分钟数")),
                ("sync_to_schedule", models.BooleanField(default=True, help_text="同步到日程", verbose_name="同步到日程")),
                ("creator", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_query_name="creator_query", to="system.Users", help_text="创建人", verbose_name="创建人", db_constraint=False)),
            ],
            options={
                "verbose_name": "收款进度",
                "verbose_name_plural": "收款进度",
                "db_table": "customer_collection_progress",
                "ordering": ["-create_datetime"],
            },
        ),
        migrations.AddIndex(
            model_name="customerplan",
            index=models.Index(fields=["customer_id", "plan_type"], name="customer_p_customer_3d1f1f_idx"),
        ),
        migrations.AddIndex(
            model_name="customerplan",
            index=models.Index(fields=["status", "create_datetime"], name="customer_p_status_8dbd3e_idx"),
        ),
        migrations.AddIndex(
            model_name="collectionprogress",
            index=models.Index(fields=["customer_id", "create_datetime"], name="customer_c_customer_1f8b4c_idx"),
        ),
    ]
