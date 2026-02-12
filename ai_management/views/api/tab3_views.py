"""
Tab3 AI 对话 HTTP 视图。
"""
import json
import logging
import queue
import threading
import time
import uuid
from urllib.parse import urlencode

from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from ai_management.models import AIChatHistory, AIConversation, AIMessage, AIPendingAction, Tab3Session
from ai_management.services.mcp_tool_service import (
    confirm_pending_action,
    crm_cancel_action,
    crm_count_customers,
    crm_get_scope,
    crm_patch_pending_action,
    crm_prepare_followup,
    crm_request_high_risk_change,
    crm_search_customer,
    crm_search_users,
    get_pending_action_draft,
    get_tab3_capabilities,
)
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.viewset import CustomModelViewSet

logger = logging.getLogger(__name__)


_MCP_SESSION_TTL_SECONDS = 60 * 30
_MCP_SESSION_LOCK = threading.Lock()
_MCP_SESSIONS: dict[str, dict] = {}


class _EmptySerializer(serializers.Serializer):
    """占位序列化器，避免默认路由触发时抛出 serializer 缺失异常。"""


def _safe_limit(value, default=20, max_limit=200):
    try:
        parsed = int(value or default)
    except Exception:
        parsed = default
    if parsed <= 0:
        return default
    return min(parsed, max_limit)


def _build_conversation_row(conversation: AIConversation, session_id: str | None = None):
    return {
        "id": conversation.id,
        "title": conversation.title,
        "pinned": conversation.pinned,
        "last_message_time": conversation.last_message_time,
        "create_time": conversation.create_datetime,
        "update_time": conversation.update_datetime,
        "session_id": session_id,
    }


def _extract_text_content(message: AIMessage):
    content = message.content_json or {}
    if isinstance(content, dict):
        return str(content.get("text") or content.get("answer") or content.get("message") or "")
    if content is None:
        return ""
    return str(content)


def _mcp_cleanup_expired_sessions():
    now = time.time()
    remove_keys = []
    with _MCP_SESSION_LOCK:
        for key, item in _MCP_SESSIONS.items():
            last_seen = item.get("last_seen") or item.get("created_at") or now
            if now - last_seen > _MCP_SESSION_TTL_SECONDS:
                remove_keys.append(key)
        for key in remove_keys:
            _MCP_SESSIONS.pop(key, None)


def _mcp_create_session(user_id: int) -> str:
    _mcp_cleanup_expired_sessions()
    session_id = uuid.uuid4().hex
    with _MCP_SESSION_LOCK:
        _MCP_SESSIONS[session_id] = {
            "user_id": user_id,
            "queue": queue.Queue(maxsize=200),
            "created_at": time.time(),
            "last_seen": time.time(),
        }
    return session_id


def _mcp_get_session(session_id: str) -> dict | None:
    with _MCP_SESSION_LOCK:
        session = _MCP_SESSIONS.get(session_id)
        if session:
            session["last_seen"] = time.time()
        return session


def _mcp_remove_session(session_id: str):
    with _MCP_SESSION_LOCK:
        _MCP_SESSIONS.pop(session_id, None)


def _mcp_enqueue_message(session_id: str, payload: dict):
    session = _mcp_get_session(session_id)
    if not session:
        return
    q = session.get("queue")
    if not q:
        return
    try:
        q.put_nowait(payload)
    except queue.Full:
        try:
            q.get_nowait()
        except Exception:
            pass
        try:
            q.put_nowait(payload)
        except Exception:
            logger.warning("MCP queue is full and drop message: session_id=%s", session_id)


