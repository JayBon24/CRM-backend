"""
Tab3 MCP 白名单工具服务。

说明：
1) 所有工具都在服务端执行范围校验，不依赖提示词约束。
2) 写入按“草稿 -> 确认执行”两阶段处理，支持幂等。
"""
from __future__ import annotations

import re
import uuid
from copy import deepcopy
from datetime import datetime
from datetime import timedelta
from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ai_management.models import AIConversation, AIMessage, AIPendingAction
from customer_management.models import ApprovalTask, Customer, FollowupRecord
from customer_management.services.scope_service import (
    can_access_customer,
    filter_customer_queryset_for_user,
    get_scope_hint_text,
    resolve_scope_context,
)
from dvadmin.system.models import Users


LOW_RISK_ACTIONS = {
    "followup_create",
}

FOLLOWUP_FIELD_META: Dict[str, Dict[str, Any]] = {
    "client_id": {"label": "客户", "required": True, "type": "customer"},
    "summary": {"label": "跟进摘要", "required": True, "type": "string"},
    "followup_time": {"label": "跟进时间", "required": True, "type": "datetime"},
    "method": {"label": "跟进方式", "required": False, "type": "enum"},
    "method_other": {"label": "其他方式说明", "required": False, "type": "string"},
    "conclusion": {"label": "关键结论", "required": False, "type": "string"},
    "internal_participants": {"label": "内部参与人员", "required": False, "type": "multi_user"},
}

FOLLOWUP_REQUIRED_FIELDS = ["client_id", "summary", "followup_time"]

TAB3_CAPABILITIES = [
    {
        "id": "scope.read",
        "name": "权限范围查询",
        "tool": "crm_get_scope",
        "mode": "read",
        "risk_level": "low",
        "requires_confirm": False,
        "enabled": True,
    },
    {
        "id": "customer.search",
        "name": "客户查询",
        "tool": "crm_search_customer",
        "mode": "read",
        "risk_level": "low",
        "requires_confirm": False,
        "enabled": True,
    },
    {
        "id": "customer.count",
        "name": "客户统计",
        "tool": "crm_count_customers",
        "mode": "read",
        "risk_level": "low",
        "requires_confirm": False,
        "enabled": True,
    },
    {
        "id": "user.search",
        "name": "人员查询",
        "tool": "crm_search_users",
        "mode": "read",
        "risk_level": "low",
        "requires_confirm": False,
        "enabled": True,
    },
    {
        "id": "followup.prepare",
        "name": "跟进草稿卡片",
        "tool": "crm_prepare_followup",
        "mode": "write",
        "risk_level": "low",
        "requires_confirm": True,
        "enabled": True,
    },
    {
        "id": "followup.commit",
        "name": "跟进提交",
        "tool": "crm_commit_followup",
        "mode": "write",
        "risk_level": "low",
        "requires_confirm": True,
        "enabled": True,
    },
    {
        "id": "followup.patch",
        "name": "跟进卡片编辑",
        "tool": "crm_patch_pending_action",
        "mode": "write",
        "risk_level": "low",
        "requires_confirm": True,
        "enabled": True,
    },
    {
        "id": "risk.approval",
        "name": "高风险变更审批",
        "tool": "crm_request_high_risk_change",
        "mode": "write",
        "risk_level": "high",
        "requires_confirm": True,
        "enabled": True,
    },
]


COUNT_INTENT_TYPES = {"by_handler", "by_customer_name_keyword", "by_org_scope", "by_city"}
COUNT_CITY_WORDS = {
    "北京", "上海", "深圳", "广州", "杭州", "南京", "苏州", "成都", "重庆", "武汉", "天津",
    "西安", "厦门", "宁波", "郑州", "长沙", "青岛", "佛山", "东莞", "福州", "合肥", "昆明",
}


def _get_user(user_or_id) -> Optional[Users]:
    if not user_or_id:
        return None
    if isinstance(user_or_id, Users):
        return user_or_id
    try:
        return Users.objects.filter(id=int(user_or_id)).first()
    except Exception:
        return None


def _normalize_limit(limit: Any, default: int = 10, max_limit: int = 50) -> int:
    try:
        parsed = int(limit or default)
    except Exception:
        parsed = default
    if parsed <= 0:
        return default
    return min(parsed, max_limit)


