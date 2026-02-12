# Generated manually on 2025-10-30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('case_management', '0014_add_sort_and_print_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='casedocument',
            name='sort_order',
            field=models.IntegerField(
                default=0, 
                verbose_name='排序序号', 
                help_text='排序序号，数值越小越靠前（从模板继承）',
                db_index=True
            ),
        ),
    ]

