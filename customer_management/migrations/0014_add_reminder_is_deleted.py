from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customer_management", "0013_create_reminder_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="remindermessage",
            name="is_deleted",
            field=models.BooleanField(default=False, verbose_name="是否软删除", help_text="是否软删除", db_index=True),
        ),
    ]
