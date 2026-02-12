# -*- coding: utf-8 -*-
from django.db import migrations, models, connection
import django.db.models.deletion


def check_column_exists(table_name, column_name):
    """检查表中是否存在指定列"""
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = '{table_name}' 
            AND COLUMN_NAME = '{column_name}'
        """)
        return cursor.fetchone()[0] > 0


def check_index_exists(table_name, index_name):
    """检查表中是否存在指定索引"""
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM information_schema.STATISTICS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = '{table_name}' 
            AND INDEX_NAME = '{index_name}'
        """)
        return cursor.fetchone()[0] > 0


def add_fields_if_not_exists(apps, schema_editor):
    """如果字段不存在则添加"""
    db_alias = schema_editor.connection.alias
    
    # 检查并添加 customer_id
    if not check_column_exists('case_management', 'customer_id'):
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE case_management 
                ADD COLUMN customer_id BIGINT NULL COMMENT '关联客户ID'
            """)
    
    # 检查并添加 owner_user_id
    if not check_column_exists('case_management', 'owner_user_id'):
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE case_management 
                ADD COLUMN owner_user_id BIGINT NULL COMMENT '经办人ID'
            """)
    
    # 检查并添加 owner_user_name
    if not check_column_exists('case_management', 'owner_user_name'):
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE case_management 
                ADD COLUMN owner_user_name VARCHAR(150) NULL COMMENT '经办人姓名'
            """)
    
    # 检查并添加 contract_id
    if not check_column_exists('case_management', 'contract_id'):
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE case_management 
                ADD COLUMN contract_id BIGINT NULL COMMENT '关联合同ID'
            """)
    
    # 检查并添加索引
    if not check_index_exists('case_management', 'case_management_customer_idx'):
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE INDEX case_management_customer_idx 
                ON case_management (customer_id)
            """)
    
    if not check_index_exists('case_management', 'case_management_owner_user_idx'):
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE INDEX case_management_owner_user_idx 
                ON case_management (owner_user_id)
            """)
    
    if not check_index_exists('case_management', 'case_management_contract_idx'):
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE INDEX case_management_contract_idx 
                ON case_management (contract_id)
            """)


def remove_fields_if_exists(apps, schema_editor):
    """如果字段存在则删除（回滚操作）"""
    # 删除索引
    if check_index_exists('case_management', 'case_management_contract_idx'):
        with connection.cursor() as cursor:
            cursor.execute("DROP INDEX case_management_contract_idx ON case_management")
    
    if check_index_exists('case_management', 'case_management_owner_user_idx'):
        with connection.cursor() as cursor:
            cursor.execute("DROP INDEX case_management_owner_user_idx ON case_management")
    
    if check_index_exists('case_management', 'case_management_customer_idx'):
        with connection.cursor() as cursor:
            cursor.execute("DROP INDEX case_management_customer_idx ON case_management")
    
    # 删除字段
    if check_column_exists('case_management', 'contract_id'):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE case_management DROP COLUMN contract_id")
    
    if check_column_exists('case_management', 'owner_user_name'):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE case_management DROP COLUMN owner_user_name")
    
    if check_column_exists('case_management', 'owner_user_id'):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE case_management DROP COLUMN owner_user_id")
    
    if check_column_exists('case_management', 'customer_id'):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE case_management DROP COLUMN customer_id")


class Migration(migrations.Migration):

    dependencies = [
        ("case_management", "0020_merge_20251108_0151"),
        ("customer_management", "0011_merge_0007_feedback_0010_customer_grade_collection_source"),
        ("system", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_fields_if_not_exists,
                    reverse_code=remove_fields_if_exists,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="casemanagement",
                    name="customer",
                    field=models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="关联客户",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="cases",
                        to="customer_management.customer",
                        verbose_name="关联客户",
                    ),
                ),
                migrations.AddField(
                    model_name="casemanagement",
                    name="owner_user",
                    field=models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="经办人",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="case_owner_users",
                        to="system.users",
                        verbose_name="经办人",
                    ),
                ),
                migrations.AddField(
                    model_name="casemanagement",
                    name="owner_user_name",
                    field=models.CharField(
                        blank=True,
                        help_text="经办人姓名",
                        max_length=150,
                        null=True,
                        verbose_name="经办人姓名",
                    ),
                ),
                migrations.AddField(
                    model_name="casemanagement",
                    name="contract",
                    field=models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="关联合同",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="case_relations",
                        to="customer_management.contract",
                        verbose_name="关联合同",
                    ),
                ),
            ],
        ),
    ]
