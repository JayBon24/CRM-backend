# -*- coding: utf-8 -*-
"""
小程序接口路由配置
提供 /api/crm/* 和 /api/mine/* 接口
"""
from django.urls import path

from customer_management.views.miniapp.client_views import (
    get_client_list,
    get_case_source_list,
    get_client_detail,
    create_client,
    create_client_with_case,
    get_owner_customers,
    apply_client,
    apply_handover,
    assign_client,
    approve_client_apply,
    get_client_visits,
    get_client_plans,
    get_client_followups,
    create_client_followup,
    create_client_visit,
    create_client_plan,
    update_client_plan,
    get_collection_progress_list,
    create_collection_progress,
    confirm_contract,
)
from customer_management.views.api.schedule_views import get_team_schedule
from customer_management.views.crm.client_views import (
    get_transfer_log_list,
    get_contract_list,
    get_recovery_payment_list,
    get_legal_fee_list,
    create_recovery_payment,
    create_legal_fee,
)
from customer_management.views.api.company_views import get_company_credit_code
from customer_management.views.api.reminder_views import (
    ReminderListView,
    ReminderReadView,
    ReminderScanView,
    ReminderUnreadCountView,
)
# from customer_management.views.miniapp.mine_views import (
#     get_mine_profile,
#     update_mine_profile,
#     submit_feedback,
#     get_feedback_list,
#     get_approval_list,
#     approve_task,
#     get_reminder_preference,
#     set_reminder_preference,
# )

