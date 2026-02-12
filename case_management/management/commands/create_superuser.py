"""
创建超级管理员用户
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from dvadmin.system.models import Role

User = get_user_model()


class Command(BaseCommand):
    help = '创建超级管理员用户'

    def handle(self, *args, **options):
        try:
            # 检查是否已存在超级管理员
            if User.objects.filter(is_superuser=True).exists():
                self.stdout.write('超级管理员用户已存在')
                return
            
            # 创建超级管理员用户
            user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            
            # 获取或创建超级管理员角色
            admin_role, created = Role.objects.get_or_create(
                name='超级管理员',
                defaults={
                    'key': 'admin',
                    'status': True,
                    'sort': 1
                }
            )
            
            # 为用户分配角色
            user.role.add(admin_role)
            
            self.stdout.write(
                self.style.SUCCESS(f'超级管理员用户创建成功！')
            )
            self.stdout.write(f'用户名: admin')
            self.stdout.write(f'密码: admin123')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'创建超级管理员用户失败: {str(e)}')
            )
