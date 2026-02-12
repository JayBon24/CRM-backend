"""
统一的数据范围判定服务。

用于小程序 API、AI 工具以及 WebSocket 消费者中的客户可见性校验。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from django.db.models import Q, QuerySet


def resolve_scope_context(user) -> Dict[str, Any]:
    """提取当前用户的组织与角色范围信息。"""
    role_level = getattr(user, "role_level", None) or getattr(user, "org_scope", None) or "SALES"
    team_id = getattr(user, "team_id", None) or getattr(user, "dept_id", None)
    branch_id = getattr(user, "branch_id", None) or getattr(user, "dept_id", None)
    hq_id = getattr(user, "headquarters_id", None)
    return {
        "role_level": role_level,
        "team_id": team_id,
        "branch_id": branch_id,
        "hq_id": hq_id,
        "user_id": getattr(user, "id", None),
    }


def build_customer_scope_q(user) -> Q:
    """构建客户数据范围过滤条件。"""
    if not user or not getattr(user, "is_authenticated", False):
        return Q(pk__in=[])

    if getattr(user, "is_superuser", False):
        return Q()

    scope = resolve_scope_context(user)
    role_level = scope["role_level"]

    if role_level == "HQ":
        return Q()

    if role_level == "BRANCH":
        branch_id = scope.get("branch_id")
        if not branch_id:
            return Q(pk__in=[])
        return Q(branch_id=branch_id)

    if role_level == "TEAM":
        team_id = scope.get("team_id")
        if not team_id:
            return Q(pk__in=[])
        return Q(team_id=team_id)

    user_id = scope.get("user_id")
    if not user_id:
        return Q(pk__in=[])
    # 销售：owner 或 handlers
    return Q(owner_user_id=user_id) | Q(handlers__id=user_id)


def filter_customer_queryset_for_user(queryset: QuerySet, user) -> QuerySet:
    """按用户范围过滤客户 QuerySet。"""
    q = build_customer_scope_q(user)
    filtered = queryset.filter(q)
    # handlers 关联会产生重复
    return filtered.distinct()


def can_access_customer(user, customer) -> bool:
    """判断用户是否可访问该客户。"""
    if not user or not getattr(user, "is_authenticated", False):
        return False

    if getattr(user, "is_superuser", False):
        return True

    scope = resolve_scope_context(user)
    role_level = scope["role_level"]

    if role_level == "HQ":
        return True

    if role_level == "BRANCH":
        branch_id = scope.get("branch_id")
        return bool(branch_id and str(getattr(customer, "branch_id", "")) == str(branch_id))

    if role_level == "TEAM":
        team_id = scope.get("team_id")
        return bool(team_id and str(getattr(customer, "team_id", "")) == str(team_id))

    user_id = scope.get("user_id")
    if not user_id:
        return False

    owner_ok = str(getattr(customer, "owner_user_id", "")) == str(user_id)
    if owner_ok:
        return True

    try:
        if hasattr(customer, "handlers"):
            return customer.handlers.filter(id=user_id).exists()
    except Exception:
        pass
    return False


def get_scope_hint_text(user) -> str:
    """返回可用于前端提示的数据范围文案。"""
    scope = resolve_scope_context(user)
    role = scope["role_level"]
    mapping = {
        "HQ": "当前为总所管理范围（全所数据）",
        "BRANCH": "当前为分所管理范围（本分所数据）",
        "TEAM": "当前为团队管理范围（本团队数据）",
        "SALES": "当前为销售范围（本人负责客户）",
    }
    return mapping.get(role, "当前为个人范围")
