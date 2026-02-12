from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ("customer_management", "0012_add_contract_case_relation"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReminderMessage",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False, verbose_name="Id")),
                ("description", models.CharField(blank=True, help_text="描述", max_length=255, null=True, verbose_name="描述")),
                ("modifier", models.CharField(blank=True, help_text="修改人", max_length=255, null=True, verbose_name="修改人")),
                ("dept_belong_id", models.CharField(blank=True, help_text="数据归属部门", max_length=255, null=True, verbose_name="数据归属部门")),
                ("update_datetime", models.DateTimeField(blank=True, help_text="修改时间", null=True, verbose_name="修改时间", auto_now=True)),
                ("create_datetime", models.DateTimeField(blank=True, help_text="创建时间", null=True, verbose_name="创建时间", auto_now_add=True)),
                ("reminder_type", models.CharField(choices=[("recycle_warning", "公海回收提醒"), ("followup_reminder", "跟进提醒"), ("other", "其他")], help_text="提醒类型：recycle_warning(公海回收提醒)、followup_reminder(跟进提醒)", max_length=50, verbose_name="提醒类型")),
                ("title", models.CharField(help_text="提醒标题", max_length=200, verbose_name="提醒标题")),
                ("content", models.TextField(help_text="提醒内容", verbose_name="提醒内容")),
                ("related_type", models.CharField(blank=True, help_text="关联类型：customer(客户)", max_length=50, null=True, verbose_name="关联类型")),
                ("related_id", models.IntegerField(blank=True, help_text="关联对象ID（如客户ID）", null=True, verbose_name="关联对象ID")),
                ("is_read", models.BooleanField(default=False, db_index=True, verbose_name="是否已读", help_text="是否已读")),
                ("read_time", models.DateTimeField(blank=True, help_text="已读时间", null=True, verbose_name="已读时间")),
                ("extra_data", models.JSONField(blank=True, default=dict, help_text="额外数据（JSON格式，如客户名称、经办人信息等）", null=True, verbose_name="额外数据")),
                ("creator", models.ForeignKey(blank=True, db_constraint=False, help_text="创建人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_query_name="creator_query", related_name="creator_query", to=settings.AUTH_USER_MODEL, verbose_name="创建人")),
                ("recipient", models.ForeignKey(blank=True, db_constraint=False, help_text="接受提醒的用户（总所账号）", null=True, on_delete=django.db.models.deletion.CASCADE, related_name="received_reminders", to=settings.AUTH_USER_MODEL, verbose_name="接收人")),
            ],
            options={
                "db_table": "reminder_message",
                "verbose_name": "提醒消息",
                "verbose_name_plural": "提醒消息",
                "ordering": ["-create_datetime"],
                "indexes": [
                    models.Index(fields=["recipient", "is_read"], name="reminder_recipient_is_read_idx"),
                    models.Index(fields=["reminder_type", "is_read"], name="reminder_type_is_read_idx"),
                    models.Index(fields=["create_datetime"], name="reminder_create_dt_idx"),
                ],
            },
        ),
    ]
