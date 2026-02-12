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


def add_field_if_not_exists(apps, schema_editor):
    """如果字段不存在则添加"""
    # 检查并添加 case_id
    if not check_column_exists('customer_contract', 'case_id'):
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE customer_contract 
                ADD COLUMN case_id BIGINT NULL COMMENT '关联案件ID'
            """)
    
    # 检查并添加索引
    if not check_index_exists('customer_contract', 'customer_contract_case_idx'):
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE INDEX customer_contract_case_idx 
                ON customer_contract (case_id)
            """)


def remove_field_if_exists(apps, schema_editor):
    """如果字段存在则删除（回滚操作）"""
    # 删除索引
    if check_index_exists('customer_contract', 'customer_contract_case_idx'):
        with connection.cursor() as cursor:
            cursor.execute("DROP INDEX customer_contract_case_idx ON customer_contract")
    
    # 删除字段
    if check_column_exists('customer_contract', 'case_id'):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE customer_contract DROP COLUMN case_id")


class Migration(migrations.Migration):

    dependencies = [
        ("customer_management", "0011_merge_0007_feedback_0010_customer_grade_collection_source"),
        ("case_management", "0021_add_case_relations"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_field_if_not_exists,
                    reverse_code=remove_field_if_exists,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="contract",
                    name="case",
                    field=models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="related_contracts",
                        to="case_management.casemanagement",
                        verbose_name="关联案件",
                    ),
                ),
            ],
        ),
    ]