def _mcp_tool_definitions():
    return [
        {
            "name": "crm_get_scope",
            "description": "获取当前用户角色与数据范围",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
        {
            "name": "crm_search_customer",
            "description": "按权限范围搜索客户",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "客户关键词"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                },
                "required": ["query"],
                "additionalProperties": True,
            },
        },
        {
            "name": "crm_search_users",
            "description": "按权限范围搜索人员（用于内部参与人选择）",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "人员关键词"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                },
                "required": ["query"],
                "additionalProperties": True,
            },
        },
        {
            "name": "crm_count_customers",
            "description": "按语义维度统计客户数量，可返回澄清选项",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "intent_type": {"type": "string"},
                    "message": {"type": "string"},
                    "handler_name": {"type": "string"},
                    "keyword": {"type": "string"},
                    "org_unit": {"type": "string"},
                    "city": {"type": "string"},
                    "confirm_on_ambiguous": {"type": "boolean"},
                },
                "additionalProperties": True,
            },
        },
        {
            "name": "crm_prepare_followup",
            "description": "生成跟进记录草稿卡片（不落库）",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input_text": {"type": "string"},
                    "conversation_id": {"type": "integer"},
                    "fields": {"type": "object"},
                },
                "additionalProperties": True,
            },
        },
        {
            "name": "crm_patch_pending_action",
            "description": "对待确认卡片做自然语言编辑（不落库）",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation_id": {"type": "string"},
                    "conversation_id": {"type": "integer"},
                    "patch_text": {"type": "string"},
                    "edited_fields": {"type": "object"},
                    "idempotency_key": {"type": "string"},
                },
                "additionalProperties": True,
            },
        },
        {
            "name": "crm_commit_followup",
            "description": "确认并提交跟进记录（低风险写入）",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation_id": {"type": "string"},
                    "edited_fields": {"type": "object"},
                    "idempotency_key": {"type": "string"},
                },
                "required": ["operation_id"],
                "additionalProperties": True,
            },
        },
        {
            "name": "crm_cancel_action",
            "description": "取消待确认操作",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation_id": {"type": "string"},
                },
                "required": ["operation_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "crm_request_high_risk_change",
            "description": "提交高风险变更审批请求",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "conversation_id": {"type": "integer"},
                    "entity_type": {"type": "string"},
                    "entity_id": {"type": "integer"},
                    "payload": {"type": "object"},
                },
                "required": ["entity_type", "payload"],
                "additionalProperties": True,
            },
        },
    ]


def _dispatch_mcp_tool(user, tool: str, args: dict, conversation_id=None):
    if tool == "crm_get_scope":
        return crm_get_scope(user)
    if tool == "crm_search_customer":
        return crm_search_customer(
            user,
            query=args.get("query") or args.get("name") or args.get("keyword") or "",
            limit=args.get("limit", 10),
        )
    if tool == "crm_search_users":
        return crm_search_users(
            user,
            query=args.get("query") or args.get("name") or args.get("keyword") or "",
            limit=args.get("limit", 10),
        )
    if tool == "crm_count_customers":
        return crm_count_customers(
            user,
            intent_type=args.get("intent_type"),
            message=args.get("message") or args.get("query") or "",
            handler_name=args.get("handler_name"),
            keyword=args.get("keyword"),
            org_unit=args.get("org_unit"),
            city=args.get("city"),
            confirm_on_ambiguous=args.get("confirm_on_ambiguous", True),
        )
    if tool == "crm_prepare_followup":
        return crm_prepare_followup(
            user,
            conversation_id=conversation_id,
            input_text=args.get("input_text") or args.get("text") or "",
            fields=args.get("fields") or args,
        )
    if tool == "crm_patch_pending_action":
        return crm_patch_pending_action(
            user,
            operation_id=args.get("operation_id"),
            patch_text=args.get("patch_text") or args.get("text") or "",
            edited_fields=args.get("edited_fields") or args.get("fields") or {},
            conversation_id=conversation_id or args.get("conversation_id"),
            idempotency_key=args.get("idempotency_key"),
        )
    if tool == "crm_commit_followup":
        return confirm_pending_action(
            user_or_id=user,
            operation_id=args.get("operation_id"),
            edited_fields=args.get("edited_fields") or {},
            idempotency_key=args.get("idempotency_key"),
        )
    if tool == "crm_cancel_action":
        return crm_cancel_action(
            user_or_id=user,
            operation_id=args.get("operation_id"),
        )
    if tool == "crm_request_high_risk_change":
        return crm_request_high_risk_change(
            user,
            conversation_id=conversation_id,
            entity_type=args.get("entity_type"),
            entity_id=args.get("entity_id"),
            payload=args.get("payload") or {},
        )
    raise ValueError(f"不支持的工具：{tool}")


def _jsonrpc_ok(request_id, result):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def _jsonrpc_error(request_id, code: int, message: str, data=None):
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if data is not None:
        payload["error"]["data"] = data
    return payload


