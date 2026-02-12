"""
初始化案例管理数据
"""
from django.core.management.base import BaseCommand
from case_management.models import CaseManagement, DocumentTemplate, CaseDocument
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = '初始化案例管理数据'

    def handle(self, *args, **options):
        # 创建文档模板
        templates_data = [
            {
                'template_name': '起诉状模板',
                'template_type': 'complaint',
                'file_path': '/template/1、起诉状（被告数量+3份）.docx',
                'description': '标准起诉状模板，适用于各类民事案件',
                'is_active': True
            },
            {
                'template_name': '法定代表人身份证明模板',
                'template_type': 'legal_representative',
                'file_path': '/template/2、法定代表人身份证明(5份).doc',
                'description': '法定代表人身份证明文件模板',
                'is_active': True
            },
            {
                'template_name': '授权委托书模板',
                'template_type': 'power_of_attorney',
                'file_path': '/template/3、授权委托书（5份）.doc',
                'description': '律师授权委托书模板',
                'is_active': True
            },
            {
                'template_name': '财产保全申请书模板',
                'template_type': 'property_preservation',
                'file_path': '/template/5、财产保全申请书（3份）.doc',
                'description': '财产保全申请书模板',
                'is_active': True
            },
            {
                'template_name': '撤诉申请书模板',
                'template_type': 'withdrawal',
                'file_path': '/template/8、撤诉申请书(3份).doc',
                'description': '撤诉申请书模板',
                'is_active': True
            }
        ]

        for template_data in templates_data:
            template, created = DocumentTemplate.objects.get_or_create(
                template_name=template_data['template_name'],
                defaults=template_data
            )
            if created:
                self.stdout.write(f'创建模板: {template.template_name}')
            else:
                self.stdout.write(f'模板已存在: {template.template_name}')

        # 创建示例案例
        cases_data = [
            {
                'case_number': '2024民初001',
                'case_type': '民事纠纷',
                'jurisdiction': '北京市朝阳区人民法院',
                'draft_person': '张律师',
                'case_name': '合同纠纷案',
                'defendant_name': '北京科技有限公司',
                'defendant_credit_code': '91110000123456789X',
                'defendant_address': '北京市朝阳区建国路88号',
                'plaintiff_name': '上海贸易有限公司',
                'plaintiff_credit_code': '91310000987654321Y',
                'plaintiff_address': '上海市浦东新区陆家嘴金融贸易区',
                'contract_amount': 500000.00,
                'lawyer_fee': 50000.00,
                'case_description': '关于货物买卖合同纠纷案件',
                'status': 'active'
            },
            {
                'case_number': '2024民初002',
                'case_type': '劳动争议',
                'jurisdiction': '上海市浦东新区人民法院',
                'draft_person': '李律师',
                'case_name': '劳动争议案',
                'defendant_name': '上海制造有限公司',
                'defendant_credit_code': '91310000111222333Z',
                'defendant_address': '上海市浦东新区张江高科技园区',
                'plaintiff_name': '王某某',
                'plaintiff_address': '上海市浦东新区世纪大道100号',
                'contract_amount': 200000.00,
                'lawyer_fee': 20000.00,
                'case_description': '关于工资拖欠和加班费争议案件',
                'status': 'draft'
            },
            {
                'case_number': '2024民初003',
                'case_type': '交通事故',
                'jurisdiction': '广州市天河区人民法院',
                'draft_person': '陈律师',
                'case_name': '交通事故损害赔偿案',
                'defendant_name': '广州运输有限公司',
                'defendant_credit_code': '91440100444555666A',
                'defendant_address': '广州市天河区珠江新城',
                'plaintiff_name': '赵某某',
                'plaintiff_address': '广州市天河区体育西路123号',
                'contract_amount': 300000.00,
                'lawyer_fee': 30000.00,
                'case_description': '关于交通事故人身损害赔偿案件',
                'status': 'completed'
            }
        ]

        for case_data in cases_data:
            case, created = CaseManagement.objects.get_or_create(
                case_number=case_data['case_number'],
                defaults=case_data
            )
            if created:
                self.stdout.write(f'创建案例: {case.case_name}')
            else:
                self.stdout.write(f'案例已存在: {case.case_name}')

        self.stdout.write(
            self.style.SUCCESS('案例管理数据初始化完成！')
        )
