#!/usr/bin/env python3
"""
初始化案例数据 - 包含新字段
"""

from django.core.management.base import BaseCommand
from case_management.models import CaseManagement
from decimal import Decimal
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = '初始化案例数据'

    def handle(self, *args, **options):
        """执行初始化"""
        self.stdout.write('开始初始化案例数据...')
        
        # 清空现有数据
        CaseManagement.objects.all().delete()
        self.stdout.write('已清空现有案例数据')
        
        # 案例数据模板
        case_templates = [
            {
                'case_number': '2024民初001',
                'case_name': '买卖合同纠纷案',
                'case_type': '民事纠纷',
                'jurisdiction': '深圳市中级人民法院',
                'draft_person': '张律师',
                'defendant_name': '深圳市振惠建混凝土有限公司',
                'defendant_credit_code': '91440300743220274C',
                'defendant_address': '深圳市南山区科技园南区深圳湾科技生态园10栋A座',
                'defendant_legal_representative': '李总',
                'plaintiff_name': '中建三局第一建设工程有限责任公司',
                'plaintiff_credit_code': '91110000123456789X',
                'plaintiff_address': '北京市朝阳区建国门外大街1号',
                'plaintiff_legal_representative': '王总',
                'contract_amount': Decimal('2562328.12'),
                'lawyer_fee': Decimal('50000.00'),
                'case_description': '双方因混凝土供应合同产生纠纷，被告未按约定支付货款'
            },
            {
                'case_number': '2024民初002',
                'case_name': '建设工程施工合同纠纷案',
                'case_type': '民事纠纷',
                'jurisdiction': '广州市中级人民法院',
                'draft_person': '李律师',
                'defendant_name': '广州恒大地产集团有限公司',
                'defendant_credit_code': '91440100111222333Z',
                'defendant_address': '广州市天河区珠江新城花城大道85号',
                'defendant_legal_representative': '许总',
                'plaintiff_name': '上海建工集团股份有限公司',
                'plaintiff_credit_code': '91310000987654321Y',
                'plaintiff_address': '上海市浦东新区世纪大道100号',
                'plaintiff_legal_representative': '陈总',
                'contract_amount': Decimal('5000000.00'),
                'lawyer_fee': Decimal('100000.00'),
                'case_description': '建设工程施工合同纠纷，涉及工程质量问题'
            },
            {
                'case_number': '2024民初003',
                'case_name': '劳动争议纠纷案',
                'case_type': '劳动争议',
                'jurisdiction': '深圳市福田区人民法院',
                'draft_person': '王律师',
                'defendant_name': '深圳市腾讯计算机系统有限公司',
                'defendant_credit_code': '91440300444555666A',
                'defendant_address': '深圳市南山区科技园科技中一路腾讯大厦',
                'defendant_legal_representative': '马总',
                'plaintiff_name': '张三',
                'plaintiff_credit_code': '',
                'plaintiff_address': '深圳市福田区华强北路100号',
                'plaintiff_legal_representative': '',
                'contract_amount': Decimal('0.00'),
                'lawyer_fee': Decimal('10000.00'),
                'case_description': '员工与公司之间的劳动争议，涉及工资支付问题'
            },
            {
                'case_number': '2024民初004',
                'case_name': '知识产权纠纷案',
                'case_type': '知识产权',
                'jurisdiction': '深圳市中级人民法院',
                'draft_person': '赵律师',
                'defendant_name': '华为技术有限公司',
                'defendant_credit_code': '91440300743220274D',
                'defendant_address': '深圳市龙岗区坂田华为基地',
                'defendant_legal_representative': '任总',
                'plaintiff_name': '苹果公司',
                'plaintiff_credit_code': 'US0378331005',
                'plaintiff_address': '美国加利福尼亚州库比蒂诺市',
                'plaintiff_legal_representative': 'Tim Cook',
                'contract_amount': Decimal('10000000.00'),
                'lawyer_fee': Decimal('500000.00'),
                'case_description': '专利侵权纠纷，涉及移动通信技术专利'
            },
            {
                'case_number': '2024民初005',
                'case_name': '金融借款合同纠纷案',
                'case_type': '金融纠纷',
                'jurisdiction': '上海市第一中级人民法院',
                'draft_person': '孙律师',
                'defendant_name': '中国工商银行股份有限公司',
                'defendant_credit_code': '91100000100000000X',
                'defendant_address': '北京市西城区复兴门内大街55号',
                'defendant_legal_representative': '易总',
                'plaintiff_name': '上海浦东发展银行股份有限公司',
                'plaintiff_credit_code': '91310000100000000Y',
                'plaintiff_address': '上海市浦东新区浦东南路588号',
                'plaintiff_legal_representative': '郑总',
                'contract_amount': Decimal('20000000.00'),
                'lawyer_fee': Decimal('200000.00'),
                'case_description': '银行间借款合同纠纷，涉及资金拆借问题'
            }
        ]
        
        # 创建案例
        created_cases = []
        for i, template in enumerate(case_templates, 1):
            # 随机生成创建时间（过去30天内）
            days_ago = random.randint(1, 30)
            create_time = datetime.now() - timedelta(days=days_ago)
            
            case = CaseManagement.objects.create(
                case_number=template['case_number'],
                case_name=template['case_name'],
                case_type=template['case_type'],
                jurisdiction=template['jurisdiction'],
                draft_person=template['draft_person'],
                defendant_name=template['defendant_name'],
                defendant_credit_code=template['defendant_credit_code'],
                defendant_address=template['defendant_address'],
                defendant_legal_representative=template['defendant_legal_representative'],
                plaintiff_name=template['plaintiff_name'],
                plaintiff_credit_code=template['plaintiff_credit_code'],
                plaintiff_address=template['plaintiff_address'],
                plaintiff_legal_representative=template['plaintiff_legal_representative'],
                contract_amount=template['contract_amount'],
                lawyer_fee=template['lawyer_fee'],
                case_description=template['case_description'],
                create_datetime=create_time
            )
            created_cases.append(case)
            
            self.stdout.write(
                self.style.SUCCESS(f'创建案例 {i}: {case.case_name} (ID: {case.id})')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'成功创建 {len(created_cases)} 个案例')
        )
        
        # 显示创建的案例信息
        self.stdout.write('\n创建的案例详情:')
        for case in created_cases:
            self.stdout.write(f'案例ID: {case.id}')
            self.stdout.write(f'案号: {case.case_number}')
            self.stdout.write(f'案件名称: {case.case_name}')
            self.stdout.write(f'原告: {case.plaintiff_name} (法定代表人: {case.plaintiff_legal_representative})')
            self.stdout.write(f'被告: {case.defendant_name} (法定代表人: {case.defendant_legal_representative})')
            self.stdout.write(f'合同金额: {case.contract_amount}元')
            self.stdout.write(f'律师费: {case.lawyer_fee}元')
            self.stdout.write('-' * 50)
