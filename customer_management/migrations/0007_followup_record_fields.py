from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("customer_management", "0006_approvalhistory_approvaltask_contract_legalfee_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="followuprecord",
            name="method_other",
            field=models.CharField(blank=True, help_text="跟进方式为其他时填写", max_length=100, null=True, verbose_name="其他跟进方式"),
        ),
        migrations.AddField(
            model_name="followuprecord",
            name="summary",
            field=models.TextField(blank=True, help_text="跟进摘要", null=True, verbose_name="跟进摘要"),
        ),
        migrations.AddField(
            model_name="followuprecord",
            name="conclusion",
            field=models.TextField(blank=True, help_text="关键结论", null=True, verbose_name="关键结论"),
        ),
        migrations.AddField(
            model_name="followuprecord",
            name="duration",
            field=models.IntegerField(blank=True, help_text="洽谈时长（分钟）", null=True, verbose_name="洽谈时长（分钟）"),
        ),
        migrations.AddField(
            model_name="followuprecord",
            name="location_status",
            field=models.CharField(blank=True, choices=[("success", "成功"), ("fail", "失败"), ("denied", "拒绝授权"), ("offline", "无网络")], default="success", help_text="定位状态", max_length=20, null=True, verbose_name="定位状态"),
        ),
        migrations.AddField(
            model_name="followuprecord",
            name="lng",
            field=models.DecimalField(blank=True, decimal_places=6, help_text="经度", max_digits=10, null=True, verbose_name="经度"),
        ),
        migrations.AddField(
            model_name="followuprecord",
            name="lat",
            field=models.DecimalField(blank=True, decimal_places=6, help_text="纬度", max_digits=10, null=True, verbose_name="纬度"),
        ),
        migrations.AddField(
            model_name="followuprecord",
            name="address",
            field=models.CharField(blank=True, help_text="跟进地点", max_length=500, null=True, verbose_name="跟进地点"),
        ),
        migrations.AddField(
            model_name="followuprecord",
            name="internal_participants",
            field=models.JSONField(blank=True, default=list, help_text="内部参与人员（用户ID列表）", verbose_name="内部参与人员"),
        ),
        migrations.AddField(
            model_name="followuprecord",
            name="customer_participants",
            field=models.JSONField(blank=True, default=list, help_text="客户方参与人员（自定义列表）", verbose_name="客户方参与人员"),
        ),
        migrations.AddField(
            model_name="followuprecord",
            name="attachments",
            field=models.JSONField(blank=True, default=list, help_text="附件列表（JSON）", verbose_name="附件列表"),
        ),
        migrations.AddField(
            model_name="followuprecord",
            name="next_followup_time",
            field=models.DateTimeField(blank=True, db_index=True, help_text="下次跟进时间", null=True, verbose_name="下次跟进时间"),
        ),
        migrations.AlterField(
            model_name="followuprecord",
            name="followup_time",
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now, help_text="跟进时间", verbose_name="跟进时间"),
        ),
    ]
