"""
Public (non-router) endpoints for ChatKit.

This keeps compatibility with simpler paths like:
- GET  /chat/config
- POST /chat/session
"""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from dvadmin.utils.json_response import DetailResponse

from ai_management.views.api.chatkit_views import ChatKitViewSet


class ChatKitConfigAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs) -> Response:
        # Reuse ViewSet logic to keep behavior identical
        viewset = ChatKitViewSet()
        return viewset.config(request)


class ChatKitSessionAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs) -> Response:
        viewset = ChatKitViewSet()
        return viewset.session(request)