# Tab1「客户」模块路由
urlpatterns = [
    path('client/list', get_client_list, name='miniapp-client-list'),
    path('client/list/', get_client_list, name='miniapp-client-list-slash'),
    path('client/case-source-list', get_case_source_list, name='miniapp-client-case-source-list'),
    path('client/case-source-list/', get_case_source_list, name='miniapp-client-case-source-list-slash'),
    path('client/<int:id>', get_client_detail, name='miniapp-client-detail'),
    path('client/<int:id>/', get_client_detail, name='miniapp-client-detail-slash'),
    path('client', create_client, name='miniapp-client-create'),
    path('client/', create_client, name='miniapp-client-create-slash'),
    path('client/create-with-case', create_client_with_case, name='miniapp-client-create-with-case'),
    path('client/create-with-case/', create_client_with_case, name='miniapp-client-create-with-case-slash'),
    path('client/owner-customers', get_owner_customers, name='miniapp-client-owner-customers'),
    path('client/owner-customers/', get_owner_customers, name='miniapp-client-owner-customers-slash'),
    path('client/<int:id>/apply', apply_client, name='miniapp-client-apply'),
    path('client/<int:id>/apply/', apply_client, name='miniapp-client-apply-slash'),
    path('client/<int:id>/assign', assign_client, name='miniapp-client-assign'),
    path('client/<int:id>/assign/', assign_client, name='miniapp-client-assign-slash'),
    path('client/handover', apply_handover, name='miniapp-client-handover'),
    path('client/handover/', apply_handover, name='miniapp-client-handover-slash'),
    path('client/approve/<str:apply_id>', approve_client_apply, name='miniapp-client-approve'),
    path('client/approve/<str:apply_id>/', approve_client_apply, name='miniapp-client-approve-slash'),
    # 拜访记录和跟进计划
    path('client/<int:client_id>/visit', get_client_visits, name='miniapp-client-visits'),
    path('client/<int:client_id>/visit/', get_client_visits, name='miniapp-client-visits-slash'),
    path('client/<int:client_id>/plan', get_client_plans, name='miniapp-client-plans'),
    path('client/<int:client_id>/plan/', get_client_plans, name='miniapp-client-plans-slash'),
    path('client/<int:client_id>/followup', get_client_followups, name='miniapp-client-followups'),
    path('client/<int:client_id>/followup/', get_client_followups, name='miniapp-client-followups-slash'),
    path('client/followup', create_client_followup, name='miniapp-client-followup-create'),
    path('client/followup/', create_client_followup, name='miniapp-client-followup-create-slash'),
    path('client/visit', create_client_visit, name='miniapp-client-visit-create'),
    path('client/visit/', create_client_visit, name='miniapp-client-visit-create-slash'),
    path('client/plan', create_client_plan, name='miniapp-client-plan-create'),
    path('client/plan/', create_client_plan, name='miniapp-client-plan-create-slash'),
    path('client/plan/<int:plan_id>', update_client_plan, name='miniapp-client-plan-update'),
    path('client/plan/<int:plan_id>/', update_client_plan, name='miniapp-client-plan-update-slash'),
    path('client/<int:client_id>/collection-progress', get_collection_progress_list, name='miniapp-client-collection-progress'),
    path('client/<int:client_id>/collection-progress/', get_collection_progress_list, name='miniapp-client-collection-progress-slash'),
    path('client/collection-progress', create_collection_progress, name='miniapp-client-collection-progress-create'),
    path('client/collection-progress/', create_collection_progress, name='miniapp-client-collection-progress-create-slash'),
    path('client/contract', confirm_contract, name='miniapp-client-contract-confirm'),
    path('client/contract/', confirm_contract, name='miniapp-client-contract-confirm-slash'),
    # 创建回款记录
    path('client/payment', create_recovery_payment, name='miniapp-client-payment-create'),
    path('client/payment/', create_recovery_payment, name='miniapp-client-payment-create-slash'),
    # 创建律师费用
    path('client/legal-fee', create_legal_fee, name='miniapp-client-legal-fee-create'),
    path('client/legal-fee/', create_legal_fee, name='miniapp-client-legal-fee-create-slash'),
    # 合同列表
    path('client/<int:pk>/contracts', get_contract_list, name='miniapp-client-contracts'),
    path('client/<int:pk>/contracts/', get_contract_list, name='miniapp-client-contracts-slash'),
    # 回款记录
    path('client/<int:pk>/recovery-payments', get_recovery_payment_list, name='miniapp-client-recovery-payments'),
    path('client/<int:pk>/recovery-payments/', get_recovery_payment_list, name='miniapp-client-recovery-payments-slash'),
    # 律师费用
    path('client/<int:pk>/legal-fees', get_legal_fee_list, name='miniapp-client-legal-fees'),
    path('client/<int:pk>/legal-fees/', get_legal_fee_list, name='miniapp-client-legal-fees-slash'),
    # 转交日志
    path('client/<int:pk>/transfer-logs', get_transfer_log_list, name='miniapp-client-transfer-logs'),
    path('client/<int:pk>/transfer-logs/', get_transfer_log_list, name='miniapp-client-transfer-logs-slash'),
    # 团队日程
    path('team/schedule', get_team_schedule, name='miniapp-team-schedule'),
    path('team/schedule/', get_team_schedule, name='miniapp-team-schedule-slash'),
    # 企业信息查询
    path('company/credit-code', get_company_credit_code, name='miniapp-company-credit-code'),
    path('company/credit-code/', get_company_credit_code, name='miniapp-company-credit-code-slash'),
    # 提醒相关
    path('reminders', ReminderListView.as_view(), name='miniapp-reminder-list'),
    path('reminders/', ReminderListView.as_view(), name='miniapp-reminder-list-slash'),
    path('reminders/<int:pk>/read', ReminderReadView.as_view(), name='miniapp-reminder-read'),
    path('reminders/<int:pk>/read/', ReminderReadView.as_view(), name='miniapp-reminder-read-slash'),
    path('reminders/scan', ReminderScanView.as_view(), name='miniapp-reminder-scan'),
    path('reminders/scan/', ReminderScanView.as_view(), name='miniapp-reminder-scan-slash'),
    path('reminders/unread-count', ReminderUnreadCountView.as_view(), name='miniapp-reminder-unread-count'),
    path('reminders/unread-count/', ReminderUnreadCountView.as_view(), name='miniapp-reminder-unread-count-slash'),
]