def _handle_mcp_rpc_message(user, payload: dict):
    if not isinstance(payload, dict):
        return _jsonrpc_error(None, -32600, "Invalid Request")

    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}
    is_notification = request_id is None

    if not method:
        if is_notification:
            return None
        return _jsonrpc_error(request_id, -32600, "Invalid Request: missing method")

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False},
            },
            "serverInfo": {
                "name": "wanfanglaw-crm-mcp",
                "version": "1.0.0",
            },
            "instructions": "Law CRM MCP tools with strict scope enforcement.",
        }
        return None if is_notification else _jsonrpc_ok(request_id, result)

    if method == "ping":
        return None if is_notification else _jsonrpc_ok(request_id, {})

    if method in ("tools/list", "tools.list"):
        result = {"tools": _mcp_tool_definitions()}
        return None if is_notification else _jsonrpc_ok(request_id, result)

    if method in ("tools/call", "tools.call"):
        if not isinstance(params, dict):
            return _jsonrpc_error(request_id, -32602, "Invalid params")
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        if not tool_name:
            return _jsonrpc_error(request_id, -32602, "Invalid params: missing tool name")
        if not isinstance(arguments, dict):
            return _jsonrpc_error(request_id, -32602, "Invalid params: arguments must be object")

        try:
            conversation_id = params.get("conversation_id") or arguments.get("conversation_id")
            tool_result = _dispatch_mcp_tool(
                user=user,
                tool=tool_name,
                args=arguments,
                conversation_id=conversation_id,
            )
            is_error = isinstance(tool_result, dict) and (
                bool(tool_result.get("error")) or tool_result.get("success") is False
            )
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(tool_result, ensure_ascii=False),
                    }
                ],
                "structuredContent": tool_result if isinstance(tool_result, dict) else {"value": tool_result},
                "isError": is_error,
            }
            return None if is_notification else _jsonrpc_ok(request_id, result)
        except ValueError as exc:
            return _jsonrpc_error(request_id, -32601, str(exc))
        except Exception as exc:
            logger.error("MCP tools.call failed: %s", exc, exc_info=True)
            return _jsonrpc_error(request_id, -32000, f"Tool call failed: {exc}")

    return _jsonrpc_error(request_id, -32601, f"Method not found: {method}")


