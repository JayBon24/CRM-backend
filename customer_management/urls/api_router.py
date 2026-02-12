from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

from customer_management.views.api import CustomerViewSet, ScheduleViewSet
from customer_management.views.api.geo_views import ReverseGeocodeView
from customer_management.views.api.approval_views import ApprovalViewSet
from customer_management.views.api.area_views import list_area_by_pid
from customer_management.views.api.feedback_views import FeedbackViewSet
from customer_management.views.api.report_views import (
    DashboardView, 
    IndicatorDetailView,
    ReportGenerateView,
    ReportListView,
    ReportDetailView,
    ReportShareView
)
from customer_management.views.api.user_views import (
    UserListView, 
    BranchListView,
    OrganizationTreeView,
    TeamsByBranchView,
    UsersByTeamView,
    UserSearchView,
    DeptTreeView,
    UsersByDeptView,
    DeptUserSearchView
)

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customers")
router.register(r"schedules", ScheduleViewSet, basename="schedules")
router.register(r"approvals", ApprovalViewSet, basename="approvals")
router.register(r"feedback", FeedbackViewSet, basename="feedback")

urlpatterns = [
    path("", include(router.urls)),
    # 用户和组织接口
    path("users/", UserListView.as_view(), name="users-list"),
    path("branches/", BranchListView.as_view(), name="branches-list"),
    path("organization/tree/", OrganizationTreeView.as_view(), name="organization-tree"),
    path("organization/branches/<int:branch_id>/teams/", TeamsByBranchView.as_view(), name="teams-by-branch"),
    path("organization/teams/<int:team_id>/users/", UsersByTeamView.as_view(), name="users-by-team"),
    path("organization/users/search/", UserSearchView.as_view(), name="user-search"),
    # 基于 lsl_system_dept 的部门树和用户接口
    path("dept/tree/", DeptTreeView.as_view(), name="dept-tree"),
    path("dept/<int:dept_id>/users/", UsersByDeptView.as_view(), name="users-by-dept"),
    path("dept/users/search/", DeptUserSearchView.as_view(), name="dept-user-search"),
    # 地理位置相关
    path("geo/reverse/", ReverseGeocodeView.as_view(), name="geo-reverse"),
    # 报表系统接口 - 使用 re_path 同时支持带和不带斜杠的URL
    re_path(r"^reports/dashboard/?$", DashboardView.as_view(), name="reports-dashboard"),
    re_path(r"^reports/indicator/detail/?$", IndicatorDetailView.as_view(), name="reports-indicator-detail"),
    re_path(r"^reports/report/generate/?$", ReportGenerateView.as_view(), name="reports-generate"),
    re_path(r"^reports/report/list/?$", ReportListView.as_view(), name="reports-list"),
    re_path(r"^reports/report/(?P<report_id>\d+)/?$", ReportDetailView.as_view(), name="reports-detail"),
    re_path(r"^reports/report/(?P<report_id>\d+)/export/?$", ReportDetailView.as_view(), name="reports-export"),
    re_path(r"^reports/report/(?P<report_id>\d+)/share/?$", ReportShareView.as_view(), name="reports-share"),
    re_path(r"^sysArea/listByPid/(?P<pid>[^/]+)/?$", list_area_by_pid, name="area-list-by-pid"),
    path("sysArea/listByPid", list_area_by_pid, name="area-list-by-pid-root"),
    path("sysArea/listByPid/", list_area_by_pid, name="area-list-by-pid-root-trailing"),
]
