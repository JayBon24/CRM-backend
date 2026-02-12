"""
为超级管理员角色设置案例管理菜单权限
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from dvadmin.system.models import Role, RoleMenuPermission, Menu

User = get_user_model()


class Command(BaseCommand):
    help = '为超级管理员角色设置案例管理菜单权限'

    def handle(self, *args, **options):
        try:
            # 获取超级管理员角色
            admin_role = Role.objects.filter(name='超级管理员').first()
            if not admin_role:
                # 尝试通过key查找
                admin_role = Role.objects.filter(key='admin').first()
                if not admin_role:
                    # 如果没有找到超级管理员角色，尝试创建
                    admin_role = Role.objects.create(
                        name='超级管理员',
                        key='admin',
                        status=True,
                        sort=1
                    )
                    self.stdout.write('创建超级管理员角色')
                else:
                    self.stdout.write('找到超级管理员角色')
            else:
                self.stdout.write('找到超级管理员角色')
            
            # 获取案例管理菜单
            case_menu = Menu.objects.filter(name='案例管理').first()
            if case_menu:
                # 检查权限是否已存在
                permission_exists = RoleMenuPermission.objects.filter(
                    role=admin_role,
                    menu=case_menu
                ).exists()
                
                if not permission_exists:
                    # 创建权限
                    RoleMenuPermission.objects.create(
                        role=admin_role,
                        menu=case_menu
                    )
                    self.stdout.write(f'为超级管理员角色分配案例管理菜单权限')
                else:
                    self.stdout.write('超级管理员角色已有案例管理菜单权限')
            else:
                self.stdout.write('案例管理菜单不存在，跳过')
            
            # 获取智能对话菜单
            intelligent_chat_menu = Menu.objects.filter(name='智能对话').first()
            if intelligent_chat_menu:
                # 检查权限是否已存在
                permission_exists = RoleMenuPermission.objects.filter(
                    role=admin_role,
                    menu=intelligent_chat_menu
                ).exists()
                
                if not permission_exists:
                    # 创建权限
                    RoleMenuPermission.objects.create(
                        role=admin_role,
                        menu=intelligent_chat_menu
                    )
                    self.stdout.write(f'为超级管理员角色分配智能对话菜单权限')
                else:
                    self.stdout.write('超级管理员角色已有智能对话菜单权限')
            else:
                self.stdout.write('智能对话菜单不存在，请先运行 load_case_menu 命令')
            
            # 为所有超级管理员用户分配权限
            superusers = User.objects.filter(is_superuser=True)
            for user in superusers:
                if not user.role.filter(id=admin_role.id).exists():
                    user.role.add(admin_role)
                    self.stdout.write(f'为用户 {user.username} 分配超级管理员角色')
            
            self.stdout.write(
                self.style.SUCCESS('案例管理菜单权限设置完成！')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'设置菜单权限失败: {str(e)}')
            )
