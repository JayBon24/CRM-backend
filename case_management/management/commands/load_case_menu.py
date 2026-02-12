"""
加载案例管理菜单数据
"""
import json
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from dvadmin.system.models import Menu, MenuButton
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = '加载案例管理菜单数据'

    def handle(self, *args, **options):
        # 获取菜单数据文件路径
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'fixtures',
            'case_menu.json'
        )
        
        try:
            with open(fixture_path, 'r', encoding='utf-8') as f:
                menu_data = json.load(f)
            
            with transaction.atomic():
                for menu_item in menu_data:
                    # 创建或更新主菜单
                    menu = self.create_or_update_menu(menu_item, None)
                    
                    # 处理子菜单
                    if 'children' in menu_item and menu_item['children']:
                        for child_item in menu_item['children']:
                            self.create_or_update_menu(child_item, menu)
                    
                    # 处理菜单按钮
                    if 'menu_button' in menu_item:
                        # 删除现有按钮
                        MenuButton.objects.filter(menu=menu).delete()
                        
                        # 创建新按钮
                        created_count = 0
                        updated_count = 0
                        for button_data in menu_item['menu_button']:
                            # 检查是否已存在相同value的按钮（可能属于其他菜单）
                            existing_button = MenuButton.objects.filter(value=button_data['value']).first()
                            if existing_button:
                                # 如果存在，更新它（移动到当前菜单）
                                existing_button.menu = menu
                                existing_button.name = button_data['name']
                                existing_button.api = button_data['api']
                                existing_button.method = button_data['method']
                                existing_button.save()
                                updated_count += 1
                            else:
                                # 如果不存在，创建新按钮
                                MenuButton.objects.create(
                                    menu=menu,
                                    name=button_data['name'],
                                    value=button_data['value'],
                                    api=button_data['api'],
                                    method=button_data['method']
                                )
                                created_count += 1
                        
                        if created_count > 0:
                            self.stdout.write(f'创建菜单按钮: {menu.name} - {created_count}个新按钮')
                        if updated_count > 0:
                            self.stdout.write(f'更新菜单按钮: {menu.name} - {updated_count}个按钮')
                        if created_count == 0 and updated_count == 0:
                            self.stdout.write(f'菜单按钮: {menu.name} - {len(menu_item["menu_button"])}个按钮')
            
            self.stdout.write(
                self.style.SUCCESS('案例管理菜单数据加载完成！')
            )
            
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'菜单数据文件不存在: {fixture_path}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'加载菜单数据失败: {str(e)}')
            )
    
    def create_or_update_menu(self, menu_item, parent_menu):
        """创建或更新菜单"""
        # 使用 web_path 和 parent 作为唯一标识，因为名称可能重复
        query_params = {
            'web_path': menu_item['web_path'],
            'parent': parent_menu
        }
        
        # 先检查是否存在重复的菜单
        existing_menus = Menu.objects.filter(**query_params)
        
        if existing_menus.count() > 1:
            # 如果存在多个，保留第一个，删除其他的
            menus_list = list(existing_menus)
            menu = menus_list[0]
            for duplicate_menu in menus_list[1:]:
                self.stdout.write(f'删除重复菜单: {duplicate_menu.name} (ID: {duplicate_menu.id})')
                duplicate_menu.delete()
        elif existing_menus.exists():
            # 如果只有一个，使用它
            menu = existing_menus.first()
        else:
            # 如果不存在，尝试通过名称和父菜单查找（向后兼容）
            name_query = Menu.objects.filter(name=menu_item['name'], parent=parent_menu)
            if name_query.exists():
                menu = name_query.first()
            else:
                # 创建新菜单
                menu = Menu.objects.create(
                    name=menu_item['name'],
                    icon=menu_item['icon'],
                    sort=menu_item['sort'],
                    is_link=menu_item['is_link'],
                    is_catalog=menu_item['is_catalog'],
                    web_path=menu_item['web_path'],
                    component=menu_item['component'],
                    component_name=menu_item['component_name'],
                    status=menu_item['status'],
                    cache=menu_item['cache'],
                    visible=menu_item['visible'],
                    parent=parent_menu,
                )
                self.stdout.write(f'创建菜单: {menu.name}')
                return menu
        
        # 更新现有菜单
        menu.icon = menu_item['icon']
        menu.sort = menu_item['sort']
        menu.is_link = menu_item['is_link']
        menu.is_catalog = menu_item['is_catalog']
        menu.web_path = menu_item['web_path']
        menu.component = menu_item['component']
        menu.component_name = menu_item['component_name']
        menu.status = menu_item['status']
        menu.cache = menu_item['cache']
        menu.visible = menu_item['visible']
        menu.parent = parent_menu
        menu.save()
        self.stdout.write(f'更新菜单: {menu.name}')
        
        return menu