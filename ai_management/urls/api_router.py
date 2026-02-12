"""
AI 模块 API 路由配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ai_management.views.api import AIChatViewSet, ChatKitViewSet, DocumentViewSet, SearchViewSet, VoiceRecognitionViewSet, OCRViewSet
from ai_management.views.api.tab3_views import Tab3ChatViewSet

router = DefaultRouter()
router.register(r'chat', AIChatViewSet, basename='ai-chat')
router.register(r'chatkit', ChatKitViewSet, basename='ai-chatkit')
router.register(r'document', DocumentViewSet, basename='ai-document')
router.register(r'search', SearchViewSet, basename='ai-search')
router.register(r'voice', VoiceRecognitionViewSet, basename='ai-voice')
router.register(r'ocr', OCRViewSet, basename='ai-ocr')
router.register(r'tab3', Tab3ChatViewSet, basename='ai-tab3')

urlpatterns = [
    path('', include(router.urls)),
]

