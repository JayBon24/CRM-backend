# -*- coding: utf-8 -*-
"""
小程序 Tab5「我的」模块路由配置
提供 /api/mine/* 接口
"""
from django.urls import path

from customer_management.views.miniapp.mine_views import (
    get_mine_profile,
    update_mine_profile,
    submit_feedback,
    get_feedback_list,
    get_approval_list,
    approve_task,
    reminder_preference,
)

urlpatterns = [
    path('profile', get_mine_profile, name='miniapp-mine-profile'),
    path('profile/', get_mine_profile, name='miniapp-mine-profile-slash'),
    path('profile/update', update_mine_profile, name='miniapp-mine-profile-update'),
    path('profile/update/', update_mine_profile, name='miniapp-mine-profile-update-slash'),
    path('feedback', submit_feedback, name='miniapp-mine-feedback'),
    path('feedback/', submit_feedback, name='miniapp-mine-feedback-slash'),
    path('feedback/list', get_feedback_list, name='miniapp-mine-feedback-list'),
    path('feedback/list/', get_feedback_list, name='miniapp-mine-feedback-list-slash'),
    path('approval/list', get_approval_list, name='miniapp-mine-approval-list'),
    path('approval/list/', get_approval_list, name='miniapp-mine-approval-list-slash'),
    path('approval/<str:id>/approve', approve_task, name='miniapp-mine-approval-approve'),
    path('approval/<str:id>/approve/', approve_task, name='miniapp-mine-approval-approve-slash'),
    path('settings/remind', reminder_preference, name='miniapp-mine-settings-remind'),
    path('settings/remind/', reminder_preference, name='miniapp-mine-settings-remind-slash'),
]
