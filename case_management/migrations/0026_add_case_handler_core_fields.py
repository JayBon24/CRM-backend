from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("case_management", "0025_add_case_handlers"),
    ]

    operations = [
        migrations.AddField(
            model_name="casehandler",
            name="description",
            field=models.CharField(max_length=255, null=True, blank=True, verbose_name="描述", help_text="描述"),
        ),
        migrations.AddField(
            model_name="casehandler",
            name="creator",
            field=models.ForeignKey(
                to="system.users",
                related_query_name="creator_query",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                db_constraint=False,
                verbose_name="创建人",
                help_text="创建人",
            ),
        ),
        migrations.AddField(
            model_name="casehandler",
            name="modifier",
            field=models.CharField(max_length=255, null=True, blank=True, help_text="修改人", verbose_name="修改人"),
        ),
        migrations.AddField(
            model_name="casehandler",
            name="dept_belong_id",
            field=models.CharField(max_length=255, help_text="数据归属部门", null=True, blank=True, verbose_name="数据归属部门"),
        ),
    ]
