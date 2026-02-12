from django.db import migrations, models
import django.db.models.deletion


def backfill_case_handlers(apps, schema_editor):
    CaseManagement = apps.get_model("case_management", "CaseManagement")
    CaseHandler = apps.get_model("case_management", "CaseHandler")
    db_alias = schema_editor.connection.alias
    handlers = []
    for case in CaseManagement.objects.using(db_alias).filter(owner_user_id__isnull=False):
        handlers.append(
            CaseHandler(
                case_id=case.id,
                user_id=case.owner_user_id,
                is_primary=True,
                sort=0,
            )
        )
    if handlers:
        CaseHandler.objects.using(db_alias).bulk_create(handlers, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("case_management", "0024_alter_casemanagement_sales_stage_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CaseHandler",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("create_datetime", models.DateTimeField(auto_now_add=True, null=True, verbose_name="创建时间")),
                ("update_datetime", models.DateTimeField(auto_now=True, null=True, verbose_name="更新时间")),
                ("is_primary", models.BooleanField(default=False, verbose_name="是否主经办人")),
                ("sort", models.IntegerField(default=0, verbose_name="排序")),
                (
                    "case",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="case_handler_links",
                        to="case_management.casemanagement",
                        verbose_name="案件",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="case_handler_links",
                        to="system.users",
                        verbose_name="经办人",
                    ),
                ),
            ],
            options={
                "verbose_name": "案件经办人",
                "verbose_name_plural": "案件经办人",
                "db_table": "case_handler",
                "ordering": ("sort", "id"),
                "unique_together": {("case", "user")},
            },
        ),
        migrations.AddField(
            model_name="casemanagement",
            name="handlers",
            field=models.ManyToManyField(
                blank=True,
                related_name="handled_cases",
                through="case_management.CaseHandler",
                to="system.users",
                verbose_name="经办人列表",
            ),
        ),
        migrations.RunPython(backfill_case_handlers, migrations.RunPython.noop),
    ]
