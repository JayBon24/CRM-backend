# -*- coding: utf-8 -*-
"""
系统配置路由
"""
from django.urls import path
from customer_management.views.api.config_views import crm_config

urlpatterns = [
    path('', crm_config, name='crm-config'),
]
