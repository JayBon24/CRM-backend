"""
Mine Profile API - 用户个人资料接口
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from dvadmin.utils.json_response import DetailResponse


class MineProfileView(APIView):
    """
    Mine Profile 接口
    GET /api/mine/profile/
    获取当前登录用户的个人资料信息
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """获取当前用户个人资料"""
        user = request.user

        def resolve_org_ids_from_dept():
            dept = getattr(user, 'dept', None)
            if not dept:
                return None, None, None
            chain = []
            cursor = dept
            for _ in range(10):
                if not cursor:
                    break
                chain.append(cursor)
                cursor = getattr(cursor, 'parent', None)

            # 链路从当前部门到根部门：team -> branch -> hq
            team_id = None
            branch_id = None
            hq_id = None
            if len(chain) >= 3:
                team_id = chain[0].id
                branch_id = chain[1].id
                hq_id = chain[-1].id
            elif len(chain) == 2:
                branch_id = chain[0].id
                hq_id = chain[-1].id
            elif len(chain) == 1:
                hq_id = chain[0].id
            return team_id, branch_id, hq_id
        
        # 构建返回数据
        data = {
            "user_id": str(user.id),
            "name": user.name or user.username,
            "username": user.username,
            "avatar": user.avatar or "",
            "mobile": user.mobile or "",
            "email": user.email or "",
            "gender": str(user.gender) if user.gender is not None else "0",
            "user_type": getattr(user, 'user_type', 0),
            "is_superuser": user.is_superuser,
        }
        
        # 角色层级（优先使用 role_level 字段）
        role_level = getattr(user, 'role_level', None)
        if role_level:
            data['roleLevel'] = role_level
        else:
            # 如果没有 role_level，根据角色key推断
            data['roleLevel'] = 'SALES'  # 默认为销售角色
        
        # 组织架构ID（优先读用户字段，缺失时按 dept 层级回填）
        team_id = user.team_id
        branch_id = user.branch_id
        hq_id = user.headquarters_id
        if not team_id or not branch_id or not hq_id:
            dept_team_id, dept_branch_id, dept_hq_id = resolve_org_ids_from_dept()
            if not team_id:
                team_id = dept_team_id
            if not branch_id:
                branch_id = dept_branch_id
            if not hq_id:
                hq_id = dept_hq_id

        data['team_id'] = team_id
        data['branch_id'] = branch_id
        data['hq_id'] = hq_id
        
        # 部门信息
        dept = getattr(user, 'dept', None)
        if dept:
            data['dept_id'] = str(dept.id)
            data['dept_name'] = dept.name
        
        # 角色信息
        role = getattr(user, 'role', None)
        if role:
            roles = list(role.values('id', 'name', 'key'))
            if roles:
                data['role_info'] = roles
        
        return DetailResponse(data=data, msg="获取成功")