def _parse_followup_time(value: Any):
    if not value:
        return timezone.now()
    if hasattr(value, "tzinfo"):
        dt = value
    else:
        dt = parse_datetime(str(value))
    if not dt:
        return timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _as_text(payload: dict, *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _extract_customer_keyword(input_text: str) -> str:
    text = (input_text or "").strip()
    if not text:
        return ""
    # 尝试识别“去了xxx公司/客户xxx”等口语表达
    patterns = [
        r"(?:去了|拜访|跟进|到)\s*([^\s，。,；;：:]{2,30}?)(?:公司|集团|企业|项目|案子|案件|客户)?(?:[，。,；;：:]|$)",
        r"(?:客户|公司)\s*([^\s，。,；;：:]{2,30})(?:[，。,；;：:]|$)",
    ]
    for pattern in patterns:
        matched = re.search(pattern, text)
        if matched:
            raw = matched.group(1).strip()
            return _normalize_customer_keyword(raw)
    return ""


def _normalize_customer_keyword(keyword: str) -> str:
    text = (keyword or "").strip()
    if not text:
        return ""
    text = re.sub(r"^了", "", text).strip()
    text = re.sub(r"^(趟|一趟|一下|下)", "", text).strip()
    text = re.sub(r"[“”\"'`]", "", text).strip()
    text = re.sub(r"(那里|那边|这边|这里|那儿|这儿|那块|这块|这家|那家|那边儿|这边儿)$", "", text).strip()
    text = re.sub(r"(客户那里|客户那边|公司那里|公司那边)$", "", text).strip()
    text = re.sub(r"(一下|一下子)$", "", text).strip()
    return text


def _build_customer_search_keywords(customer_name: str) -> list[str]:
    base = _normalize_customer_keyword(customer_name)
    if not base:
        return []
    keywords: list[str] = [base]

    trimmed = re.sub(r"(客户|公司|集团|企业|项目|案子|案件)$", "", base).strip()
    if trimmed and trimmed not in keywords:
        keywords.append(trimmed)

    # 进一步把“深圳德利客户”一类表达拆成核心词，提升命中率
    split_tokens = [token for token in re.split(r"[\s,，。.;；:：/\\-]+", trimmed or base) if token]
    for token in split_tokens:
        if len(token) >= 2 and token not in keywords:
            keywords.append(token)
    return keywords[:5]


def _normalize_followup_method(raw_value: Any) -> str:
    value = str(raw_value or "").strip().upper()
    mapping = {
        "PHONE": "PHONE",
        "WECHAT": "WECHAT",
        "EMAIL": "EMAIL",
        "VISIT": "VISIT",
        "MEETING": "VISIT",
        "OTHER": "OTHER",
    }
    return mapping.get(value, "OTHER")


def _normalize_candidate_row(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "contact_person": row.get("contact_person"),
        "contact_phone": row.get("contact_phone"),
    }


def _normalize_role_level(user) -> str:
    role_level = str(getattr(user, "role_level", "") or "").upper().strip()
    if role_level in {"HQ", "BRANCH", "TEAM", "SALES"}:
        return role_level
    org_scope = str(getattr(user, "org_scope", "") or "").upper().strip()
    if org_scope == "HQ":
        return "HQ"
    if org_scope == "BRANCH":
        return "BRANCH"
    if org_scope == "TEAM":
        return "TEAM"
    return "SALES"


def _scoped_user_queryset(user):
    queryset = Users.objects.filter(is_active=True)
    role_level = _normalize_role_level(user)
    if role_level == "HQ":
        return queryset
    if role_level == "BRANCH":
        branch_id = getattr(user, "branch_id", None)
        if not branch_id:
            return queryset.none()
        return queryset.filter(branch_id=branch_id)
    if role_level == "TEAM":
        team_id = getattr(user, "team_id", None)
        if not team_id:
            return queryset.none()
        return queryset.filter(team_id=team_id)
    team_id = getattr(user, "team_id", None)
    branch_id = getattr(user, "branch_id", None)
    if team_id:
        return queryset.filter(team_id=team_id)
    if branch_id:
        return queryset.filter(branch_id=branch_id)
    return queryset.filter(id=getattr(user, "id", 0))


def _normalize_user_row(user: Users) -> dict:
    return {
        "id": user.id,
        "name": user.name or user.username or f"用户{user.id}",
        "username": user.username,
        "mobile": user.mobile,
        "role_level": user.role_level,
        "team_id": user.team_id,
        "branch_id": user.branch_id,
    }


def _is_city_like_keyword(keyword: str) -> bool:
    text = (keyword or "").strip()
    if not text:
        return False
    if text in COUNT_CITY_WORDS:
        return True
    if text.endswith(("市", "省", "区", "县")) and len(text) <= 6:
        return True
    return False


def _extract_customer_count_subject(text: str) -> str:
    value = re.sub(r"[？?！!。,.，]", "", (text or "").strip())
    if not value:
        return ""
    patterns = [
        r"(?:查一下|查询|查|统计)\s*([^\s，。,；;：:]{1,24}?)\s*(?:有多少|多少)(?:家|个|位)?客户",
        r"([^\s，。,；;：:]{1,24}?)(?:有多少|多少)(?:家|个|位)?客户",
        r"([^\s，。,；;：:]{1,24}?)(?:客户)(?:有多少|多少|数量|总数)",
    ]
    for pattern in patterns:
        matched = re.search(pattern, value)
        if matched:
            subject = (matched.group(1) or "").strip()
            subject = re.sub(r"^(现在|目前|当前|我要查|帮我查|帮我查询)", "", subject).strip()
            subject = re.sub(r"(啊|呀|呢|吗)$", "", subject).strip()
            return subject
    return ""


def _extract_person_keywords(text: str) -> list[str]:
    value = (text or "").strip()
    if not value:
        return []
    normalized = value.replace("，", ",").replace("、", ",").replace("和", ",").replace("及", ",")
    chunks = [chunk.strip() for chunk in normalized.split(",") if chunk.strip()]
    names: list[str] = []
    for chunk in chunks:
        if chunk in {"我", "本人", "自己"}:
            names.append(chunk)
            continue
        matched = re.findall(r"[\u4e00-\u9fa5A-Za-z]{2,8}", chunk)
        for token in matched:
            cleaned = token.strip()
            cleaned = re.sub(r"^(内部参与人员|参与人员|经办人|负责人|销售|同事|同学|把)", "", cleaned).strip()
            for _ in range(4):
                trimmed = re.sub(r"(经办人|负责人|销售|同事|同学|内部参与人员|参与人员|把|也|一起|选上|加上|加入|添加)$", "", cleaned).strip()
                if trimmed == cleaned:
                    break
                cleaned = trimmed
            if len(cleaned) >= 2:
                names.append(cleaned)
    deduped: list[str] = []
    for name in names:
        if name not in deduped:
            deduped.append(name)
    return deduped[:10]


def _normalize_participants(raw: Any) -> list[dict]:
    if not isinstance(raw, list):
        return []
    rows: list[dict] = []
    for item in raw:
        if isinstance(item, dict):
            try:
                user_id = int(item.get("id"))
            except Exception:
                user_id = None
            if not user_id:
                continue
            name = str(item.get("name") or "").strip() or f"用户{user_id}"
            rows.append({"id": user_id, "name": name})
        else:
            try:
                user_id = int(item)
            except Exception:
                continue
            rows.append({"id": user_id, "name": f"用户{user_id}"})
    deduped: dict[int, dict] = {}
    for row in rows:
        deduped[int(row["id"])] = row
    return list(deduped.values())


def _merge_participants(existing: Any, additions: list[dict]) -> list[dict]:
    base = _normalize_participants(existing)
    merged = {int(row["id"]): row for row in base if row.get("id")}
    for row in additions or []:
        try:
            user_id = int(row.get("id"))
        except Exception:
            continue
        merged[user_id] = {
            "id": user_id,
            "name": str(row.get("name") or f"用户{user_id}"),
        }
    return list(merged.values())


def _build_followup_card_from_pending(pending: AIPendingAction) -> dict:
    draft_payload = deepcopy(pending.draft_payload or {})
    prefilled = draft_payload.get("prefilled_fields") or {}
    required_fields = draft_payload.get("required_fields") or deepcopy(FOLLOWUP_REQUIRED_FIELDS)
    missing_fields = _detect_missing_fields(prefilled, required_fields)
    return {
        "operation_id": pending.operation_id,
        "risk_level": pending.risk_level,
        "entity_type": pending.entity_type or "followup_record",
        "entity_id": pending.entity_id,
        "prefilled_fields": prefilled,
        "missing_fields": missing_fields,
        "required_fields": required_fields,
        "field_meta": draft_payload.get("field_meta") or deepcopy(FOLLOWUP_FIELD_META),
        "customer_candidates": draft_payload.get("customer_candidates") or draft_payload.get("duplicates") or [],
        "participants_candidates": draft_payload.get("participants_candidates") or [],
        "ui_mode": draft_payload.get("ui_mode") or "hybrid",
        "next_actions": draft_payload.get("next_actions") or ["confirm", "edit", "open_form", "cancel"],
        "expires_at": pending.expire_at.strftime("%Y-%m-%d %H:%M:%S") if pending.expire_at else None,
        "status": pending.status,
    }


def _parse_followup_time_from_text(text: str):
    value = (text or "").strip()
    if not value:
        return None
    direct = parse_datetime(value)
    if direct:
        if timezone.is_naive(direct):
            direct = timezone.make_aware(direct, timezone.get_current_timezone())
        return direct
    full_match = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})(?:日)?\s*(上午|下午|晚上)?\s*(\d{1,2})(?:[:点时](\d{1,2}))?", value)
    if full_match:
        year, month, day, period, hour, minute = full_match.groups()
        h = int(hour)
        m = int(minute or 0)
        if period in {"下午", "晚上"} and h < 12:
            h += 12
        dt = datetime(int(year), int(month), int(day), h, m, 0)
        return timezone.make_aware(dt, timezone.get_current_timezone())
    relative_match = re.search(r"(今天|明天|后天)\s*(上午|下午|晚上)?\s*(\d{1,2})(?:[:点时](\d{1,2}))?", value)
    if relative_match:
        day_label, period, hour, minute = relative_match.groups()
        offset = {"今天": 0, "明天": 1, "后天": 2}.get(day_label, 0)
        base = timezone.localtime(timezone.now()) + timedelta(days=offset)
        h = int(hour)
        m = int(minute or 0)
        if period in {"下午", "晚上"} and h < 12:
            h += 12
        dt = base.replace(hour=h, minute=m, second=0, microsecond=0)
        return dt
    return None


