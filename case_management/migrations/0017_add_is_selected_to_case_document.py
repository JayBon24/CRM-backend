# Generated manually for adding is_selected field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('case_management', '0016_add_wps_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='casedocument',
            name='is_selected',
            field=models.BooleanField(default=False, verbose_name='是否选中', help_text='文档在批量打印中是否被选中'),
        ),
    ]

