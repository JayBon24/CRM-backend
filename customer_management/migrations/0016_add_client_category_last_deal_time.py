from django.db import migrations, models


def _get_existing_columns(schema_editor, table_name):
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(cursor, table_name)
    return {col.name for col in description}


def ensure_columns_exist(apps, schema_editor):
    table_name = "customer"
    existing_columns = _get_existing_columns(schema_editor, table_name)
    with schema_editor.connection.cursor() as cursor:
        if "client_category" not in existing_columns:
            cursor.execute(
                "ALTER TABLE customer ADD COLUMN client_category varchar(16) NULL"
            )
        if "last_deal_time" not in existing_columns:
            cursor.execute(
                "ALTER TABLE customer ADD COLUMN last_deal_time datetime NULL"
            )


def forwards_fill_category_and_deal_time(apps, schema_editor):
    Customer = apps.get_model("customer_management", "Customer")
    import random

    categories = ["construction", "material"]
    normalize_map = {
        "建工": "construction",
        "建材": "material",
    }

    # 随机填充客户类别（仅填充为空的记录）
    mapped_qs = Customer.objects.filter(client_category__in=list(normalize_map.keys()))
    for customer in mapped_qs.iterator():
        customer.client_category = normalize_map.get(customer.client_category, customer.client_category)
        customer.save(update_fields=["client_category"])

    missing_qs = Customer.objects.filter(client_category__isnull=True) | Customer.objects.filter(client_category="")
    for customer in missing_qs.iterator():
        customer.client_category = random.choice(categories)
        customer.save(update_fields=["client_category"])

    # 填充最后成交时间（仅 WON 且为空）
    won_qs = Customer.objects.filter(status="WON", last_deal_time__isnull=True)
    for customer in won_qs.iterator():
        fallback = customer.update_datetime or customer.create_datetime
        if fallback:
            customer.last_deal_time = fallback
            customer.save(update_fields=["last_deal_time"])


def enforce_client_category_not_null(apps, schema_editor):
    table_name = "customer"
    existing_columns = _get_existing_columns(schema_editor, table_name)
    if "client_category" not in existing_columns:
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE customer MODIFY client_category varchar(16) NOT NULL"
        )


def backwards_clear_category_and_deal_time(apps, schema_editor):
    Customer = apps.get_model("customer_management", "Customer")
    Customer.objects.update(client_category=None, last_deal_time=None)


class Migration(migrations.Migration):

    dependencies = [
        ("customer_management", "0015_reminder_fields_and_other_type_content"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_columns_exist, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="customer",
                    name="client_category",
                    field=models.CharField(
                        max_length=16,
                        choices=[("construction", "建工"), ("material", "建材")],
                        null=True,
                        blank=True,
                        verbose_name="客户类别",
                    ),
                ),
                migrations.AddField(
                    model_name="customer",
                    name="last_deal_time",
                    field=models.DateTimeField(null=True, blank=True, verbose_name="最后成交时间"),
                ),
            ],
        ),
        migrations.RunPython(forwards_fill_category_and_deal_time, backwards_clear_category_and_deal_time),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(enforce_client_category_not_null, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="customer",
                    name="client_category",
                    field=models.CharField(
                        max_length=16,
                        choices=[("construction", "建工"), ("material", "建材")],
                        null=False,
                        blank=False,
                        verbose_name="客户类别",
                    ),
                ),
            ],
        ),
    ]
