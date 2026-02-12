"""backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.urls import path, include, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from application import dispatch
from application import settings
from application.sse_views import sse_view
from dvadmin.system.views.dictionary import InitDictionaryViewSet
from dvadmin.system.views.login import (
    LoginView,
    CaptchaView,
    ApiLogin,
    LogoutView,
    LoginTokenView
)
from dvadmin.system.views.api.miniapp_login import MiniappLoginView
from dvadmin.system.views.api.miniapp_auth import SmsSendView, SmsLoginView, WechatCheckView, WechatRegisterView, RegisterView
from dvadmin.system.views.api.mine_profile import MineProfileView
from ai_management.views.chatkit_public import ChatKitConfigAPIView, ChatKitSessionAPIView
from dvadmin.system.views.system_config import InitSettingsViewSet
from dvadmin.utils.swagger import CustomOpenAPISchemaGenerator
from case_management.media_views import serve_protected_media
from case_management.wps_callback_views import wps_office_view
from customer_management.views.api.area_views import list_area_by_pid

# =========== 初始化系统配置 =================
dispatch.init_system_config()
dispatch.init_dictionary()
# =========== 初始化系统配置 =================

permission_classes = [permissions.AllowAny, ] if settings.DEBUG else [permissions.IsAuthenticated, ]
schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=permission_classes,
    generator_class=CustomOpenAPISchemaGenerator,
)
# 前端页面映射
from django.http import Http404, HttpResponse
from django.shortcuts import render
import mimetypes
import os


def web_view(request):
    return render(request, 'web/index.html')


def serve_web_files(request, filename):
    # 设定文件路径
    filepath = os.path.join(settings.BASE_DIR, 'templates', 'web', filename)

    # 检查文件是否存在
    if not os.path.exists(filepath):
        raise Http404("File does not exist")

    # 根据文件扩展名，确定 MIME 类型
    mime_type, _ = mimetypes.guess_type(filepath)

    # 打开文件并读取内容
    with open(filepath, 'rb') as f:
        response = HttpResponse(f.read(), content_type=mime_type)
        return response


def version_build(request):
    version = os.getenv("APP_VERSION", "unknown")
    build = os.getenv("APP_BUILD", "unknown")
    if build and build != "unknown":
        payload = f"{version}.{build}"
    else:
        payload = version
    return HttpResponse(payload)


urlpatterns = (
        [
            re_path(
                r"^swagger(?P<format>\.json|\.yaml)$",
                schema_view.without_ui(cache_timeout=0),
                name="schema-json",
            ),
            path(
                "",
                schema_view.with_ui("swagger", cache_timeout=0),
                name="schema-swagger-ui",
            ),
             path(
                 r"redoc/",
                 schema_view.with_ui("redoc", cache_timeout=0),
                 name="schema-redoc",
             ),
             # 添加 admin-api 路径下的 swagger
             re_path(
                 r"^admin-api/swagger(?P<format>\.json|\.yaml)$",
                 schema_view.without_ui(cache_timeout=0),
                 name="admin-api-schema-json",
             ),
             path(
                 "admin-api/swagger/",
                 schema_view.with_ui("swagger", cache_timeout=0),
                 name="admin-api-swagger-ui",
             ),
             path(
                 "admin-api/redoc/",
                 schema_view.with_ui("redoc", cache_timeout=0),
                 name="admin-api-redoc",
             ),
             path("admin-api/system/", include("dvadmin.system.urls")),
            # 前端导入/导出等请求使用 api/system/ 前缀，此处兼容该路径避免 404
            path("admin-api/api/system/", include("dvadmin.system.urls")),
             path("admin-api/case/", include("case_management.urls")),
             path("admin-api/customer/", include("customer_management.urls.admin_router")),
             path("admin-api/crm/", include("customer_management.urls.crm_router")),
             # 用户登录类
             path("admin-api/login/", LoginView.as_view(), name="token_obtain_pair"),
             path("admin-api/logout/", LogoutView.as_view(), name="token_obtain_pair"),
             path("admin-api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
             re_path(
                 r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")
             ),
            path("admin-api/captcha/", CaptchaView.as_view()),
            path("admin-api/init/dictionary/", InitDictionaryViewSet.as_view()),
            path("admin-api/init/settings/", InitSettingsViewSet.as_view()),
            path("admin-api/apiLogin/", ApiLogin.as_view()),
            # 仅用于开发，上线需关闭
            path("admin-api/token/", LoginTokenView.as_view()),
            path("version-build", version_build),

            # 前端页面映射
            ## 用户登录
            path("api/login/", LoginView.as_view(), name="token_obtain_pair"),
            path("api/logout/", LogoutView.as_view(), name="token_obtain_pair"),
            path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
            ## 小程序登录
            path("api/miniapp/login/", MiniappLoginView.as_view(), name="miniapp_login"),
            path("api/auth/login/sms", SmsLoginView.as_view(), name="miniapp_sms_login"),
            path("api/auth/login/sms/", SmsLoginView.as_view(), name="miniapp_sms_login_slash"),
            path("api/user/sms/send", SmsSendView.as_view(), name="miniapp_sms_send"),
            path("api/user/sms/send/", SmsSendView.as_view(), name="miniapp_sms_send_slash"),
            path("api/auth/register", RegisterView.as_view(), name="miniapp_register"),
            path("api/auth/register/", RegisterView.as_view(), name="miniapp_register_slash"),
            path("api/auth/wechat/check", WechatCheckView.as_view(), name="miniapp_wechat_check"),
            path("api/auth/wechat/check/", WechatCheckView.as_view(), name="miniapp_wechat_check_slash"),
            path("api/auth/wechat/register", WechatRegisterView.as_view(), name="miniapp_wechat_register"),
            path("api/auth/wechat/register/", WechatRegisterView.as_view(), name="miniapp_wechat_register_slash"),
            ## Mine Profile - 用户个人资料
            path("api/mine/profile/", MineProfileView.as_view(), name="mine_profile"),
            ## 客户功能模块（包含日程管理）
            path("api/customer/", include("customer_management.urls.api_router")),
            path("api/sysArea/listByPid/<str:pid>/", list_area_by_pid),
            path("api/sysArea/listByPid/", list_area_by_pid),
            ## AI功能模块
            path("api/ai/", include("ai_management.urls.api_router")),
            path("api/case/", include("case_management.miniapp_urls")),
            ## 小程序案件管理模块
            path("api/case/", include("case_management.urls")),
            ## 小程序 Tab1「客户」模块
            path("api/crm/", include("customer_management.urls.miniapp_router")),
            ## 小程序 Tab5「我的」模块
            path("api/mine/", include("customer_management.urls.mine_router")),
            ## 系统配置接口
            path("api/sys/config/crm", include("customer_management.urls.sys_router")),

            # ChatKit simple aliases (for uniapp web-view / external H5 host)
            path("chat/config", ChatKitConfigAPIView.as_view()),
            path("chat/session", ChatKitSessionAPIView.as_view()),


            # 前端WEB页面映射
            path('web/', web_view, name='web_view'),
            path('web/<path:filename>', serve_web_files, name='serve_web_files'),
            # sse
            path('sse/', sse_view, name='sse'),
            
            # WPS直接访问路由（WPS SDK默认路径格式：/office/{type}/{id}）
            # 必须放在media路由之前，确保优先匹配
            # 同时支持带斜杠和不带斜杠的路径
            re_path(r'^office/(?P<office_type>[a-z]+)/(?P<file_id>\d+)/?$', wps_office_view, name='wps_office_view'),
            
            # 媒体文件访问（需要登录权限）
            # 所有环境都需要登录才能访问
            re_path(r'^media/(?P<file_path>.+)$', serve_protected_media, name='protected_media'),
        ]
        + static(settings.STATIC_URL, document_root=settings.STATIC_URL)
        + [re_path(ele.get('re_path'), include(ele.get('include'))) for ele in settings.PLUGINS_URL_PATTERNS]
)
