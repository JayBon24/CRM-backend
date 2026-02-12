# -*- coding: utf-8 -*-
"""
CRM客户管理路由配置
提供 /crm/client/* 接口
"""
from django.urls import path

from customer_management.views.crm.client_views import (
    list_clients,
    get_stats,
    get_client_detail,
    update_client,
    batch_delete_clients,
    get_followup_list,
    get_visit_list,
    get_contract_list,
    confirm_contract,
    get_recovery_payment_list,
    get_legal_fee_list,
    get_transfer_log_list,
    update_ai_tags,
)
from customer_management.views.miniapp.client_views import get_case_source_list

urlpatterns = [
    path('client/list/', list_clients, name='crm-client-list'),
    path('client/list', list_clients, name='crm-client-list-no-slash'),
    path('client/case-source-list/', get_case_source_list, name='crm-client-case-source-list'),
    path('client/case-source-list', get_case_source_list, name='crm-client-case-source-list-no-slash'),
    path('client/stats/', get_stats, name='crm-client-stats'),
    path('client/stats', get_stats, name='crm-client-stats-no-slash'),
    path('client/batch-delete/', batch_delete_clients, name='crm-client-batch-delete'),
    path('client/batch-delete', batch_delete_clients, name='crm-client-batch-delete-no-slash'),
    path('client/<int:pk>/detail/', get_client_detail, name='crm-client-detail'),
    path('client/<int:pk>/detail', get_client_detail, name='crm-client-detail-no-slash'),
    # 跟进记录（GET和POST都使用同一个视图函数）
    path('client/<int:pk>/followups/', get_followup_list, name='crm-client-followups'),
    path('client/<int:pk>/followups', get_followup_list, name='crm-client-followups-no-slash'),
    # 拜访记录（GET和POST都使用同一个视图函数）
    path('client/<int:pk>/visits/', get_visit_list, name='crm-client-visits'),
    path('client/<int:pk>/visits', get_visit_list, name='crm-client-visits-no-slash'),
    # 合同列表（GET和POST都使用同一个视图函数）
    path('client/<int:pk>/contracts/', get_contract_list, name='crm-client-contracts'),
    path('client/<int:pk>/contracts', get_contract_list, name='crm-client-contracts-no-slash'),
    path('client/<int:pk>/contracts/<int:contract_id>/confirm/', confirm_contract, name='crm-client-contracts-confirm'),
    path('client/<int:pk>/contracts/<int:contract_id>/confirm', confirm_contract, name='crm-client-contracts-confirm-no-slash'),
    # 回款记录（GET和POST都使用同一个视图函数）
    path('client/<int:pk>/recovery-payments/', get_recovery_payment_list, name='crm-client-recovery-payments'),
    path('client/<int:pk>/recovery-payments', get_recovery_payment_list, name='crm-client-recovery-payments-no-slash'),
    # 律师费用（GET和POST都使用同一个视图函数）
    path('client/<int:pk>/legal-fees/', get_legal_fee_list, name='crm-client-legal-fees'),
    path('client/<int:pk>/legal-fees', get_legal_fee_list, name='crm-client-legal-fees-no-slash'),
    # AI标记
    path('client/<int:pk>/ai-tags/', update_ai_tags, name='crm-client-ai-tags-update'),
    path('client/<int:pk>/ai-tags', update_ai_tags, name='crm-client-ai-tags-update-no-slash'),
    # 转交日志
    path('client/<int:pk>/transfer-logs/', get_transfer_log_list, name='crm-client-transfer-logs'),
    path('client/<int:pk>/transfer-logs', get_transfer_log_list, name='crm-client-transfer-logs-no-slash'),
    # 更新客户信息（PUT/PATCH）- 放在最后，避免匹配到其他路径
    path('client/<int:pk>/', update_client, name='crm-client-update'),
    path('client/<int:pk>', update_client, name='crm-client-update-no-slash'),
]