def _find_latest_pending_action(user: Users, conversation_id: Optional[int] = None):
    queryset = AIPendingAction.objects.filter(
        user_id=user.id,
        status__in=("pending", "failed"),
        is_deleted=False,
    )
    if conversation_id:
        queryset = queryset.filter(conversation_id=conversation_id)
    return queryset.order_by("-id").first()


def _detect_missing_fields(prefilled_fields: dict, required_fields: list[str]) -> list[str]:
    missing = []
    for field in required_fields:
        value = prefilled_fields.get(field)
        if value is None:
            missing.append(field)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(field)
            continue
        if isinstance(value, list) and not value:
            missing.append(field)
    return missing


def _append_message(
    conversation_id: int,
    role: str,
    message_type: str,
    content_json: Optional[dict] = None,
    creator_id: Optional[int] = None,
):
    if not conversation_id:
        return
    AIMessage.objects.create(
        conversation_id=conversation_id,
        role=role,
        message_type=message_type,
        content_json=content_json or {},
        creator_id=creator_id,
        modifier=str(creator_id or ""),
    )
    AIConversation.objects.filter(id=conversation_id).update(last_message_time=timezone.now())


def crm_get_scope(user_or_id) -> Dict[str, Any]:
    user = _get_user(user_or_id)
    if not user:
        return {"error": "用户不存在或未认证"}
    scope = resolve_scope_context(user)
    scope_text = get_scope_hint_text(user)
    return {
        "role_level": scope.get("role_level"),
        "team_id": scope.get("team_id"),
        "branch_id": scope.get("branch_id"),
        "hq_id": scope.get("hq_id"),
        "scope_text": scope_text,
    }


def get_tab3_capabilities() -> Dict[str, Any]:
    return {
        "version": "1.0",
        "items": deepcopy(TAB3_CAPABILITIES),
    }


def crm_search_customer(user_or_id, query: str, limit: int = 10) -> Dict[str, Any]:
    user = _get_user(user_or_id)
    if not user:
        return {"rows": [], "scope_applied": {}, "error": "用户不存在或未认证"}

    keyword = (query or "").strip()
    if not keyword:
        return {"rows": [], "scope_applied": crm_get_scope(user)}

    limit = _normalize_limit(limit, default=10, max_limit=50)
    queryset = Customer.objects.filter(is_deleted=False, name__icontains=keyword).select_related("owner_user").prefetch_related("handlers")
    scoped = filter_customer_queryset_for_user(queryset, user)[:limit]
    rows = []
    for customer in scoped:
        rows.append(
            {
                "id": customer.id,
                "name": customer.name,
                "contact_person": customer.contact_person,
                "contact_phone": customer.contact_phone,
                "owner_user_id": customer.owner_user_id,
                "team_id": customer.team_id,
                "branch_id": customer.branch_id,
            }
        )
    return {"rows": rows, "scope_applied": crm_get_scope(user)}


