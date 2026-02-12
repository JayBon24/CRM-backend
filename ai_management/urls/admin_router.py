"""
AI 模块管理后台路由配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# TODO: 如果需要管理后台视图，在这里注册
# from ai_management.views.admin import AIConfigViewSet

router = DefaultRouter()
# router.register(r'config', AIConfigViewSet, basename='ai-config')

urlpatterns = [
    path('', include(router.urls)),
]

