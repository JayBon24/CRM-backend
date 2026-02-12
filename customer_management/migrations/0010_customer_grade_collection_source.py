from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customer_management", "0009_rename_customer_c_customer_1f8b4c_idx_customer_co_custome_878cba_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="grade_source",
            field=models.CharField(blank=True, choices=[("ai", "AI"), ("manual", "manual")], default="ai", max_length=16, null=True, verbose_name="客户等级来源"),
        ),
        migrations.AddField(
            model_name="customer",
            name="collection_source",
            field=models.CharField(blank=True, choices=[("ai", "AI"), ("manual", "manual")], default="ai", max_length=16, null=True, verbose_name="催收类别来源"),
        ),
    ]
