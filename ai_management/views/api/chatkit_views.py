"""
ChatKit (XpertAI) integration views.

Endpoints (mounted under /api/ai/chatkit/ via router):
- GET  /api/ai/chatkit/config/
- POST /api/ai/chatkit/session/
"""

import os
from typing import Any, Mapping, Optional

import requests
from rest_framework.decorators import action

from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.request_util import get_request_user
from dvadmin.utils.viewset import CustomModelViewSet


def _get_env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip() or default


def _pick_str(data: Any, keys: list[str]) -> Optional[str]:
    if not isinstance(data, Mapping):
        return None
    for k in keys:
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _resolve_chatkit_user(request) -> str:
    """
    Map current request identity to ChatKit's `user` field (string).
    Preference:
    1) Authenticated JWT user (user.id)
    2) Body provided openid/user_id
    3) Fallback anonymous
    """
    user = get_request_user(request)
    if user is not None and hasattr(user, "id") and getattr(user, "id", None) is not None:
        return f"lsl-user:{user.id}"

    openid = _pick_str(getattr(request, "data", {}), ["openid", "openId"])
    if openid:
        return f"wx-openid:{openid}"

    user_id = _pick_str(getattr(request, "data", {}), ["user_id", "userId"])
    if user_id:
        return f"user:{user_id}"

    # Last resort: anonymous (will not persist across devices/sessions)
    return "anon"


def _resolve_assistant_id(request) -> Optional[str]:
    # Allow body override, otherwise use backend config
    from conf import env as backend_env  # imported here to avoid settings import side effects

    assistant_id = _pick_str(getattr(request, "data", {}), ["assistant_id", "assistantId", "workflow_id", "workflowId"])
    if assistant_id:
        return assistant_id

    # Prefer env module constants if present; fallback to os.getenv
    value = getattr(backend_env, "XPERTAI_CHATKIT_ASSISTANT_ID", "") or _get_env("XPERTAI_CHATKIT_ASSISTANT_ID", "")
    return value or None


def _chatkit_api_base() -> str:
    # Allow override (useful for self-hosted gateway); default to official XpertAI endpoint
    return _get_env("XPERTAI_API_URL", "https://api.mtda.cloud/api/ai").rstrip("/")


class ChatKitViewSet(CustomModelViewSet):
    """
    ChatKit API adapters for uniapp/web clients.
    """

    # 添加空的 queryset 以满足 DRF 要求（此 ViewSet 不使用数据库模型）
    queryset = None
    permission_classes = []
    
    # 禁用 Swagger 文档生成（避免因无 queryset 导致错误）
    swagger_schema = None

    @action(detail=False, methods=["get"], url_path="config")
    def config(self, request):
        """
        Return universal config for frontend:
        - assistantId: XpertAI assistant/workflow id
        - frameUrl: must point to chatkit-host (typically :5200)
        - h5Url: URL used by miniapp <web-view> to load the H5 host page
        - apiUrl: XpertAI API Base URL (defaults to https://api.mtda.cloud/api/ai)
        """
        from conf import env as backend_env

        assistant_id = getattr(backend_env, "XPERTAI_CHATKIT_ASSISTANT_ID", "") or _get_env("XPERTAI_CHATKIT_ASSISTANT_ID")
        frame_url = getattr(backend_env, "XPERTAI_CHATKIT_FRAME_URL", "") or _get_env("XPERTAI_CHATKIT_FRAME_URL")
        h5_url = getattr(backend_env, "XPERTAI_CHATKIT_H5_URL", "") or _get_env("XPERTAI_CHATKIT_H5_URL")
        api_url = getattr(backend_env, "XPERTAI_API_URL", "") or _get_env("XPERTAI_API_URL") or "https://api.mtda.cloud/api/ai"

        if not assistant_id:
            return ErrorResponse(msg="缺少后端配置：XPERTAI_CHATKIT_ASSISTANT_ID", code=500)
        if not frame_url:
            return ErrorResponse(msg="缺少后端配置：XPERTAI_CHATKIT_FRAME_URL（需指向 chatkit-host:5200）", code=500)

        return DetailResponse(
            data={
                "assistantId": assistant_id,
                "frameUrl": frame_url,
                "h5Url": h5_url,
                "apiUrl": api_url,
            }
        )

    @action(detail=False, methods=["post"], url_path="session")
    def session(self, request):
        """
        Create ChatKit session (exchange assistantId -> client_secret).
        """
        # Prefer Django config module (conf.env imported by settings), fallback to OS env
        from conf import env as backend_env

        api_key = (getattr(backend_env, "XPERTAI_API_KEY", "") or "").strip() or _get_env("XPERTAI_API_KEY")
        if not api_key:
            return ErrorResponse(msg="Missing XPERTAI_API_KEY environment variable", code=500)

        assistant_id = _resolve_assistant_id(request)
        if not assistant_id:
            return ErrorResponse(msg="缺少 assistantId（请求体或后端配置）", code=400)

        chatkit_user = _resolve_chatkit_user(request)
        api_base = (getattr(backend_env, "XPERTAI_API_URL", "") or "").strip() or _chatkit_api_base()

        try:
            upstream = requests.post(
                f"{api_base}/v1/chatkit/sessions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "OpenAI-Beta": "chatkit_beta=v1",
                    "Content-Type": "application/json",
                },
                json={"assistant": {"id": assistant_id}, "user": chatkit_user},
                timeout=10,
            )
        except requests.RequestException as e:
            return ErrorResponse(msg=f"Failed to reach ChatKit API: {str(e)}", code=502)

        try:
            payload = upstream.json()
        except Exception:
            payload = None

        if not (200 <= upstream.status_code < 300):
            message = None
            if isinstance(payload, Mapping):
                message = payload.get("error") or payload.get("message")
            message = message or upstream.reason or "Failed to create session"
            return ErrorResponse(msg=str(message), code=upstream.status_code)

        client_secret = None
        expires_after = None
        if isinstance(payload, Mapping):
            client_secret = payload.get("client_secret")
            expires_after = payload.get("expires_after")

        if not client_secret:
            return ErrorResponse(msg="Missing client_secret in response", code=502)

        return DetailResponse(data={"client_secret": client_secret, "expires_after": expires_after})


