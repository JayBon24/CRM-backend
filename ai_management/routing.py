"""
Tab3 WebSocket 路由配置
"""
from django.urls import re_path

from ai_management.consumers.tab3_chat import Tab3ChatConsumer

websocket_urlpatterns = [
    # Tab3 WebSocket 路由：/api/ai/ws/tab3/
    # 注意：Django Channels 的路径匹配时，路径以 / 开头
    re_path(r'^api/ai/ws/tab3/$', Tab3ChatConsumer.as_asgi()),
]
