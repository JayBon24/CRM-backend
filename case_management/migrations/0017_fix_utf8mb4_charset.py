# Generated manually to fix UTF-8 emoji support

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('case_management', '0016_regulationconversation_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            # 修改 regulation_message 表的字符集
            sql=[
                "ALTER TABLE regulation_message CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
                "ALTER TABLE regulation_conversation CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
            ],
            reverse_sql=[
                "ALTER TABLE regulation_message CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;",
                "ALTER TABLE regulation_conversation CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;",
            ]
        ),
    ]

