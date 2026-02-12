"""
禁用验证码配置
"""
from django.core.management.base import BaseCommand
from dvadmin.system.models import SystemConfig


class Command(BaseCommand):
    help = '禁用验证码配置'

    def handle(self, *args, **options):
        try:
            # 更新验证码配置
            config, created = SystemConfig.objects.get_or_create(
                key='captcha_state',
                defaults={
                    'title': '开启验证码',
                    'value': False,
                    'status': True,
                    'sort': 1
                }
            )
            
            if not created:
                config.value = False
                config.save()
                self.stdout.write('验证码已禁用')
            else:
                self.stdout.write('验证码配置已创建并禁用')
            
            self.stdout.write(
                self.style.SUCCESS('验证码已成功禁用！')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'禁用验证码失败: {str(e)}')
            )
