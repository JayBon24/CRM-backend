"""
基于角色的数据范围过滤 Mixin
"""
from django.db.models import Q


class RoleBasedFilterMixin:
    """
    基于角色的数据范围过滤 Mixin
    
    根据用户的 role_level 自动过滤数据：
    - HQ（总所管理）：查看全所数据
    - BRANCH（分所管理）：查看本分所数据
    - TEAM（团队管理）：查看本团队数据
    - SALES（销售）：仅查看本人负责的客户
    
    使用方法：
        class CustomerViewSet(RoleBasedFilterMixin, CustomModelViewSet):
            queryset = Customer.objects.filter(is_deleted=False)
            # ...
    """
    
    # 可以在子类中覆盖这些字段名
    owner_field = 'owner_user'  # 经办人字段名
    team_field = 'team_id'      # 团队ID字段名
    branch_field = 'branch_id'  # 分所ID字段名
    hq_field = 'hq_id'          # 总部ID字段名
    
    def get_queryset(self):
        """根据用户角色过滤数据"""
        # 直接从 ViewSet 的 queryset 属性获取基础查询集
        # 不调用 super().get_queryset()，避免被其他 Mixin 过滤
        if hasattr(self, 'queryset') and self.queryset is not None:
            queryset = self.queryset.all()
        else:
            # 如果没有 queryset 属性，才调用 super()
            queryset = super().get_queryset()
        
        user = self.request.user
        
        # 未认证用户不返回任何数据
        if not user or not user.is_authenticated:
            return queryset.none()
        
        # 超级管理员查看所有数据
        if user.is_superuser:
            return queryset
        
        # 获取用户的角色层级
        role_level = getattr(user, 'role_level', None)
        
        if not role_level:
            # 如果没有设置 role_level，默认只能查看本人数据
            return self._filter_by_owner(queryset, user)
        
        # 根据角色层级过滤
        if role_level == 'HQ':
            # 总所管理：查看全所数据
            return self._filter_by_hq(queryset, user)
        
        elif role_level == 'BRANCH':
            # 分所管理：查看本分所数据
            return self._filter_by_branch(queryset, user)
        
        elif role_level == 'TEAM':
            # 团队管理：查看本团队数据
            return self._filter_by_team(queryset, user)
        
        elif role_level == 'SALES':
            # 销售：仅查看本人负责的客户
            return self._filter_by_owner(queryset, user)
        
        # 默认不返回任何数据
        return queryset.none()
    
    def _filter_by_hq(self, queryset, user):
        """HQ 角色：查看全所数据"""
        # HQ 可以查看所有数据，不需要过滤
        # 如果需要按总部过滤，可以取消下面的注释
        # hq_id = self._get_user_hq_id(user)
        # if hq_id:
        #     return queryset.filter(**{self.hq_field: hq_id})
        return queryset
    
    def _filter_by_branch(self, queryset, user):
        """BRANCH 角色：查看本分所数据"""
        if not self.branch_field:
            # 如果没有配置 branch_field，回退到按 owner 过滤
            return self._filter_by_owner(queryset, user)
        branch_id = self._get_user_branch_id(user)
        if branch_id:
            return queryset.filter(**{self.branch_field: branch_id})
        return queryset.none()
    
    def _filter_by_team(self, queryset, user):
        """TEAM 角色：查看本团队数据"""
        if not self.team_field:
            # 如果没有配置 team_field，回退到按 owner 过滤
            return self._filter_by_owner(queryset, user)
        team_id = self._get_user_team_id(user)
        if team_id:
            return queryset.filter(**{self.team_field: team_id})
        return queryset.none()
    
    def _filter_by_owner(self, queryset, user):
        """SALES 角色：仅查看本人负责的客户"""
        model = getattr(queryset, "model", None)
        if model and hasattr(model, "handlers"):
            return queryset.filter(handlers=user)
        return queryset.filter(**{self.owner_field: user})
    
    def _get_user_team_id(self, user):
        """获取用户的团队ID"""
        # 方案1：如果 Users 模型有 team_id 字段
        team_id = getattr(user, 'team_id', None)
        if team_id:
            return team_id
        
        # 方案2：如果 Users 模型有 team 外键
        team = getattr(user, 'team', None)
        if team:
            return team.id
        
        return None
    
    def _get_user_branch_id(self, user):
        """获取用户的分所ID"""
        # 方案1：如果 Users 模型有 branch_id 字段
        branch_id = getattr(user, 'branch_id', None)
        if branch_id:
            return branch_id
        
        # 方案2：如果 Users 模型有 branch 外键
        branch = getattr(user, 'branch', None)
        if branch:
            return branch.id
        
        # 方案3：通过 team 获取 branch_id
        team = getattr(user, 'team', None)
        if team and hasattr(team, 'branch_id'):
            return team.branch_id
        
        return None
    
    def _get_user_hq_id(self, user):
        """获取用户的总部ID"""
        # 方案1：如果 Users 模型有 hq_id 字段
        hq_id = getattr(user, 'hq_id', None)
        if hq_id:
            return hq_id
        
        # 方案2：如果 Users 模型有 headquarters 外键
        hq = getattr(user, 'headquarters', None)
        if hq:
            return hq.id
        
        # 方案3：通过 branch 获取 hq_id
        branch = getattr(user, 'branch', None)
        if branch and hasattr(branch, 'headquarters_id'):
            return branch.headquarters_id
        
        # 方案4：通过 team 获取 hq_id
        team = getattr(user, 'team', None)
        if team and hasattr(team, 'headquarters_id'):
            return team.headquarters_id
        
        return None


class PublicPoolFilterMixin(RoleBasedFilterMixin):
    """
    公海客户过滤 Mixin
    
    在 RoleBasedFilterMixin 的基础上，只返回公海客户（status='PUBLIC_POOL'）
    并根据角色限制可见范围
    """
    
    def get_queryset(self):
        """获取公海客户列表"""
        queryset = super().get_queryset()
        
        # 只返回公海客户
        queryset = queryset.filter(status='PUBLIC_POOL')
        
        return queryset
