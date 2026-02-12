"""
初始化搜索建议数据
"""
from django.core.management.base import BaseCommand
from case_management.models import SearchSuggestion


class Command(BaseCommand):
    help = '初始化搜索建议数据'

    def handle(self, *args, **options):
        # 常见法律问题数据
        suggestions_data = [
            {
                'question': '邻居趁我家中无人时潜入盗窃现金3万元，被发现后持刀威胁阻拦的家人逃跑。这种情况是否构成抢劫罪？',
                'category': '刑法',
                'keywords': '盗窃,抢劫罪,持刀威胁,入户盗窃',
                'sort_order': 1
            },
            {
                'question': '我在上班路上被电动车撞伤，对方逃逸，交警无法找到肇事者。我可以通过什么途径获得赔偿？',
                'category': '交通事故',
                'keywords': '交通事故,逃逸,赔偿,工伤保险',
                'sort_order': 2
            },
            {
                'question': '公司以经营困难为由要求我主动辞职，但拒绝支付经济补偿金。我应该如何维护自己的权益？',
                'category': '劳动法',
                'keywords': '主动辞职,经济补偿金,劳动权益,裁员',
                'sort_order': 3
            },
            {
                'question': '丈夫出轨并有私生子，离婚时财产如何分割？私生子的抚养费如何计算？',
                'category': '婚姻家庭',
                'keywords': '出轨,离婚,财产分割,私生子,抚养费',
                'sort_order': 4
            },
            {
                'question': '开发商延期交房8个月，合同中约定延期交房按日支付万分之五的违约金。这个标准是否合理？',
                'category': '合同法',
                'keywords': '延期交房,违约金,开发商,购房合同',
                'sort_order': 5
            },
            {
                'question': '我在网上购买的商品存在质量问题，商家拒绝退货退款，还要求我承担运费。消费者权益如何保护？',
                'category': '消费者权益',
                'keywords': '网购,质量问题,退货退款,消费者权益',
                'sort_order': 6
            },
            {
                'question': '公司大股东利用控制权转移公司资产，损害小股东利益。小股东如何维权？',
                'category': '公司法',
                'keywords': '大股东,资产转移,小股东权益,公司治理',
                'sort_order': 7
            },
            {
                'question': '我的原创作品被他人抄袭并在网上传播获利，如何通过法律途径维权？',
                'category': '知识产权',
                'keywords': '原创作品,抄袭,网络传播,著作权侵权',
                'sort_order': 8
            },
            {
                'question': '医院误诊导致病情延误，造成严重后果。医疗事故责任如何认定？赔偿标准是什么？',
                'category': '医疗纠纷',
                'keywords': '误诊,医疗事故,责任认定,医疗赔偿',
                'sort_order': 9
            },
            {
                'question': '朋友借钱不还，有借条但对方声称已经还清。如何证明债务关系？',
                'category': '债权债务',
                'keywords': '借钱不还,借条,债务关系,证据',
                'sort_order': 10
            },
            {
                'question': '我因正当防卫致人轻伤，是否构成犯罪？正当防卫的界限是什么？',
                'category': '刑法',
                'keywords': '正当防卫,轻伤,犯罪,防卫过当',
                'sort_order': 11
            },
            {
                'question': '父母去世后，兄弟姐妹对遗产分配产生争议。继承顺序和份额如何确定？',
                'category': '继承法',
                'keywords': '遗产分配,继承顺序,继承份额,兄弟姐妹',
                'sort_order': 12
            },
            {
                'question': '有人在网上发布我的隐私信息并恶意诽谤，造成名誉损害。如何维权？',
                'category': '网络法',
                'keywords': '隐私泄露,网络诽谤,名誉损害,网络维权',
                'sort_order': 13
            },
            {
                'question': '承包方拖欠工程款，发包方以工程质量问题为由拒绝支付。工程款纠纷如何解决？',
                'category': '建设工程',
                'keywords': '工程款,拖欠,工程质量,建设工程纠纷',
                'sort_order': 14
            },
            {
                'question': '保险公司以投保人隐瞒病史为由拒绝理赔，但投保人认为已如实告知。保险理赔纠纷如何解决？',
                'category': '保险法',
                'keywords': '保险理赔,隐瞒病史,如实告知,保险纠纷',
                'sort_order': 15
            }
        ]
        
        try:
            # 清空现有数据
            SearchSuggestion.objects.all().delete()
            
            # 创建新数据
            for data in suggestions_data:
                SearchSuggestion.objects.create(**data)
            
            self.stdout.write(
                self.style.SUCCESS(f'成功创建 {len(suggestions_data)} 条搜索建议数据')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'创建搜索建议数据失败: {str(e)}')
            )
