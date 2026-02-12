# -*- coding: utf-8 -*-
"""
小程序案件接口路由
"""
from django.urls import path

from case_management.miniapp_views import get_case_list, get_case_detail

urlpatterns = [
    path("cases/", get_case_list, name="miniapp-case-list"),
    path("cases", get_case_list, name="miniapp-case-list-no-slash"),
    path("cases/<int:case_id>/", get_case_detail, name="miniapp-case-detail"),
    path("cases/<int:case_id>", get_case_detail, name="miniapp-case-detail-no-slash"),
]
