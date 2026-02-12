# -*- coding: utf-8 -*-
"""
删除指定客户数据的管理命令
用法: python manage.py delete_customer --name "杭州建筑工程有限公司" --sales-stage MEETING
"""
from django.core.management.base import BaseCommand
from customer_management.models import Customer


class Command(BaseCommand):
    help = '删除指定条件的客户数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            required=True,
            help='客户名称',
        )
        parser.add_argument(
            '--sales-stage',
            type=str,
            required=True,
            help='展业状态',
        )
        parser.add_argument(
            '--hard-delete',
            action='store_true',
            help='硬删除（彻底删除），默认是软删除',
        )

    def handle(self, *args, **options):
        name = options['name']
        sales_stage = options['sales_stage']
        hard_delete = options.get('hard_delete', False)

        # 查询符合条件的客户
        customers = Customer.objects.filter(
            sales_stage=sales_stage,
            name=name,
            is_deleted=False
        )

        count = customers.count()
        self.stdout.write(f'找到 {count} 条符合条件的记录')

        if count == 0:
            self.stdout.write(self.style.WARNING('没有找到需要删除的数据'))
            return

        # 显示要删除的记录
        self.stdout.write('\n要删除的记录:')
        for customer in customers:
            self.stdout.write(
                f'  ID: {customer.id}, Name: {customer.name}, '
                f'Sales Stage: {customer.sales_stage}, Status: {customer.status}'
            )

        # 确认删除
        if hard_delete:
            self.stdout.write(self.style.WARNING(
                f'\n警告: 将执行硬删除，彻底删除 {count} 条记录！'
            ))
            deleted_count = customers.delete()
            self.stdout.write(
                self.style.SUCCESS(f'成功硬删除 {deleted_count[0]} 条记录')
            )
        else:
            # 软删除
            updated_count = customers.update(is_deleted=True)
            self.stdout.write(
                self.style.SUCCESS(f'成功软删除 {updated_count} 条记录')
            )
