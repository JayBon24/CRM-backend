# -*- coding: utf-8 -*-
"""
初始化客户管理权限
执行命令: python manage.py init_client_permissions
"""
import logging
from collections import Counter
from django.core.management.base import BaseCommand
from dvadmin.system.models import Menu, MenuButton, Role, RoleMenuButtonPermission, Users

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '初始化客户管理菜单和按钮权限，并根据角色层级配置默认权限'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化客户管理权限...')
        
        # 1. 创建或获取客户管理菜单
        menu = self.create_client_menu()
        
        # 2. 创建客户管理按钮权限
        permissions = self.create_client_permissions(menu)
        
        # 3. 根据用户角色层级配置默认权限
        self.set_role_default_permissions(permissions)
        
        self.stdout.write(self.style.SUCCESS('客户管理权限初始化完成！'))

    def create_client_menu(self):
        """创建或获取客户管理菜单"""
        menu = Menu.objects.filter(name='客户管理', parent__isnull=True).first()
        if menu:
            menu.is_catalog = True
            menu.web_path = '/client'
            menu.component = ''
            menu.component_name = 'client'
            menu.status = True
            menu.visible = True
            menu.is_link = False
            menu.cache = False
            menu.is_iframe = False
            menu.is_affix = False
            if not menu.icon:
                menu.icon = 'User'
            if not menu.sort:
                menu.sort = 10
            menu.save()
            self.stdout.write(f'✓客户管理菜单已存在: {menu.name} (ID: {menu.id})')
        else:
            menu = Menu.objects.create(
                name='客户管理',
                web_path='/client',
                component='',
                component_name='client',
                icon='User',
                sort=10,
                status=True,
                visible=True,
                is_catalog=True,
                is_link=False,
                cache=False,
                is_iframe=False,
                is_affix=False,
            )
            self.stdout.write(self.style.SUCCESS(f'✓创建客户管理菜单: {menu.name} (ID: {menu.id})'))

        self.create_client_children(menu)
        return menu

    def create_client_children(self, menu):
        """创建客户管理子菜单"""
        children_config = [
            {
                'name': '案源管理',
                'web_path': '/client/manage',
                'component': 'client/manage',
                'component_name': 'clientManage',
                'icon': 'User',
                'sort': 1,
            },
            {
                'name': '公海管理',
                'web_path': '/client/public-pool',
                'component': 'client/public-pool',
                'component_name': 'clientPublicPool',
                'icon': 'iconfont icon-gonghai',
                'sort': 2,
            },
        ]

        for config in children_config:
            child, created = Menu.objects.get_or_create(
                name=config['name'],
                parent=menu,
                defaults={
                    'web_path': config['web_path'],
                    'component': config['component'],
                    'component_name': config['component_name'],
                    'icon': config['icon'],
                    'sort': config['sort'],
                    'status': True,
                    'visible': True,
                    'is_catalog': False,
                    'is_link': False,
                    'cache': False,
                    'is_iframe': False,
                    'is_affix': False,
                }
            )
            if not created:
                child.name = config['name'].strip()
                child.parent = menu
                child.web_path = config['web_path']
                child.component = config['component']
                child.component_name = config['component_name']
                child.status = True
                child.visible = True
                child.is_catalog = False
                child.is_link = False
                child.cache = False
                child.is_iframe = False
                child.is_affix = False
                child.icon = config['icon']
                child.sort = config['sort']
                child.save()

            self.stdout.write(f'✓客户管理子菜单已存在: {child.name} (ID: {child.id})')

    def create_client_permissions(self, menu):
        """创建客户管理按钮权限"""
        permissions_config = [
            {
                'name': '新建客户',
                'value': 'client:create',
                'api': '/api/crm/client/',
                'method': 1,  # POST
            },
            {
                'name': '编辑客户',
                'value': 'client:edit',
                'api': '/api/crm/client/{id}/',
                'method': 2,  # PUT
            },
            {
                'name': '分配客户',
                'value': 'client:assign',
                'api': '/api/crm/client/batch-assign',
                'method': 1,  # POST
            },
            {
                'name': '公海批量分配',
                'value': 'client:assign_public_pool',
                'api': '/api/customer/customers/batch_assign/',
                'method': 1,  # POST
            },
            {
                'name': '删除客户',
                'value': 'client:delete',
                'api': '/api/crm/client/{id}/',
                'method': 3,  # DELETE
            },
            {
                'name': '转交客户',
                'value': 'client:transfer',
                'api': '/api/crm/client/transfer/',
                'method': 1,  # POST
            },
            {
                'name': '导入客户',
                'value': 'client:import',
                'api': '/api/customer/customers/import_data/',
                'method': 1,  # POST
            },
            {
                'name': '导入模板下载',
                'value': 'client:import_template',
                'api': '/api/customer/customers/import_data/',
                'method': 0,  # GET
            },
            {
                'name': '批量更新模板下载',
                'value': 'client:update_template',
                'api': '/api/customer/customers/update_template/',
                'method': 0,  # GET
            },
            {
                'name': '导出客户',
                'value': 'client:export',
                'api': '/api/customer/customers/export_data/',
                'method': 0,  # GET
            },
            {
                'name': '申领客户',
                'value': 'client:claim',
                'api': '/api/customer/customers/{id}/claim/',
                'method': 1,  # POST
            },
            {
                'name': '批量申领',
                'value': 'client:batch_claim',
                'api': '/api/customer/customers/batch_claim/',
                'method': 1,  # POST
            },
        ]
        
        permissions = {}
        for config in permissions_config:
            button, created = MenuButton.objects.get_or_create(
                value=config['value'],
                defaults={
                    'menu': menu,
                    'name': config['name'],
                    'api': config['api'],
                    'method': config['method'],
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ 创建权限: {button.name} ({button.value})'))
            else:
                updated = False
                if button.api != config['api']:
                    button.api = config['api']
                    updated = True
                if button.method != config['method']:
                    button.method = config['method']
                    updated = True
                if updated:
                    button.save(update_fields=['api', 'method'])
                    self.stdout.write(self.style.SUCCESS(f'✓ 权限已更新: {button.name} ({button.value})'))
                else:
                    self.stdout.write(f'✓ 权限已存在: {button.name} ({button.value})')
            
            permissions[config['value']] = button
        
        return permissions

    def set_role_default_permissions(self, permissions):
        """根据用户角色层级配置默认权限"""
        # 定义角色层级权限规则
        role_level_permissions = {
            'HQ': [
                'client:create',
                'client:edit',
                'client:assign',
                'client:assign_public_pool',
                'client:export',
                'client:import',
                'client:import_template',
                'client:update_template',
                'client:claim',
                'client:batch_claim',
                'client:delete',
                'client:transfer',
            ],
            'BRANCH': [
                'client:create',
                'client:edit',
                'client:assign',
                'client:assign_public_pool',
                'client:export',
                'client:import',
                'client:import_template',
                'client:update_template',
                'client:claim',
                'client:batch_claim',
                'client:delete',
                'client:transfer',
            ],
            'TEAM': [
                'client:create',
                'client:edit',
                'client:assign',
                'client:assign_public_pool',
                'client:export',
                'client:import',
                'client:import_template',
                'client:update_template',
                'client:claim',
                'client:batch_claim',
                'client:transfer',
            ],  # 不包括delete
            'SALES': [
                'client:create',
                'client:edit',
                'client:assign',
                'client:assign_public_pool',
                'client:export',
                'client:import',
                'client:import_template',
                'client:update_template',
                'client:claim',
                'client:batch_claim',
            ],  # 不包括delete和transfer
        }
        
        # 获取所有角色
        all_roles = Role.objects.all()
        configured_count = 0
        
        # 为每个角色查找对应的用户，根据用户的role_level设置权限
        for role in all_roles:
            # 获取该角色的所有用户
            users_with_role = Users.objects.filter(role=role)
            
            if not users_with_role.exists():
                # 如果没有用户使用该角色，跳过
                continue
            
            # 获取该角色下用户的role_level
            # 注意：一个角色可能对应多个不同role_level的用户
            # 这里取最常见的role_level（出现次数最多的）
            role_levels = [level for level in users_with_role.values_list('role_level', flat=True) if level]
            
            if not role_levels:
                # 如果用户没有设置role_level，跳过
                continue
            
            # 找到最常见的role_level
            role_level_counter = Counter(role_levels)
            most_common_role_level = role_level_counter.most_common(1)[0][0] if role_level_counter else None
            
            if not most_common_role_level or most_common_role_level not in role_level_permissions:
                continue
            
            permission_values = role_level_permissions[most_common_role_level]
            
            # 为角色配置权限
            for perm_value in permission_values:
                if perm_value not in permissions:
                    continue
                
                button = permissions[perm_value]
                
                # 检查是否已存在
                role_perm, created = RoleMenuButtonPermission.objects.get_or_create(
                    role=role,
                    menu_button=button,
                    defaults={
                        'data_range': 3,  # 全部数据权限（可根据需要调整）
                    }
                )
                
                if created:
                    configured_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ 为角色 {role.name} (role_level: {most_common_role_level}) 配置权限: {button.name}'
                        )
                    )
        
        if configured_count > 0:
            self.stdout.write(self.style.SUCCESS(f'✓ 角色权限配置完成，共配置 {configured_count} 个权限'))
        else:
            self.stdout.write(self.style.WARNING('⚠ 未找到需要配置权限的角色（请确保用户已设置role_level）'))

