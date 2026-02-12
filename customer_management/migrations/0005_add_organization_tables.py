# Generated manually to add organization tables (Headquarters, Branch, Team)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('customer_management', '0004_merge_client_to_customer'),
    ]

    operations = [
        # 创建 Headquarters 表
        migrations.CreateModel(
            name='Headquarters',
            fields=[
                ('id', models.BigAutoField(help_text='Id', primary_key=True, serialize=False, verbose_name='Id')),
                ('description', models.CharField(blank=True, help_text='描述', max_length=255, null=True, verbose_name='描述')),
                ('modifier', models.CharField(blank=True, help_text='修改人', max_length=255, null=True, verbose_name='修改人')),
                ('dept_belong_id', models.CharField(blank=True, help_text='数据归属部门', max_length=255, null=True, verbose_name='数据归属部门')),
                ('update_datetime', models.DateTimeField(auto_now=True, help_text='修改时间', null=True, verbose_name='修改时间')),
                ('create_datetime', models.DateTimeField(auto_now_add=True, help_text='创建时间', null=True, verbose_name='创建时间')),
                ('name', models.CharField(help_text='总部名称', max_length=100, verbose_name='总部名称')),
                ('code', models.CharField(help_text='总部编码', max_length=50, unique=True, verbose_name='总部编码')),
                ('address', models.CharField(blank=True, help_text='地址', max_length=500, null=True, verbose_name='地址')),
                ('contact_person', models.CharField(blank=True, help_text='负责人', max_length=100, null=True, verbose_name='负责人')),
                ('contact_phone', models.CharField(blank=True, help_text='联系电话', max_length=50, null=True, verbose_name='联系电话')),
                ('status', models.BooleanField(default=True, help_text='状态：True-启用，False-停用', verbose_name='状态')),
                ('sort', models.IntegerField(default=0, help_text='排序', verbose_name='排序')),
                ('creator', models.ForeignKey(db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_query_name='creator_query', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
            ],
            options={
                'verbose_name': '总部',
                'verbose_name_plural': '总部',
                'db_table': 'organization_headquarters',
                'ordering': ['sort', 'id'],
            },
        ),
        
        # 创建 Branch 表
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.BigAutoField(help_text='Id', primary_key=True, serialize=False, verbose_name='Id')),
                ('description', models.CharField(blank=True, help_text='描述', max_length=255, null=True, verbose_name='描述')),
                ('modifier', models.CharField(blank=True, help_text='修改人', max_length=255, null=True, verbose_name='修改人')),
                ('dept_belong_id', models.CharField(blank=True, help_text='数据归属部门', max_length=255, null=True, verbose_name='数据归属部门')),
                ('update_datetime', models.DateTimeField(auto_now=True, help_text='修改时间', null=True, verbose_name='修改时间')),
                ('create_datetime', models.DateTimeField(auto_now_add=True, help_text='创建时间', null=True, verbose_name='创建时间')),
                ('name', models.CharField(help_text='分所名称', max_length=100, verbose_name='分所名称')),
                ('code', models.CharField(help_text='分所编码', max_length=50, unique=True, verbose_name='分所编码')),
                ('address', models.CharField(blank=True, help_text='地址', max_length=500, null=True, verbose_name='地址')),
                ('contact_person', models.CharField(blank=True, help_text='负责人', max_length=100, null=True, verbose_name='负责人')),
                ('contact_phone', models.CharField(blank=True, help_text='联系电话', max_length=50, null=True, verbose_name='联系电话')),
                ('status', models.BooleanField(default=True, help_text='状态：True-启用，False-停用', verbose_name='状态')),
                ('sort', models.IntegerField(default=0, help_text='排序', verbose_name='排序')),
                ('headquarters', models.ForeignKey(db_constraint=False, help_text='所属总部', on_delete=django.db.models.deletion.CASCADE, related_name='branches', to='customer_management.headquarters', verbose_name='所属总部')),
                ('creator', models.ForeignKey(db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_query_name='creator_query', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
            ],
            options={
                'verbose_name': '分所',
                'verbose_name_plural': '分所',
                'db_table': 'organization_branch',
                'ordering': ['sort', 'id'],
            },
        ),
        
        # 创建 Team 表
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.BigAutoField(help_text='Id', primary_key=True, serialize=False, verbose_name='Id')),
                ('description', models.CharField(blank=True, help_text='描述', max_length=255, null=True, verbose_name='描述')),
                ('modifier', models.CharField(blank=True, help_text='修改人', max_length=255, null=True, verbose_name='修改人')),
                ('dept_belong_id', models.CharField(blank=True, help_text='数据归属部门', max_length=255, null=True, verbose_name='数据归属部门')),
                ('update_datetime', models.DateTimeField(auto_now=True, help_text='修改时间', null=True, verbose_name='修改时间')),
                ('create_datetime', models.DateTimeField(auto_now_add=True, help_text='创建时间', null=True, verbose_name='创建时间')),
                ('name', models.CharField(help_text='团队名称', max_length=100, verbose_name='团队名称')),
                ('code', models.CharField(help_text='团队编码', max_length=50, unique=True, verbose_name='团队编码')),
                ('leader', models.CharField(blank=True, help_text='团队负责人', max_length=100, null=True, verbose_name='团队负责人')),
                ('contact_phone', models.CharField(blank=True, help_text='联系电话', max_length=50, null=True, verbose_name='联系电话')),
                ('status', models.BooleanField(default=True, help_text='状态：True-启用，False-停用', verbose_name='状态')),
                ('sort', models.IntegerField(default=0, help_text='排序', verbose_name='排序')),
                ('branch', models.ForeignKey(db_constraint=False, help_text='所属分所', on_delete=django.db.models.deletion.CASCADE, related_name='teams', to='customer_management.branch', verbose_name='所属分所')),
                ('creator', models.ForeignKey(db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_query_name='creator_query', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
            ],
            options={
                'verbose_name': '团队',
                'verbose_name_plural': '团队',
                'db_table': 'organization_team',
                'ordering': ['sort', 'id'],
            },
        ),
        
        # 添加索引
        migrations.AddIndex(
            model_name='branch',
            index=models.Index(fields=['headquarters', 'status'], name='org_branch_hq_status_idx'),
        ),
        migrations.AddIndex(
            model_name='team',
            index=models.Index(fields=['branch', 'status'], name='org_team_branch_status_idx'),
        ),
    ]
