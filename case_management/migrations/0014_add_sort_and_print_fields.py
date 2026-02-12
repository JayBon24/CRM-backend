# Generated manually on 2025-10-30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('case_management', '0013_casefolder_alter_casedocument_options_and_more'),
    ]

    operations = [
        # 为 DocumentTemplate 添加 sort_order 字段
        migrations.AddField(
            model_name='documenttemplate',
            name='sort_order',
            field=models.IntegerField(
                db_index=True,
                default=0,
                help_text='排序序号，数值越小越靠前',
                verbose_name='排序序号'
            ),
        ),
        # 为 DocumentTemplate 添加 print_count 字段
        migrations.AddField(
            model_name='documenttemplate',
            name='print_count',
            field=models.IntegerField(
                default=0,
                help_text='模板被打印的次数',
                verbose_name='打印数量'
            ),
        ),
        # 为 CaseDocument 添加 print_count 字段
        migrations.AddField(
            model_name='casedocument',
            name='print_count',
            field=models.IntegerField(
                default=0,
                help_text='文档被打印的次数',
                verbose_name='打印数量'
            ),
        ),
        # 修改 DocumentTemplate 的 Meta.ordering
        migrations.AlterModelOptions(
            name='documenttemplate',
            options={
                'ordering': ['sort_order', 'id'],
                'verbose_name': '文档模板',
                'verbose_name_plural': '文档模板'
            },
        ),
    ]

