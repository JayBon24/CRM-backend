#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新案件关联关系脚本
为现有案件数据补齐 customer_id, owner_user_id, contract_id 关联
为现有合同数据补齐 case_id 关联
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from case_management.models import CaseManagement
from customer_management.models import Customer, Contract
from dvadmin.system.models import Users
import random


class Command(BaseCommand):
    help = '更新案件和合同的关联关系'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='预览模式，不实际更新数据',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== 预览模式：不会实际更新数据 ==='))
        else:
            self.stdout.write(self.style.SUCCESS('=== 开始更新关联关系 ==='))

        # 获取所有数据
        cases = CaseManagement.objects.filter(is_deleted=False)
        customers = Customer.objects.filter(is_deleted=False)
        contracts = Contract.objects.filter()
        users = Users.objects.filter()

        self.stdout.write(f'案件总数: {cases.count()}')
        self.stdout.write(f'客户总数: {customers.count()}')
        self.stdout.write(f'合同总数: {contracts.count()}')
        self.stdout.write(f'用户总数: {users.count()}')

        # 1. 更新案件关联关系
        self.stdout.write('\n--- 更新案件关联关系 ---')
        
        # 获取有状态的客户（CASE, PAYMENT, WON）
        customers_with_cases = customers.filter(status__in=['CASE', 'PAYMENT', 'WON'])
        customers_with_contracts = customers.filter(contracts__isnull=False).distinct()
        
        updated_cases = 0
        with transaction.atomic():
            for case in cases:
                updated = False
                
                # 1.1 关联客户：优先关联有合同且状态为CASE/PAYMENT/WON的客户
                if not case.customer_id:
                    # 尝试通过案件名称或原告名称匹配客户
                    matched_customer = None
                    
                    # 方法1: 通过原告名称匹配客户名称
                    if case.plaintiff_name:
                        matched_customer = customers_with_cases.filter(
                            name__icontains=case.plaintiff_name[:10] if len(case.plaintiff_name) > 10 else case.plaintiff_name
                        ).first()
                    
                    # 方法2: 如果没有匹配，随机分配一个有合同的客户
                    if not matched_customer and customers_with_contracts.exists():
                        matched_customer = random.choice(list(customers_with_contracts))
                    
                    # 方法3: 如果还是没有，随机分配一个有状态的客户
                    if not matched_customer and customers_with_cases.exists():
                        matched_customer = random.choice(list(customers_with_cases))
                    
                    if matched_customer:
                        case.customer_id = matched_customer.id
                        updated = True
                
                # 1.2 关联经办人：从关联客户获取，或随机分配
                if not case.owner_user_id:
                    if case.customer_id:
                        customer = Customer.objects.filter(id=case.customer_id).first()
                        if customer and customer.owner_user_id:
                            case.owner_user_id = customer.owner_user_id
                            case.owner_user_name = customer.owner_user_name
                            updated = True
                    
                    # 如果没有客户或客户没有经办人，随机分配一个用户
                    if not case.owner_user_id and users.exists():
                        random_user = random.choice(list(users))
                        case.owner_user_id = random_user.id
                        case.owner_user_name = getattr(random_user, 'name', None) or getattr(random_user, 'username', '')
                        updated = True
                
                # 1.3 关联合同：从关联客户获取
                if not case.contract_id and case.customer_id:
                    customer = Customer.objects.filter(id=case.customer_id).first()
                    if customer:
                        # 获取客户已确认的合同
                        confirmed_contract = customer.contracts.filter(status='confirmed').first()
                        if confirmed_contract:
                            case.contract_id = confirmed_contract.id
                            updated = True
                
                if updated:
                    if not dry_run:
                        case.save(update_fields=['customer_id', 'owner_user_id', 'owner_user_name', 'contract_id'])
                    updated_cases += 1
                    self.stdout.write(f'  更新案件 {case.id} ({case.case_name}): customer={case.customer_id}, owner={case.owner_user_id}, contract={case.contract_id}')

        self.stdout.write(self.style.SUCCESS(f'[OK] 更新了 {updated_cases} 个案件的关联关系'))

        # 2. 更新合同关联关系
        self.stdout.write('\n--- 更新合同关联关系 ---')
        
        updated_contracts = 0
        with transaction.atomic():
            for contract in contracts:
                # 如果合同已有案件关联，跳过
                if contract.case_id:
                    continue
                
                # 如果合同状态为已确认，尝试关联案件
                if contract.status == 'confirmed' and contract.customer_id:
                    # 查找该客户关联的案件
                    customer = Customer.objects.filter(id=contract.customer_id).first()
                    if customer:
                        # 优先查找已关联该客户的案件
                        case = CaseManagement.objects.filter(
                            customer_id=customer.id,
                            contract_id__isnull=True
                        ).first()
                        
                        # 如果没有，查找该客户的其他案件
                        if not case:
                            case = CaseManagement.objects.filter(
                                customer_id=customer.id
                            ).first()
                        
                        if case:
                            contract.case_id = case.id
                            if not dry_run:
                                contract.save(update_fields=['case_id'])
                            updated_contracts += 1
                            self.stdout.write(f'  更新合同 {contract.id} ({contract.contract_no}): case={case.id}')

        self.stdout.write(self.style.SUCCESS(f'[OK] 更新了 {updated_contracts} 个合同的关联关系'))

        # 3. 验证关联关系
        self.stdout.write('\n--- 验证关联关系 ---')
        cases_with_customer = CaseManagement.objects.filter(customer_id__isnull=False).count()
        cases_with_owner = CaseManagement.objects.filter(owner_user_id__isnull=False).count()
        cases_with_contract = CaseManagement.objects.filter(contract_id__isnull=False).count()
        contracts_with_case = Contract.objects.filter(case_id__isnull=False).count()
        
        self.stdout.write(f'  有客户的案件: {cases_with_customer}/{cases.count()}')
        self.stdout.write(f'  有经办人的案件: {cases_with_owner}/{cases.count()}')
        self.stdout.write(f'  有合同的案件: {cases_with_contract}/{cases.count()}')
        self.stdout.write(f'  有案件的合同: {contracts_with_case}/{contracts.count()}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== 预览完成，使用 --dry-run=false 执行实际更新 ==='))
        else:
            self.stdout.write(self.style.SUCCESS('\n=== 关联关系更新完成 ==='))
