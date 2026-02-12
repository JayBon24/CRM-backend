"""
用户相关视图（小程序端）
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from customer_management.models.organization import Branch, Team
from dvadmin.system.models import Dept

User = get_user_model()


# 基础序列化器，用于 Swagger 文档生成
class BaseUserSerializer(serializers.Serializer):
    """基础用户序列化器"""
    pass


class UserListView(APIView):
    """获取用户列表"""
    permission_classes = [IsAuthenticated]
    serializer_class = BaseUserSerializer
    
    @swagger_auto_schema(
        operation_summary="获取用户列表",
        operation_description="获取所有激活用户列表",
        responses={200: "成功"},
        tags=['用户管理']
    )
    def get(self, request):
        """获取全部用户列表"""
        users = User.objects.filter(is_active=True).order_by('id')
        
        data = [{
            'id': user.id,
            'username': user.username,
            'name': user.name or user.username,
            'branch_id': user.branch_id,
            'team_id': user.team_id,
        } for user in users]
        
        return Response({
            'code': 200,
            'msg': 'success',
            'data': data
        })


class BranchListView(APIView):
    """获取分所列表（基于 lsl_system_dept）"""
    permission_classes = [IsAuthenticated]
    serializer_class = BaseUserSerializer
    
    @swagger_auto_schema(
        operation_summary="获取分所列表",
        operation_description="获取所有启用的分所列表（从 lsl_system_dept 读取）",
        responses={200: "成功"},
        tags=['组织管理']
    )
    def get(self, request):
        """获取全部分所列表（从 lsl_system_dept 读取）"""
        # 获取所有根部门（parent=None）的直接子部门，这些就是分所
        root_depts = Dept.objects.filter(status=True, parent__isnull=True).order_by('sort', 'id')
        
        branch_list = []
        for root_dept in root_depts:
            # 获取该根部门下的所有直接子部门（分所级别）
            branches = Dept.objects.filter(
                status=True,
                parent_id=root_dept.id
            ).order_by('sort', 'id')
            
            for branch in branches:
                # 计算该分所下的用户数量
                dept_ids = Dept.recursion_all_dept(branch.id)
                user_count = User.objects.filter(dept_id__in=dept_ids, is_active=True).count()
                
                branch_list.append({
                    'id': branch.id,
                    'name': branch.name,
                    'code': branch.key or '',  # 使用 key 字段作为 code
                    'headquarters_id': root_dept.id,  # 根部门ID作为总部ID
                    'user_count': user_count,
                })
        
        return Response({
            'code': 200,
            'msg': 'success',
            'data': branch_list
        })


class OrganizationTreeView(APIView):
    """获取组织架构树（根据当前用户角色）"""
    permission_classes = [IsAuthenticated]
    serializer_class = BaseUserSerializer
    
    @swagger_auto_schema(
        operation_summary="获取组织架构树",
        operation_description="根据当前用户角色返回对应层级的组织架构",
        responses={200: "成功"},
        tags=['组织管理']
    )
    def get(self, request):
        """获取组织架构树"""
        user = request.user
        role_level = getattr(user, 'role_level', None)
        
        # 根据角色返回不同的数据
        if role_level == 'HQ':
            # HQ：返回所有分所
            branches = Branch.objects.filter(status=True).order_by('sort', 'id')
            
            # 由于User.team_id不是ForeignKey，需要通过子查询计算用户数量
            data = []
            for branch in branches:
                # 获取该分所下的所有团队ID
                team_ids = Team.objects.filter(branch_id=branch.id, status=True).values_list('id', flat=True)
                # 统计这些团队下的用户数量
                user_count = User.objects.filter(
                    team_id__in=team_ids,
                    is_active=True,
                    role_level__in=['TEAM', 'SALES']
                ).count()
                
                data.append({
                    'id': branch.id,
                    'name': branch.name,
                    'code': branch.code,
                    'headquarters_id': branch.headquarters_id,
                    'user_count': user_count,
                })
        elif role_level == 'BRANCH':
            # BRANCH：返回本分所的团队
            branch_id = getattr(user, 'branch_id', None)
            if not branch_id:
                return Response({
                    'code': 400,
                    'msg': '用户未关联分所',
                    'data': []
                })
            
            teams = Team.objects.filter(branch_id=branch_id, status=True).order_by('sort', 'id')
            
            # 由于User.team_id不是ForeignKey，需要通过子查询计算用户数量
            data = []
            for team in teams:
                user_count = User.objects.filter(
                    team_id=team.id,
                    is_active=True,
                    role_level__in=['TEAM', 'SALES']
                ).count()
                
                data.append({
                    'id': team.id,
                    'name': team.name,
                    'code': team.code,
                    'branch_id': team.branch_id,
                    'user_count': user_count,
                })
        elif role_level == 'TEAM':
            # TEAM：返回本团队的用户
            team_id = getattr(user, 'team_id', None)
            if not team_id:
                return Response({
                    'code': 400,
                    'msg': '用户未关联团队',
                    'data': []
                })
            
            users = User.objects.filter(
                team_id=team_id,
                is_active=True,
                role_level__in=['TEAM', 'SALES']
            ).order_by('id')
            
            data = [{
                'id': user.id,
                'username': user.username,
                'name': user.name or user.username,
                'mobile': user.mobile,
                'role_level': user.role_level,
                'branch_id': user.branch_id,
                'team_id': user.team_id,
            } for user in users]
        else:
            # 其他角色：返回空列表
            data = []
        
        return Response({
            'code': 200,
            'msg': 'success',
            'data': data
        })


class TeamsByBranchView(APIView):
    """获取分所下的团队列表"""
    permission_classes = [IsAuthenticated]
    serializer_class = BaseUserSerializer
    
    @swagger_auto_schema(
        operation_summary="获取分所下的团队列表",
        operation_description="获取指定分所下的所有团队",
        responses={200: "成功"},
        tags=['组织管理']
    )
    def get(self, request, branch_id):
        """获取分所下的团队列表"""
        try:
            branch = Branch.objects.get(id=branch_id, status=True)
        except Branch.DoesNotExist:
            return Response({
                'code': 404,
                'msg': '分所不存在',
                'data': []
            })
        
        # 权限检查：HQ可以查看所有分所，BRANCH只能查看自己的分所
        user = request.user
        role_level = getattr(user, 'role_level', None)
        if role_level == 'BRANCH':
            user_branch_id = getattr(user, 'branch_id', None)
            if user_branch_id and int(branch_id) != int(user_branch_id):
                return Response({
                    'code': 403,
                    'msg': '无权查看该分所',
                    'data': []
                })
        
        teams = Team.objects.filter(branch_id=branch_id, status=True).order_by('sort', 'id')
        
        # 由于User.team_id不是ForeignKey，需要通过子查询计算用户数量
        data = []
        for team in teams:
            user_count = User.objects.filter(
                team_id=team.id,
                is_active=True,
                role_level__in=['TEAM', 'SALES']
            ).count()
            
            data.append({
                'id': team.id,
                'name': team.name,
                'code': team.code,
                'branch_id': team.branch_id,
                'user_count': user_count,
            })
        
        return Response({
            'code': 200,
            'msg': 'success',
            'data': data
        })


class UsersByTeamView(APIView):
    """获取团队下的用户列表（仅TEAM和SALES角色）"""
    permission_classes = [IsAuthenticated]
    serializer_class = BaseUserSerializer
    
    @swagger_auto_schema(
        operation_summary="获取团队下的用户列表",
        operation_description="获取指定团队下的所有用户（仅TEAM和SALES角色）",
        responses={200: "成功"},
        tags=['用户管理']
    )
    def get(self, request, team_id):
        """获取团队下的用户列表"""
        try:
            team = Team.objects.get(id=team_id, status=True)
        except Team.DoesNotExist:
            return Response({
                'code': 404,
                'msg': '团队不存在',
                'data': []
            })
        
        # 权限检查：HQ可以查看所有团队，BRANCH只能查看自己分所的团队，TEAM只能查看自己的团队
        user = request.user
        role_level = getattr(user, 'role_level', None)
        if role_level == 'BRANCH':
            user_branch_id = getattr(user, 'branch_id', None)
            if user_branch_id and team.branch_id != user_branch_id:
                return Response({
                    'code': 403,
                    'msg': '无权查看该团队',
                    'data': []
                })
        elif role_level == 'TEAM':
            user_team_id = getattr(user, 'team_id', None)
            if user_team_id and int(team_id) != int(user_team_id):
                return Response({
                    'code': 403,
                    'msg': '无权查看该团队',
                    'data': []
                })
        
        users = User.objects.filter(
            team_id=team_id,
            is_active=True,
            role_level__in=['TEAM', 'SALES']
        ).select_related('dept').order_by('id')
        
        data = [{
            'id': user.id,
            'username': user.username,
            'name': user.name or user.username,
            'mobile': user.mobile,
            'role_level': user.role_level,
            'branch_id': user.branch_id,
            'team_id': user.team_id,
            'branch_name': team.branch.name if team.branch else None,
            'team_name': team.name,
        } for user in users]
        
        return Response({
            'code': 200,
            'msg': 'success',
            'data': data
        })


class UserSearchView(APIView):
    """搜索用户（跨层级搜索，仅返回TEAM和SALES角色）"""
    permission_classes = [IsAuthenticated]
    serializer_class = BaseUserSerializer
    
    @swagger_auto_schema(
        operation_summary="搜索用户",
        operation_description="跨层级搜索用户（仅返回TEAM和SALES角色）",
        manual_parameters=[
            openapi.Parameter('keyword', openapi.IN_QUERY, description="搜索关键词（姓名或手机号）", type=openapi.TYPE_STRING),
            openapi.Parameter('branchId', openapi.IN_QUERY, description="分所ID（可选）", type=openapi.TYPE_INTEGER),
            openapi.Parameter('teamId', openapi.IN_QUERY, description="团队ID（可选）", type=openapi.TYPE_INTEGER),
        ],
        responses={200: "成功"},
        tags=['用户管理']
    )
    def get(self, request):
        """搜索用户"""
        keyword = request.query_params.get('keyword', '').strip()
        branch_id = request.query_params.get('branchId') or request.query_params.get('branch_id')
        team_id = request.query_params.get('teamId') or request.query_params.get('team_id')
        
        # 权限检查：根据当前用户角色限制搜索范围
        user = request.user
        role_level = getattr(user, 'role_level', None)
        
        # 构建查询条件
        query = Q(is_active=True)
        
        if role_level == 'HQ':
            # HQ：可以搜索全所
            pass
        elif role_level == 'BRANCH':
            # BRANCH：只能搜索本分所
            user_branch_id = getattr(user, 'branch_id', None)
            if not user_branch_id:
                user_branch_id = getattr(user, 'dept_id', None)
            if user_branch_id:
                branch_dept_ids = Dept.recursion_all_dept(int(user_branch_id))
                team_ids = Team.objects.filter(branch_id__in=branch_dept_ids, status=True).values_list('id', flat=True)
                query &= (
                    Q(branch_id__in=branch_dept_ids) |
                    Q(dept_id__in=branch_dept_ids) |
                    Q(team_id__in=team_ids)
                )
        elif role_level == 'TEAM':
            # TEAM：只能搜索本团队
            user_team_id = getattr(user, 'team_id', None)
            if user_team_id:
                query &= Q(team_id=user_team_id)
        else:
            # 其他角色：返回空
            return Response({
                'code': 200,
                'msg': 'success',
                'data': []
            })
        
        # 应用过滤条件
        if branch_id:
            try:
                branch_dept_ids = Dept.recursion_all_dept(int(branch_id))
            except Exception:
                branch_dept_ids = [branch_id]
            team_ids = Team.objects.filter(branch_id__in=branch_dept_ids, status=True).values_list('id', flat=True)
            query &= (
                Q(branch_id__in=branch_dept_ids) |
                Q(dept_id__in=branch_dept_ids) |
                Q(team_id__in=team_ids)
            )
        if team_id:
            query &= Q(team_id=team_id)
        
        # 搜索关键词
        if keyword:
            query &= (Q(name__icontains=keyword) | Q(username__icontains=keyword) | Q(mobile__icontains=keyword))
        
        users = User.objects.filter(query).select_related('dept').order_by('id')[:50]  # 限制最多50条
        
        data = []
        for user in users:
            # 获取组织名称
            branch_name = None
            team_name = None
            if user.branch_id:
                try:
                    branch = Branch.objects.get(id=user.branch_id)
                    branch_name = branch.name
                except Branch.DoesNotExist:
                    pass
            if user.team_id:
                try:
                    team = Team.objects.get(id=user.team_id)
                    team_name = team.name
                except Team.DoesNotExist:
                    pass
            
            data.append({
                'id': user.id,
                'username': user.username,
                'name': user.name or user.username,
                'mobile': user.mobile,
                'role_level': user.role_level,
                'branch_id': user.branch_id,
                'team_id': user.team_id,
                'branch_name': branch_name,
                'team_name': team_name,
            })
        
        return Response({
            'code': 200,
            'msg': 'success',
            'data': data
        })


class DeptTreeView(APIView):
    """获取部门树形结构（基于 lsl_system_dept）"""
    permission_classes = [IsAuthenticated]
    serializer_class = BaseUserSerializer
    
    @swagger_auto_schema(
        operation_summary="获取部门树形结构",
        operation_description="获取基于 lsl_system_dept 的部门树，支持懒加载",
        manual_parameters=[
            openapi.Parameter('parent', openapi.IN_QUERY, description="父部门ID，为空则返回根部门", type=openapi.TYPE_INTEGER),
        ],
        responses={200: "成功"},
        tags=['部门管理']
    )
    def get(self, request):
        """获取部门树形结构"""
        parent_id = request.query_params.get('parent')
        
        # 如果指定了 parent，返回该部门的子部门；否则返回根部门（parent=None）
        if parent_id:
            try:
                parent_id = int(parent_id)
                depts = Dept.objects.filter(status=True, parent_id=parent_id).order_by('sort', 'id')
            except ValueError:
                return Response({
                    'code': 400,
                    'msg': 'parent 参数无效',
                    'data': []
                })
        else:
            depts = Dept.objects.filter(status=True, parent__isnull=True).order_by('sort', 'id')
        
        data = []
        for dept in depts:
            # 检查是否有子部门
            has_children = Dept.objects.filter(parent_id=dept.id, status=True).exists()
            
            # 计算该部门及所有子部门的用户总数
            # 获取该部门及所有子部门的ID列表
            dept_ids = Dept.recursion_all_dept(dept.id)
            user_count = User.objects.filter(dept_id__in=dept_ids, is_active=True).count()
            
            data.append({
                'id': dept.id,
                'name': dept.name,
                'parent': dept.parent_id,
                'user_count': user_count,
                'has_children': has_children,
            })
        
        return Response({
            'code': 200,
            'msg': 'success',
            'data': data
        })


class UsersByDeptView(APIView):
    """获取指定部门下的用户列表"""
    permission_classes = [IsAuthenticated]
    serializer_class = BaseUserSerializer
    
    @swagger_auto_schema(
        operation_summary="获取部门用户列表",
        operation_description="获取指定部门下的所有用户",
        manual_parameters=[
            openapi.Parameter('include_children', openapi.IN_QUERY, description="是否包含子部门用户", type=openapi.TYPE_BOOLEAN),
        ],
        responses={200: "成功"},
        tags=['用户管理']
    )
    def get(self, request, dept_id):
        """获取部门用户列表"""
        try:
            dept = Dept.objects.get(id=dept_id, status=True)
        except Dept.DoesNotExist:
            return Response({
                'code': 404,
                'msg': '部门不存在',
                'data': []
            })
        
        # 是否包含子部门用户
        include_children = request.query_params.get('include_children', 'false').lower() == 'true'
        
        if include_children:
            # 获取该部门及所有子部门的ID列表
            dept_ids = Dept.recursion_all_dept(dept_id)
            users = User.objects.filter(dept_id__in=dept_ids, is_active=True).order_by('id')
        else:
            # 只获取该部门的用户
            users = User.objects.filter(dept_id=dept_id, is_active=True).order_by('id')
        
        data = [{
            'id': user.id,
            'username': user.username,
            'name': user.name or user.username,
            'mobile': user.mobile,
            'role_level': user.role_level,
            'dept_id': user.dept_id,
            'dept_name': dept.name if not include_children else None,
        } for user in users]
        
        return Response({
            'code': 200,
            'msg': 'success',
            'data': data
        })


class DeptUserSearchView(APIView):
    """跨部门搜索用户"""
    permission_classes = [IsAuthenticated]
    serializer_class = BaseUserSerializer
    
    @swagger_auto_schema(
        operation_summary="搜索部门用户",
        operation_description="跨部门搜索用户（按姓名或手机号）",
        manual_parameters=[
            openapi.Parameter('keyword', openapi.IN_QUERY, description="搜索关键词（姓名或手机号）", type=openapi.TYPE_STRING),
            openapi.Parameter('dept_id', openapi.IN_QUERY, description="部门ID（可选，限制搜索范围）", type=openapi.TYPE_INTEGER),
        ],
        responses={200: "成功"},
        tags=['用户管理']
    )
    def get(self, request):
        """搜索用户"""
        keyword = request.query_params.get('keyword', '').strip()
        dept_id = request.query_params.get('dept_id')
        
        if not keyword:
            return Response({
                'code': 400,
                'msg': '搜索关键词不能为空',
                'data': []
            })
        
        # 构建查询条件
        query = Q(is_active=True)
        
        # 如果指定了部门，限制搜索范围
        if dept_id:
            try:
                dept_id = int(dept_id)
                # 获取该部门及所有子部门的ID列表
                dept_ids = Dept.recursion_all_dept(dept_id)
                query &= Q(dept_id__in=dept_ids)
            except (ValueError, Dept.DoesNotExist):
                return Response({
                    'code': 400,
                    'msg': '部门ID无效',
                    'data': []
                })
        
        # 搜索关键词
        query &= (Q(name__icontains=keyword) | Q(username__icontains=keyword) | Q(mobile__icontains=keyword))
        
        users = User.objects.filter(query).order_by('id')[:50]  # 限制最多50条
        
        data = []
        for user in users:
            dept_name = None
            if user.dept_id:
                try:
                    dept = Dept.objects.get(id=user.dept_id)
                    dept_name = dept.name
                except Dept.DoesNotExist:
                    pass
            
            data.append({
                'id': user.id,
                'username': user.username,
                'name': user.name or user.username,
                'mobile': user.mobile,
                'role_level': user.role_level,
                'dept_id': user.dept_id,
                'dept_name': dept_name,
            })
        
        return Response({
            'code': 200,
            'msg': 'success',
            'data': data
        })
