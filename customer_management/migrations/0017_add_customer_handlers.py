from django.db import migrations, models
import django.db.models.deletion


def backfill_customer_handlers(apps, schema_editor):
    Customer = apps.get_model("customer_management", "Customer")
    CustomerHandler = apps.get_model("customer_management", "CustomerHandler")
    db_alias = schema_editor.connection.alias
    handlers = []
    for customer in Customer.objects.using(db_alias).filter(owner_user_id__isnull=False):
        handlers.append(
            CustomerHandler(
                customer_id=customer.id,
                user_id=customer.owner_user_id,
                is_primary=True,
                sort=0,
            )
        )
    if handlers:
        CustomerHandler.objects.using(db_alias).bulk_create(handlers, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("customer_management", "0016_add_client_category_last_deal_time"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerHandler",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("create_datetime", models.DateTimeField(auto_now_add=True, null=True, verbose_name="创建时间")),
                ("update_datetime", models.DateTimeField(auto_now=True, null=True, verbose_name="更新时间")),
                ("is_primary", models.BooleanField(default=False, verbose_name="是否主经办人")),
                ("sort", models.IntegerField(default=0, verbose_name="排序")),
                (
                    "customer",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="customer_handler_links",
                        to="customer_management.customer",
                        verbose_name="客户",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="customer_handler_links",
                        to="system.users",
                        verbose_name="经办人",
                    ),
                ),
            ],
            options={
                "verbose_name": "客户经办人",
                "verbose_name_plural": "客户经办人",
                "db_table": "customer_handler",
                "ordering": ("sort", "id"),
                "unique_together": {("customer", "user")},
            },
        ),
        migrations.AddField(
            model_name="customer",
            name="handlers",
            field=models.ManyToManyField(
                blank=True,
                related_name="handled_customers",
                through="customer_management.CustomerHandler",
                to="system.users",
                verbose_name="经办人列表",
            ),
        ),
        migrations.RunPython(backfill_customer_handlers, migrations.RunPython.noop),
    ]
