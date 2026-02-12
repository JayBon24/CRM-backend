# Generated manually for report system tables

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('customer_management', '0001_initial'),
    ]

    operations = [
        # 创建 Client 表
        migrations.CreateModel(
            name='Client',
            fields=[
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否软删除', verbose_name='是否软删除')),
                ('id', models.BigAutoField(help_text='Id', primary_key=True, serialize=False, verbose_name='Id')),
                ('description', models.CharField(blank=True, help_text='描述', max_length=255, null=True, verbose_name='描述')),
                ('modifier', models.CharField(blank=True, help_text='修改人', max_length=255, null=True, verbose_name='修改人')),
                ('dept_belong_id', models.CharField(blank=True, help_text='数据归属部门', max_length=255, null=True, verbose_name='数据归属部门')),
                ('update_datetime', models.DateTimeField(auto_now=True, help_text='修改时间', null=True, verbose_name='修改时间')),
                ('create_datetime', models.DateTimeField(auto_now_add=True, help_text='创建时间', null=True, verbose_name='创建时间')),
                ('name', models.CharField(help_text='客户名称', max_length=200, verbose_name='客户名称')),
                ('contact_person', models.CharField(blank=True, help_text='联系人', max_length=100, null=True, verbose_name='联系人')),
                ('contact_phone', models.CharField(blank=True, help_text='联系电话', max_length=50, null=True, verbose_name='联系电话')),
                ('status', models.CharField(choices=[('PUBLIC_POOL', '公海'), ('FOLLOW_UP', '跟进'), ('CASE', '交案'), ('PAYMENT', '回款'), ('WON', '赢单'), ('LOST', '输单')], db_index=True, default='PUBLIC_POOL', help_text='客户状态', max_length=20, verbose_name='客户状态')),
                ('grade', models.CharField(choices=[('A', 'A级'), ('B', 'B级'), ('C', 'C级'), ('D', 'D级')], db_index=True, default='C', help_text='客户等级', max_length=10, verbose_name='客户等级')),
                ('source', models.CharField(choices=[('ONLINE', '线上'), ('OFFLINE', '线下'), ('REFERRAL', '转介绍'), ('OTHER', '其他')], db_index=True, default='OTHER', help_text='客户来源', max_length=20, verbose_name='客户来源')),
                ('owner_user_id', models.IntegerField(blank=True, db_index=True, help_text='负责人ID', null=True, verbose_name='负责人ID')),
                ('team_id', models.IntegerField(blank=True, db_index=True, help_text='团队ID', null=True, verbose_name='团队ID')),
                ('branch_id', models.IntegerField(blank=True, db_index=True, help_text='分所ID', null=True, verbose_name='分所ID')),
                ('remark', models.TextField(blank=True, help_text='备注', null=True, verbose_name='备注')),
                ('creator', models.ForeignKey(db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_query_name='creator_query', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
            ],
            options={
                'verbose_name': '客户线索',
                'verbose_name_plural': '客户线索',
                'db_table': 'client',
                'ordering': ['-id'],
            },
        ),
        
        # 创建 FollowupRecord 表
        migrations.CreateModel(
            name='FollowupRecord',
            fields=[
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否软删除', verbose_name='是否软删除')),
                ('id', models.BigAutoField(help_text='Id', primary_key=True, serialize=False, verbose_name='Id')),
                ('description', models.CharField(blank=True, help_text='描述', max_length=255, null=True, verbose_name='描述')),
                ('modifier', models.CharField(blank=True, help_text='修改人', max_length=255, null=True, verbose_name='修改人')),
                ('dept_belong_id', models.CharField(blank=True, help_text='数据归属部门', max_length=255, null=True, verbose_name='数据归属部门')),
                ('update_datetime', models.DateTimeField(auto_now=True, help_text='修改时间', null=True, verbose_name='修改时间')),
                ('create_datetime', models.DateTimeField(auto_now_add=True, help_text='创建时间', null=True, verbose_name='创建时间')),
                ('client_id', models.IntegerField(db_index=True, help_text='客户ID', verbose_name='客户ID')),
                ('user_id', models.IntegerField(db_index=True, help_text='跟进人ID', verbose_name='跟进人ID')),
                ('method', models.CharField(choices=[('PHONE', '电话'), ('WECHAT', '微信'), ('EMAIL', '邮件'), ('VISIT', '拜访'), ('OTHER', '其他')], default='PHONE', help_text='跟进方式', max_length=20, verbose_name='跟进方式')),
                ('content', models.TextField(help_text='跟进内容', verbose_name='跟进内容')),
                ('followup_time', models.DateTimeField(auto_now_add=True, db_index=True, help_text='跟进时间', verbose_name='跟进时间')),
                ('creator', models.ForeignKey(db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_query_name='creator_query', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
            ],
            options={
                'verbose_name': '跟进记录',
                'verbose_name_plural': '跟进记录',
                'db_table': 'followup_record',
                'ordering': ['-followup_time'],
            },
        ),
        
        # 创建 VisitRecord 表
        migrations.CreateModel(
            name='VisitRecord',
            fields=[
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否软删除', verbose_name='是否软删除')),
                ('id', models.BigAutoField(help_text='Id', primary_key=True, serialize=False, verbose_name='Id')),
                ('description', models.CharField(blank=True, help_text='描述', max_length=255, null=True, verbose_name='描述')),
                ('modifier', models.CharField(blank=True, help_text='修改人', max_length=255, null=True, verbose_name='修改人')),
                ('dept_belong_id', models.CharField(blank=True, help_text='数据归属部门', max_length=255, null=True, verbose_name='数据归属部门')),
                ('update_datetime', models.DateTimeField(auto_now=True, help_text='修改时间', null=True, verbose_name='修改时间')),
                ('create_datetime', models.DateTimeField(auto_now_add=True, help_text='创建时间', null=True, verbose_name='创建时间')),
                ('client_id', models.IntegerField(db_index=True, help_text='客户ID', verbose_name='客户ID')),
                ('user_id', models.IntegerField(db_index=True, help_text='拜访人ID', verbose_name='拜访人ID')),
                ('visit_time', models.DateTimeField(db_index=True, help_text='拜访时间', verbose_name='拜访时间')),
                ('duration', models.IntegerField(blank=True, help_text='洽谈时长（分钟）', null=True, verbose_name='洽谈时长（分钟）')),
                ('content', models.TextField(blank=True, help_text='拜访内容', null=True, verbose_name='拜访内容')),
                ('location_status', models.CharField(choices=[('success', '成功'), ('failed', '失败'), ('pending', '待定位')], default='pending', help_text='定位状态', max_length=20, verbose_name='定位状态')),
                ('lng', models.DecimalField(blank=True, decimal_places=6, help_text='经度', max_digits=10, null=True, verbose_name='经度')),
                ('lat', models.DecimalField(blank=True, decimal_places=6, help_text='纬度', max_digits=10, null=True, verbose_name='纬度')),
                ('address', models.CharField(blank=True, help_text='拜访地址', max_length=500, null=True, verbose_name='拜访地址')),
                ('creator', models.ForeignKey(db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_query_name='creator_query', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
            ],
            options={
                'verbose_name': '拜访记录',
                'verbose_name_plural': '拜访记录',
                'db_table': 'visit_record',
                'ordering': ['-visit_time'],
            },
        ),
        
        # 添加索引
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['status', 'owner_user_id'], name='client_status_1af351_idx'),
        ),
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['grade', 'status'], name='client_grade_1e6559_idx'),
        ),
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['source', 'status'], name='client_source_2e6c75_idx'),
        ),
        migrations.AddIndex(
            model_name='followuprecord',
            index=models.Index(fields=['client_id', 'followup_time'], name='followup_re_client__00834a_idx'),
        ),
        migrations.AddIndex(
            model_name='followuprecord',
            index=models.Index(fields=['user_id', 'followup_time'], name='followup_re_user_id_468089_idx'),
        ),
        migrations.AddIndex(
            model_name='visitrecord',
            index=models.Index(fields=['client_id', 'visit_time'], name='visit_reco_client__a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='visitrecord',
            index=models.Index(fields=['user_id', 'visit_time'], name='visit_reco_user_id_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='visitrecord',
            index=models.Index(fields=['location_status'], name='visit_reco_locatio_g7h8i9_idx'),
        ),
    ]
