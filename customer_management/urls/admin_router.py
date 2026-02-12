from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

from customer_management.views.admin import AdminCustomerViewSet, AdminApprovalViewSet
from customer_management.views.api import ScheduleViewSet
from customer_management.views.api.report_views import (
    DashboardView, 
    IndicatorDetailView,
    ReportGenerateView,
    ReportListView,
    ReportDetailView,
    ReportShareView
)
from customer_management.views.api.user_views import UserListView, BranchListView

router = DefaultRouter()
router.register(r"customers", AdminCustomerViewSet, basename="admin-customers")
router.register(r"approvals", AdminApprovalViewSet, basename="customer-approvals")
router.register(r"schedules", ScheduleViewSet, basename="admin-schedules")

urlpatterns = [
    path("", include(router.urls)),
    # 用户和组织接口
    path("users/", UserListView.as_view(), name="admin-users-list"),
    path("branches/", BranchListView.as_view(), name="admin-branches-list"),
    # 报表系统接口 - 使用 re_path 同时支持带和不带斜杠的URL
    re_path(r"^reports/dashboard/?$", DashboardView.as_view(), name="admin-reports-dashboard"),
    re_path(r"^reports/indicator/detail/?$", IndicatorDetailView.as_view(), name="admin-reports-indicator-detail"),
    re_path(r"^reports/report/generate/?$", ReportGenerateView.as_view(), name="admin-reports-generate"),
    re_path(r"^reports/report/list/?$", ReportListView.as_view(), name="admin-reports-list"),
    re_path(r"^reports/report/(?P<report_id>\d+)/?$", ReportDetailView.as_view(), name="admin-reports-detail"),
    re_path(r"^reports/report/(?P<report_id>\d+)/export/?$", ReportDetailView.as_view(), name="admin-reports-export"),
    re_path(r"^reports/report/(?P<report_id>\d+)/share/?$", ReportShareView.as_view(), name="admin-reports-share"),
]