def crm_search_users(user_or_id, query: str, limit: int = 10) -> Dict[str, Any]:
    user = _get_user(user_or_id)
    if not user:
        return {"rows": [], "scope_applied": {}, "error": "用户不存在或未认证"}

    keyword = (query or "").strip()
    limit = _normalize_limit(limit, default=10, max_limit=50)
    queryset = _scoped_user_queryset(user)
    if keyword:
        queryset = queryset.filter(
            Q(name__icontains=keyword) | Q(username__icontains=keyword) | Q(mobile__icontains=keyword)
        )
    rows = [_normalize_user_row(item) for item in queryset.order_by("id")[:limit]]
    return {"rows": rows, "scope_applied": crm_get_scope(user)}


def _classify_customer_count_intent(message: str, intent_type: Optional[str] = None) -> tuple[str, dict]:
    explicit = (intent_type or "").strip()
    if explicit in COUNT_INTENT_TYPES:
        return explicit, {}

    text = (message or "").strip()
    subject = _extract_customer_count_subject(text)
    if not subject:
        return "by_org_scope", {}

    handler_markers = ("经办人", "负责人", "销售", "顾问", "跟进人")
    if any(marker in text for marker in handler_markers):
        for marker in handler_markers:
            if marker in text:
                return "by_handler", {"handler_name": text.split(marker, 1)[-1].replace("有多少客户", "").replace("多少客户", "").strip() or subject}
        return "by_handler", {"handler_name": subject}

    if subject in {"我", "本人", "自己"}:
        return "by_handler", {"handler_name": subject}

    if "分所" in text or "团队" in text:
        return "by_org_scope", {}

    if _is_city_like_keyword(subject):
        return "ambiguous", {"keyword": subject}

    if len(subject) <= 4 and re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", subject or ""):
        return "by_handler", {"handler_name": subject}

    return "by_customer_name_keyword", {"keyword": subject}


def crm_count_customers(
    user_or_id,
    intent_type: Optional[str] = None,
    message: str | None = None,
    handler_name: str | None = None,
    keyword: str | None = None,
    org_unit: str | None = None,
    city: str | None = None,
    confirm_on_ambiguous: bool = True,
) -> Dict[str, Any]:
    user = _get_user(user_or_id)
    if not user:
        return {"success": False, "error": "用户不存在或未认证"}

    base_queryset = filter_customer_queryset_for_user(
        Customer.objects.filter(is_deleted=False),
        user,
    )
    classified, inferred = _classify_customer_count_intent(message or "", intent_type)
    if classified == "ambiguous" and confirm_on_ambiguous:
        ambiguous_keyword = (keyword or inferred.get("keyword") or _extract_customer_count_subject(message or "")).strip()
        return {
            "success": True,
            "need_clarify": True,
            "clarify_options": [
                {"intent_type": "by_customer_name_keyword", "label": f"客户名称包含“{ambiguous_keyword}”", "keyword": ambiguous_keyword},
                {"intent_type": "by_org_scope", "label": f"{ambiguous_keyword}分所客户总数", "org_unit": ambiguous_keyword},
                {"intent_type": "by_city", "label": f"客户地址包含“{ambiguous_keyword}”", "city": ambiguous_keyword},
            ],
            "clarify_question": (
                f"您要查的是：1) 客户名称包含“{ambiguous_keyword}”；2) {ambiguous_keyword}分所客户总数；"
                f"3) 地址包含“{ambiguous_keyword}”的客户数？"
            ),
            "dimension": "ambiguous",
            "scope_applied": crm_get_scope(user),
            "evidence": {"message": message},
        }

    resolved_intent = classified if classified != "ambiguous" else "by_customer_name_keyword"
    resolved_keyword = (keyword or inferred.get("keyword") or "").strip()
    resolved_handler_name = (handler_name or inferred.get("handler_name") or "").strip()
    resolved_city = (city or inferred.get("keyword") or "").strip()

    if resolved_intent == "by_handler":
        if resolved_handler_name in {"我", "本人", "自己"}:
            users = [_normalize_user_row(user)]
            user_ids = [user.id]
        else:
            search_result = crm_search_users(user, resolved_handler_name, limit=10)
            users = search_result.get("rows") or []
            user_ids = [int(item["id"]) for item in users if item.get("id")]
        if not user_ids:
            return {
                "success": True,
                "need_clarify": False,
                "count": 0,
                "dimension": "handler",
                "scope_applied": crm_get_scope(user),
                "evidence": {"handler_name": resolved_handler_name, "matched_users": []},
                "message": f"未在当前范围内找到经办人“{resolved_handler_name}”。",
            }
        if len(user_ids) > 1 and confirm_on_ambiguous:
            return {
                "success": True,
                "need_clarify": True,
                "clarify_options": [
                    {"intent_type": "by_handler", "handler_name": item.get("name"), "label": f"按经办人 {item.get('name')} 统计"}
                    for item in users
                ],
                "clarify_question": f"匹配到多个经办人，请确认要统计哪位：{', '.join(item.get('name') or '' for item in users if item.get('name'))}",
                "dimension": "handler",
                "scope_applied": crm_get_scope(user),
                "evidence": {"handler_name": resolved_handler_name, "matched_users": users},
            }
        count = base_queryset.filter(Q(owner_user_id__in=user_ids) | Q(handlers__id__in=user_ids)).distinct().count()
        return {
            "success": True,
            "need_clarify": False,
            "count": count,
            "dimension": "handler",
            "scope_applied": crm_get_scope(user),
            "evidence": {"handler_name": resolved_handler_name, "matched_users": users},
        }

    if resolved_intent == "by_city":
        city_keyword = resolved_city or resolved_keyword
        if not city_keyword:
            return {
                "success": True,
                "need_clarify": True,
                "clarify_options": [],
                "clarify_question": "请补充城市名称（例如：深圳）。",
                "dimension": "city",
                "scope_applied": crm_get_scope(user),
                "evidence": {"message": message},
            }
        count = base_queryset.filter(address__icontains=city_keyword).count()
        return {
            "success": True,
            "need_clarify": False,
            "count": count,
            "dimension": "city",
            "scope_applied": crm_get_scope(user),
            "evidence": {"city": city_keyword},
        }

    if resolved_intent == "by_org_scope":
        role_level = _normalize_role_level(user)
        branch_keyword = (org_unit or resolved_keyword or "").strip()
        scoped_queryset = base_queryset
        if branch_keyword and role_level == "HQ":
            scoped_queryset = scoped_queryset.filter(Q(branch_id__isnull=False), Q(address__icontains=branch_keyword) | Q(name__icontains=branch_keyword))
        return {
            "success": True,
            "need_clarify": False,
            "count": scoped_queryset.distinct().count(),
            "dimension": "org_scope",
            "scope_applied": crm_get_scope(user),
            "evidence": {"role_level": role_level, "org_unit": branch_keyword},
        }

    name_keyword = resolved_keyword or _extract_customer_count_subject(message or "")
    if not name_keyword:
        return {
            "success": True,
            "need_clarify": True,
            "clarify_options": [],
            "clarify_question": "请补充要匹配的客户名称关键词。",
            "dimension": "name_keyword",
            "scope_applied": crm_get_scope(user),
            "evidence": {"message": message},
        }
    queryset = base_queryset
    for token in _build_customer_search_keywords(name_keyword):
        queryset = queryset.filter(name__icontains=token)
    return {
        "success": True,
        "need_clarify": False,
        "count": queryset.distinct().count(),
        "dimension": "name_keyword",
        "scope_applied": crm_get_scope(user),
        "evidence": {"keyword": name_keyword},
    }