class Tab3ChatViewSet(CustomModelViewSet):
    """
    Tab3 AI 对话 HTTP 接口（会话管理 + 历史 + 动作确认 + MCP调用）。
    """

    queryset = AIConversation.objects.none()
    serializer_class = _EmptySerializer
    permission_classes = [IsAuthenticated]
    swagger_schema = None

    @action(detail=False, methods=["post"], url_path="chat")
    def chat(self, request: Request):
        """
        非流式对话接口（保留占位）。
        """
        message = request.data.get("message", "").strip()
        if not message:
            return ErrorResponse(msg="消息不能为空", code=400)
        session_id = request.data.get("sessionId")
        return DetailResponse(
            data={
                "sessionId": session_id or "placeholder",
                "answer": "非流式接口暂未实现，请使用 WebSocket /api/ai/ws/tab3/",
                "usage": None,
            }
        )

    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request: Request):
        """
        获取指定 sessionId 的历史消息（最近 N 条，严格校验会话归属）。
        """
        user = request.user
        session_id = request.query_params.get("sessionId")
        limit = _safe_limit(request.query_params.get("limit"), default=20, max_limit=100)
        if not session_id:
            return ErrorResponse(msg="缺少 sessionId", code=400)

        session = (
            Tab3Session.objects.select_related("conversation")
            .filter(session_id=session_id, user_id=user.id)
            .first()
        )
        if not session:
            # 未命中本人会话，不透露是否存在
            return DetailResponse(data={"messages": []})

        # 新会话模型优先
        if session.conversation_id:
            msg_qs = (
                AIMessage.objects.filter(
                    conversation_id=session.conversation_id,
                    conversation__user_id=user.id,
                    is_deleted=False,
                    message_type="text",
                    role__in=["user", "assistant"],
                )
                .order_by("id")
            )
            rows = list(msg_qs[: limit * 2 + 20])
            pairs = []
            pending_user = None
            for row in rows:
                text = _extract_text_content(row).strip()
                if not text:
                    continue
                if row.role == "user":
                    pending_user = text
                    continue
                if row.role == "assistant":
                    if pending_user is not None:
                        pairs.append(
                            {
                                "message": pending_user,
                                "response": text,
                                "created_at": row.create_datetime,
                            }
                        )
                        pending_user = None
                    else:
                        pairs.append(
                            {
                                "message": "",
                                "response": text,
                                "created_at": row.create_datetime,
                            }
                        )
            if len(pairs) > limit:
                pairs = pairs[-limit:]
            return DetailResponse(data={"messages": pairs, "conversationId": session.conversation_id})

        # 旧模型兼容：仅限本人
        qs = (
            AIChatHistory.objects.filter(context_type="tab3", user_id=user.id)
            .order_by("-create_datetime")[:limit]
        )
        data = [
            {
                "message": item.message,
                "response": item.response,
                "created_at": item.create_datetime,
            }
            for item in qs
        ]
        return DetailResponse(data={"messages": list(reversed(data))})

    @action(detail=False, methods=["get", "post"], url_path="conversations")
    def conversations(self, request: Request):
        """
        会话列表 / 新建会话。
        """
        user = request.user
        if request.method.upper() == "GET":
            conversations = list(
                AIConversation.objects.filter(user_id=user.id, is_deleted=False).order_by(
                    "-pinned", "-last_message_time", "-create_datetime"
                )
            )
            rows = []
            for conv in conversations:
                session = (
                    Tab3Session.objects.filter(
                        conversation_id=conv.id, user_id=user.id, is_active=True
                    )
                    .order_by("-update_datetime")
                    .first()
                )
                rows.append(_build_conversation_row(conv, session_id=getattr(session, "session_id", None)))
            return DetailResponse(data={"rows": rows, "total": len(rows)})

        title = (request.data.get("title") or "").strip() or "新会话"
        conv = AIConversation.objects.create(
            user_id=user.id,
            title=title,
            pinned=bool(request.data.get("pinned", False)),
            last_message_time=timezone.now(),
            creator_id=user.id,
            modifier=user.name or str(user.id),
        )
        return DetailResponse(data=_build_conversation_row(conv))

    @action(detail=False, methods=["put", "delete"], url_path=r"conversations/(?P<conversation_id>[^/.]+)")
    def conversation_detail(self, request: Request, conversation_id: str = None):
        """
        会话重命名/置顶/删除。
        """
        user = request.user
        conversation = AIConversation.objects.filter(
            id=conversation_id, user_id=user.id, is_deleted=False
        ).first()
        if not conversation:
            return ErrorResponse(msg="会话不存在", code=404)

        if request.method.upper() == "DELETE":
            conversation.is_deleted = True
            conversation.modifier = user.name or str(user.id)
            conversation.save(update_fields=["is_deleted", "modifier", "update_datetime"])
            Tab3Session.objects.filter(conversation_id=conversation.id, user_id=user.id).update(is_active=False)
            AIPendingAction.objects.filter(
                conversation_id=conversation.id,
                user_id=user.id,
                status="pending",
                is_deleted=False,
            ).update(status="cancelled", modifier=user.name or str(user.id))
            return DetailResponse(data={"id": conversation.id, "deleted": True})

        payload = request.data or {}
        if "title" in payload:
            title = str(payload.get("title") or "").strip()
            if title:
                conversation.title = title[:200]
        if "pinned" in payload:
            conversation.pinned = bool(payload.get("pinned"))
        conversation.modifier = user.name or str(user.id)
        conversation.save(update_fields=["title", "pinned", "modifier", "update_datetime"])
        session = (
            Tab3Session.objects.filter(conversation_id=conversation.id, user_id=user.id, is_active=True)
            .order_by("-update_datetime")
            .first()
        )
        return DetailResponse(data=_build_conversation_row(conversation, session_id=getattr(session, "session_id", None)))

    @action(detail=False, methods=["post"], url_path=r"conversations/(?P<conversation_id>[^/.]+)/clear")
    def clear_conversation(self, request: Request, conversation_id: str = None):
        """
        清空会话消息并停用当前会话下的 session 映射。
        """
        user = request.user
        conversation = AIConversation.objects.filter(
            id=conversation_id, user_id=user.id, is_deleted=False
        ).first()
        if not conversation:
            return ErrorResponse(msg="会话不存在", code=404)
        AIMessage.objects.filter(conversation_id=conversation.id, is_deleted=False).update(is_deleted=True)
        Tab3Session.objects.filter(conversation_id=conversation.id, user_id=user.id).update(is_active=False)
        conversation.last_message_time = timezone.now()
        conversation.modifier = user.name or str(user.id)
        conversation.save(update_fields=["last_message_time", "modifier", "update_datetime"])
        return DetailResponse(data={"id": conversation.id, "cleared": True})

    @action(detail=False, methods=["get"], url_path=r"conversations/(?P<conversation_id>[^/.]+)/messages")
    def conversation_messages(self, request: Request, conversation_id: str = None):
        """
        获取会话消息列表。
        """
        user = request.user
        limit = _safe_limit(request.query_params.get("limit"), default=100, max_limit=500)
        conversation = AIConversation.objects.filter(
            id=conversation_id, user_id=user.id, is_deleted=False
        ).first()
        if not conversation:
            return ErrorResponse(msg="会话不存在", code=404)

        rows = (
            AIMessage.objects.filter(conversation_id=conversation.id, is_deleted=False)
            .order_by("-id")[:limit]
        )
        messages = []
        for item in reversed(list(rows)):
            messages.append(
                {
                    "id": item.id,
                    "role": item.role,
                    "message_type": item.message_type,
                    "content_json": item.content_json or {},
                    "tool_trace": item.tool_trace or [],
                    "create_time": item.create_datetime,
                }
            )
        return DetailResponse(data={"rows": messages, "total": len(messages)})

    @action(detail=False, methods=["get"], url_path="scope")
    def scope(self, request: Request):
        """
        返回当前用户的数据范围提示信息。
        """
        return DetailResponse(data=crm_get_scope(request.user))

    @action(detail=False, methods=["get"], url_path="capabilities")
    def capabilities(self, request: Request):
        """
        返回 Tab3 AI 当前可执行能力清单。
        """
        return DetailResponse(data=get_tab3_capabilities())

    @action(detail=False, methods=["get"], url_path="users/search")
    def search_users(self, request: Request):
        """
        在当前权限范围内搜索用户（卡片内部参与人员候选）。
        """
        keyword = (request.query_params.get("q") or request.query_params.get("query") or "").strip()
        limit = _safe_limit(request.query_params.get("limit"), default=10, max_limit=50)
        result = crm_search_users(request.user, query=keyword, limit=limit)
        if result.get("error"):
            return ErrorResponse(msg=result.get("error"), code=400)
        return DetailResponse(data=result)

    @action(detail=False, methods=["get"], url_path=r"actions/(?P<operation_id>[^/.]+)/draft")
    def action_draft(self, request: Request, operation_id: str = None):
        """
        获取待确认动作草稿（用于页面预填）。
        """
        result = get_pending_action_draft(request.user, operation_id)
        if not result.get("success"):
            return ErrorResponse(msg=result.get("error") or "草稿不存在", code=404)
        return DetailResponse(data=result)

    @action(detail=False, methods=["post"], url_path=r"actions/(?P<operation_id>[^/.]+)/confirm")
    def confirm_action(self, request: Request, operation_id: str = None):
        """
        确认执行待办动作。
        """
        edited_fields = request.data.get("edited_fields") or request.data.get("fields") or {}
        idempotency_key = request.data.get("idempotency_key") or request.headers.get("X-Idempotency-Key")
        result = confirm_pending_action(
            user_or_id=request.user,
            operation_id=operation_id,
            edited_fields=edited_fields,
            idempotency_key=idempotency_key,
        )
        if not result.get("success"):
            return ErrorResponse(msg=result.get("error") or "确认失败", code=400)
        return DetailResponse(data=result)

    @action(detail=False, methods=["post"], url_path=r"actions/(?P<operation_id>[^/.]+)/patch")
    def patch_action(self, request: Request, operation_id: str = None):
        """
        编辑待确认动作草稿。
        """
        result = crm_patch_pending_action(
            user_or_id=request.user,
            operation_id=operation_id,
            patch_text=request.data.get("patch_text") or request.data.get("text") or "",
            edited_fields=request.data.get("edited_fields") or request.data.get("fields") or {},
            conversation_id=request.data.get("conversation_id"),
            idempotency_key=request.data.get("idempotency_key"),
        )
        if not result.get("success"):
            return ErrorResponse(msg=result.get("error") or "编辑失败", code=400)
        return DetailResponse(data=result)

    @action(detail=False, methods=["post"], url_path=r"actions/(?P<operation_id>[^/.]+)/cancel")
    def cancel_action(self, request: Request, operation_id: str = None):
        """
        取消待办动作。
        """
        result = crm_cancel_action(user_or_id=request.user, operation_id=operation_id)
        if not result.get("success"):
            return ErrorResponse(msg=result.get("error") or "取消失败", code=400)
        return DetailResponse(data=result)

    @action(detail=False, methods=["post"], url_path="mcp/call")
    def mcp_call(self, request: Request):
        """
        MCP 白名单工具调用入口（HTTP）。
        """
        tool = (request.data.get("tool") or "").strip()
        args = request.data.get("args") or {}
        conversation_id = request.data.get("conversation_id")

        if not tool:
            return ErrorResponse(msg="缺少 tool 参数", code=400)
        if not isinstance(args, dict):
            return ErrorResponse(msg="args 必须是对象", code=400)

        try:
            result = _dispatch_mcp_tool(
                user=request.user,
                tool=tool,
                args=args,
                conversation_id=conversation_id,
            )
            response_payload = {
                "tool": tool,
                "result": result,
                "is_error": isinstance(result, dict) and (
                    bool(result.get("error")) or result.get("success") is False
                ),
            }
        except Exception as exc:
            logger.error("MCP call failed: tool=%s error=%s", tool, exc, exc_info=True)
            return ErrorResponse(msg=f"工具调用失败: {exc}", code=400)

        return DetailResponse(data=response_payload)

    @action(detail=False, methods=["get"], url_path="mcp/sse")
    def mcp_sse(self, request: Request):
        """
        标准 MCP SSE 握手流。

        连接成功后会先返回 `endpoint` 事件，客户端向该 endpoint 发送 JSON-RPC 消息。
        """
        user = request.user
        session_id = _mcp_create_session(int(user.id))
        endpoint = request.build_absolute_uri("/api/ai/tab3/mcp/messages/")
        endpoint_with_session = f"{endpoint}?{urlencode({'session_id': session_id})}"

        def stream():
            try:
                yield f"event: endpoint\ndata: {endpoint_with_session}\n\n"
                while True:
                    session = _mcp_get_session(session_id)
                    if not session:
                        break
                    q = session.get("queue")
                    try:
                        message = q.get(timeout=15)
                        payload = json.dumps(message, ensure_ascii=False)
                        yield f"event: message\ndata: {payload}\n\n"
                    except queue.Empty:
                        # SSE 注释行心跳，避免代理超时
                        yield f": heartbeat {int(time.time())}\n\n"
            finally:
                _mcp_remove_session(session_id)

        response = StreamingHttpResponse(stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["Connection"] = "keep-alive"
        response["X-Accel-Buffering"] = "no"
        return response

    @action(detail=False, methods=["post"], url_path="mcp/messages")
    def mcp_messages(self, request: Request):
        """
        标准 MCP SSE 的 message endpoint。
        接收 JSON-RPC 请求并把响应推送到对应 SSE 会话。
        """
        user = request.user
        session_id = request.query_params.get("session_id") or request.data.get("session_id")
        if not session_id:
            return ErrorResponse(msg="缺少 session_id", code=400)

        session = _mcp_get_session(session_id)
        if not session:
            return ErrorResponse(msg="MCP 会话不存在或已过期", code=404)
        if int(session.get("user_id") or 0) != int(user.id):
            return ErrorResponse(msg="无权访问该 MCP 会话", code=403)

        payload = request.data
        accepted = 0
        emitted = 0

        def _handle_one(item):
            nonlocal accepted, emitted
            accepted += 1
            response_payload = _handle_mcp_rpc_message(user, item)
            if response_payload is not None:
                _mcp_enqueue_message(session_id, response_payload)
                emitted += 1

        try:
            if isinstance(payload, list):
                for item in payload:
                    _handle_one(item)
            else:
                _handle_one(payload)
        except Exception as exc:
            logger.error("MCP message handling failed: %s", exc, exc_info=True)
            return ErrorResponse(msg=f"MCP message handling failed: {exc}", code=400)

        return DetailResponse(
            data={
                "session_id": session_id,
                "accepted": accepted,
                "emitted": emitted,
            }
        )
