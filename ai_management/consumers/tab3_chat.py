"""
Tab3 AI 对话 WebSocket Consumer

职责：
1) WebSocket 对话入口（Tab3）
2) session/thread/conversation 归属强校验
3) MCP 白名单工具桥接（客户端工具调用）
4) 结构化消息推送（card/action_result/scope_hint）
"""
import asyncio
import json
import logging
import re
import uuid
from typing import Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from ai_management.models import AIChatHistory, AIConversation, AIMessage, Tab3Session
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
    get_latest_pending_action,
    get_tab3_capabilities,
)
from conf import env

logger = logging.getLogger(__name__)


def _looks_like_customer_count_question(text: str) -> bool:
    value = (text or "").strip()
    if not value:
        return False
    return ("客户" in value) and any(k in value for k in ("多少", "几家", "数量", "总数", "几位"))


def _extract_customer_keyword_from_message(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    value = re.sub(r"[？?！!。,.，]", "", value)
    patterns = [
        r"(?:查一下|查询|查|搜)\s*([^\s，。,；;：:]{1,20}?)\s*(?:有多少|多少|客户)",
        r"([^\s，。,；;：:]{1,20}?)(?:有多少|多少)(?:家|个|位)?客户",
        r"([^\s，。,；;：:]{1,20}?)(?:的)?客户(?:有多少|多少|数量|总数)",
        r"([^\s，。,；;：:]{1,20}?)(?:有多少|多少)(?:客户)?在跟进",
    ]
    for pattern in patterns:
        m = re.search(pattern, value)
        if m:
            keyword = (m.group(1) or "").strip()
            keyword = re.sub(r"(在跟进|跟进|客户)$", "", keyword).strip()
            keyword = re.sub(r"(啊|呀|呢|吗)$", "", keyword).strip()
            if keyword and keyword not in ("我", "当前", "本人", "自己"):
                return keyword
    return ""


def _build_fallback_answer_for_tool_interrupt(user_id: int, message: str, tool_results: list[dict]) -> str:
    """
    仅在工具链路异常时返回最小兜底文案，避免错误语义回答覆盖模型推理。
    """
    scope = crm_get_scope(user_id)
    scope_text = str(scope.get("scope_text") or "当前范围未知").strip()
    if _looks_like_customer_count_question(message):
        return f"{scope_text}。工具链路中断，请重试本次统计请求。"
    return f"{scope_text}。工具链路中断，请重试当前请求。"


def _extract_tool_call_id(tool_call: dict) -> Optional[str]:
    """兼容不同 SDK 事件格式中的 tool_call_id 字段。"""
    if not isinstance(tool_call, dict):
        return None
    candidates = (
        tool_call.get("id"),
        tool_call.get("toolCallId"),
        tool_call.get("tool_call_id"),
        tool_call.get("call_id"),
    )
    for value in candidates:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    nested = tool_call.get("toolCall") or tool_call.get("call") or {}
    if isinstance(nested, dict):
        return _extract_tool_call_id(nested)
    return None


def _extract_run_id(event_data: dict) -> Optional[str]:
    """从流式事件中提取 execution/run id。"""
    if not isinstance(event_data, dict):
        return None
    candidates = [
        event_data.get("executionId"),
        event_data.get("run_id"),
        event_data.get("runId"),
    ]
    data = event_data.get("data")
    if isinstance(data, dict):
        candidates.extend(
            [
                data.get("executionId"),
                data.get("run_id"),
                data.get("runId"),
            ]
        )
    for value in candidates:
        if not value:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _looks_like_tool_interrupt(event_data: dict) -> bool:
    """粗略判断事件是否在要求客户端处理工具（但可能未被正确解析）。"""
    if not isinstance(event_data, dict):
        return False
    haystacks = [
        str(event_data.get("type") or ""),
        str(event_data.get("event") or ""),
    ]
    data = event_data.get("data")
    if isinstance(data, dict):
        haystacks.extend(
            [
                str(data.get("type") or ""),
                str(data.get("event") or ""),
                str(data.get("status") or ""),
            ]
        )
    text = " ".join(h.lower() for h in haystacks if h).strip()
    if not text:
        return False
    keywords = ("interrupt", "tool", "action_required", "client_tool")
    return any(k in text for k in keywords)


def _is_stream_interrupted_status(event_data: dict) -> bool:
    if not isinstance(event_data, dict):
        return False
    data = event_data.get("data")
    if isinstance(data, dict):
        status = str(data.get("status") or "").strip().lower()
        if status == "interrupted":
            return True
    status = str(event_data.get("status") or "").strip().lower()
    return status == "interrupted"


def _try_get_langgraph_client(api_url: str, api_key: str | None):
    """尝试创建 LangGraph SDK 客户端。"""
    try:
        from langgraph_sdk import get_client
    except Exception as exc:
        logger.error("Failed to import langgraph_sdk: %s", exc, exc_info=True)
        return None

    try:
        try:
            return get_client(url=api_url, api_key=api_key)
        except TypeError:
            # 兼容旧版本 SDK
            return get_client(url=api_url)
    except Exception as exc:
        logger.error("Failed to create XpertAI client: %s", exc, exc_info=True)
        return None


def _coerce_tool_call_item(item) -> Optional[dict]:
    """兼容不同结构的 tool call item，归一为 {name,args,id,...}。"""
    if not isinstance(item, dict):
        return None
    function = item.get("function") if isinstance(item.get("function"), dict) else {}
    name = item.get("name") or item.get("tool") or function.get("name")
    args = item.get("args")
    if args is None:
        args = item.get("arguments")
    if args is None:
        args = function.get("arguments")

    if isinstance(args, str):
        text = args.strip()
        if text:
            try:
                parsed = json.loads(text)
                args = parsed
            except Exception:
                args = {"raw_args": text}
        else:
            args = {}
    elif not isinstance(args, dict):
        args = {} if args is None else {"raw_args": args}

    normalized = dict(item)
    if name:
        normalized["name"] = name
    normalized["args"] = args
    return normalized


def _coerce_tool_calls(value) -> list[dict]:
    """把各种可能的 tool calls 载体统一解析为 list[dict]。"""
    if not value:
        return []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        parsed = _coerce_tool_call_item(item)
        if parsed:
            rows.append(parsed)
    return rows


def _find_client_tool_request(obj) -> dict | None:
    """
    尝试检测 ClientToolRequest payload。
    兼容字段：
    - clientToolCalls / client_tool_calls
    - toolCalls / tool_calls
    - actionRequired.tool_calls
    """
    if isinstance(obj, str):
        text = obj.strip()
        if text:
            try:
                obj = json.loads(text)
            except Exception:
                return None
        else:
            return None

    if isinstance(obj, list):
        for item in obj:
            found = _find_client_tool_request(item)
            if found:
                return found
        return None

    if not isinstance(obj, dict):
        return None

    for key in ("clientToolCalls", "client_tool_calls", "toolCalls", "tool_calls"):
        calls = _coerce_tool_calls(obj.get(key))
        if calls:
            return {"clientToolCalls": calls}

    action_required = obj.get("actionRequired")
    if isinstance(action_required, dict):
        calls = _coerce_tool_calls(action_required.get("tool_calls"))
        if calls:
            return {"clientToolCalls": calls}

    for key in (
        "data",
        "event",
        "payload",
        "value",
        "values",
        "interrupt",
        "interrupted",
        "output",
        "result",
    ):
        value = obj.get(key)
        found = _find_client_tool_request(value)
        if found:
            return found

    for value in obj.values():
        found = _find_client_tool_request(value)
        if found:
            return found
    return None


def _execute_client_tool(
    tool_call: dict,
    *,
    user_id: Optional[int],
    conversation_id: Optional[int],
) -> dict:
    """
    执行客户端工具调用（MCP 白名单）。
    """
    name = tool_call.get("name") or tool_call.get("tool")
    args = tool_call.get("args")
    if args is None:
        args = tool_call.get("arguments") or {}
    if not isinstance(args, dict):
        args = {"raw_args": args}
    tool_call_id = _extract_tool_call_id(tool_call)

    events = []
    result = None

    if not tool_call_id:
        # 不可 resume：缺少 tool_call_id 会导致 INVALID_TOOL_RESULTS。
        result = {
            "error": "Missing tool_call_id in client tool call payload",
            "tool": name,
            "args": args,
            "raw_tool_call": tool_call,
        }
        return {"tool_message": None, "events": events, "result": result, "missing_tool_call_id": True}

    try:
        if name == "crm_get_scope":
            result = crm_get_scope(user_id)
        elif name in ("crm_search_customer", "query_customer"):
            result = crm_search_customer(
                user_id,
                query=args.get("query") or args.get("name") or args.get("keyword") or "",
                limit=args.get("limit", 10),
            )
        elif name == "crm_search_users":
            result = crm_search_users(
                user_id,
                query=args.get("query") or args.get("name") or args.get("keyword") or "",
                limit=args.get("limit", 10),
            )
        elif name == "crm_count_customers":
            result = crm_count_customers(
                user_id,
                intent_type=args.get("intent_type"),
                message=args.get("message") or args.get("query") or "",
                handler_name=args.get("handler_name"),
                keyword=args.get("keyword"),
                org_unit=args.get("org_unit"),
                city=args.get("city"),
                confirm_on_ambiguous=args.get("confirm_on_ambiguous", True),
            )
            if isinstance(result, dict) and result.get("need_clarify"):
                events.append(
                    {
                        "type": "need_clarify",
                        "payload": result,
                    }
                )
        elif name == "crm_prepare_followup":
            result = crm_prepare_followup(
                user_or_id=user_id,
                conversation_id=conversation_id,
                input_text=args.get("input_text") or args.get("text") or "",
                fields=args.get("fields") or args,
            )
            card = (result or {}).get("card")
            if card:
                events.append({"type": "card", "card": card})
        elif name == "crm_patch_pending_action":
            result = crm_patch_pending_action(
                user_or_id=user_id,
                operation_id=args.get("operation_id"),
                patch_text=args.get("patch_text") or args.get("text") or "",
                edited_fields=args.get("edited_fields") or args.get("fields") or {},
                conversation_id=conversation_id or args.get("conversation_id"),
                idempotency_key=args.get("idempotency_key") or uuid.uuid4().hex,
            )
            card = (result or {}).get("card")
            if card:
                events.append({"type": "card_updated", "card": card, "operationId": result.get("operation_id")})
        elif name in ("crm_commit_followup", "confirm_pending_action"):
            result = confirm_pending_action(
                user_or_id=user_id,
                operation_id=args.get("operation_id"),
                edited_fields=args.get("edited_fields") or {},
                idempotency_key=args.get("idempotency_key") or uuid.uuid4().hex,
            )
            events.append({"type": "action_result", "result": result})
        elif name == "crm_cancel_action":
            result = crm_cancel_action(
                user_or_id=user_id,
                operation_id=args.get("operation_id"),
            )
            events.append({"type": "action_result", "result": result})
        elif name == "crm_request_high_risk_change":
            result = crm_request_high_risk_change(
                user_or_id=user_id,
                conversation_id=conversation_id,
                entity_type=args.get("entity_type"),
                entity_id=args.get("entity_id"),
                payload=args.get("payload") or {},
            )
            events.append({"type": "action_result", "result": result})
        else:
            result = {
                "error": f"Unknown client tool: {name}",
                "available_tools": [
                    "crm_get_scope",
                    "crm_search_customer",
                    "crm_search_users",
                    "crm_count_customers",
                    "crm_prepare_followup",
                    "crm_patch_pending_action",
                    "crm_commit_followup",
                    "crm_cancel_action",
                    "crm_request_high_risk_change",
                ],
                "args": args,
            }
    except Exception as exc:
        logger.error("Tool execution failed: name=%s err=%s", name, exc, exc_info=True)
        result = {
            "error": f"Tool execution failed: {exc}",
            "tool": name,
            "args": args,
        }

    tool_message = {
        "tool_call_id": tool_call_id,
        "name": name,
        "content": result if isinstance(result, str) else json.dumps(result, ensure_ascii=False),
    }
    return {"tool_message": tool_message, "events": events, "result": result, "missing_tool_call_id": False}


class Tab3ChatConsumer(AsyncJsonWebsocketConsumer):
    """Tab3 AI 对话 WebSocket Consumer。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id: Optional[str] = None
        self.thread_id: Optional[str] = None
        self.run_id: Optional[str] = None
        self.user_id: Optional[int] = None
        self.conversation_id: Optional[int] = None
        self.client = None

    def _extract_token(self) -> Optional[str]:
        """从 headers 或 querystring 提取 Bearer token。"""
        headers = dict(self.scope.get("headers") or [])
        auth = headers.get(b"authorization") or headers.get(b"Authorization")
        if auth:
            try:
                text = auth.decode()
                if text.lower().startswith("bearer "):
                    return text.split(" ", 1)[1].strip()
            except Exception:
                pass

        proto = headers.get(b"sec-websocket-protocol")
        if proto:
            try:
                return proto.decode().strip()
            except Exception:
                pass

        qs = self.scope.get("query_string", b"").decode()
        if qs:
            for part in qs.split("&"):
                if part.startswith("token="):
                    return part.split("=", 1)[1]
        return None

    async def _authenticate(self) -> bool:
        token = self._extract_token()
        if not token:
            await self.send_json({"type": "error", "code": "unauthorized", "message": "Missing token"})
            await self.close()
            return False

        jwt_auth = JWTAuthentication()
        try:
            validated = jwt_auth.get_validated_token(token)
            user = await asyncio.to_thread(jwt_auth.get_user, validated)
            self.user_id = getattr(user, "id", None)
            return bool(self.user_id)
        except InvalidToken:
            await self.send_json({"type": "error", "code": "invalid_token", "message": "Token is invalid"})
            await self.close()
            return False
        except Exception as exc:
            logger.error("Token auth failed: %s", exc, exc_info=True)
            await self.send_json({"type": "error", "code": "auth_error", "message": "Authentication failed"})
            await self.close()
            return False

    @staticmethod
    def _conversation_title_from_message(text: str) -> str:
        base = (text or "").strip()
        if not base:
            return "新会话"
        if len(base) <= 24:
            return base
        return f"{base[:24]}..."

    def _db_get_session(self, session_id: str):
        return Tab3Session.objects.select_related("conversation").filter(session_id=session_id).first()

    def _db_get_latest_session_by_conversation(self, conversation_id: int, user_id: int):
        return (
            Tab3Session.objects.filter(
                conversation_id=conversation_id,
                user_id=user_id,
                is_active=True,
            )
            .order_by("-update_datetime")
            .first()
        )

    def _db_get_conversation(self, conversation_id: int, user_id: int):
        return AIConversation.objects.filter(id=conversation_id, user_id=user_id, is_deleted=False).first()

    def _db_create_conversation(self, user_id: int, title: str):
        now = timezone.now()
        return AIConversation.objects.create(
            user_id=user_id,
            title=title or "新会话",
            last_message_time=now,
            creator_id=user_id,
            modifier=str(user_id),
        )

    def _db_touch_conversation(self, conversation_id: int):
        AIConversation.objects.filter(id=conversation_id, is_deleted=False).update(last_message_time=timezone.now())

    def _db_create_session(
        self,
        session_id: str,
        thread_id: str,
        user_id: int,
        conversation_id: Optional[int] = None,
    ):
        return Tab3Session.objects.create(
            session_id=session_id,
            thread_id=thread_id,
            user_id=user_id,
            conversation_id=conversation_id,
            is_active=True,
            creator_id=user_id,
            modifier=str(user_id),
        )

    def _db_update_session(self, session_obj: Tab3Session, **fields):
        for key, value in fields.items():
            setattr(session_obj, key, value)
        session_obj.save(update_fields=list(fields.keys()) + ["update_datetime"])
        return session_obj

    def _db_save_user_message(self, conversation_id: int, user_id: int, text: str, attachments: list):
        AIMessage.objects.create(
            conversation_id=conversation_id,
            role="user",
            message_type="text",
            content_json={"text": text, "attachments": attachments or []},
            creator_id=user_id,
            modifier=str(user_id),
        )
        self._db_touch_conversation(conversation_id)

    def _db_save_ai_message(self, conversation_id: int, user_id: int, text: str):
        AIMessage.objects.create(
            conversation_id=conversation_id,
            role="assistant",
            message_type="text",
            content_json={"text": text},
            creator_id=user_id,
            modifier=str(user_id),
        )
        self._db_touch_conversation(conversation_id)

    def _db_save_legacy_history(self, user_id: int, message: str, answer: str):
        AIChatHistory.objects.create(
            user_id=user_id,
            message=message,
            response=answer,
            context_type="tab3",
            context_id=None,
            model_name="xpert",
        )

    def _db_save_scope_hint_message(self, conversation_id: int, user_id: int, scope_payload: dict):
        AIMessage.objects.create(
            conversation_id=conversation_id,
            role="assistant",
            message_type="scope_hint",
            content_json=scope_payload,
            creator_id=user_id,
            modifier=str(user_id),
        )
        self._db_touch_conversation(conversation_id)

    async def _reset_current_thread(self, reason: str):
        """
        发生工具回传异常时，丢弃当前 thread/run 绑定，避免脏会话持续报错。
        """
        logger.warning(
            "Reset tab3 thread context: user_id=%s session_id=%s thread_id=%s run_id=%s reason=%s",
            self.user_id,
            self.session_id,
            self.thread_id,
            self.run_id,
            reason,
        )
        old_thread = self.thread_id
        self.thread_id = None
        self.run_id = None

        if self.session_id:
            session = await asyncio.to_thread(self._db_get_session, self.session_id)
            if session and session.user_id == self.user_id:
                await asyncio.to_thread(
                    self._db_update_session,
                    session,
                    thread_id="",
                    last_run_id="",
                    is_active=False,
                )
        await self.send_json(
            {
                "type": "error",
                "code": "tool_context_reset",
                "message": "工具执行上下文已重置，请重试当前请求。",
                "sessionId": self.session_id,
                "conversationId": self.conversation_id,
                "threadId": old_thread,
            }
        )

    async def connect(self):
        ok = await self._authenticate()
        if not ok:
            return
        await self.accept()
        scope_payload = await asyncio.to_thread(crm_get_scope, self.user_id)
        capabilities_payload = await asyncio.to_thread(get_tab3_capabilities)
        await self.send_json(
            {
                "type": "scope_hint",
                "scope": scope_payload,
            }
        )
        await self.send_json(
            {
                "type": "capabilities",
                "capabilities": capabilities_payload,
            }
        )
        logger.info("Tab3 WS connected: user_id=%s", self.user_id)

    async def disconnect(self, close_code):
        if self.session_id:
            session = await asyncio.to_thread(self._db_get_session, self.session_id)
            if session and session.user_id == self.user_id:
                try:
                    await asyncio.to_thread(self._db_update_session, session, is_active=False)
                except Exception:
                    logger.warning("Failed to update session status on disconnect", exc_info=True)
        logger.info("Tab3 WS disconnected: user_id=%s session=%s code=%s", self.user_id, self.session_id, close_code)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get("type")
        if msg_type == "user_message":
            await self.handle_user_message(content)
            return
        if msg_type == "switch_conversation":
            await self.handle_switch_conversation(content)
            return
        if msg_type == "confirm_action":
            await self.handle_confirm_action(content)
            return
        if msg_type == "cancel_action":
            await self.handle_cancel_action(content)
            return
        if msg_type == "edit_pending_action":
            await self.handle_edit_pending_action(content)
            return
        await self.send_json(
            {
                "type": "error",
                "code": "unknown_message_type",
                "message": f"Unknown message type: {msg_type}",
            }
        )

    async def handle_switch_conversation(self, content: dict):
        conversation_id = content.get("conversationId")
        if not conversation_id:
            await self.send_json({"type": "error", "code": "missing_conversation", "message": "缺少 conversationId"})
            return
        conversation = await asyncio.to_thread(self._db_get_conversation, int(conversation_id), int(self.user_id))
        if not conversation:
            await self.send_json({"type": "error", "code": "conversation_not_found", "message": "会话不存在或无权访问"})
            return

        latest_session = await asyncio.to_thread(
            self._db_get_latest_session_by_conversation,
            conversation.id,
            int(self.user_id),
        )
        self.conversation_id = conversation.id
        self.session_id = latest_session.session_id if latest_session else None
        self.thread_id = latest_session.thread_id if latest_session else None
        scope_payload = await asyncio.to_thread(crm_get_scope, self.user_id)
        await self.send_json(
            {
                "type": "conversation_meta",
                "conversationId": conversation.id,
                "title": conversation.title,
                "sessionId": self.session_id,
            }
        )
        await self.send_json(
            {
                "type": "scope_hint",
                "scope": scope_payload,
                "conversationId": conversation.id,
                "sessionId": self.session_id,
            }
        )

    async def handle_confirm_action(self, content: dict):
        operation_id = content.get("operationId")
        if not operation_id:
            await self.send_json({"type": "error", "code": "missing_operation_id", "message": "缺少 operationId"})
            return
        result = await asyncio.to_thread(
            confirm_pending_action,
            self.user_id,
            operation_id,
            content.get("editedFields") or {},
            content.get("idempotencyKey") or uuid.uuid4().hex,
        )
        if not result.get("success"):
            await self.send_json(
                {
                    "type": "error",
                    "code": "confirm_failed",
                    "message": result.get("error") or "确认失败",
                    "operationId": operation_id,
                }
            )
            return
        await self.send_json(
            {
                "type": "action_result",
                "operationId": operation_id,
                "result": result,
            }
        )

    async def handle_cancel_action(self, content: dict):
        operation_id = content.get("operationId")
        if not operation_id:
            await self.send_json({"type": "error", "code": "missing_operation_id", "message": "缺少 operationId"})
            return
        result = await asyncio.to_thread(crm_cancel_action, self.user_id, operation_id)
        if not result.get("success"):
            await self.send_json(
                {
                    "type": "error",
                    "code": "cancel_failed",
                    "message": result.get("error") or "取消失败",
                    "operationId": operation_id,
                }
            )
            return
        await self.send_json(
            {
                "type": "action_result",
                "operationId": operation_id,
                "result": result,
            }
        )

    async def handle_edit_pending_action(self, content: dict):
        operation_id = (content.get("operationId") or "").strip()
        patch_text = (content.get("patchText") or content.get("message") or "").strip()
        conversation_id = content.get("conversationId") or self.conversation_id
        if not operation_id and not conversation_id:
            await self.send_json({"type": "error", "code": "missing_operation_id", "message": "缺少 operationId"})
            return
        result = await asyncio.to_thread(
            crm_patch_pending_action,
            self.user_id,
            operation_id or None,
            patch_text,
            content.get("editedFields") or {},
            conversation_id,
            content.get("idempotencyKey") or uuid.uuid4().hex,
        )
        if not result.get("success"):
            await self.send_json(
                {
                    "type": "error",
                    "code": "edit_pending_failed",
                    "message": result.get("error") or "编辑失败",
                    "operationId": operation_id,
                }
            )
            return
        await self.send_json(
            {
                "type": "card_updated",
                "operationId": result.get("operation_id"),
                "conversationId": conversation_id,
                "card": result.get("card"),
            }
        )
        await self.send_json(
            {
                "type": "final",
                "sessionId": self.session_id,
                "conversationId": conversation_id,
                "answer": "已更新待确认卡片，您可以继续补充字段或直接确认。",
            }
        )

    @staticmethod
    def _is_followup_intent(text: str) -> bool:
        normalized = (text or "").strip()
        if not normalized:
            return False
        keywords = [
            "跟进记录",
            "记个跟进",
            "记一下跟进",
            "添加跟进",
            "新增跟进",
            "记录一下跟进",
            "拜访记录",
            "记个拜访",
        ]
        return any(key in normalized for key in keywords)

    @staticmethod
    def _is_exit_edit_intent(text: str) -> bool:
        normalized = (text or "").strip()
        if not normalized:
            return False
        exits = ["退出编辑", "取消编辑", "新查询", "结束编辑", "不改了", "不用改了"]
        return any(item in normalized for item in exits)

    @staticmethod
    def _is_customer_count_intent(text: str) -> bool:
        normalized = (text or "").strip()
        if not normalized:
            return False
        return ("客户" in normalized) and any(k in normalized for k in ("多少", "几家", "数量", "总数", "统计"))

    @staticmethod
    def _format_count_result_message(result: dict) -> str:
        if not isinstance(result, dict):
            return "统计完成。"
        if result.get("need_clarify"):
            options = result.get("clarify_options") or []
            if options:
                lines = [result.get("clarify_question") or "请先确认统计口径："]
                for idx, option in enumerate(options, start=1):
                    lines.append(f"{idx}) {option.get('label')}")
                return "\n".join(lines)
            return result.get("clarify_question") or "请先补充统计口径。"
        count = result.get("count")
        dimension = str(result.get("dimension") or "")
        evidence = result.get("evidence") or {}
        if dimension == "handler":
            handler_name = evidence.get("handler_name") or "指定经办人"
            return f"已按经办人口径统计，{handler_name}在当前权限范围内关联客户 {count} 家。"
        if dimension == "name_keyword":
            keyword = evidence.get("keyword") or "关键词"
            return f"已按客户名称匹配口径统计，名称包含“{keyword}”的客户共有 {count} 家。"
        if dimension == "city":
            city = evidence.get("city") or "该城市"
            return f"已按地址口径统计，地址包含“{city}”的客户共有 {count} 家。"
        return f"已按当前权限范围统计，客户总数为 {count} 家。"

    async def _resolve_session_and_conversation(self, content: dict, message: str):
        requested_session_id = content.get("sessionId")
        requested_conversation_id = content.get("conversationId")

        session = None
        conversation = None

        # 1) 如果传入 sessionId，先校验归属
        if requested_session_id:
            session = await asyncio.to_thread(self._db_get_session, requested_session_id)
            if session and session.user_id and int(session.user_id) != int(self.user_id):
                await self.send_json(
                    {
                        "type": "error",
                        "code": "session_forbidden",
                        "message": "会话不属于当前用户",
                    }
                )
                return None, None, None
            if session and session.user_id in (None, 0):
                session = await asyncio.to_thread(
                    self._db_update_session,
                    session,
                    user_id=self.user_id,
                )
            if session and session.conversation_id and not requested_conversation_id:
                requested_conversation_id = session.conversation_id

        # 2) 如果传入 conversationId，校验归属
        if requested_conversation_id:
            try:
                conversation = await asyncio.to_thread(
                    self._db_get_conversation,
                    int(requested_conversation_id),
                    int(self.user_id),
                )
            except Exception:
                conversation = None
            if not conversation:
                await self.send_json(
                    {
                        "type": "error",
                        "code": "conversation_forbidden",
                        "message": "会话不存在或无权访问",
                    }
                )
                return None, None, None

        if session and conversation and session.conversation_id and int(session.conversation_id) != int(conversation.id):
            await self.send_json(
                {
                    "type": "error",
                    "code": "session_conversation_mismatch",
                    "message": "sessionId 与 conversationId 不匹配",
                }
            )
            return None, None, None

        # 3) 若都没有，则新建 conversation
        if not conversation:
            conversation = await asyncio.to_thread(
                self._db_create_conversation,
                int(self.user_id),
                self._conversation_title_from_message(message),
            )
            await self.send_json(
                {
                    "type": "conversation_created",
                    "conversation": {
                        "id": conversation.id,
                        "title": conversation.title,
                        "pinned": conversation.pinned,
                        "last_message_time": conversation.last_message_time.isoformat() if conversation.last_message_time else None,
                    },
                }
            )
            scope_payload = await asyncio.to_thread(crm_get_scope, self.user_id)
            await asyncio.to_thread(self._db_save_scope_hint_message, conversation.id, int(self.user_id), scope_payload)
            await self.send_json(
                {
                    "type": "scope_hint",
                    "scope": scope_payload,
                    "conversationId": conversation.id,
                    "sessionId": None,
                }
            )

        # 4) 若没有 session 但已有 conversation，尝试找到该会话最近活跃 session
        if not session:
            session = await asyncio.to_thread(
                self._db_get_latest_session_by_conversation,
                conversation.id,
                int(self.user_id),
            )

        # 5) 若 session 存在但未绑 conversation，则回填
        if session and not session.conversation_id:
            session = await asyncio.to_thread(
                self._db_update_session,
                session,
                conversation_id=conversation.id,
            )

        self.conversation_id = conversation.id
        self.session_id = session.session_id if session else None
        self.thread_id = session.thread_id if session else None
        return session, conversation, (self.session_id or str(uuid.uuid4()))

    async def handle_user_message(self, content: dict):
        message = (content.get("message") or "").strip()
        if not message:
            await self.send_json({"type": "error", "code": "empty_message", "message": "Message cannot be empty"})
            return
        attachments = content.get("attachments") or []
        if not isinstance(attachments, list):
            attachments = []

        session, conversation, decided_session_id = await self._resolve_session_and_conversation(content, message)
        if not conversation:
            return

        # 记录用户消息
        await asyncio.to_thread(
            self._db_save_user_message,
            conversation.id,
            int(self.user_id),
            message,
            attachments,
        )

        # 默认编辑模式：会话内存在待确认卡片时，优先把用户输入解释为卡片编辑
        editing_operation_id = (content.get("editingOperationId") or "").strip()
        if not self._is_exit_edit_intent(message):
            latest_pending = await asyncio.to_thread(
                get_latest_pending_action,
                self.user_id,
                conversation.id,
            )
            operation_id_for_edit = editing_operation_id or latest_pending.get("operation_id")
            if operation_id_for_edit:
                patched = await asyncio.to_thread(
                    crm_patch_pending_action,
                    self.user_id,
                    operation_id_for_edit,
                    message,
                    {},
                    conversation.id,
                    uuid.uuid4().hex,
                )
                if patched.get("success"):
                    card = patched.get("card")
                    if card:
                        await self.send_json(
                            {
                                "type": "card_updated",
                                "sessionId": self.session_id,
                                "conversationId": conversation.id,
                                "operationId": patched.get("operation_id"),
                                "card": card,
                            }
                        )
                    await self.send_json(
                        {
                            "type": "final",
                            "sessionId": self.session_id,
                            "conversationId": conversation.id,
                            "answer": "已根据您的指令更新待确认卡片，您可以继续修改或点击确认。",
                        }
                    )
                    return

        # 计数查询优先走结构化工具，避免误用名称模糊匹配
        if self._is_customer_count_intent(message):
            counted = await asyncio.to_thread(
                crm_count_customers,
                self.user_id,
                None,
                message,
                None,
                None,
                None,
                None,
                True,
            )
            if counted.get("success"):
                answer = self._format_count_result_message(counted)
                await asyncio.to_thread(self._db_save_legacy_history, int(self.user_id), message, answer)
                await asyncio.to_thread(self._db_save_ai_message, conversation.id, int(self.user_id), answer)
                if counted.get("need_clarify"):
                    await self.send_json(
                        {
                            "type": "need_clarify",
                            "sessionId": self.session_id,
                            "conversationId": conversation.id,
                            "payload": counted,
                        }
                    )
                await self.send_json(
                    {
                        "type": "final",
                        "sessionId": self.session_id,
                        "conversationId": conversation.id,
                        "answer": answer,
                    }
                )
                return

        # 快速卡片链路：跟进意图直接生成草稿卡
        if self._is_followup_intent(message):
            prepared = await asyncio.to_thread(
                crm_prepare_followup,
                self.user_id,
                conversation.id,
                message,
                {"attachments": attachments},
            )
            card = (prepared or {}).get("card")
            if card:
                await self.send_json(
                    {
                        "type": "card",
                        "sessionId": self.session_id,
                        "conversationId": conversation.id,
                        "card": card,
                    }
                )
                await self.send_json(
                    {
                        "type": "final",
                        "sessionId": self.session_id,
                        "conversationId": conversation.id,
                        "answer": "已生成待确认卡片，请确认后再执行写入。",
                    }
                )
                return

        # 初始化 Xpert 客户端
        if not self.client:
            api_url = getattr(env, "XPERT_SDK_API_URL", "https://api.mtda.cloud/api/ai/")
            api_key = getattr(env, "XPERT_API_KEY", "") or getattr(env, "XPERTAI_API_KEY", "")
            self.client = _try_get_langgraph_client(api_url, api_key)
            if not self.client:
                await self.send_json(
                    {
                        "type": "error",
                        "code": "client_init_failed",
                        "message": "XpertAI client init failed",
                    }
                )
                return

        # 若无 thread，创建并绑定 session
        if not self.thread_id:
            try:
                created = await self.client.threads.create()
                thread_id = None
                if isinstance(created, dict):
                    thread_id = created.get("thread_id") or created.get("id")
                else:
                    thread_id = getattr(created, "thread_id", None) or getattr(created, "id", None)
                if not thread_id:
                    await self.send_json({"type": "error", "code": "thread_creation_failed", "message": "Failed to create thread"})
                    return
                self.thread_id = thread_id

                if session:
                    session = await asyncio.to_thread(
                        self._db_update_session,
                        session,
                        thread_id=thread_id,
                        user_id=self.user_id,
                        is_active=True,
                        conversation_id=conversation.id,
                    )
                else:
                    session = await asyncio.to_thread(
                        self._db_create_session,
                        decided_session_id,
                        thread_id,
                        int(self.user_id),
                        conversation.id,
                    )
                self.session_id = session.session_id
                await self.send_json(
                    {
                        "type": "session_created",
                        "sessionId": self.session_id,
                        "conversationId": conversation.id,
                    }
                )
            except Exception as exc:
                logger.error("Error creating thread: %s", exc, exc_info=True)
                await self.send_json(
                    {
                        "type": "error",
                        "code": "thread_creation_error",
                        "message": f"Error creating thread: {exc}",
                    }
                )
                return
        else:
            if session:
                await asyncio.to_thread(
                    self._db_update_session,
                    session,
                    is_active=True,
                    conversation_id=conversation.id,
                )

        assistant_id = getattr(env, "XPERT_ASSISTANT_ID", "")
        stream_mode = getattr(env, "XPERT_STREAM_MODE", "debug")
        if not assistant_id:
            await self.send_json(
                {
                    "type": "error",
                    "code": "missing_assistant_id",
                    "message": "XPERT_ASSISTANT_ID is not configured",
                }
            )
            return

        expert_input = {
            "input": message,
            "question": message,
            "query": message,
            "human": message,
            "content": message,
            "attachments": attachments,
            "uploaded_files": attachments,
            "files": attachments,
            "messages": [{"role": "user", "content": message}],
            "scope": await asyncio.to_thread(crm_get_scope, self.user_id),
            "scope_prefetched": True,
            "tool_runtime_policy": {
                "scope_prefetched": True,
                "avoid_scope_call_unless_user_explicitly_requests_scope": True,
            },
            "conversation_id": conversation.id,
        }

        try:
            pending_input = expert_input
            pending_command = None
            resume_hops = 0
            max_resume_hops = 8

            while True:
                stream = self.client.runs.stream(
                    thread_id=self.thread_id,
                    assistant_id=assistant_id,
                    input=pending_input,
                    command=pending_command,
                    stream_mode=stream_mode,
                )
                pending_input = None
                pending_command = None
                restart_stream = False

                async for event in stream:
                    if isinstance(event, (list, tuple)) and len(event) > 1:
                        event_data = event[1] if isinstance(event[1], dict) else {}
                    elif isinstance(event, dict):
                        event_data = event
                    else:
                        continue

                    # 提取并保存 run_id（兼容不同事件结构）
                    extracted_run_id = _extract_run_id(event_data)
                    if extracted_run_id and extracted_run_id != self.run_id:
                        self.run_id = extracted_run_id
                        if self.session_id:
                            session = await asyncio.to_thread(self._db_get_session, self.session_id)
                            if session and session.user_id == self.user_id:
                                await asyncio.to_thread(
                                    self._db_update_session,
                                    session,
                                    last_run_id=self.run_id,
                                )

                    # 客户端工具调用中断
                    req = _find_client_tool_request(event_data if isinstance(event_data, dict) else {"data": event_data})
                    if req:
                        tool_calls = req.get("clientToolCalls") or []
                        if tool_calls:
                            tool_messages = []
                            executed_tool_results = []
                            missing_tool_call_id = False
                            for tool_call in tool_calls:
                                try:
                                    executed = await asyncio.to_thread(
                                        _execute_client_tool,
                                        tool_call,
                                        user_id=self.user_id,
                                        conversation_id=self.conversation_id,
                                    )
                                except Exception as exc:
                                    tool_call_id = _extract_tool_call_id(tool_call)
                                    logger.error("Execute client tool crashed: %s", exc, exc_info=True)
                                    executed = {
                                        "events": [],
                                        "result": {"error": f"Tool crashed: {exc}"},
                                        "missing_tool_call_id": not bool(tool_call_id),
                                        "tool_message": (
                                            {
                                                "tool_call_id": tool_call_id,
                                                "name": tool_call.get("name"),
                                                "content": json.dumps(
                                                    {"error": f"Tool crashed: {exc}"},
                                                    ensure_ascii=False,
                                                ),
                                            }
                                            if tool_call_id
                                            else None
                                        ),
                                    }

                                missing_tool_call_id = missing_tool_call_id or bool(
                                    executed.get("missing_tool_call_id")
                                )
                                tool_message = executed.get("tool_message")
                                if tool_message and tool_message.get("tool_call_id"):
                                    tool_messages.append(tool_message)
                                executed_tool_results.append(
                                    {
                                        "name": (tool_call or {}).get("name"),
                                        "result": executed.get("result"),
                                    }
                                )
                                for evt in executed.get("events") or []:
                                    payload = {
                                        "type": evt.get("type"),
                                        "sessionId": self.session_id,
                                        "conversationId": self.conversation_id,
                                    }
                                    payload.update({k: v for k, v in evt.items() if k != "type"})
                                    await self.send_json(payload)

                            if missing_tool_call_id:
                                fallback_answer = await asyncio.to_thread(
                                    _build_fallback_answer_for_tool_interrupt,
                                    int(self.user_id),
                                    message,
                                    executed_tool_results,
                                )
                                if fallback_answer:
                                    await asyncio.to_thread(
                                        self._db_save_legacy_history,
                                        int(self.user_id),
                                        message,
                                        fallback_answer,
                                    )
                                    await asyncio.to_thread(
                                        self._db_save_ai_message,
                                        conversation.id,
                                        int(self.user_id),
                                        fallback_answer,
                                    )
                                    await self.send_json(
                                        {
                                            "type": "final",
                                            "sessionId": self.session_id,
                                            "conversationId": self.conversation_id,
                                            "answer": fallback_answer,
                                        }
                                    )
                                    return
                                await self._reset_current_thread("missing tool_call_id in client tool calls")
                                return

                            if len(tool_messages) != len(tool_calls):
                                logger.error(
                                    "Tool call/message mismatch: calls=%s messages=%s user=%s run=%s",
                                    len(tool_calls),
                                    len(tool_messages),
                                    self.user_id,
                                    self.run_id,
                                )
                                fallback_answer = await asyncio.to_thread(
                                    _build_fallback_answer_for_tool_interrupt,
                                    int(self.user_id),
                                    message,
                                    executed_tool_results,
                                )
                                if fallback_answer:
                                    await asyncio.to_thread(
                                        self._db_save_legacy_history,
                                        int(self.user_id),
                                        message,
                                        fallback_answer,
                                    )
                                    await asyncio.to_thread(
                                        self._db_save_ai_message,
                                        conversation.id,
                                        int(self.user_id),
                                        fallback_answer,
                                    )
                                    await self.send_json(
                                        {
                                            "type": "final",
                                            "sessionId": self.session_id,
                                            "conversationId": self.conversation_id,
                                            "answer": fallback_answer,
                                        }
                                    )
                                    return
                                await self._reset_current_thread("tool message count mismatch")
                                return

                            resume_hops += 1
                            if resume_hops > max_resume_hops:
                                await self._reset_current_thread("too many tool resume hops")
                                return

                            # langgraph_sdk 0.3.x 无 runs.resume，改用 command.resume 续跑。
                            pending_command = {"resume": tool_messages}
                            restart_stream = True
                            break
                    elif _looks_like_tool_interrupt(event_data):
                        logger.warning(
                            "Detected tool-like interrupt but no parseable tool calls: user=%s run=%s event=%s",
                            self.user_id,
                            self.run_id,
                            json.dumps(event_data, ensure_ascii=False)[:2000],
                        )
                        if _is_stream_interrupted_status(event_data):
                            await self.send_json(
                                {
                                    "type": "error",
                                    "code": "interrupt_without_calls",
                                    "sessionId": self.session_id,
                                    "conversationId": self.conversation_id,
                                    "message": "工具中断但未返回可解析调用，请重试当前请求。",
                                }
                            )
                            return

                    event_type = event_data.get("type")
                    event_name = event_data.get("event")
                    data = event_data.get("data", {})

                    if event_type == "message" and isinstance(data, dict):
                        if data.get("type") == "text":
                            text_delta = data.get("text", "")
                            if text_delta:
                                await self.send_json(
                                    {
                                        "type": "token",
                                        "sessionId": self.session_id,
                                        "conversationId": self.conversation_id,
                                        "textDelta": text_delta,
                                    }
                                )

                    if event_name == "on_agent_end" and isinstance(data, dict):
                        outputs = data.get("outputs", {})
                        if isinstance(outputs, dict):
                            answer = outputs.get("output", "")
                            if answer:
                                await asyncio.to_thread(self._db_save_legacy_history, int(self.user_id), message, answer)
                                await asyncio.to_thread(self._db_save_ai_message, conversation.id, int(self.user_id), answer)
                                await self.send_json(
                                    {
                                        "type": "final",
                                        "sessionId": self.session_id,
                                        "conversationId": self.conversation_id,
                                        "answer": answer,
                                    }
                                )

                if not restart_stream:
                    break
        except Exception as exc:
            logger.error("Stream error: %s", exc, exc_info=True)
            await self.send_json(
                {
                    "type": "error",
                    "code": "stream_error",
                    "message": f"流式响应处理失败: {exc}",
                }
            )
