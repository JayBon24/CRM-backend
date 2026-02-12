# Generated manually to merge Client model into Customer model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer_management', '0003_schedule_schedulereminder_and_more'),
    ]

    operations = [
        # 删除 Client 表（如果存在）
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS `client`;",
            reverse_sql="",  # 不可逆操作
        ),
    ]