def crm_prepare_followup(
    user_or_id,
    conversation_id: Optional[int] = None,
    input_text: str | None = None,
    fields: Optional[dict] = None,
) -> Dict[str, Any]:
    user = _get_user(user_or_id)
    if not user:
        return {"error": "用户不存在或未认证"}

    fields = fields or {}
    input_text = (input_text or "").strip()
    customer_id = fields.get("client_id") or fields.get("customer_id")
    customer_name = _as_text(fields, "customer_name", "client_name", "name")
    if not customer_name:
        customer_name = _extract_customer_keyword(input_text)
    customer_name = _normalize_customer_keyword(customer_name)

    customer = None
    duplicates: list[dict] = []
    customer_candidates: list[dict] = []
    if customer_id:
        customer = Customer.objects.filter(id=customer_id, is_deleted=False).first()
        if customer and not can_access_customer(user, customer):
            return {"error": "无权操作该客户"}
    elif customer_name:
        candidates_map: dict[int, dict] = {}
        for keyword in _build_customer_search_keywords(customer_name):
            search = crm_search_customer(user, keyword, limit=10)
            rows = search.get("rows") or []
            for row in rows:
                row_id = row.get("id")
                if not row_id:
                    continue
                candidates_map[int(row_id)] = _normalize_candidate_row(row)
            if len(candidates_map) >= 10:
                break

        customer_candidates = list(candidates_map.values())[:10]
        if len(customer_candidates) == 1:
            candidate = customer_candidates[0]
            customer = Customer.objects.filter(id=candidate.get("id"), is_deleted=False).first()
        elif len(customer_candidates) > 1:
            duplicates = customer_candidates

    summary = _as_text(fields, "summary", "content") or input_text
    conclusion = _as_text(fields, "conclusion")
    followup_time = fields.get("followup_time") or fields.get("time")
    next_followup_time = fields.get("next_followup_time") or fields.get("next_plan_at")
    method = _normalize_followup_method(fields.get("method") or fields.get("type") or "OTHER")
    method_other = _as_text(fields, "method_other")

    participants_candidates_map: dict[int, dict] = {}
    internal_participants = _normalize_participants(fields.get("internal_participants") or fields.get("system_users") or [])
    for person_keyword in _extract_person_keywords(input_text):
        if person_keyword in {"我", "本人", "自己"}:
            participants_candidates_map[int(user.id)] = _normalize_user_row(user)
            internal_participants = _merge_participants(
                internal_participants,
                [{"id": user.id, "name": user.name or user.username or f"用户{user.id}"}],
            )
            continue
        result = crm_search_users(user, person_keyword, limit=10)
        for row in result.get("rows") or []:
            try:
                row_id = int(row.get("id"))
            except Exception:
                continue
            participants_candidates_map[row_id] = row
        rows = result.get("rows") or []
        if len(rows) == 1:
            internal_participants = _merge_participants(internal_participants, rows)
    participants_candidates = list(participants_candidates_map.values())[:10]

    prefilled_fields = {
        "client_id": customer.id if customer else customer_id,
        "customer_name": customer.name if customer else customer_name,
        "summary": summary,
        "conclusion": conclusion,
        "method": method,
        "method_other": method_other,
        "followup_time": str(followup_time or timezone.now().strftime("%Y-%m-%d %H:%M:%S")),
        "next_followup_time": str(next_followup_time) if next_followup_time else None,
        "location_status": fields.get("location_status") or "success",
        "address": fields.get("address") or "",
        "attachments": fields.get("attachments") or [],
        "internal_participants": internal_participants,
        "customer_participants": fields.get("customer_participants") or fields.get("client_contacts") or [],
    }
    missing_fields = _detect_missing_fields(prefilled_fields, FOLLOWUP_REQUIRED_FIELDS)

    operation_id = uuid.uuid4().hex
    expire_at = timezone.now() + timedelta(hours=2)
    draft_payload = {
        "prefilled_fields": prefilled_fields,
        "missing_fields": missing_fields,
        "duplicates": duplicates,
        "required_fields": deepcopy(FOLLOWUP_REQUIRED_FIELDS),
        "field_meta": deepcopy(FOLLOWUP_FIELD_META),
        "customer_candidates": customer_candidates,
        "participants_candidates": participants_candidates,
        "ui_mode": "hybrid",
        "next_actions": ["confirm", "edit", "open_form", "cancel"],
        "input_text": input_text,
    }

    pending = AIPendingAction.objects.create(
        operation_id=operation_id,
        user_id=user.id,
        conversation_id=conversation_id,
        action_type="followup_create",
        risk_level="low",
        entity_type="customer",
        entity_id=prefilled_fields.get("client_id") or None,
        draft_payload=draft_payload,
        status="pending",
        expire_at=expire_at,
        creator_id=user.id,
        modifier=user.name or str(user.id),
    )

    card = {
        "operation_id": pending.operation_id,
        "risk_level": "low",
        "entity_type": "followup_record",
        "entity_id": prefilled_fields.get("client_id"),
        "prefilled_fields": prefilled_fields,
        "missing_fields": missing_fields,
        "duplicates": duplicates,
        "required_fields": deepcopy(FOLLOWUP_REQUIRED_FIELDS),
        "field_meta": deepcopy(FOLLOWUP_FIELD_META),
        "customer_candidates": customer_candidates,
        "participants_candidates": participants_candidates,
        "ui_mode": "hybrid",
        "next_actions": ["confirm", "edit", "open_form", "cancel"],
        "confirm_text": "确认后将写入跟进记录",
        "expires_at": expire_at.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if conversation_id:
        _append_message(
            conversation_id=conversation_id,
            role="assistant",
            message_type="card",
            content_json={"card": card},
            creator_id=user.id,
        )
    return {"operation_id": pending.operation_id, "card": card}


@transaction.atomic
def crm_patch_pending_action(
    user_or_id,
    operation_id: Optional[str] = None,
    patch_text: str | None = None,
    edited_fields: Optional[dict] = None,
    conversation_id: Optional[int] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    user = _get_user(user_or_id)
    if not user:
        return {"success": False, "error": "用户不存在或未认证"}

    pending = None
    if operation_id:
        pending = (
            AIPendingAction.objects.select_for_update()
            .filter(operation_id=(operation_id or "").strip(), user_id=user.id, is_deleted=False)
            .first()
        )
    if not pending:
        pending = (
            AIPendingAction.objects.select_for_update()
            .filter(
                user_id=user.id,
                conversation_id=conversation_id,
                status__in=("pending", "failed"),
                is_deleted=False,
            )
            .order_by("-id")
            .first()
        )
    if not pending:
        return {"success": False, "error": "没有可编辑的待确认卡片"}
    if pending.status not in ("pending", "failed"):
        return {"success": False, "error": f"当前状态不允许编辑：{pending.status}"}

    payload = deepcopy(pending.draft_payload or {})
    prefilled = payload.get("prefilled_fields") or {}
    updated_fields: dict[str, Any] = {}
    customer_candidates = payload.get("customer_candidates") or payload.get("duplicates") or []
    participants_candidates = payload.get("participants_candidates") or []

    if isinstance(edited_fields, dict) and edited_fields:
        prefilled.update(edited_fields)
        updated_fields.update(edited_fields)

    patch_text = (patch_text or "").strip()
    if patch_text:
        normalized = patch_text.replace("：", ":")
        if any(word in normalized for word in ("客户", "公司", "改成", "选择")):
            extracted_customer = _extract_customer_keyword(normalized) or _normalize_customer_keyword(_as_text({"q": normalized}, "q"))
            if extracted_customer:
                candidates_map: dict[int, dict] = {}
                for token in _build_customer_search_keywords(extracted_customer):
                    search = crm_search_customer(user, token, limit=10)
                    for row in search.get("rows") or []:
                        try:
                            row_id = int(row.get("id"))
                        except Exception:
                            continue
                        candidates_map[row_id] = _normalize_candidate_row(row)
                    if len(candidates_map) >= 10:
                        break
                customer_candidates = list(candidates_map.values())[:10]
                if len(customer_candidates) == 1:
                    prefilled["client_id"] = customer_candidates[0].get("id")
                    prefilled["customer_name"] = customer_candidates[0].get("name")
                    updated_fields["client_id"] = prefilled["client_id"]
                    updated_fields["customer_name"] = prefilled["customer_name"]
                else:
                    prefilled["customer_name"] = extracted_customer
                    updated_fields["customer_name"] = extracted_customer

        dt = _parse_followup_time_from_text(normalized)
        if dt:
            formatted = timezone.localtime(dt).strftime("%Y-%m-%d %H:%M:%S")
            prefilled["followup_time"] = formatted
            updated_fields["followup_time"] = formatted

        method_map = {
            "电话": "PHONE",
            "微信": "WECHAT",
            "邮件": "EMAIL",
            "拜访": "VISIT",
            "面谈": "VISIT",
        }
        for k, v in method_map.items():
            if k in normalized:
                prefilled["method"] = v
                if v != "OTHER":
                    prefilled["method_other"] = ""
                updated_fields["method"] = v
                break
        if "其他方式" in normalized or "OTHER" in normalized.upper():
            prefilled["method"] = "OTHER"
            updated_fields["method"] = "OTHER"
            matched_other = re.search(r"(?:其他方式|方式)\s*[:：]?\s*(.+)$", normalized)
            if matched_other:
                other_text = matched_other.group(1).strip()
                prefilled["method_other"] = other_text
                updated_fields["method_other"] = other_text

        summary_match = re.search(r"(?:摘要|跟进摘要)\s*[:：]?\s*(.+)$", normalized)
        if summary_match:
            summary = summary_match.group(1).strip()
            prefilled["summary"] = summary
            updated_fields["summary"] = summary

        conclusion_match = re.search(r"(?:结论|关键结论|结果)\s*[:：]?\s*(.+)$", normalized)
        if conclusion_match:
            conclusion = conclusion_match.group(1).strip()
            prefilled["conclusion"] = conclusion
            updated_fields["conclusion"] = conclusion

        if any(k in normalized for k in ("参与", "同事", "我和", "加上", "选上")):
            participant_rows = []
            participants_map: dict[int, dict] = {}
            for keyword in _extract_person_keywords(normalized):
                if keyword in {"我", "本人", "自己"}:
                    me = _normalize_user_row(user)
                    participant_rows.append({"id": me["id"], "name": me["name"]})
                    participants_map[int(me["id"])] = me
                    continue
                search = crm_search_users(user, keyword, limit=10)
                rows = search.get("rows") or []
                for row in rows:
                    try:
                        row_id = int(row.get("id"))
                    except Exception:
                        continue
                    participants_map[row_id] = row
                if len(rows) == 1:
                    participant_rows.append({"id": rows[0].get("id"), "name": rows[0].get("name")})
            participants_candidates = list(participants_map.values())[:10] or participants_candidates
            merged = _merge_participants(prefilled.get("internal_participants") or [], participant_rows)
            if merged:
                prefilled["internal_participants"] = merged
                updated_fields["internal_participants"] = merged

    payload["prefilled_fields"] = prefilled
    payload["customer_candidates"] = customer_candidates
    payload["participants_candidates"] = participants_candidates
    payload["required_fields"] = payload.get("required_fields") or deepcopy(FOLLOWUP_REQUIRED_FIELDS)
    payload["field_meta"] = payload.get("field_meta") or deepcopy(FOLLOWUP_FIELD_META)
    payload["missing_fields"] = _detect_missing_fields(prefilled, payload["required_fields"])
    payload["last_patch_text"] = patch_text

    pending.draft_payload = payload
    if idempotency_key:
        pending.last_idempotency_key = idempotency_key
    pending.modifier = user.name or str(user.id)
    pending.save(update_fields=["draft_payload", "last_idempotency_key", "modifier", "update_datetime"])

    card = _build_followup_card_from_pending(pending)
    if pending.conversation_id:
        _append_message(
            conversation_id=pending.conversation_id,
            role="assistant",
            message_type="card",
            content_json={"card": card},
            creator_id=user.id,
        )
    return {
        "success": True,
        "operation_id": pending.operation_id,
        "updated_fields": updated_fields,
        "missing_fields": card.get("missing_fields") or [],
        "customer_candidates": card.get("customer_candidates") or [],
        "participants_candidates": card.get("participants_candidates") or [],
        "card": card,
    }


@transaction.atomic
def crm_commit_followup(
    user_or_id,
    operation_id: str,
    edited_fields: Optional[dict] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    user = _get_user(user_or_id)
    if not user:
        return {"success": False, "error": "用户不存在或未认证"}

    operation_id = (operation_id or "").strip()
    if not operation_id:
        return {"success": False, "error": "缺少 operation_id"}

    pending = (
        AIPendingAction.objects.select_for_update()
        .filter(operation_id=operation_id, user_id=user.id, is_deleted=False)
        .first()
    )
    if not pending:
        return {"success": False, "error": "待确认操作不存在"}

    if pending.status == "executed":
        if idempotency_key and pending.last_idempotency_key == idempotency_key:
            result = deepcopy(pending.result_json or {})
            result["replayed"] = True
            return result
        return {"success": False, "error": "该操作已执行"}

    if pending.status not in ("pending", "failed"):
        return {"success": False, "error": f"当前状态不允许确认：{pending.status}"}

    if pending.expire_at and pending.expire_at < timezone.now():
        pending.status = "expired"
        pending.modifier = user.name or str(user.id)
        pending.save(update_fields=["status", "modifier", "update_datetime"])
        return {"success": False, "error": "操作已过期，请重新发起"}

    payload = deepcopy(pending.draft_payload or {})
    prefilled = payload.get("prefilled_fields") or {}
    if isinstance(edited_fields, dict):
        prefilled.update(edited_fields)

    client_id = prefilled.get("client_id")
    try:
        if client_id is not None:
            client_id = int(client_id)
    except Exception:
        client_id = None
    if not client_id:
        return {"success": False, "error": "缺少客户ID，无法提交"}
    customer = Customer.objects.filter(id=client_id, is_deleted=False).first()
    if not customer:
        return {"success": False, "error": "客户不存在或已删除"}
    if not can_access_customer(user, customer):
        return {"success": False, "error": "无权操作该客户"}

    method = _normalize_followup_method(prefilled.get("method") or prefilled.get("followup_type") or "OTHER")

    summary = _as_text(prefilled, "summary", "content")
    conclusion = _as_text(prefilled, "conclusion")
    content = _as_text(prefilled, "content")
    if not content:
        content = summary
    if conclusion and conclusion not in content:
        content = f"{content}\n关键结论：{conclusion}".strip()

    followup_time = _parse_followup_time(prefilled.get("followup_time") or prefilled.get("time"))
    next_followup_time = _parse_followup_time(prefilled.get("next_followup_time")) if prefilled.get("next_followup_time") else None

    try:
        record = FollowupRecord.objects.create(
            client_id=customer.id,
            user_id=user.id,
            method=method,
            method_other=prefilled.get("method_other"),
            summary=summary,
            conclusion=conclusion,
            content=content or summary or "AI创建跟进记录",
            duration=prefilled.get("duration"),
            location_status=prefilled.get("location_status") or "success",
            lng=prefilled.get("lng"),
            lat=prefilled.get("lat"),
            address=prefilled.get("address"),
            internal_participants=prefilled.get("internal_participants") or [],
            customer_participants=prefilled.get("customer_participants") or [],
            attachments=prefilled.get("attachments") or [],
            followup_time=followup_time,
            next_followup_time=next_followup_time,
            creator_id=user.id,
            modifier=user.name or str(user.id),
        )
    except Exception as exc:
        pending.status = "failed"
        pending.result_json = {"success": False, "error": str(exc)}
        pending.modifier = user.name or str(user.id)
        pending.save(update_fields=["status", "result_json", "modifier", "update_datetime"])
        return {"success": False, "error": f"写入失败：{exc}"}

    result = {
        "success": True,
        "record_id": record.id,
        "operation_id": pending.operation_id,
        "message": "跟进记录已创建",
    }
    pending.status = "executed"
    pending.last_idempotency_key = idempotency_key or pending.last_idempotency_key
    pending.result_json = result
    pending.modifier = user.name or str(user.id)
    pending.save(
        update_fields=[
            "status",
            "last_idempotency_key",
            "result_json",
            "modifier",
            "update_datetime",
        ]
    )
    if pending.conversation_id:
        _append_message(
            conversation_id=pending.conversation_id,
            role="assistant",
            message_type="action_result",
            content_json=result,
            creator_id=user.id,
        )
    return result


@transaction.atomic
def crm_cancel_action(user_or_id, operation_id: str) -> Dict[str, Any]:
    user = _get_user(user_or_id)
    if not user:
        return {"success": False, "error": "用户不存在或未认证"}

    pending = (
        AIPendingAction.objects.select_for_update()
        .filter(operation_id=operation_id, user_id=user.id, is_deleted=False)
        .first()
    )
    if not pending:
        return {"success": False, "error": "待确认操作不存在"}
    if pending.status in ("executed", "expired"):
        return {"success": False, "error": f"当前状态不允许取消：{pending.status}"}
    pending.status = "cancelled"
    pending.modifier = user.name or str(user.id)
    pending.save(update_fields=["status", "modifier", "update_datetime"])
    result = {"success": True, "operation_id": operation_id, "status": "cancelled"}
    if pending.conversation_id:
        _append_message(
            conversation_id=pending.conversation_id,
            role="assistant",
            message_type="action_result",
            content_json=result,
            creator_id=user.id,
        )
    return result


def crm_request_high_risk_change(
    user_or_id,
    conversation_id: Optional[int] = None,
    entity_type: str | None = None,
    entity_id: Optional[int] = None,
    payload: Optional[dict] = None,
) -> Dict[str, Any]:
    user = _get_user(user_or_id)
    if not user:
        return {"success": False, "error": "用户不存在或未认证"}

    payload = payload or {}
    customer_id = entity_id
    if entity_type == "customer" and not customer_id:
        customer_id = payload.get("customer_id")
    if not customer_id:
        return {"success": False, "error": "高风险变更必须指定客户ID"}
    customer = Customer.objects.filter(id=customer_id, is_deleted=False).first()
    if not customer:
        return {"success": False, "error": "客户不存在或已删除"}
    if not can_access_customer(user, customer):
        return {"success": False, "error": "无权操作该客户"}

    approval = ApprovalTask.objects.create(
        approval_type="HANDOVER",
        applicant_id=user.id,
        approval_chain=["TEAM", "BRANCH", "HQ"],
        current_step=0,
        current_approver_role="TEAM",
        status="pending",
        related_customer_id=customer.id,
        related_data=payload,
        creator_id=user.id,
        modifier=user.name or str(user.id),
    )

    operation_id = uuid.uuid4().hex
    pending = AIPendingAction.objects.create(
        operation_id=operation_id,
        user_id=user.id,
        conversation_id=conversation_id,
        action_type="high_risk_change",
        risk_level="high",
        entity_type=entity_type or "customer",
        entity_id=customer.id,
        draft_payload=payload,
        status="approval_pending",
        expire_at=timezone.now() + timedelta(days=7),
        result_json={"approval_id": approval.id, "status": approval.status},
        creator_id=user.id,
        modifier=user.name or str(user.id),
    )
    result = {"success": True, "approval_id": approval.id, "status": approval.status, "operation_id": pending.operation_id}
    if conversation_id:
        _append_message(
            conversation_id=conversation_id,
            role="assistant",
            message_type="action_result",
            content_json=result,
            creator_id=user.id,
        )
    return result


def confirm_pending_action(
    user_or_id,
    operation_id: str,
    edited_fields: Optional[dict] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    user = _get_user(user_or_id)
    if not user:
        return {"success": False, "error": "用户不存在或未认证"}
    pending = AIPendingAction.objects.filter(
        operation_id=operation_id,
        user_id=user.id,
        is_deleted=False,
    ).first()
    if not pending:
        return {"success": False, "error": "待确认操作不存在"}
    if pending.risk_level == "high":
        return {"success": False, "error": "高风险操作不支持直接确认，请走审批流"}
    if pending.action_type in LOW_RISK_ACTIONS:
        return crm_commit_followup(
            user_or_id=user,
            operation_id=operation_id,
            edited_fields=edited_fields,
            idempotency_key=idempotency_key or uuid.uuid4().hex,
        )
    return {"success": False, "error": f"不支持的动作类型：{pending.action_type}"}


def get_latest_pending_action(user_or_id, conversation_id: Optional[int] = None) -> Dict[str, Any]:
    user = _get_user(user_or_id)
    if not user:
        return {"success": False, "error": "用户不存在或未认证"}
    pending = _find_latest_pending_action(user, conversation_id=conversation_id)
    if not pending:
        return {"success": False, "error": "当前没有待确认操作"}
    card = _build_followup_card_from_pending(pending)
    return {
        "success": True,
        "operation_id": pending.operation_id,
        "action_type": pending.action_type,
        "status": pending.status,
        "risk_level": pending.risk_level,
        "card": card,
        "draft_payload": deepcopy(pending.draft_payload or {}),
    }


def get_pending_action_draft(user_or_id, operation_id: str) -> Dict[str, Any]:
    user = _get_user(user_or_id)
    if not user:
        return {"success": False, "error": "用户不存在或未认证"}
    pending = AIPendingAction.objects.filter(
        operation_id=(operation_id or "").strip(),
        user_id=user.id,
        is_deleted=False,
    ).first()
    if not pending:
        return {"success": False, "error": "待确认操作不存在"}
    draft_payload = deepcopy(pending.draft_payload or {})
    card = _build_followup_card_from_pending(pending)
    return {
        "success": True,
        "operation_id": pending.operation_id,
        "action_type": pending.action_type,
        "status": pending.status,
        "risk_level": pending.risk_level,
        "card": card,
        "draft_payload": draft_payload,
    }
