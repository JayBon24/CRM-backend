# Generated manually to add organization fields to Users model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0004_add_user_role_level_fields'),
    ]

    operations = [
        # 添加总部ID字段
        migrations.AddField(
            model_name='users',
            name='headquarters_id',
            field=models.IntegerField(
                blank=True,
                db_index=True,
                help_text='所属总部ID',
                null=True,
                verbose_name='所属总部ID'
            ),
        ),
        
        # 添加分所ID字段
        migrations.AddField(
            model_name='users',
            name='branch_id',
            field=models.IntegerField(
                blank=True,
                db_index=True,
                help_text='所属分所ID',
                null=True,
                verbose_name='所属分所ID'
            ),
        ),
        
        # 添加团队ID字段
        migrations.AddField(
            model_name='users',
            name='team_id',
            field=models.IntegerField(
                blank=True,
                db_index=True,
                help_text='所属团队ID',
                null=True,
                verbose_name='所属团队ID'
            ),
        ),
    ]
