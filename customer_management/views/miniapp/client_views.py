# -*- coding: utf-8 -*-
"""
小程序 Tab1「客户」模块视图
提供 /api/crm/client/* 接口
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q, Count, Max
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta, datetime
import json

from customer_management.models import (
    ApprovalTask,
    CollectionProgress,
    Customer,
    CustomerPlan,
    FollowupRecord,
    TransferLog,
    VisitRecord,
)
from customer_management.models.contract import Contract
from case_management.models import CaseManagement
from case_management.services.case_service import (
    create_case_from_contract_data,
    create_case_from_effective_case,
    generate_case_number,
)
from customer_management.services.customer_service import CustomerService
from customer_management.services.approval_service import ApprovalService
from customer_management.services.scope_service import can_access_customer
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.system.models import Users

try:
    from customer_management.views.api.config_views import DEFAULT_CRM_CONFIG, get_crm_config
except Exception:
    DEFAULT_CRM_CONFIG = {}
    def get_crm_config():
        return DEFAULT_CRM_CONFIG


DEFAULT_RECYCLE_DAYS = 30
GRADE_RECYCLE_KEY_MAP = {
    "A": "grade_a_days",
    "B": "grade_b_days",
    "C": "grade_c_days",
    "D": "grade_d_days",
}


def _get_recycle_timeout_days(grade):
    config = get_crm_config() or DEFAULT_CRM_CONFIG
    timeout_config = config.get("recycle_timeout", {}) if isinstance(config, dict) else {}
    grade_key = GRADE_RECYCLE_KEY_MAP.get((grade or "").upper())
    if grade_key and timeout_config.get(grade_key):
        try:
            return int(timeout_config.get(grade_key))
        except Exception:
            return DEFAULT_RECYCLE_DAYS
    return DEFAULT_RECYCLE_DAYS


def _resolve_recycle_deadline(customer: Customer, last_followup_dt=None, last_visit_dt=None):
    if customer.recycle_deadline:
        return customer.recycle_deadline
    if customer.status == Customer.STATUS_PUBLIC_POOL:
        return None
    base_candidates = [
        last_followup_dt,
        last_visit_dt,
        customer.update_datetime,
        customer.create_datetime,
    ]
    base_candidates = [item for item in base_candidates if item]
    if not base_candidates:
        return None
    base_dt = max(base_candidates)
    days = _get_recycle_timeout_days(customer.client_grade)
    return (base_dt + timedelta(days=days)).date()


def _parse_datetime_value(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            ts = value / 1000 if value > 1_000_000_000_000 else value
            return datetime.fromtimestamp(ts)
        except Exception:
            return None
    if isinstance(value, str):
        parsed = parse_datetime(value)
        if parsed:
            return parsed
        try:
            return datetime.strptime(value, '%Y-%m-%d')
        except Exception:
            try:
                return datetime.fromisoformat(value.replace('Z', ''))
            except Exception:
                return None
    return None


def _get_followup_queryset(client):
    try:
        return FollowupRecord.objects.filter(customer=client, is_deleted=False)
    except Exception:
        return FollowupRecord.objects.filter(client_id=client.id, is_deleted=False)


def _is_valid_followup(record: FollowupRecord, sales_stage: str = None) -> bool:
    """
    判定跟进是否有效：
    location_status=success 或 (lng & lat) 或 address
    """
    if sales_stage == Customer.SALES_STAGE_BLANK:
        return False
    if record.location_status == "success":
        return True
    if record.lng and record.lat:
        return True
    address = (record.address or "").strip()
    return bool(address)


def _get_handler_payload(customer):
    handlers = []
    try:
        if hasattr(customer, "handlers"):
            handlers = list(customer.handlers.all())
    except Exception:
        handlers = []
    if not handlers and getattr(customer, "owner_user", None):
        handlers = [customer.owner_user]
    handler_ids = [user.id for user in handlers if user]
    handler_names = [user.name or user.username for user in handlers if user]
    handler_list = [{"id": user.id, "name": user.name or user.username} for user in handlers if user]
    return handler_ids, handler_names, handler_list


def _has_handler(customer, user):
    try:
        if hasattr(customer, "handlers"):
            return customer.handlers.filter(id=user.id).exists()
    except Exception:
        pass
    return str(getattr(customer, "owner_user_id", "")) == str(getattr(user, "id", ""))


def _sync_followup_stats(customer: Customer):
    followups = list(_get_followup_queryset(customer))
    followup_count = len(followups)
    valid_followup_count = sum(1 for item in followups if _is_valid_followup(item))
    update_data = {
        "followup_count": followup_count,
        "valid_visit_count": valid_followup_count,
    }
    if valid_followup_count > 0:
        update_data["sales_stage"] = Customer.SALES_STAGE_MEETING
    Customer.objects.filter(
        is_deleted=False,
        id=customer.id,
    ).update(**update_data)
    for key, value in update_data.items():
        setattr(customer, key, value)
    return followup_count, valid_followup_count


def _format_customer_row(customer: Customer, role_level: str):
    try:
        last_followup = FollowupRecord.objects.filter(customer=customer).order_by('-followup_time').first()
    except Exception:
        last_followup = FollowupRecord.objects.filter(client_id=customer.id).order_by('-followup_time').first()
    if last_followup and getattr(last_followup, 'followup_time', None):
        last_followup_at = last_followup.followup_time.strftime('%Y-%m-%d %H:%M:%S')
        last_followup_dt = last_followup.followup_time
    else:
        last_followup_at = last_followup.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if last_followup else None
        last_followup_dt = last_followup.create_datetime if last_followup else None

    try:
        last_visit = VisitRecord.objects.filter(customer=customer).order_by('-visit_time').first()
    except Exception:
        last_visit = VisitRecord.objects.filter(client_id=customer.id).order_by('-visit_time').first()
    last_visit_at = last_visit.visit_time.strftime('%Y-%m-%d %H:%M:%S') if last_visit else None
    last_visit_dt = last_visit.visit_time if last_visit else None

    next_plan_at = None
    try:
        try:
            next_plan = FollowupRecord.objects.filter(
                customer=customer,
                next_followup_time__isnull=False
            ).order_by('next_followup_time').first()
        except Exception:
            next_plan = FollowupRecord.objects.filter(
                client_id=customer.id,
                next_followup_time__isnull=False
            ).order_by('next_followup_time').first()
        if next_plan and getattr(next_plan, 'next_followup_time', None):
            next_plan_at = next_plan.next_followup_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        next_plan_at = None

    collection_categories = []
    if customer.collection_category:
        try:
            if isinstance(customer.collection_category, str):
                collection_categories = json.loads(customer.collection_category) if customer.collection_category.startswith('[') else [customer.collection_category]
            else:
                collection_categories = customer.collection_category
        except Exception:
            collection_categories = [customer.collection_category] if customer.collection_category else []

    owner_name = customer.owner_user_name
    if not owner_name and getattr(customer, "owner_user", None):
        owner_name = customer.owner_user.name or customer.owner_user.username
    handler_ids, handler_names, handler_list = _get_handler_payload(customer)

    followups = list(_get_followup_queryset(customer))
    followup_count = len(followups)
    valid_followup_count = sum(
        1 for item in followups if _is_valid_followup(item, customer.sales_stage)
    )
    recycle_deadline = _resolve_recycle_deadline(customer, last_followup_dt, last_visit_dt)

    return {
        'id': customer.id,
        'case_id': None,
        'case_name': None,
        'case_number': None,
        'customer_id': customer.id,
        'customer_name': customer.name,
        'display_name': customer.name,
        'status': customer.status,
        'sales_stage': customer.sales_stage,
        'client_name': customer.name,
        'contact_name': customer.contact_person,
        'mobile': customer.contact_phone,
        'region': customer.address,
        'grade': customer.client_grade,
        'grade_source': customer.grade_source or 'ai',
        'category': customer.client_category,
        'collection_category': collection_categories,
        'collection_source': customer.collection_source or 'ai',
        'preservation_status': None,
        'court': None,
        'lawyer': None,
        'owner_user_id': customer.owner_user_id,
        'owner_user_name': owner_name,
        'handler_ids': handler_ids,
        'handler_names': handler_names,
        'handlers': handler_list,
        'org_scope': role_level if role_level else 'SELF',
        'team_id': customer.team_id,
        'branch_id': customer.branch_id,
        'team_name': None,
        'branch_name': None,
        'followup_count': followup_count,
        'valid_followup_count': valid_followup_count,
        'visit_count': customer.valid_visit_count,
        'valid_visit_count': customer.valid_visit_count,
        'last_followup_at': last_followup_at,
        'last_visit_at': last_visit_at,
        'next_plan_at': next_plan_at,
        'recycle_risk_level': customer.recycle_risk_level,
        'recycle_deadline': recycle_deadline.strftime('%Y-%m-%d') if recycle_deadline else None,
        'last_deal_time': customer.last_deal_time.strftime('%Y-%m-%d %H:%M:%S') if customer.last_deal_time else None,
        'create_time': customer.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if customer.create_datetime else None,
        'update_time': customer.update_datetime.strftime('%Y-%m-%d %H:%M:%S') if customer.update_datetime else None,
    }


def _format_case_row(case: CaseManagement, role_level: str):
    customer = case.customer
    if not customer:
        return None

    try:
        last_followup = FollowupRecord.objects.filter(customer=customer).order_by('-followup_time').first()
    except Exception:
        last_followup = FollowupRecord.objects.filter(client_id=customer.id).order_by('-followup_time').first()
    if last_followup and getattr(last_followup, 'followup_time', None):
        last_followup_at = last_followup.followup_time.strftime('%Y-%m-%d %H:%M:%S')
        last_followup_dt = last_followup.followup_time
    else:
        last_followup_at = last_followup.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if last_followup else None
        last_followup_dt = last_followup.create_datetime if last_followup else None

    try:
        last_visit = VisitRecord.objects.filter(customer=customer).order_by('-visit_time').first()
    except Exception:
        last_visit = VisitRecord.objects.filter(client_id=customer.id).order_by('-visit_time').first()
    last_visit_at = last_visit.visit_time.strftime('%Y-%m-%d %H:%M:%S') if last_visit else None
    last_visit_dt = last_visit.visit_time if last_visit else None

    next_plan_at = None
    try:
        try:
            next_plan = FollowupRecord.objects.filter(
                customer=customer,
                next_followup_time__isnull=False
            ).order_by('next_followup_time').first()
        except Exception:
            next_plan = FollowupRecord.objects.filter(
                client_id=customer.id,
                next_followup_time__isnull=False
            ).order_by('next_followup_time').first()
        if next_plan and getattr(next_plan, 'next_followup_time', None):
            next_plan_at = next_plan.next_followup_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        next_plan_at = None

    collection_categories = []
    if customer.collection_category:
        try:
            if isinstance(customer.collection_category, str):
                collection_categories = json.loads(customer.collection_category) if customer.collection_category.startswith('[') else [customer.collection_category]
            else:
                collection_categories = customer.collection_category
        except Exception:
            collection_categories = [customer.collection_category] if customer.collection_category else []

    owner_name = customer.owner_user_name
    if not owner_name and getattr(customer, "owner_user", None):
        owner_name = customer.owner_user.name or customer.owner_user.username
    handler_ids, handler_names, handler_list = _get_handler_payload(customer)

    followups = list(_get_followup_queryset(customer))
    followup_count = len(followups)
    valid_followup_count = sum(
        1 for item in followups if _is_valid_followup(item, customer.sales_stage)
    )
    recycle_deadline = _resolve_recycle_deadline(customer, last_followup_dt, last_visit_dt)

    return {
        'id': case.id,
        'case_id': case.id,
        'case_name': case.case_name,
        'case_number': case.case_number,
        'customer_id': customer.id,
        'customer_name': customer.name,
        'display_name': f"{customer.name}--{case.case_name}" if case.case_name else customer.name,
        'status': case.status,
        'sales_stage': case.sales_stage,
        'client_name': customer.name,
        'contact_name': customer.contact_person,
        'mobile': customer.contact_phone,
        'region': customer.address,
        'grade': customer.client_grade,
        'grade_source': customer.grade_source or 'ai',
        'category': customer.client_category,
        'collection_category': collection_categories,
        'collection_source': customer.collection_source or 'ai',
        'preservation_status': None,
        'court': None,
        'lawyer': None,
        'owner_user_id': customer.owner_user_id,
        'owner_user_name': owner_name,
        'handler_ids': handler_ids,
        'handler_names': handler_names,
        'handlers': handler_list,
        'org_scope': role_level if role_level else 'SELF',
        'team_id': customer.team_id,
        'branch_id': customer.branch_id,
        'team_name': None,
        'branch_name': None,
        'followup_count': followup_count,
        'valid_followup_count': valid_followup_count,
        'visit_count': customer.valid_visit_count,
        'valid_visit_count': customer.valid_visit_count,
        'last_followup_at': last_followup_at,
        'last_visit_at': last_visit_at,
        'next_plan_at': next_plan_at,
        'recycle_risk_level': customer.recycle_risk_level,
        'recycle_deadline': recycle_deadline.strftime('%Y-%m-%d') if recycle_deadline else None,
        'last_deal_time': customer.last_deal_time.strftime('%Y-%m-%d %H:%M:%S') if customer.last_deal_time else None,
        'create_time': case.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if case.create_datetime else None,
        'update_time': case.update_datetime.strftime('%Y-%m-%d %H:%M:%S') if case.update_datetime else None,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_client_list(request):
    """
    Get client list
    GET /api/crm/client/list
    """
    try:
        user = request.user

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 20))
        status = request.query_params.get('status')
        sales_stage = request.query_params.get('sales_stage')
        keyword = request.query_params.get('keyword') or request.query_params.get('search')
        grade = request.query_params.get('grade')
        collection_category = request.query_params.get('collection_category')
        owner_user_id = request.query_params.get('owner_user_id')
        team_id = request.query_params.get('team_id')
        branch_id = request.query_params.get('branch_id')
        recycle_risk_level = request.query_params.get('recycle_risk_level')
        order_by = request.query_params.get('order_by', 'create_time')
        order_direction = request.query_params.get('order_direction', 'desc')

        use_case_view = False
        if sales_stage in [
            Customer.SALES_STAGE_CASE,
            Customer.SALES_STAGE_PAYMENT,
            Customer.SALES_STAGE_WON,
        ]:
            use_case_view = True
        if status in [
            Customer.STATUS_CASE,
            Customer.STATUS_PAYMENT,
            Customer.STATUS_WON,
        ]:
            use_case_view = True

        if use_case_view:
            queryset = CaseManagement.objects.filter(
                is_deleted=False,
                customer__isnull=False,
                customer__is_deleted=False,
            ).select_related('customer', 'customer__owner_user').prefetch_related('customer__handlers')
        else:
            queryset = Customer.objects.filter(is_deleted=False).select_related('owner_user').prefetch_related('handlers')

        role_level = getattr(user, 'role_level', None) or getattr(user, 'org_scope', None)
        if role_level == 'HQ':
            pass
        elif role_level == 'BRANCH':
            branch_id = getattr(user, 'branch_id', None) or getattr(user, 'dept_id', None)
            if branch_id:
                queryset = queryset.filter(customer__branch_id=branch_id) if use_case_view else queryset.filter(branch_id=branch_id)
        elif role_level == 'TEAM':
            team_id = getattr(user, 'team_id', None) or getattr(user, 'dept_id', None)
            if team_id:
                queryset = queryset.filter(customer__team_id=team_id) if use_case_view else queryset.filter(team_id=team_id)
        else:
            queryset = queryset.filter(handlers=user)

        if status:
            queryset = queryset.filter(status=status) if use_case_view else queryset.filter(status=status)

        if sales_stage:
            queryset = queryset.filter(sales_stage=sales_stage) if use_case_view else queryset.filter(sales_stage=sales_stage)

        if keyword:
            if use_case_view:
                queryset = queryset.filter(
                    Q(customer__name__icontains=keyword) |
                    Q(customer__contact_phone__icontains=keyword) |
                    Q(customer__contact_person__icontains=keyword) |
                    Q(case_name__icontains=keyword) |
                    Q(case_number__icontains=keyword)
                )
            else:
                queryset = queryset.filter(
                    Q(name__icontains=keyword) |
                    Q(contact_phone__icontains=keyword) |
                    Q(contact_person__icontains=keyword)
                )

        if grade:
            queryset = queryset.filter(customer__client_grade=grade) if use_case_view else queryset.filter(client_grade=grade)

        if collection_category:
            categories = [c.strip() for c in collection_category.split(',')]
            queryset = queryset.filter(customer__collection_category__in=categories) if use_case_view else queryset.filter(collection_category__in=categories)

        if owner_user_id:
            queryset = queryset.filter(handlers__id=owner_user_id)

        if team_id:
            queryset = queryset.filter(customer__team_id=team_id) if use_case_view else queryset.filter(team_id=team_id)

        if branch_id:
            queryset = queryset.filter(customer__branch_id=branch_id) if use_case_view else queryset.filter(branch_id=branch_id)

        if recycle_risk_level:
            queryset = queryset.filter(customer__recycle_risk_level=recycle_risk_level) if use_case_view else queryset.filter(recycle_risk_level=recycle_risk_level)

        if order_by == 'last_followup':
            if use_case_view:
                queryset = queryset.annotate(
                    last_followup_at=Max('customer__followups__create_datetime')
                ).order_by(f'-last_followup_at' if order_direction == 'desc' else 'last_followup_at')
            else:
                queryset = queryset.annotate(
                    last_followup_at=Max('followups__create_datetime')
                ).order_by(f'-last_followup_at' if order_direction == 'desc' else 'last_followup_at')
        elif order_by == 'last_visit':
            if use_case_view:
                queryset = queryset.annotate(
                    last_visit_at=Max('customer__visits__visit_time')
                ).order_by(f'-last_visit_at' if order_direction == 'desc' else 'last_visit_at')
            else:
                queryset = queryset.annotate(
                    last_visit_at=Max('visits__visit_time')
                ).order_by(f'-last_visit_at' if order_direction == 'desc' else 'last_visit_at')
        else:
            order_prefix = '-' if order_direction == 'desc' else ''
            queryset = queryset.order_by(f'{order_prefix}create_datetime')

        # 过滤 handlers 或 owner_user_id 时 JOIN 可能产生重复行，需 distinct
        if owner_user_id or (role_level not in ('HQ', 'BRANCH', 'TEAM') and not use_case_view):
            queryset = queryset.distinct()

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        results = list(queryset[start:end])

        rows = []
        if use_case_view:
            for case in results:
                row = _format_case_row(case, role_level)
                if row:
                    rows.append(row)
        else:
            for customer in results:
                rows.append(_format_customer_row(customer, role_level))

        return DetailResponse(data={
            'rows': rows,
            'total': total,
            'page': page,
            'pageSize': page_size
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"获取客户列表失败: {str(e)}", code=4000)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_case_source_list(request):
    """
    Get case source list
    GET /api/crm/client/case-source-list
    """
    try:
        user = request.user

        def _safe_int(value, default):
            try:
                return int(value)
            except Exception:
                return default

        page = _safe_int(request.query_params.get('page', 1), 1)
        page_size_raw = request.query_params.get('pageSize')
        if page_size_raw in (None, '', 'null', 'undefined'):
            page_size_raw = request.query_params.get('page_size')
        page_size = _safe_int(page_size_raw if page_size_raw is not None else 20, 20)
        if page <= 0:
            page = 1
        if page_size <= 0:
            page_size = 20
        keyword = request.query_params.get('keyword')
        grade = request.query_params.get('grade')
        collection_category = request.query_params.get('collection_category')
        owner_user_id = request.query_params.get('owner_user_id')
        team_id = request.query_params.get('team_id')
        branch_id = request.query_params.get('branch_id')
        recycle_risk_level = request.query_params.get('recycle_risk_level')
        status = request.query_params.get('status')
        sales_stage = request.query_params.get('sales_stage')
        order_by = request.query_params.get('order_by', 'create_time')
        order_direction = request.query_params.get('order_direction', 'desc')

        queryset = Customer.objects.filter(is_deleted=False).select_related('owner_user').prefetch_related('handlers')

        # avoid failure if m2m table not migrated
        handlers_table_ready = True
        try:
            from django.db import connection
            handlers_table = Customer.handlers.through._meta.db_table
            handlers_table_ready = handlers_table in connection.introspection.table_names()
        except Exception:
            handlers_table_ready = True

        role_level = getattr(user, 'role_level', None) or getattr(user, 'org_scope', None)
        if role_level == 'HQ':
            pass
        elif role_level == 'BRANCH':
            branch_id = getattr(user, 'branch_id', None) or getattr(user, 'dept_id', None)
            if branch_id:
                queryset = queryset.filter(branch_id=branch_id)
        elif role_level == 'TEAM':
            team_id = getattr(user, 'team_id', None) or getattr(user, 'dept_id', None)
            if team_id:
                queryset = queryset.filter(team_id=team_id)
        else:
            if handlers_table_ready:
                queryset = queryset.filter(handlers=user)
            else:
                queryset = queryset.filter(owner_user=user)
            if role_level == 'SALES':
                queryset = queryset.exclude(status=Customer.STATUS_PUBLIC_POOL)

        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword) |
                Q(contact_phone__icontains=keyword) |
                Q(contact_person__icontains=keyword)
            )

        def _parse_multi_param(value):
            if value is None:
                return []
            if isinstance(value, (list, tuple)):
                raw = value
            else:
                raw = str(value).split(',')
            return [str(item).strip() for item in raw if str(item).strip()]

        grade_list = _parse_multi_param(grade)
        category_list = _parse_multi_param(collection_category)
        owner_list = _parse_multi_param(owner_user_id)
        team_list = _parse_multi_param(team_id)
        branch_list = _parse_multi_param(branch_id)
        risk_list = _parse_multi_param(recycle_risk_level)
        status_list = _parse_multi_param(status)
        sales_stage_list = _parse_multi_param(sales_stage)

        if grade_list:
            queryset = queryset.filter(client_grade__in=grade_list)

        if category_list:
            queryset = queryset.filter(collection_category__in=category_list)

        if owner_list:
            if handlers_table_ready:
                queryset = queryset.filter(handlers__id__in=owner_list)
            else:
                queryset = queryset.filter(owner_user_id__in=owner_list)

        if team_list:
            queryset = queryset.filter(team_id__in=team_list)

        if branch_list:
            queryset = queryset.filter(branch_id__in=branch_list)

        if risk_list:
            queryset = queryset.filter(recycle_risk_level__in=risk_list)

        if status_list or sales_stage_list:
            stage_q = Q()
            if status_list:
                stage_q |= Q(cases__status__in=status_list)
                stage_q |= Q(status__in=status_list)
            if sales_stage_list:
                stage_q |= Q(cases__sales_stage__in=sales_stage_list)
                stage_q |= Q(sales_stage__in=sales_stage_list)
            queryset = queryset.filter(stage_q)

        if order_by == 'last_followup':
            queryset = queryset.annotate(
                last_followup_at=Max('followups__create_datetime')
            ).order_by(f'-last_followup_at' if order_direction == 'desc' else 'last_followup_at')
        elif order_by == 'last_visit':
            queryset = queryset.annotate(
                last_visit_at=Max('visits__visit_time')
            ).order_by(f'-last_visit_at' if order_direction == 'desc' else 'last_visit_at')
        else:
            order_prefix = '-' if order_direction == 'desc' else ''
            queryset = queryset.order_by(f'{order_prefix}create_datetime')

        try:
            queryset = queryset.annotate(
                total_cases=Count('cases', filter=Q(cases__is_deleted=False), distinct=True),
                public_pool_count=Count(
                    'cases',
                    filter=Q(
                        cases__is_deleted=False
                    ) & (Q(cases__sales_stage=CaseManagement.SALES_STAGE_PUBLIC) | Q(cases__status=CaseManagement.STATUS_PUBLIC_POOL)),
                    distinct=True
                ),
                opportunity_count=Count(
                    'cases',
                    filter=Q(cases__is_deleted=False, cases__sales_stage=CaseManagement.SALES_STAGE_BLANK),
                    distinct=True
                ),
                followup_case_count=Count(
                    'cases',
                    filter=Q(cases__is_deleted=False, cases__sales_stage=CaseManagement.SALES_STAGE_MEETING),
                    distinct=True
                ),
                case_count=Count(
                    'cases',
                    filter=Q(
                        cases__is_deleted=False
                    ) & (Q(cases__sales_stage=CaseManagement.SALES_STAGE_CASE) | Q(cases__status=CaseManagement.STATUS_CASE)),
                    distinct=True
                ),
                payment_count=Count(
                    'cases',
                    filter=Q(
                        cases__is_deleted=False
                    ) & (Q(cases__sales_stage=CaseManagement.SALES_STAGE_PAYMENT) | Q(cases__status=CaseManagement.STATUS_PAYMENT)),
                    distinct=True
                ),
                won_count=Count(
                    'cases',
                    filter=Q(
                        cases__is_deleted=False
                    ) & (Q(cases__sales_stage=CaseManagement.SALES_STAGE_WON) | Q(cases__status=CaseManagement.STATUS_WON)),
                    distinct=True
                ),
            ).distinct()
        except Exception:
            queryset = queryset.distinct()

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        customers = list(queryset[start:end])

        rows = []
        for customer in customers:
            try:
                last_followup = FollowupRecord.objects.filter(customer=customer).order_by('-followup_time').first()
            except Exception:
                last_followup = FollowupRecord.objects.filter(client_id=customer.id).order_by('-followup_time').first()
            if last_followup and getattr(last_followup, 'followup_time', None):
                last_followup_at = last_followup.followup_time.strftime('%Y-%m-%d %H:%M:%S')
                last_followup_dt = last_followup.followup_time
            else:
                last_followup_at = last_followup.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if last_followup else None
                last_followup_dt = last_followup.create_datetime if last_followup else None

            try:
                last_visit = VisitRecord.objects.filter(customer=customer).order_by('-visit_time').first()
            except Exception:
                last_visit = VisitRecord.objects.filter(client_id=customer.id).order_by('-visit_time').first()
            last_visit_at = last_visit.visit_time.strftime('%Y-%m-%d %H:%M:%S') if last_visit else None
            last_visit_dt = last_visit.visit_time if last_visit else None

            next_plan_at = None
            try:
                try:
                    next_plan = FollowupRecord.objects.filter(
                        customer=customer,
                        next_followup_time__isnull=False
                    ).order_by('next_followup_time').first()
                except Exception:
                    next_plan = FollowupRecord.objects.filter(
                        client_id=customer.id,
                        next_followup_time__isnull=False
                    ).order_by('next_followup_time').first()
                if next_plan and getattr(next_plan, 'next_followup_time', None):
                    next_plan_at = next_plan.next_followup_time.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                next_plan_at = None

            collection_categories = []
            if customer.collection_category:
                try:
                    if isinstance(customer.collection_category, str):
                        collection_categories = json.loads(customer.collection_category) if customer.collection_category.startswith('[') else [customer.collection_category]
                    else:
                        collection_categories = customer.collection_category
                except Exception:
                    collection_categories = [customer.collection_category] if customer.collection_category else []

            owner_name = customer.owner_user_name
            if not owner_name and getattr(customer, "owner_user", None):
                owner_name = customer.owner_user.name or customer.owner_user.username
            handler_ids, handler_names, handler_list = _get_handler_payload(customer)

            followups = list(_get_followup_queryset(customer))
            followup_count = len(followups)
            valid_followup_count = sum(
                1 for item in followups if _is_valid_followup(item, customer.sales_stage)
            )
            recycle_deadline = _resolve_recycle_deadline(customer, last_followup_dt, last_visit_dt)

            total_cases = getattr(customer, 'total_cases', 0) or 0
            public_pool_count = getattr(customer, 'public_pool_count', 0) or 0
            opportunity_count = getattr(customer, 'opportunity_count', 0) or 0
            followup_case_count = getattr(customer, 'followup_case_count', 0) or 0
            case_count = getattr(customer, 'case_count', 0) or 0
            payment_count = getattr(customer, 'payment_count', 0) or 0
            won_count = getattr(customer, 'won_count', 0) or 0

            if total_cases == 0:
                stage = customer.sales_stage
                status_value = customer.status
                if status_value == Customer.STATUS_PUBLIC_POOL or stage == Customer.SALES_STAGE_PUBLIC:
                    public_pool_count = 1
                elif status_value == Customer.STATUS_CASE or stage == Customer.SALES_STAGE_CASE:
                    case_count = 1
                elif status_value == Customer.STATUS_PAYMENT or stage == Customer.SALES_STAGE_PAYMENT:
                    payment_count = 1
                elif status_value == Customer.STATUS_WON or stage == Customer.SALES_STAGE_WON:
                    won_count = 1
                elif stage == Customer.SALES_STAGE_MEETING:
                    followup_case_count = 1
                else:
                    opportunity_count = 1

            rows.append({
                'id': customer.id,
                'customer_id': customer.id,
                'customer_name': customer.name,
                'client_name': customer.name,
                'status': customer.status,
                'sales_stage': customer.sales_stage,
                'contact_name': customer.contact_person,
                'mobile': customer.contact_phone,
                'email': customer.contact_email or '',
                'region': customer.address,
                'grade': customer.client_grade,
                'grade_source': customer.grade_source or 'ai',
                'category': customer.client_category,
                'collection_category': collection_categories,
                'collection_source': customer.collection_source or 'ai',
                'preservation_status': None,
                'court': None,
                'lawyer': None,
                'owner_user_id': customer.owner_user_id,
                'owner_user_name': owner_name,
                'handler_ids': handler_ids,
                'handler_names': handler_names,
                'handlers': handler_list,
                'org_scope': role_level if role_level else 'SELF',
                'team_id': customer.team_id,
                'branch_id': customer.branch_id,
                'team_name': None,
                'branch_name': None,
                'followup_count': followup_count,
                'valid_followup_count': valid_followup_count,
                'visit_count': customer.valid_visit_count,
                'valid_visit_count': customer.valid_visit_count,
                'last_followup_at': last_followup_at,
                'last_visit_at': last_visit_at,
                'next_plan_at': next_plan_at,
                'recycle_risk_level': customer.recycle_risk_level,
                'recycle_deadline': recycle_deadline.strftime('%Y-%m-%d') if recycle_deadline else None,
                'last_deal_time': customer.last_deal_time.strftime('%Y-%m-%d %H:%M:%S') if customer.last_deal_time else None,
                'create_time': customer.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if customer.create_datetime else None,
                'update_time': customer.update_datetime.strftime('%Y-%m-%d %H:%M:%S') if customer.update_datetime else None,
                'total_cases': total_cases,
                'public_pool_count': public_pool_count,
                'opportunity_count': opportunity_count,
                'followup_case_count': followup_case_count,
                'case_count': case_count,
                'payment_count': payment_count,
                'won_count': won_count,
            })

        return DetailResponse(data={
            'rows': rows,
            'total': total,
            'page': page,
            'pageSize': page_size
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"获取案源清单失败: {str(e)}", code=4000)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def get_client_detail(request, id):
    """
    获取客户详情或更新客户信息
    GET /api/crm/client/{id} - 获取详情
    PUT /api/crm/client/{id} - 更新信息
    """
    if request.method == 'PUT':
        # 更新客户信息
        try:
            user = request.user
            
            try:
                client = Customer.objects.get(id=id, is_deleted=False)
            except Customer.DoesNotExist:
                return ErrorResponse(msg="客户不存在", code=4004)
            
            # 权限检查：销售只能更新自己的客户
            role_level = getattr(user, 'role_level', None)
            if role_level not in ['HQ', 'BRANCH', 'TEAM']:
                if not _has_handler(client, user):
                    return ErrorResponse(msg="无权更新该客户", code=4003)
            
            data = request.data
            
            # 更新字段
            if 'client_name' in data:
                client.name = data['client_name']
            if 'contact_name' in data:
                client.contact_person = data['contact_name']
            if 'mobile' in data:
                client.contact_phone = data['mobile']
            # 处理地址字段：优先使用拼接后的region，如果没有则使用province/city/district/detail_address拼接
            if 'region' in data:
                client.address = data['region']
            elif 'province' in data or 'city' in data or 'district' in data or 'detail_address' in data:
                # 拼接省市区和详细地址
                address_parts = []
                if data.get('province'):
                    address_parts.append(data['province'])
                if data.get('city'):
                    address_parts.append(data['city'])
                if data.get('district'):
                    address_parts.append(data['district'])
                if data.get('detail_address'):
                    address_parts.append(data['detail_address'])
                if address_parts:
                    client.address = ' '.join(address_parts)
            if 'grade' in data:
                client.client_grade = data['grade']
                client.grade_source = data.get('grade_source', 'manual')
            if 'category' in data:
                if not data['category']:
                    return ErrorResponse(msg="请选择客户类别", code=4001)
                client.client_category = data['category']
            if 'last_deal_time' in data:
                parsed_last_deal = _parse_datetime_value(data.get('last_deal_time'))
                if data.get('last_deal_time') and not parsed_last_deal:
                    return ErrorResponse(msg="最后成交时间格式错误", code=4002)
                client.last_deal_time = parsed_last_deal
            if 'collection_category' in data:
                collection_value = data.get('collection_category')
                if isinstance(collection_value, (list, tuple)):
                    client.collection_category = json.dumps(collection_value, ensure_ascii=False)
                else:
                    client.collection_category = collection_value
                client.collection_source = data.get('collection_source', 'manual')
            
            client.modifier = user.name or str(user.id)
            client.save()
            
            return DetailResponse(data={
                'id': client.id,
                'update_time': client.update_datetime.strftime('%Y-%m-%d %H:%M:%S') if client.update_datetime else None
            }, msg='更新成功')
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ErrorResponse(msg=f"更新客户失败: {str(e)}", code=4000)
    
    # GET 方法：获取客户详情
    try:
        user = request.user
        
        try:
            client = Customer.objects.get(id=id, is_deleted=False)
        except Customer.DoesNotExist:
            return ErrorResponse(msg="客户不存在", code=4004)
        
        # 权限检查：销售只能查看自己的客户
        role_level = getattr(user, 'role_level', None)
        if role_level not in ['HQ', 'BRANCH', 'TEAM']:
            if not _has_handler(client, user):
                return ErrorResponse(msg="无权查看该客户", code=4003)
        
        # 获取最近跟进时间（根据迁移文件，可能使用 client_id 或 customer 字段）
        try:
            last_followup = FollowupRecord.objects.filter(customer=client).order_by('-followup_time').first()
        except Exception:
            last_followup = FollowupRecord.objects.filter(client_id=client.id).order_by('-followup_time').first()
        if last_followup and getattr(last_followup, 'followup_time', None):
            last_followup_at = last_followup.followup_time.strftime('%Y-%m-%d %H:%M:%S')
            last_followup_dt = last_followup.followup_time
        else:
            last_followup_at = last_followup.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if last_followup else None
            last_followup_dt = last_followup.create_datetime if last_followup else None
        
        # 获取最近拜访时间（根据迁移文件，可能使用 client_id 或 customer 字段）
        try:
            last_visit = VisitRecord.objects.filter(customer=client).order_by('-visit_time').first()
        except:
            # 如果 customer 字段不存在，尝试使用 client_id
            last_visit = VisitRecord.objects.filter(client_id=client.id).order_by('-visit_time').first()
        last_visit_at = last_visit.visit_time.strftime('%Y-%m-%d %H:%M:%S') if last_visit else None
        last_visit_dt = last_visit.visit_time if last_visit else None
        
        # 获取下次计划时间（根据迁移文件，可能没有 next_plan_at 字段）
        # 使用 try-except 处理字段不存在的情况
        next_plan_at = None
        try:
            try:
                next_plan = FollowupRecord.objects.filter(
                    customer=client,
                    next_followup_time__isnull=False
                ).order_by('next_followup_time').first()
            except Exception:
                next_plan = FollowupRecord.objects.filter(
                    client_id=client.id,
                    next_followup_time__isnull=False
                ).order_by('next_followup_time').first()
            if next_plan and getattr(next_plan, 'next_followup_time', None):
                next_plan_at = next_plan.next_followup_time.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            next_plan_at = None
        
        # 解析催收类别
        collection_categories = []
        if client.collection_category:
            try:
                if isinstance(client.collection_category, str):
                    collection_categories = json.loads(client.collection_category) if client.collection_category.startswith('[') else [client.collection_category]
                else:
                    collection_categories = client.collection_category
            except:
                collection_categories = [client.collection_category] if client.collection_category else []
        
        owner_name = client.owner_user_name
        if not owner_name and getattr(client, "owner_user", None):
            owner_name = client.owner_user.name or client.owner_user.username
        handler_ids, handler_names, handler_list = _get_handler_payload(client)

        followups = list(_get_followup_queryset(client))
        followup_count = len(followups)
        valid_followup_count = sum(
            1 for item in followups if _is_valid_followup(item, client.sales_stage)
        )
        recycle_deadline = _resolve_recycle_deadline(client, last_followup_dt, last_visit_dt)

        # 解析地址字段：尝试从address中解析出province/city/district/detail_address
        province = ''
        city = ''
        district = ''
        detail_address = ''
        
        if client.address:
            # 按空格分割地址
            address_parts = client.address.split(' ')
            
            # 处理不同格式的地址
            if len(address_parts) == 1:
                # 只有一部分，可能是完整地址，尝试解析
                full_addr = address_parts[0]
                # 尝试提取省市
                if '市' in full_addr:
                    # 找到第一个"市"的位置
                    city_idx = full_addr.find('市')
                    province = full_addr[:city_idx + 1]  # 包含"市"
                    remaining = full_addr[city_idx + 1:]
                    # 尝试提取区
                    if '区' in remaining:
                        district_idx = remaining.find('区')
                        district = remaining[:district_idx + 1]  # 包含"区"
                        detail_address = remaining[district_idx + 1:]
                    else:
                        detail_address = remaining
                else:
                    province = full_addr
            elif len(address_parts) == 2:
                # 两部分：可能是 "省市 区" 或 "省 市"
                first = address_parts[0]
                second = address_parts[1]
                if '市' in first:
                    # 第一部分包含市，可能是"北京市市辖区"
                    if first.endswith('市辖区'):
                        province = first[:-3]
                        city = '市辖区'
                        district = second
                    elif first.endswith('市'):
                        province = first
                        if '区' in second:
                            district = second
                        else:
                            city = second
                    else:
                        province = first
                        district = second
                else:
                    province = first
                    if '区' in second:
                        district = second
                    else:
                        city = second
            elif len(address_parts) == 3:
                # 三部分：可能是 "省市 区 详细地址" 或 "省 市 区"
                first = address_parts[0]
                second = address_parts[1]
                third = address_parts[2]
                
                if '市' in first:
                    # 第一部分包含市
                    if first.endswith('市辖区'):
                        province = first[:-3]
                        city = '市辖区'
                        district = second
                        detail_address = third
                    elif first.endswith('市'):
                        province = first
                        if '区' in second:
                            district = second
                            detail_address = third
                        else:
                            city = second
                            district = third
                    else:
                        province = first
                        district = second
                        detail_address = third
                else:
                    province = first
                    if '市' in second:
                        city = second
                        district = third
                    else:
                        district = second
                        detail_address = third
            elif len(address_parts) >= 4:
                # 四部分或更多：标准格式 "省 市 区 详细地址"
                province = address_parts[0]
                city = address_parts[1]
                district = address_parts[2]
                detail_address = ' '.join(address_parts[3:])
        

        case_queryset = CaseManagement.objects.filter(
            customer=client,
            is_deleted=False,
        ).order_by('-create_datetime')
        case_stats = {
            'total': case_queryset.count(),
            'follow_up': case_queryset.filter(status=CaseManagement.STATUS_FOLLOW_UP).count(),
            'case': case_queryset.filter(status=CaseManagement.STATUS_CASE).count(),
            'payment': case_queryset.filter(status=CaseManagement.STATUS_PAYMENT).count(),
            'won': case_queryset.filter(status=CaseManagement.STATUS_WON).count(),
        }
        case_rows = []
        for case in case_queryset:
            case_rows.append({
                'id': case.id,
                'case_name': case.case_name,
                'case_number': case.case_number,
                'case_type': case.case_type,
                'status': case.status,
                'sales_stage': case.sales_stage,
                'create_time': case.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if case.create_datetime else None,
                'update_time': case.update_datetime.strftime('%Y-%m-%d %H:%M:%S') if case.update_datetime else None,
            })

        data = {
            'id': client.id,
            'status': client.status,
            'sales_stage': client.sales_stage,
            'client_name': client.name,
            'contact_name': client.contact_person,
            'mobile': client.contact_phone,
            'region': client.address,  # 保留region字段以兼容旧代码
            'province': province,
            'city': city,
            'district': district,
            'detail_address': detail_address,
            'source_channel': client.source_channel,
            'referrer': client.referrer,
            'demand_summary': client.remark,  # TODO: 确认字段映射
            'grade': client.client_grade,
            'grade_source': client.grade_source or 'ai',
            'category': client.client_category,
            'collection_category': collection_categories,
            'collection_source': client.collection_source or 'ai',
            'preservation_status': None,  # TODO: 从模型获取
            'court': None,  # TODO: 从模型获取
            'lawyer': None,  # TODO: 从模型获取
            'owner_user_id': client.owner_user_id,
            'owner_user_name': owner_name,
            'handler_ids': handler_ids,
            'handler_names': handler_names,
            'handlers': handler_list,
            'org_scope': role_level if role_level else 'SELF',
            'team_id': client.team_id,
            'branch_id': client.branch_id,
            'team_name': None,  # TODO: 从团队表获取
            'branch_name': None,  # TODO: 从分所表获取
            'followup_count': followup_count,
            'valid_followup_count': valid_followup_count,
            'visit_count': client.valid_visit_count,  # 暂时使用 valid_visit_count，TODO: 需要添加 visit_count 字段或计算
            'valid_visit_count': client.valid_visit_count,
            'last_followup_at': last_followup_at,
            'last_visit_at': last_visit_at,
            'next_plan_at': next_plan_at,
            'recycle_risk_level': client.recycle_risk_level,
            'recycle_deadline': recycle_deadline.strftime('%Y-%m-%d') if recycle_deadline else None,
            'last_deal_time': client.last_deal_time.strftime('%Y-%m-%d %H:%M:%S') if client.last_deal_time else None,
            'ai_tags': {},  # TODO: AI tags placeholder
            'cases': case_rows,
            'case_statistics': case_stats,  # TODO: 从模型获取 AI 标记信息
            'create_time': client.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if client.create_datetime else None,
            'update_time': client.update_datetime.strftime('%Y-%m-%d %H:%M:%S') if client.update_datetime else None,
        }
        
        return DetailResponse(data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"获取客户详情失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_client(request):
    """
    创建客户/线索
    POST /api/crm/client
    """
    try:
        user = request.user
        data = request.data

        role_level = getattr(user, "role_level", None) or getattr(user, "org_scope", None)

        category_value = data.get("category")
        if not category_value:
            return ErrorResponse(msg="请选择客户类别", code=4001)

        owner_user = user
        owner_user_id = data.get("owner_user_id")
        handler_ids = data.get("handler_ids") or data.get("owner_user_ids")
        if handler_ids:
            if isinstance(handler_ids, str):
                handler_ids = [item for item in handler_ids.split(",") if str(item).strip()]
            if not isinstance(handler_ids, (list, tuple)):
                handler_ids = [handler_ids]
            handler_ids = [int(x) for x in handler_ids if str(x).isdigit()]
            if handler_ids:
                owner_user = Users.objects.get(id=handler_ids[0])
        elif owner_user_id:
            owner_user = Users.objects.get(id=owner_user_id)

        # 处理地址字段：优先使用拼接后的region，如果没有则使用province/city/district/detail_address拼接
        address_value = data.get("region")
        address_parts = []
        if not address_value:
            # 拼接省市区和详细地址
            if data.get("province"):
                address_parts.append(data["province"])
            if data.get("city"):
                address_parts.append(data["city"])
            if data.get("district"):
                address_parts.append(data["district"])
            if data.get("detail_address"):
                address_parts.append(data["detail_address"])
        if address_parts:
            address_value = " ".join(address_parts)

        last_deal_time_value = _parse_datetime_value(data.get("last_deal_time"))
        if data.get("last_deal_time") and not last_deal_time_value:
            return ErrorResponse(msg="最后成交时间格式错误", code=4002)
        
        base_fields = dict(
            name=data.get("client_name"),
            contact_person=data.get("contact_name"),
            contact_phone=data.get("mobile"),
            address=address_value,
            source_channel=data.get("source_channel"),
            referrer=data.get("referrer"),
            remark=data.get("demand_summary"),
            client_grade=data.get("grade"),
            grade_source="manual" if data.get("grade") else "ai",
            client_category=category_value,
            last_deal_time=last_deal_time_value,
            collection_category=(
                json.dumps(data.get("collection_category"), ensure_ascii=False)
                if isinstance(data.get("collection_category"), (list, tuple))
                else data.get("collection_category")
            ),
            collection_source="manual" if data.get("collection_category") else "ai",
            status=Customer.STATUS_PUBLIC_POOL,
            owner_user=owner_user,
            owner_user_name=owner_user.name or owner_user.username,
            team_id=CustomerService._derive_team_id(owner_user),
            branch_id=CustomerService._derive_branch_id(owner_user),
            creator=user,
            modifier=user.name or str(user.id),
        )

        # SALES 新增线索：先创建草稿客户（软删除）+ 审批任务，避免未审批数据直接出现在列表
        if role_level == "SALES":
            client = Customer.objects.create(**base_fields, is_deleted=True)
            if handler_ids:
                CustomerService.set_handlers(client, handler_ids, primary_id=handler_ids[0], mode="replace")
            CaseManagement.objects.create(
                case_number=generate_case_number(),
                case_name=f"{client.name}案件",
                case_type="other",
                case_status="待处理",
                status=CaseManagement.STATUS_PUBLIC_POOL,
                sales_stage=CaseManagement.SALES_STAGE_PUBLIC,
                customer=client,
                owner_user=client.owner_user,
                owner_user_name=client.owner_user_name,
                is_deleted=True,
            )
            task = ApprovalService.create_task(
                applicant=user,
                approval_type="LEAD_CREATE",
                customer=client,
                related_data={"form": dict(data), "handler_ids": handler_ids or []},
            )
            return DetailResponse(
                data={
                    "id": client.id,
                    "client_name": client.name,
                    "create_time": client.create_datetime.strftime("%Y-%m-%d %H:%M:%S")
                    if client.create_datetime
                    else None,
                    "approval_id": f"approval_{task.id}",
                    "status": "pending",
                },
                msg="提交成功，等待审批",
            )

        # 管理/团队角色：直接创建客户
        client = Customer.objects.create(**base_fields, is_deleted=False)
        if handler_ids:
            CustomerService.set_handlers(client, handler_ids, primary_id=handler_ids[0], mode="replace")
        CaseManagement.objects.create(
            case_number=generate_case_number(),
            case_name=f"{client.name}案件",
            case_type="other",
            case_status="待处理",
            status=CaseManagement.STATUS_PUBLIC_POOL,
            sales_stage=CaseManagement.SALES_STAGE_PUBLIC,
            customer=client,
            owner_user=client.owner_user,
            owner_user_name=client.owner_user_name,
            is_deleted=False,
        )
        return DetailResponse(
            data={
                "id": client.id,
                "client_name": client.name,
                "create_time": client.create_datetime.strftime("%Y-%m-%d %H:%M:%S")
                if client.create_datetime
                else None,
            },
            msg="创建成功",
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"创建客户失败: {str(e)}", code=4000)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_owner_customers(request):
    """
    Get owner customers
    GET /api/crm/client/owner-customers
    """
    try:
        user = request.user
        keyword = request.query_params.get('keyword')

        queryset = Customer.objects.filter(
            is_deleted=False,
            handlers=user,
            status__in=[
                Customer.STATUS_FOLLOW_UP,
                Customer.STATUS_CASE,
                Customer.STATUS_PAYMENT,
                Customer.STATUS_WON,
            ],
        )

        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword) |
                Q(contact_phone__icontains=keyword) |
                Q(contact_person__icontains=keyword)
            )

        rows = []
        for customer in queryset.order_by('-update_datetime')[:50]:
            rows.append({
                'id': customer.id,
                'name': customer.name,
                'contact_person': customer.contact_person,
                'contact_phone': customer.contact_phone,
                'address': customer.address,
                'status': customer.status,
                'sales_stage': customer.sales_stage,
            })

        return DetailResponse(data=rows)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"获取我的客户失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_client_with_case(request):
    """
    Create client with case
    POST /api/crm/client/create-with-case
    """
    try:
        user = request.user
        data = request.data
        customer_id = data.get('customer_id')
        if not customer_id:
            return ErrorResponse(msg="缺少客户ID", code=4001)

        customer = Customer.objects.filter(id=customer_id, is_deleted=False).first()
        if not customer:
            return ErrorResponse(msg="客户不存在", code=4004)

        if not _has_handler(customer, user):
            return ErrorResponse(msg="无权限为该客户新增案件", code=4003)

        if customer.status == Customer.STATUS_PUBLIC_POOL:
            return ErrorResponse(msg="客户在公海池，无法新增案件", code=4005)

        project_name = data.get('project_name')
        debt_subject = data.get('debt_subject')
        project_background = data.get('project_background')
        remark = data.get('remark')
        case_description = data.get('case_description')

        extra_parts = []
        if project_name:
            extra_parts.append(f"项目名称：{project_name}")
        if debt_subject:
            extra_parts.append(f"欠付标的：{debt_subject}")
        if project_background:
            extra_parts.append(f"项目背景：{project_background}")
        if remark:
            extra_parts.append(f"备注：{remark}")
        if extra_parts:
            extra_text = "\n".join(extra_parts)
            case_description = f"{extra_text}\n{case_description}" if case_description else extra_text

        case_name = data.get('case_name')
        case_type = data.get('case_type')
        if not case_name:
            if case_type:
                case_name = f"{customer.name}-{case_type}"
            else:
                case_name = f"{customer.name}案件"

        filing_date = data.get('filing_date')
        parsed_filing_date = None
        if filing_date:
            parsed = parse_datetime(str(filing_date))
            if parsed:
                parsed_filing_date = parsed.date()
            else:
                try:
                    parsed_filing_date = datetime.strptime(str(filing_date), '%Y-%m-%d').date()
                except Exception:
                    parsed_filing_date = None

        case = CaseManagement.objects.create(
            case_number=generate_case_number(),
            case_name=case_name,
            case_type=case_type or 'other',
            case_status=data.get('case_status') or '待处理',
            case_description=case_description,
            plaintiff_name=data.get('plaintiff_name'),
            plaintiff_credit_code=data.get('plaintiff_credit_code'),
            plaintiff_address=data.get('plaintiff_address'),
            plaintiff_legal_representative=data.get('plaintiff_legal_representative'),
            defendant_name=data.get('defendant_name'),
            defendant_credit_code=data.get('defendant_credit_code'),
            defendant_address=data.get('defendant_address'),
            defendant_legal_representative=data.get('defendant_legal_representative'),
            contract_amount=data.get('contract_amount'),
            lawyer_fee=data.get('lawyer_fee'),
            litigation_request=data.get('litigation_request'),
            facts_and_reasons=data.get('facts_and_reasons'),
            jurisdiction=data.get('jurisdiction'),
            petitioner=data.get('petitioner'),
            draft_person=data.get('draft_person'),
            filing_date=parsed_filing_date,
            status=CaseManagement.STATUS_FOLLOW_UP,
            sales_stage=CaseManagement.SALES_STAGE_BLANK,
            customer=customer,
            owner_user=customer.owner_user,
            owner_user_name=customer.owner_user_name,
        )
        try:
            handler_ids = list(customer.handlers.values_list("id", flat=True))
            if handler_ids:
                case.handlers.set(handler_ids)
        except Exception:
            pass

        return DetailResponse(data={
            'customer_id': customer.id,
            'case_id': case.id,
        }, msg='创建成功')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"新增案件失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_client(request, id):
    """
    申领公海客户
    POST /api/crm/client/{id}/apply
    """
    try:
        user = request.user
        
        # 权限检查：只有 SALES、TEAM 和 BRANCH 可以申领（HQ不能申领）
        role_level = getattr(user, 'role_level', None)
        if role_level == 'HQ':
            return ErrorResponse(msg="HQ 角色不能申领", code=4003)
        
        try:
            client = Customer.objects.get(id=id, is_deleted=False)
        except Customer.DoesNotExist:
            return ErrorResponse(msg="客户不存在", code=4004)
        
        # 检查客户状态
        if client.status != Customer.STATUS_PUBLIC_POOL:
            return ErrorResponse(msg="只能申领公海客户", code=4005)
        
        # 创建审批任务
        reason = request.data.get('reason', '')
        related_data = {
            'client_id': str(client.id),
            'name': client.name,
            'reason': reason
        }
        
        task = ApprovalService.create_task(
            applicant=user,
            approval_type='LEAD_CLAIM',
            customer=client,
            related_data=related_data
        )
        
        return DetailResponse(data={
            'apply_id': f'apply_{task.id}',
            'status': 'pending'
        }, msg='申领成功，等待审批')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"申领客户失败: {str(e)}", code=4000)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def apply_handover(request):
    """
    申请客户转交（创建审批任务）
    POST /api/crm/client/handover
    """
    try:
        user = request.user
        data = request.data

        client_id = data.get("client_id")
        to_owner_ids = data.get("to_owner_ids") or data.get("to_owner_id") or data.get("to_user_id")
        transfer_mode = (data.get("transfer_mode") or data.get("handover_mode") or "append").lower()
        reason = (data.get("reason") or "").strip()

        if not client_id:
            return ErrorResponse(msg="缺少客户ID", code=4001)
        if not to_owner_ids:
            return ErrorResponse(msg="请选择目标经办人", code=4001)
        if not reason:
            return ErrorResponse(msg="请填写转交原因", code=4001)

        try:
            client = Customer.objects.get(id=client_id, is_deleted=False)
        except Customer.DoesNotExist:
            return ErrorResponse(msg="客户不存在", code=4004)

        # 仅当前经办人（或管理）可发起转交
        if not getattr(user, "role_level", None) in ["HQ", "BRANCH", "TEAM"]:
            if not _has_handler(client, user):
                return ErrorResponse(msg="只有当前经办人可以发起转交", code=4003)

        if isinstance(to_owner_ids, str):
            to_owner_ids = [item for item in to_owner_ids.split(",") if str(item).strip()]
        if not isinstance(to_owner_ids, (list, tuple)):
            to_owner_ids = [to_owner_ids]
        to_owner_ids = [int(x) for x in to_owner_ids if str(x).isdigit()]
        if not to_owner_ids:
            return ErrorResponse(msg="请选择目标经办人", code=4001)
        if transfer_mode not in ["append", "replace"]:
            transfer_mode = "append"

        target_users = list(Users.objects.filter(id__in=to_owner_ids, is_active=True))
        if not target_users:
            return ErrorResponse(msg="目标经办人不存在", code=4004)

        # 计算当前经办人和目标经办人的分所，用于判断是否为同分所转交
        from_branch_id = client.branch_id or CustomerService._derive_branch_id(client.owner_user)  # type: ignore[attr-defined]
        to_branch_ids = [CustomerService._derive_branch_id(item) for item in target_users]

        # 记录转交日志
        transfer_log = TransferLog.objects.create(
            customer=client,
            from_user=client.owner_user,
            to_user=target_users[0],
            transfer_reason=reason,
            status="pending",
            creator=user,
            modifier=user.name or str(user.id),
        )

        # 同分所内转交：不走审批，直接生效
        if from_branch_id and all(str(from_branch_id) == str(item) for item in to_branch_ids if item):
            primary_id = client.owner_user_id if transfer_mode == "append" else (to_owner_ids[0] if to_owner_ids else None)
            CustomerService.set_handlers(client, to_owner_ids, primary_id=primary_id, mode=transfer_mode)
            transfer_log.status = "approved"
            transfer_log.save(update_fields=["status"])

            return DetailResponse(
                data={
                    "handover_id": f"handover_{transfer_log.id}",
                    "status": "approved",
                    "owner_user_id": client.owner_user_id,
                    "owner_user_name": client.owner_user_name,
                    "handler_ids": list(client.handlers.values_list("id", flat=True)),
                },
                msg="转交成功",
            )

        # 跨分所转交：创建审批任务，等待审批
        related_data = {
            "client_id": str(client.id),
            "from_user": {
                "id": str(client.owner_user_id or ""),
                "name": client.owner_user_name or "",
            },
            "to_users": [
                {
                    "id": str(item.id),
                    "name": item.name or item.username,
                }
                for item in target_users
            ],
            "transfer_mode": transfer_mode,
            "reason": reason,
            "transfer_log_id": transfer_log.id,
        }

        task = ApprovalService.create_task(
            applicant=user,
            approval_type="HANDOVER",
            customer=client,
            related_data=related_data,
        )

        transfer_log.approval_task = task
        transfer_log.save(update_fields=["approval_task"])

        return DetailResponse(
            data={"handover_id": f"handover_{transfer_log.id}", "status": "pending"},
            msg="申请成功，等待审批",
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"提交转交申请失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_client(request, id):
    """
    分配客户（管理权限）
    POST /api/crm/client/{id}/assign
    """
    try:
        user = request.user
        
        # 权限检查：只有管理角色可以分配
        role_level = getattr(user, 'role_level', None)
        if role_level not in ['HQ', 'BRANCH', 'TEAM']:
            return ErrorResponse(msg="只有管理角色可以分配客户", code=4003)
        
        try:
            client = Customer.objects.get(id=id, is_deleted=False)
        except Customer.DoesNotExist:
            return ErrorResponse(msg="客户不存在", code=4004)
        
        data = request.data
        handler_ids = data.get("handler_ids") or data.get("owner_user_ids")
        owner_user_id = data.get('owner_user_id')
        target_user_role_level = data.get('target_user_role_level')
        
        if not handler_ids and not owner_user_id:
            return ErrorResponse(msg="请指定经办人", code=4001)
        
        # 校验：不能分配给 HQ 角色，但可以分配给 BRANCH（因为BRANCH也有销售职能）
        if target_user_role_level == 'HQ':
            return ErrorResponse(msg="不能分配给HQ角色，只能分配给销售人员（BRANCH/TEAM/SALES）", code=4005)
        
        if handler_ids:
            if isinstance(handler_ids, str):
                handler_ids = [item for item in handler_ids.split(",") if str(item).strip()]
            if not isinstance(handler_ids, (list, tuple)):
                handler_ids = [handler_ids]
            handler_ids = [int(x) for x in handler_ids if str(x).isdigit()]
        if not handler_ids and owner_user_id:
            handler_ids = [owner_user_id]

        try:
            owner_user = Users.objects.get(id=handler_ids[0])
        except Users.DoesNotExist:
            return ErrorResponse(msg="经办人不存在", code=4004)

        # 分配范围检查：只能在同分所内直接分配，跨分所请走转交审批
        manager_branch_id = getattr(user, "branch_id", None) or CustomerService._derive_branch_id(user)  # type: ignore[arg-type]
        target_branch_id = getattr(owner_user, "branch_id", None) or CustomerService._derive_branch_id(owner_user)

        if (
            manager_branch_id
            and target_branch_id
            and str(manager_branch_id) != str(target_branch_id)
        ):
            return ErrorResponse(msg="不能直接分配给其他分所，请使用转交并走审批流程", code=4005)

        # 分配客户（同分所内直接生效）
        CustomerService.set_handlers(client, handler_ids, primary_id=handler_ids[0], mode="replace")
        # assign_customer 会覆盖 handlers，仅保留单一经办人，已由 set_handlers 处理
        
        return DetailResponse(data={
            'id': client.id,
            'owner_user_id': client.owner_user_id,
            'owner_user_name': client.owner_user_name,
            'handler_ids': list(client.handlers.values_list("id", flat=True)),
        }, msg='分配成功')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"分配客户失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_client_apply(request, apply_id):
    """
    审批客户申领
    POST /api/crm/client/approve/{apply_id}
    """
    try:
        user = request.user
        
        # 权限检查：只有HQ角色可以审批
        role_level = getattr(user, 'role_level', None)
        if role_level != 'HQ':
            return ErrorResponse(msg="只有总所账号可以审批", code=4003)
        
        try:
            task = ApprovalTask.objects.get(id=apply_id.replace('apply_', ''))
        except (ApprovalTask.DoesNotExist, ValueError):
            return ErrorResponse(msg="审批任务不存在", code=4004)
        
        # 检查是否可以审批
        if not ApprovalService.can_approve(task, user):
            return ErrorResponse(msg="当前无权审批此任务", code=4003)
        
        data = request.data
        approved = data.get('approved', False)
        reject_reason = data.get('reject_reason', '')
        
        if approved:
            # 审批通过
            ApprovalService.advance_task(task, user, 'approve', reject_reason)
            
            # 如果所有审批都通过，执行申领操作
            if task.status == 'approved':
                client = task.related_customer
                if task.applicant:
                    CustomerService.set_handlers(
                        client,
                        [task.applicant.id],
                        primary_id=task.applicant.id,
                        mode="replace",
                    )
                client.status = Customer.STATUS_FOLLOW_UP
                client.sales_stage = client.calculate_sales_stage()
                client.save()
        else:
            # 审批驳回
            if not reject_reason:
                return ErrorResponse(msg="驳回时必须填写原因", code=4001)
            ApprovalService.advance_task(task, user, 'reject', reject_reason)
        
        return DetailResponse(data={
            'apply_id': f'apply_{task.id}',
            'status': task.status
        }, msg='审批成功')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"审批失败: {str(e)}", code=4000)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_client_visits(request, client_id):
    """
    获取客户拜访记录列表
    GET /api/crm/client/{client_id}/visit
    """
    try:
        user = request.user
        customer = Customer.objects.filter(id=client_id, is_deleted=False).first()
        if not customer:
            return ErrorResponse(msg="客户不存在或已删除", code=4004)
        if not can_access_customer(user, customer):
            return ErrorResponse(msg="无权访问该客户", code=403)

        # 查询拜访记录
        visits = VisitRecord.objects.filter(client_id=client_id).order_by('-visit_time')
        
        rows = []
        for visit in visits:
            rows.append({
                'id': visit.id,
                'client_id': visit.client_id,
                'visit_time': visit.visit_time.strftime('%Y-%m-%d %H:%M:%S') if visit.visit_time else None,
                'duration': getattr(visit, 'duration', 60),
                'value_info': getattr(visit, 'value_info', '') or getattr(visit, 'content', ''),
                'location_status': getattr(visit, 'location_status', 'success'),
                'address': getattr(visit, 'address', ''),
                'lng': getattr(visit, 'lng', None),
                'lat': getattr(visit, 'lat', None),
                'system_users': [],
                'system_users_info': [],
                'client_contacts': [],
                'client_contacts_info': [],
                'create_time': visit.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if visit.create_datetime else None,
            })
        
        return DetailResponse(data={
            'rows': rows,
            'total': len(rows)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"获取拜访记录失败: {str(e)}", code=4000)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_client_plans(request, client_id):
    """
    获取客户跟进计划列表
    GET /api/crm/client/{client_id}/plan
    """
    try:
        user = request.user
        customer = Customer.objects.filter(id=client_id, is_deleted=False).first()
        if not customer:
            return ErrorResponse(msg="客户不存在或已删除", code=4004)
        if not can_access_customer(user, customer):
            return ErrorResponse(msg="无权访问该客户", code=403)

        plans = CustomerPlan.objects.filter(
            customer_id=client_id,
            is_deleted=False
        ).order_by('-create_datetime')

        rows = []
        for plan in plans:
            rows.append({
                'id': plan.id,
                'client_id': plan.customer_id,
                'title': plan.title,
                'plan_type': plan.plan_type,
                'time_points': plan.time_points or [],
                'status': plan.status,
                'is_completed': plan.status == 'completed',
                'remind_method': plan.remind_method or 'system',
                'remind_advance': plan.remind_advance or 30,
                'sync_to_schedule': plan.sync_to_schedule,
                'extra_data': plan.extra_data or {},
                'create_time': plan.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if plan.create_datetime else None,
            })
        
        return DetailResponse(data={
            'rows': rows,
            'total': len(rows)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"获取跟进计划失败: {str(e)}", code=4000)


def _parse_datetime_string(value):
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = parse_datetime(str(value))
    if not parsed:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _map_followup_method(raw_type: str):
    if not raw_type:
        return "OTHER"
    lowered = str(raw_type).lower()
    mapping = {
        "phone": "PHONE",
        "wechat": "WECHAT",
        "email": "EMAIL",
        "meeting": "VISIT",
        "visit": "VISIT",
        "other": "OTHER",
    }
    return mapping.get(lowered, "OTHER")


def _format_followup_item(item: FollowupRecord):
    method_map = {
        "PHONE": "phone",
        "WECHAT": "wechat",
        "EMAIL": "email",
        "VISIT": "meeting",
        "OTHER": "other",
    }
    followup_time = item.followup_time
    return {
        "id": item.id,
        "client_id": item.client_id,
        "time": followup_time.strftime("%Y-%m-%d %H:%M:%S") if followup_time else None,
        "type": method_map.get(item.method, "other"),
        "method_other": item.method_other or "",
        "summary": item.summary or "",
        "conclusion": item.conclusion or "",
        "next_plan_at": item.next_followup_time.strftime("%Y-%m-%d %H:%M:%S") if item.next_followup_time else None,
        "attachments": item.attachments or [],
        "internal_participants": item.internal_participants or [],
        "customer_participants": item.customer_participants or [],
        "duration": item.duration,
        "location_status": item.location_status,
        "address": item.address,
        "lng": item.lng,
        "lat": item.lat,
        "creator_id": item.creator_id,
        "creator_name": getattr(item.creator, "name", None),
        "create_time": item.create_datetime.strftime("%Y-%m-%d %H:%M:%S") if item.create_datetime else None,
        "update_time": item.update_datetime.strftime("%Y-%m-%d %H:%M:%S") if item.update_datetime else None,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_client_followups(request, client_id):
    """
    获取客户跟进情况列表
    GET /api/crm/client/{client_id}/followup
    """
    try:
        user = request.user
        customer = Customer.objects.filter(id=client_id, is_deleted=False).first()
        if not customer:
            return ErrorResponse(msg="客户不存在或已删除", code=4004)
        if not can_access_customer(user, customer):
            return ErrorResponse(msg="无权访问该客户", code=403)

        followups = FollowupRecord.objects.filter(
            client_id=client_id,
            is_deleted=False
        ).order_by("-followup_time")

        rows = [_format_followup_item(item) for item in followups]
        return DetailResponse(data={
            "rows": rows,
            "total": len(rows)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"获取跟进情况失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_client_followup(request):
    """
    创建客户跟进情况
    POST /api/crm/client/followup
    """
    try:
        user = request.user
        data = request.data
        client_id = data.get("client_id")
        if not client_id:
            return ErrorResponse(msg="缺少客户ID", code=4001)
        customer = Customer.objects.filter(id=client_id, is_deleted=False).first()
        if not customer:
            return ErrorResponse(msg="客户不存在或已删除", code=4004)
        if not can_access_customer(user, customer):
            return ErrorResponse(msg="无权操作该客户", code=403)

        method = _map_followup_method(data.get("type") or data.get("followup_type"))
        followup_time = _parse_datetime_string(data.get("time") or data.get("followup_time")) or timezone.now()
        next_followup_time = _parse_datetime_string(data.get("next_plan_at") or data.get("next_followup_time"))

        summary = data.get("summary") or ""
        conclusion = data.get("conclusion") or ""
        content = data.get("content") or summary
        if conclusion:
            content = f"{summary}\n关键结论：{conclusion}".strip()

        record = FollowupRecord.objects.create(
            client_id=client_id,
            user_id=user.id,
            method=method,
            method_other=data.get("method_other"),
            summary=summary,
            conclusion=conclusion,
            content=content,
            duration=data.get("duration"),
            location_status=data.get("location_status") or "success",
            lng=data.get("lng"),
            lat=data.get("lat"),
            address=data.get("address"),
            internal_participants=data.get("internal_participants") or data.get("system_users") or [],
            customer_participants=data.get("customer_participants") or data.get("client_contacts") or [],
            attachments=data.get("attachments") or [],
            followup_time=followup_time,
            next_followup_time=next_followup_time,
            creator=user,
            modifier=user.name or str(user.id),
        )

        try:
            _sync_followup_stats(customer)
        except Exception:
            pass

        return DetailResponse(data=_format_followup_item(record))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"创建跟进情况失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_client_visit(request):
    """
    兼容旧接口：创建拜访记录（实际写入跟进记录）
    POST /api/crm/client/visit
    """
    try:
        user = request.user
        data = request.data
        client_id = data.get("client_id")
        if not client_id:
            return ErrorResponse(msg="缺少客户ID", code=4001)
        customer = Customer.objects.filter(id=client_id, is_deleted=False).first()
        if not customer:
            return ErrorResponse(msg="客户不存在或已删除", code=4004)
        if not can_access_customer(user, customer):
            return ErrorResponse(msg="无权操作该客户", code=403)

        followup_time = _parse_datetime_string(data.get("visit_time") or data.get("time")) or timezone.now()
        summary = data.get("summary") or data.get("value_info") or ""
        conclusion = data.get("conclusion") or ""
        content = data.get("content") or summary
        if conclusion:
            content = f"{summary}\n关键结论：{conclusion}".strip()

        record = FollowupRecord.objects.create(
            client_id=client_id,
            user_id=user.id,
            method="VISIT",
            summary=summary,
            conclusion=conclusion,
            content=content,
            duration=data.get("duration"),
            location_status=data.get("location_status") or "success",
            lng=data.get("lng"),
            lat=data.get("lat"),
            address=data.get("address"),
            internal_participants=data.get("system_users") or [],
            customer_participants=data.get("client_contacts") or [],
            attachments=data.get("attachments") or [],
            followup_time=followup_time,
            next_followup_time=_parse_datetime_string(data.get("next_plan_at")),
            creator=user,
            modifier=user.name or str(user.id),
        )

        try:
            _sync_followup_stats(customer)
        except Exception:
            pass

        return DetailResponse(data=_format_followup_item(record))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"创建拜访失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_client_plan(request):
    """
    创建客户计划
    POST /api/crm/client/plan
    """
    try:
        user = request.user
        data = request.data
        client_id = data.get("client_id")
        if not client_id:
            return ErrorResponse(msg="缺少客户ID", code=4001)
        customer = Customer.objects.filter(id=client_id, is_deleted=False).first()
        if not customer:
            return ErrorResponse(msg="客户不存在或已删除", code=4004)
        if not can_access_customer(user, customer):
            return ErrorResponse(msg="无权操作该客户", code=403)

        plan_type = data.get("plan_type") or "case_plan"
        title = data.get("title") or ""
        extra_data = data.get("extra_data") or {}

        if plan_type == "effective_case":
            extra_data = {
                "project_name": data.get("project_name") or extra_data.get("project_name"),
                "debt_subject": data.get("debt_subject") or extra_data.get("debt_subject"),
                "project_background": data.get("project_background") or extra_data.get("project_background"),
                "remark": data.get("remark") or extra_data.get("remark"),
                "case_name": data.get("case_name") or extra_data.get("case_name"),
                "case_type": data.get("case_type") or extra_data.get("case_type"),
                "case_description": data.get("case_description") or extra_data.get("case_description"),
                "plaintiff_name": data.get("plaintiff_name") or extra_data.get("plaintiff_name"),
                "plaintiff_credit_code": data.get("plaintiff_credit_code") or extra_data.get("plaintiff_credit_code"),
                "plaintiff_address": data.get("plaintiff_address") or extra_data.get("plaintiff_address"),
                "plaintiff_legal_representative": data.get("plaintiff_legal_representative") or extra_data.get("plaintiff_legal_representative"),
                "defendant_name": data.get("defendant_name") or extra_data.get("defendant_name"),
                "defendant_credit_code": data.get("defendant_credit_code") or extra_data.get("defendant_credit_code"),
                "defendant_address": data.get("defendant_address") or extra_data.get("defendant_address"),
                "defendant_legal_representative": data.get("defendant_legal_representative") or extra_data.get("defendant_legal_representative"),
                "contract_amount": data.get("contract_amount") or extra_data.get("contract_amount"),
                "lawyer_fee": data.get("lawyer_fee") or extra_data.get("lawyer_fee"),
                "litigation_request": data.get("litigation_request") or extra_data.get("litigation_request"),
                "facts_and_reasons": data.get("facts_and_reasons") or extra_data.get("facts_and_reasons"),
                "jurisdiction": data.get("jurisdiction") or extra_data.get("jurisdiction"),
                "filing_date": data.get("filing_date") or extra_data.get("filing_date"),
                "petitioner": data.get("petitioner") or extra_data.get("petitioner"),
                "draft_person": data.get("draft_person") or extra_data.get("draft_person"),
            }
            if not title:
                title = extra_data.get("project_name") or "有效案源"

        time_points = data.get("time_points") or []
        if isinstance(time_points, str):
            try:
                time_points = json.loads(time_points)
            except Exception:
                time_points = [time_points]

        plan = CustomerPlan.objects.create(
            customer_id=client_id,
            plan_type=plan_type,
            title=title,
            time_points=time_points,
            remind_method=data.get("remind_method"),
            remind_advance=data.get("remind_advance"),
            sync_to_schedule=bool(data.get("sync_to_schedule", True)),
            extra_data=extra_data,
            creator=user,
            modifier=user.name or str(user.id),
        )

        # 同步到日程
        if plan.sync_to_schedule and time_points:
            from customer_management.models import Schedule
            for point in time_points:
                start_time = _parse_datetime_string(point)
                if not start_time:
                    continue
                Schedule.objects.create(
                    title=plan.title,
                    description=json.dumps(plan.extra_data, ensure_ascii=False) if plan.extra_data else "",
                    schedule_type="reminder",
                    start_time=start_time,
                    status="pending",
                    priority="medium",
                    reminder_enabled=True,
                    reminder_time=plan.remind_advance or 30,
                    reminder_method=plan.remind_method or "system",
                    related_type="customer_plan",
                    related_id=plan.id,
                    creator=user,
                    modifier=user.name or str(user.id),
                )

        return DetailResponse(data={
            "id": plan.id,
            "client_id": plan.customer_id,
            "title": plan.title,
            "plan_type": plan.plan_type,
            "time_points": plan.time_points,
            "remind_method": plan.remind_method,
            "remind_advance": plan.remind_advance,
            "sync_to_schedule": plan.sync_to_schedule,
            "extra_data": plan.extra_data,
            "create_time": plan.create_datetime.strftime("%Y-%m-%d %H:%M:%S") if plan.create_datetime else None,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"创建计划失败: {str(e)}", code=4000)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_client_plan(request, plan_id):
    """
    更新客户计划
    PUT /api/crm/client/plan/{id}
    """
    try:
        user = request.user
        data = request.data
        plan = CustomerPlan.objects.filter(id=plan_id, is_deleted=False).first()
        if not plan:
            return ErrorResponse(msg="计划不存在", code=4004)
        customer = Customer.objects.filter(id=plan.customer_id, is_deleted=False).first()
        if not customer:
            return ErrorResponse(msg="客户不存在或已删除", code=4004)
        if not can_access_customer(user, customer):
            return ErrorResponse(msg="无权操作该客户", code=403)

        if "title" in data:
            plan.title = data.get("title") or plan.title
        if "plan_type" in data:
            plan.plan_type = data.get("plan_type") or plan.plan_type
        if "time_points" in data:
            time_points = data.get("time_points") or []
            if isinstance(time_points, str):
                try:
                    time_points = json.loads(time_points)
                except Exception:
                    time_points = [time_points]
            plan.time_points = time_points
        if "remind_method" in data:
            plan.remind_method = data.get("remind_method")
        if "remind_advance" in data:
            plan.remind_advance = data.get("remind_advance")
        if "sync_to_schedule" in data:
            plan.sync_to_schedule = bool(data.get("sync_to_schedule"))
        if "status" in data:
            plan.status = data.get("status") or plan.status
        if "extra_data" in data:
            plan.extra_data = data.get("extra_data") or {}

        plan.modifier = user.name or str(user.id)
        plan.save()

        return DetailResponse(data={
            "id": plan.id,
            "client_id": plan.customer_id,
            "title": plan.title,
            "plan_type": plan.plan_type,
            "time_points": plan.time_points,
            "status": plan.status,
            "extra_data": plan.extra_data,
            "update_time": plan.update_datetime.strftime("%Y-%m-%d %H:%M:%S") if plan.update_datetime else None,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"更新计划失败: {str(e)}", code=4000)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_collection_progress_list(request, client_id):
    """
    获取收款进度列表
    GET /api/crm/client/{client_id}/collection-progress
    """
    try:
        progress_list = CollectionProgress.objects.filter(
            customer_id=client_id,
            is_deleted=False
        ).order_by("-create_datetime")

        rows = []
        for item in progress_list:
            rows.append({
                "id": item.id,
                "client_id": item.customer_id,
                "total_amount": str(item.total_amount),
                "installment_count": item.installment_count,
                "mode": item.mode,
                "installments": item.installments or [],
                "remind_method": item.remind_method,
                "remind_advance": item.remind_advance,
                "sync_to_schedule": item.sync_to_schedule,
                "create_time": item.create_datetime.strftime("%Y-%m-%d %H:%M:%S") if item.create_datetime else None,
            })
        return DetailResponse(data={
            "rows": rows,
            "total": len(rows)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"获取收款进度失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_collection_progress(request):
    """
    创建收款进度
    POST /api/crm/client/collection-progress
    """
    try:
        user = request.user
        data = request.data
        client_id = data.get("client_id")
        if not client_id:
            return ErrorResponse(msg="缺少客户ID", code=4001)

        installments = data.get("installments") or []
        if isinstance(installments, str):
            try:
                installments = json.loads(installments)
            except Exception:
                installments = []

        progress = CollectionProgress.objects.create(
            customer_id=client_id,
            total_amount=data.get("total_amount") or 0,
            installment_count=data.get("installment_count") or 1,
            mode=data.get("mode") or "average",
            installments=installments,
            remind_method=data.get("remind_method"),
            remind_advance=data.get("remind_advance"),
            sync_to_schedule=bool(data.get("sync_to_schedule", True)),
            creator=user,
            modifier=user.name or str(user.id),
        )

        # 同步到日程
        if progress.sync_to_schedule and installments:
            from customer_management.models import Schedule
            for index, item in enumerate(installments, start=1):
                start_time = _parse_datetime_string(item.get("time"))
                if not start_time:
                    continue
                title = f"收款第{index}期 - {item.get('amount', '')}万"
                Schedule.objects.create(
                    title=title,
                    description=f"收款进度：{progress.total_amount}万，期数{progress.installment_count}",
                    schedule_type="reminder",
                    start_time=start_time,
                    status="pending",
                    priority="medium",
                    reminder_enabled=True,
                    reminder_time=progress.remind_advance or 30,
                    reminder_method=progress.remind_method or "system",
                    related_type="customer",
                    related_id=client_id,
                    creator=user,
                    modifier=user.name or str(user.id),
                )

        return DetailResponse(data={
            "id": progress.id,
            "client_id": progress.customer_id,
            "total_amount": str(progress.total_amount),
            "installment_count": progress.installment_count,
            "mode": progress.mode,
            "installments": progress.installments,
            "remind_method": progress.remind_method,
            "remind_advance": progress.remind_advance,
            "sync_to_schedule": progress.sync_to_schedule,
            "create_time": progress.create_datetime.strftime("%Y-%m-%d %H:%M:%S") if progress.create_datetime else None,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"创建收款进度失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_contract(request):
    """
    确认合同并创建案件
    POST /api/crm/client/contract
    """
    try:
        user = request.user
        data = request.data
        client_id = data.get("client_id")
        if not client_id:
            return ErrorResponse(msg="缺少客户ID", code=4001)

        customer = Customer.objects.filter(id=client_id, is_deleted=False).first()
        if not customer:
            return ErrorResponse(msg="客户不存在", code=4004)

        contract_no = data.get("contract_no") or ""
        if not contract_no:
            return ErrorResponse(msg="缺少合同编号", code=4001)

        contract_amount = data.get("amount") or data.get("contract_amount") or 0
        try:
            contract_amount = float(contract_amount)
        except Exception:
            return ErrorResponse(msg="合同金额格式错误", code=4002)
        term = data.get("term")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if not term and start_date and end_date:
            term = f"{start_date}至{end_date}"

        contract = None
        case = None
        case_payload = {
            "case_name": data.get("case_name"),
            "case_type": data.get("case_type"),
            "case_description": data.get("case_description"),
            "plaintiff_name": data.get("plaintiff_name"),
            "plaintiff_credit_code": data.get("plaintiff_credit_code"),
            "plaintiff_address": data.get("plaintiff_address"),
            "plaintiff_legal_representative": data.get("plaintiff_legal_representative"),
            "defendant_name": data.get("defendant_name"),
            "defendant_credit_code": data.get("defendant_credit_code"),
            "defendant_address": data.get("defendant_address"),
            "defendant_legal_representative": data.get("defendant_legal_representative"),
            "contract_amount": contract_amount,
            "lawyer_fee": data.get("lawyer_fee"),
            "litigation_request": data.get("litigation_request"),
            "facts_and_reasons": data.get("facts_and_reasons"),
            "jurisdiction": data.get("jurisdiction"),
            "filing_date": data.get("filing_date"),
            "petitioner": data.get("petitioner"),
            "draft_person": data.get("draft_person"),
        }

        effective_case = CustomerPlan.objects.filter(
            customer_id=client_id,
            plan_type="effective_case",
            is_deleted=False
        ).order_by("-create_datetime").first()

        with transaction.atomic():
            contract = Contract.objects.create(
                customer=customer,
                contract_no=contract_no,
                amount=contract_amount,
                term=term or "",
                service_type=data.get("service_type"),
                client_subject=data.get("client_subject") or data.get("client_entity"),
                status="confirmed",
                confirmed_at=timezone.now(),
                confirmed_by=user,
                attachments=data.get("attachments") or [],
            )

            if effective_case:
                case = create_case_from_effective_case(customer, effective_case, contract, case_payload)
            else:
                case = create_case_from_contract_data(customer, contract, case_payload)

            contract.case = case
            contract.save(update_fields=["case"])

            customer.status = Customer.STATUS_CASE
            customer.modifier = user.name or str(user.id)
            customer.save(update_fields=["status", "sales_stage", "update_datetime", "modifier"])

        return DetailResponse(data={
            "contract_id": contract.id if contract else None,
            "case_id": case.id if case else None,
        }, msg="确认成功")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"确认合同失败: {str(e)}", code=4000)
