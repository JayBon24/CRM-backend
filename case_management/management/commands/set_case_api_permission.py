"""
为案例管理API设置权限配置
"""
from django.core.management.base import BaseCommand
from dvadmin.system.models import Role, RoleMenuButtonPermission, MenuButton, Menu


class Command(BaseCommand):
    help = '为案例管理API设置权限配置'

    def handle(self, *args, **options):
        try:
            # 获取超级管理员角色
            admin_role = Role.objects.filter(name='超级管理员').first()
            if not admin_role:
                admin_role = Role.objects.filter(key='admin').first()
            
            if not admin_role:
                self.stdout.write(
                    self.style.ERROR('超级管理员角色不存在')
                )
                return
            
            # 获取案例管理菜单
            case_menu = Menu.objects.filter(name='案例管理').first()
            if case_menu:
                # 获取案例管理菜单的所有按钮权限
                case_buttons = MenuButton.objects.filter(menu=case_menu)
                
                # 为超级管理员角色分配所有案例管理权限
                for button in case_buttons:
                    permission, created = RoleMenuButtonPermission.objects.get_or_create(
                        role=admin_role,
                        menu_button=button
                    )
                    if created:
                        self.stdout.write(f'为超级管理员分配权限: {button.name}')
                    else:
                        self.stdout.write(f'超级管理员已有权限: {button.name}')
            
            # 获取智能对话菜单
            intelligent_chat_menu = Menu.objects.filter(name='智能对话').first()
            if intelligent_chat_menu:
                # 获取智能对话菜单的所有按钮权限
                chat_buttons = MenuButton.objects.filter(menu=intelligent_chat_menu)
                
                # 为超级管理员角色分配所有智能对话权限
                for button in chat_buttons:
                    permission, created = RoleMenuButtonPermission.objects.get_or_create(
                        role=admin_role,
                        menu_button=button
                    )
                    if created:
                        self.stdout.write(f'为超级管理员分配权限: {button.name}')
                    else:
                        self.stdout.write(f'超级管理员已有权限: {button.name}')
            
            self.stdout.write(
                self.style.SUCCESS('案例管理API权限配置完成！')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'设置API权限失败: {str(e)}')
            )
