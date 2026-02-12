# -*- coding: utf-8 -*-
"""
CRM 配置接口
"""
import json
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from dvadmin.system.models import SystemConfig
from dvadmin.utils.json_response import SuccessResponse, ErrorResponse


# 默认配置
DEFAULT_CRM_CONFIG = {
    'recycle_timeout': {
        'grade_a_days': 90,
        'grade_b_days': 60,
        'grade_c_days': 30,
        'grade_d_days': 15,
        # 按无赢单天数回收提醒
        'no_won_days': 30,
    },
    'followup_frequency': {
        'meeting_days': 3,
        'case_days': 7,
        'payment_days': 14
    },
    'recycle_warning_enabled': True,
    'followup_reminder': {
        'enabled': True,
        'days': 15
    },
    'stage_transition_threshold': {
        'meeting_requires_visit': False,
        'case_requires_contract': True,
        'payment_requires_amount': 0
    }
}

CRM_CONFIG_KEY = "crm_config"
CRM_CONFIG_CACHE_KEY = "crm_config:cache"
CRM_CONFIG_CACHE_TTL = 3600


def _normalize_config_value(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
    return None


def get_crm_config():
    cached = cache.get(CRM_CONFIG_CACHE_KEY)
    if isinstance(cached, dict):
        return cached

    config_obj = SystemConfig.objects.filter(key=CRM_CONFIG_KEY).first()
    config_data = _normalize_config_value(config_obj.value) if config_obj else None
    if not config_data:
        config_data = DEFAULT_CRM_CONFIG

    cache.set(CRM_CONFIG_CACHE_KEY, config_data, timeout=CRM_CONFIG_CACHE_TTL)
    return config_data


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def crm_config(request):
    """CRM配置接口"""
    if request.method == 'GET':
        config_data = get_crm_config()
        return SuccessResponse(data={'config': config_data})
    
    elif request.method == 'POST':
        config = request.data.get('config')
        if not config:
            return ErrorResponse(msg='配置参数不能为空')
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except Exception:
                return ErrorResponse(msg='配置参数格式错误')
        if not isinstance(config, dict):
            return ErrorResponse(msg='配置参数格式错误')

        config_obj, created = SystemConfig.objects.get_or_create(
            key=CRM_CONFIG_KEY,
            defaults={
                'title': 'CRM规则配置',
                'value': config,
                'status': True,
            }
        )
        if not created:
            config_obj.value = config
            config_obj.save()

        cache.set(CRM_CONFIG_CACHE_KEY, config, timeout=CRM_CONFIG_CACHE_TTL)
        return SuccessResponse(data={'ok': True})
