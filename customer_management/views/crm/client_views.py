# -*- coding: utf-8 -*-
"""
CRM客户管理视图
提供 /crm/client/* 接口
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from datetime import datetime, time, timedelta
import json
import random

from customer_management.models import Customer, CustomerPlan
from customer_management.models.contract import Contract, RecoveryPayment, LegalFee
from customer_management.services.customer_service import CustomerService
from case_management.services.case_service import (
    create_case_from_contract_data,
    create_case_from_effective_case,
)
from customer_management.services.customer_service import CustomerService
from customer_management.models.transfer import TransferLog
from dvadmin.system.models import Users
from dvadmin.utils.json_response import DetailResponse, ErrorResponse


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_clients(request):
    """
    获取客户列表
    GET /crm/client/list
    
    查询参数:
    - page: 页码，默认1
    - pageSize: 每页数量，默认20
    - status: 生命周期状态 (PUBLIC_POOL, FOLLOW_UP, CASE, PAYMENT, WON)
    - sales_stage: 展业状态 (PUBLIC_POOL, BLANK, MEETING, CASE, PAYMENT, WON)
    - client_grade: 客户等级 (A, B, C, D)
    - collection_category: 催收类别
    - owner_user_id: 经办人ID
    - recycle_risk_level: 回收风险等级
    - start_date: 开始日期
    - end_date: 结束日期
    """
    try:
        user = request.user

        page = int(request.query_params.get('page', 1))
        raw_page_size = request.query_params.get('page_size') or request.query_params.get('pageSize') or 20
        page_size = int(raw_page_size)

        client_status = request.query_params.get('status')
        sales_stage = request.query_params.get('sales_stage')
        sales_stage_list = request.query_params.getlist('sales_stage_list')
        if not sales_stage_list:
            raw_stage_list = request.query_params.get('sales_stage_list')
            if raw_stage_list:
                sales_stage_list = [item.strip() for item in raw_stage_list.split(',') if item.strip()]
        keyword = request.query_params.get('keyword')
        grade = request.query_params.get('grade') or request.query_params.get('client_grade')
        collection_category = request.query_params.get('collection_category')
        owner_user_id = request.query_params.get('owner_user_id')
        team_id = request.query_params.get('team_id')
        branch_id = request.query_params.get('branch_id')
        recycle_risk_level = request.query_params.get('recycle_risk_level')
        created_at_start = request.query_params.get('created_at_start')
        created_at_end = request.query_params.get('created_at_end')
        last_followup_at_start = request.query_params.get('last_followup_at_start')
        last_followup_at_end = request.query_params.get('last_followup_at_end')

        queryset = Customer.objects.filter(is_deleted=False)
        queryset = _apply_data_scope(queryset, user)

        if client_status:
            queryset = queryset.filter(status=client_status)
        if sales_stage_list:
            queryset = queryset.filter(sales_stage__in=sales_stage_list)
        elif sales_stage:
            queryset = queryset.filter(sales_stage=sales_stage)
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword)
                | Q(contact_person__icontains=keyword)
                | Q(contact_phone__icontains=keyword)
                | Q(contact_email__icontains=keyword)
            )
        if grade:
            queryset = queryset.filter(client_grade=grade)
        if collection_category:
            categories = [c.strip() for c in collection_category.split(',') if c.strip()]
            if categories:
                category_query = Q()
                for category in categories:
                    category_query |= Q(collection_category__icontains=category)
                queryset = queryset.filter(category_query)
        if owner_user_id:
            queryset = queryset.filter(handlers__id=owner_user_id)
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if recycle_risk_level:
            queryset = queryset.filter(recycle_risk_level=recycle_risk_level)

        created_start_dt = _parse_datetime_value(created_at_start)
        created_end_dt = _parse_datetime_value(created_at_end, end_of_day=True)
        if created_start_dt and created_end_dt:
            queryset = queryset.filter(create_datetime__range=(created_start_dt, created_end_dt))
        elif created_start_dt:
            queryset = queryset.filter(create_datetime__gte=created_start_dt)
        elif created_end_dt:
            queryset = queryset.filter(create_datetime__lte=created_end_dt)

        followup_start_dt = _parse_datetime_value(last_followup_at_start)
        followup_end_dt = _parse_datetime_value(last_followup_at_end, end_of_day=True)
        if followup_start_dt and followup_end_dt:
            queryset = queryset.filter(update_datetime__range=(followup_start_dt, followup_end_dt))
        elif followup_start_dt:
            queryset = queryset.filter(update_datetime__gte=followup_start_dt)
        elif followup_end_dt:
            queryset = queryset.filter(update_datetime__lte=followup_end_dt)

        queryset = queryset.order_by('-create_datetime', '-id')

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        customers = queryset[start:end]

        return DetailResponse(data={
            'results': [_format_customer_list_item(customer) for customer in customers],
            'total': total,
            'page': page,
            'pageSize': page_size
        })
    except Exception as e:
        return ErrorResponse(msg=f"获取客户列表失败: {str(e)}")


def _generate_mock_clients(status_filter=None, sales_stage_filter=None):
    """生成模拟客户数据"""
    # 所有可能的状态组合
    statuses = ['PUBLIC_POOL', 'FOLLOW_UP', 'CASE', 'PAYMENT', 'WON']
    sales_stages = {
        'PUBLIC_POOL': ['PUBLIC_POOL'],
        'FOLLOW_UP': ['BLANK', 'MEETING'],
        'CASE': ['CASE'],
        'PAYMENT': ['PAYMENT'],
        'WON': ['WON']
    }
    
    # 客户名称模板
    company_names = [
        '北京科技有限公司', '上海贸易有限公司', '深圳投资管理有限公司',
        '广州制造有限公司', '杭州电子商务有限公司', '成都服务有限公司',
        '武汉物流有限公司', '西安建筑有限公司', '南京咨询有限公司',
        '天津食品有限公司', '重庆能源有限公司', '苏州电子有限公司',
        '无锡机械有限公司', '青岛化工有限公司', '大连船舶有限公司',
        '厦门旅游有限公司', '长沙文化有限公司', '郑州医药有限公司',
        '济南农业有限公司', '合肥科技发展有限公司'
    ]
    
    # 联系人姓名
    contact_names = [
        '张三', '李四', '王五', '赵六', '钱七', '孙八', '周九', '吴十',
        '郑一', '王二', '冯三', '陈四', '褚五', '卫六', '蒋七', '沈八',
        '韩九', '杨十', '朱一', '秦二'
    ]
    
    # 手机号前缀
    mobile_prefixes = ['138', '139', '150', '151', '152', '158', '159', '188', '189']
    
    mock_clients = []
    client_id = 1
    
    # 为每个状态生成数据
    for status in statuses:
        # 如果指定了状态过滤，只生成该状态的数据
        if status_filter and status != status_filter:
            continue
        
        # 获取该状态对应的展业状态列表
        stage_list = sales_stages.get(status, [status])
        
        for stage in stage_list:
            # 如果指定了展业状态过滤，只生成该状态的数据
            if sales_stage_filter and stage != sales_stage_filter:
                continue
            
            # 每个状态生成5-10条数据
            count = random.randint(5, 10)
            for i in range(count):
                company_name = random.choice(company_names)
                contact_name = random.choice(contact_names)
                mobile = f"{random.choice(mobile_prefixes)}{random.randint(10000000, 99999999)}"
                
                # 生成时间（最近30天内）
                days_ago = random.randint(0, 30)
                create_time = timezone.now() - timedelta(days=days_ago)
                last_followup_days = random.randint(0, min(days_ago, 7)) if status != 'PUBLIC_POOL' else None
                last_followup_at = (create_time + timedelta(days=last_followup_days)).isoformat() if last_followup_days is not None else None
                
                # 客户等级
                grade = random.choice(['A', 'B', 'C', 'D'])
                
                # 回收风险等级
                risk_levels = ['none', 'low', 'medium', 'high']
                recycle_risk = random.choice(risk_levels)
                
                # 跟进次数和拜访次数
                followup_count = random.randint(0, 10) if status != 'PUBLIC_POOL' else 0
                visit_count = random.randint(0, 5) if stage == 'MEETING' else 0
                valid_visit_count = visit_count - random.randint(0, 1) if visit_count > 0 else 0
                
                client_data = {
                    'id': client_id,
                    'client_name': f"{company_name}",
                    'mobile': mobile,
                    'contact_name': contact_name,
                    'email': f'contact{client_id}@example.com',
                    'region': random.choice(['北京', '上海', '深圳', '广州', '杭州']),
                    'source_channel': random.choice(['官网', '转介绍', '展会', '广告', '其他']),
                    'status': status,
                    'sales_stage': stage,
                    'client_grade': grade,
                    'owner_user_id': random.randint(1, 5),
                    'owner_user_name': f"销售{random.randint(1, 5)}",
                    'last_followup_at': last_followup_at,
                    'recycle_risk_level': recycle_risk,
                    'followup_count': followup_count,
                    'visit_count': visit_count,
                    'valid_visit_count': valid_visit_count,
                    'create_datetime': create_time.isoformat(),
                    'update_datetime': create_time.isoformat(),
                }
                
                # 存储到缓存中，供详情页使用
                _generated_clients_cache[client_id] = client_data.copy()
                
                mock_clients.append(client_data)
                client_id += 1
    
    # 如果没有过滤条件，返回所有数据
    return mock_clients


def _apply_data_scope(queryset, user):
    scope = getattr(user, 'role_level', None) or getattr(user, 'org_scope', None)
    if scope == 'HQ':
        return queryset
    if scope == 'BRANCH':
        branch_id = getattr(user, 'branch_id', None) or getattr(user, 'dept_id', None)
        if branch_id:
            return queryset.filter(branch_id=branch_id)
        return queryset.none()
    if scope == 'TEAM':
        team_id = getattr(user, 'team_id', None) or getattr(user, 'dept_id', None)
        if team_id:
            return queryset.filter(team_id=team_id)
        return queryset.none()
    return queryset.filter(handlers=user)


def _parse_datetime_value(value, end_of_day=False):
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        value_str = str(value)
        parsed = parse_datetime(value_str)
        if parsed is None:
            date_value = parse_date(value_str)
            if not date_value:
                return None
            parsed = datetime.combine(date_value, time.max if end_of_day else time.min)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _parse_collection_category(value):
    if not value:
        return []
    parsed = value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith('[') or raw.startswith('{'):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = [raw]
        else:
            parsed = [raw]
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        parsed = [parsed]
    results = []
    for index, item in enumerate(parsed):
        if isinstance(item, dict):
            category = item.get('type') or item.get('value') or item.get('category')
            if not category:
                continue
            results.append({
                'type': category,
                'is_primary': bool(item.get('is_primary', index == 0)),
            })
        else:
            results.append({
                'type': str(item),
                'is_primary': index == 0,
            })
    return results


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


def _format_customer_list_item(customer):
    owner_name = customer.owner_user_name
    if not owner_name and getattr(customer, 'owner_user', None):
        owner_name = customer.owner_user.name or customer.owner_user.username
    handler_ids, handler_names, handler_list = _get_handler_payload(customer)
    return {
        'id': customer.id,
        'client_name': customer.name,
        'contact_name': customer.contact_person,
        'mobile': customer.contact_phone,
        'email': customer.contact_email,
        'status': customer.status,
        'sales_stage': customer.sales_stage,
        'grade': customer.client_grade,
        'category': customer.client_category,
        'collection_category': _parse_collection_category(customer.collection_category),
        'owner_user_id': customer.owner_user_id,
        'owner_user_name': owner_name,
        'handler_ids': handler_ids,
        'handler_names': handler_names,
        'handlers': handler_list,
        'team_id': customer.team_id,
        'branch_id': customer.branch_id,
        'last_followup_at': customer.update_datetime.isoformat() if customer.update_datetime else None,
        'created_at': customer.create_datetime.isoformat() if customer.create_datetime else None,
        'updated_at': customer.update_datetime.isoformat() if customer.update_datetime else None,
        'recycle_risk_level': customer.recycle_risk_level or 'none',
        'recycle_deadline': customer.recycle_deadline.isoformat() if customer.recycle_deadline else None,
        'last_deal_time': customer.last_deal_time.isoformat() if customer.last_deal_time else None,
        'followup_count': customer.followup_count or 0,
        'visit_count': customer.valid_visit_count or 0,
        'valid_visit_count': customer.valid_visit_count or 0,
    }


def _format_customer_detail(customer):
    detail = _format_customer_list_item(customer)
    
    # 解析地址字段：尝试从address中解析出province/city/district/detail_address
    # 如果address为空，返回空值
    province = ''
    city = ''
    district = ''
    detail_address = ''
    
    if customer.address:
        # 按空格分割地址
        address_parts = customer.address.split(' ')
        
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
    
    detail.update({
        'region': customer.address,  # 保留region字段以兼容旧代码
        'province': province,
        'city': city,
        'district': district,
        'detail_address': detail_address,
        'source_channel': customer.source_channel,
        'referrer': customer.referrer,
        'demand_summary': customer.remark,
        'preservation_status': None,
    })
    return detail
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stats(request):
    """
    获取客户统计信息
    GET /crm/client/stats
    """
    try:
        queryset = Customer.objects.filter(is_deleted=False)
        queryset = _apply_data_scope(queryset, request.user)

        status_keys = [
            Customer.STATUS_PUBLIC_POOL,
            Customer.STATUS_FOLLOW_UP,
            Customer.STATUS_CASE,
            Customer.STATUS_PAYMENT,
            Customer.STATUS_WON,
        ]
        status_counts = {key: 0 for key in status_keys}
        for item in queryset.values('status').annotate(total=Count('id')):
            status = item['status']
            if status in status_counts:
                status_counts[status] = item['total']

        sales_stage_keys = [
            Customer.SALES_STAGE_PUBLIC,
            Customer.SALES_STAGE_BLANK,
            Customer.SALES_STAGE_MEETING,
            Customer.SALES_STAGE_CASE,
            Customer.SALES_STAGE_PAYMENT,
            Customer.SALES_STAGE_WON,
        ]
        sales_stage_counts = {key: 0 for key in sales_stage_keys}
        for item in queryset.values('sales_stage').annotate(total=Count('id')):
            stage = item['sales_stage']
            if stage in sales_stage_counts:
                sales_stage_counts[stage] = item['total']

        stats = {
            'total_clients': queryset.count(),
            'status_counts': status_counts,
            'sales_stage_counts': sales_stage_counts,
        }

        return DetailResponse(data=stats)
    except Exception as e:
        return ErrorResponse(msg=f"获取客户统计失败: {str(e)}")


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def batch_delete_clients(request):
    """
    批量删除客户（软删除）
    DELETE /crm/client/batch-delete
    请求体: { "client_ids": [1, 2, 3] }
    """
    try:
        user = request.user
        # 支持 request.data（DELETE 带 body）或 request.query_params
        payload = getattr(request, 'data', None) or {}
        client_ids = payload.get('client_ids') or payload.get('customer_ids') or []
        if not client_ids:
            return ErrorResponse(msg='请提供 client_ids')
        if isinstance(client_ids, str):
            client_ids = [int(x) for x in client_ids.split(',') if str(x).strip().isdigit()]
        else:
            client_ids = [int(x) for x in client_ids if str(x).strip().isdigit()]
        if not client_ids:
            return ErrorResponse(msg='client_ids 无效')
        queryset = Customer.objects.filter(is_deleted=False)
        queryset = _apply_data_scope(queryset, user)
        to_delete = queryset.filter(id__in=client_ids)
        count = to_delete.count()
        to_delete.update(is_deleted=True)
        return DetailResponse(data={'success_count': count, 'fail_count': len(client_ids) - count, 'failed_ids': []}, msg=f'成功删除 {count} 条客户')
    except Exception as e:
        return ErrorResponse(msg=f'批量删除失败: {str(e)}')


# 全局存储生成的客户数据，用于详情页获取
_generated_clients_cache = {}

# 全局缓存，用于存储每个客户的跟进记录、拜访记录、合同记录等
_followup_cache = {}  # {client_id: [followup1, followup2, ...]}
_visit_cache = {}     # {client_id: [visit1, visit2, ...]}
_contract_cache = {}  # {client_id: [contract1, contract2, ...]}
_payment_cache = {}   # {client_id: [payment1, payment2, ...]}
_legal_fee_cache = {} # {client_id: [fee1, fee2, ...]}

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_client(request, pk):
    """
    更新客户信息
    PUT /crm/client/{id}
    PATCH /crm/client/{id}
    """
    try:
        user = request.user
        queryset = Customer.objects.filter(is_deleted=False)
        queryset = _apply_data_scope(queryset, user)

        try:
            client = queryset.get(id=pk)
        except Customer.DoesNotExist:
            return ErrorResponse(msg='客户不存在')

        data = request.data

        if 'client_name' in data:
            client.name = data['client_name']
        if 'contact_name' in data:
            client.contact_person = data['contact_name']
        if 'mobile' in data:
            client.contact_phone = data['mobile']
        if 'email' in data:
            client.contact_email = data['email']
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
        if 'source_channel' in data:
            client.source_channel = data['source_channel']
        if 'referrer' in data:
            client.referrer = data['referrer']
        if 'demand_summary' in data:
            client.remark = data['demand_summary']
        if 'grade' in data:
            client.client_grade = data['grade']
        if 'collection_category' in data:
            category_value = data['collection_category']
            if isinstance(category_value, (list, dict)):
                client.collection_category = json.dumps(category_value, ensure_ascii=False)
            else:
                client.collection_category = category_value
        if 'category' in data:
            if not data['category']:
                return ErrorResponse(msg='请选择客户类别')
            client.client_category = data['category']
        if 'last_deal_time' in data:
            last_deal_raw = data.get('last_deal_time')
            parsed_last = parse_datetime(str(last_deal_raw)) if last_deal_raw else None
            if not parsed_last and last_deal_raw:
                try:
                    parsed_last = datetime.strptime(str(last_deal_raw), '%Y-%m-%d')
                except Exception:
                    parsed_last = None
            if last_deal_raw and not parsed_last:
                return ErrorResponse(msg='最后成交时间格式错误')
            client.last_deal_time = parsed_last
        status_value = data.get('status') if 'status' in data else None
        if 'sales_stage' in data and status_value is None:
            client.sales_stage = data['sales_stage']
        # 如果更新了 owner_user_id，需要根据新的经办人自动计算 team_id 和 branch_id
        handler_ids = data.get("handler_ids") or data.get("owner_user_ids")
        if handler_ids:
            if isinstance(handler_ids, str):
                handler_ids = [item for item in handler_ids.split(",") if str(item).strip()]
            if not isinstance(handler_ids, (list, tuple)):
                handler_ids = [handler_ids]
            handler_ids = [int(x) for x in handler_ids if str(x).isdigit()]
        # 若传入 handler_ids，则用其设置 handlers，并推导 owner/team/branch
        if handler_ids:
            CustomerService.set_handlers(client, handler_ids, primary_id=handler_ids[0], mode="replace")
        # 若仅传 owner_user_id，则据此推导 team_id 与 branch_id
        if 'owner_user_id' in data and not handler_ids:
            owner_user_id = data['owner_user_id']
            if owner_user_id:
                owner_user = Users.objects.filter(id=owner_user_id).first()
                if not owner_user:
                    return ErrorResponse(msg='经办人不存在')
                client.owner_user = owner_user
                client.owner_user_name = owner_user.name or owner_user.username
                # 根据 owner_user 推导 team_id 与 branch_id
                client.team_id = CustomerService._derive_team_id(owner_user)
                client.branch_id = CustomerService._derive_branch_id(owner_user)
            else:
                client.owner_user = None
                client.owner_user_name = None
        elif 'team_id' in data:
            # 若未传 owner_user_id，仅允许直接设置 team_id
            client.team_id = data['team_id']
        if 'branch_id' in data and 'owner_user_id' not in data and not handler_ids:
            # 若未传 owner_user_id/handler_ids，仅允许直接设置 branch_id
            client.branch_id = data['branch_id']

        client.modifier = user.name or str(user.id)
        if status_value:
            CustomerService.update_status(client, status_value)
        else:
            client.save()

        return DetailResponse(data=_format_customer_detail(client), msg='更新成功')
    except Exception as e:
        return ErrorResponse(msg=f"更新客户失败: {str(e)}")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_client_detail(request, pk):
    """
    获取客户详情
    GET /crm/client/{id}/detail
    """
    try:
        queryset = Customer.objects.filter(is_deleted=False)
        queryset = _apply_data_scope(queryset, request.user)
        client = queryset.filter(id=pk).first()
        if not client:
            return ErrorResponse(msg='客户不存在')
        return DetailResponse(data=_format_customer_detail(client))
    except Exception as e:
        return ErrorResponse(msg=f"获取客户详情失败: {str(e)}")


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # 暂时允许匿名访问，用于测试
def get_followup_list(request, pk):
    """
    获取跟进记录列表或创建跟进记录
    GET /crm/client/{id}/followups - 获取列表
    POST /crm/client/{id}/followups - 创建记录
    """
    client_id = int(pk)
    
    if request.method == 'POST':
        # 创建跟进记录
        followup = {
            'id': random.randint(1000, 9999),  # 使用更大的ID范围避免冲突
            'client_id': client_id,
            'time': timezone.now().isoformat(),
            'type': request.data.get('type', 'phone'),
            'summary': request.data.get('content', request.data.get('summary', '')),
            'conclusion': request.data.get('conclusion', ''),
            'attachments': request.data.get('attachments', []),
            'next_plan_at': request.data.get('next_plan_at'),
            'created_by': 1,  # TODO: 从request.user获取
            'created_by_name': '当前用户',
            'created_at': timezone.now().isoformat(),
            'updated_at': timezone.now().isoformat(),
        }
        
        # 添加到缓存
        if client_id not in _followup_cache:
            _followup_cache[client_id] = []
        _followup_cache[client_id].insert(0, followup)  # 插入到开头
        
        return DetailResponse(data=followup)
    
    # GET 请求 - 获取列表
    # 如果缓存中没有，初始化一些模拟数据
    if client_id not in _followup_cache:
        followup_types = ['phone', 'wechat', 'meeting', 'other']
        followup_contents = [
            '电话沟通，客户对服务很感兴趣',
            '微信联系，发送了相关资料',
            '面谈沟通，详细了解了客户需求',
            '邮件跟进，客户正在考虑中',
            '电话回访，客户满意度较高',
        ]
        
        followups = []
        for i in range(random.randint(3, 5)):
            followup_time = timezone.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
            followup = {
                'id': i + 1,
                'client_id': client_id,
                'time': followup_time.isoformat(),
                'type': random.choice(followup_types),
                'summary': random.choice(followup_contents),
                'conclusion': random.choice(['', '客户有意向', '需要进一步沟通', '暂不考虑']),
                'attachments': [] if random.random() > 0.3 else [
                    {
                        'name': f'附件{i+1}.pdf',
                        'url': f'/uploads/attachments/{client_id}/followup_{i+1}.pdf',
                        'type': 'application/pdf',
                    }
                ],
                'next_plan_at': (followup_time + timedelta(days=random.randint(1, 7))).isoformat() if random.random() > 0.5 else None,
                'created_by': random.randint(1, 5),
                'created_by_name': f'销售{random.randint(1, 5)}',
                'created_at': followup_time.isoformat(),
                'updated_at': followup_time.isoformat(),
            }
            followups.append(followup)
        
        # 按时间倒序排列
        followups.sort(key=lambda x: x['created_at'], reverse=True)
        _followup_cache[client_id] = followups
    else:
        followups = _followup_cache[client_id]
    
    return DetailResponse(data={
        'results': followups,
        'total': len(followups),
    })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # 暂时允许匿名访问，用于测试
def get_visit_list(request, pk):
    """
    获取拜访记录列表或创建拜访记录
    GET /crm/client/{id}/visits - 获取列表
    POST /crm/client/{id}/visits - 创建记录
    """
    client_id = int(pk)
    
    if request.method == 'POST':
        # 创建拜访记录
        visit = {
            'id': random.randint(1000, 9999),
            'client_id': client_id,
            'visit_time': request.data.get('visit_time', timezone.now().isoformat()),
            'duration': request.data.get('duration', 60),
            'location_status': 'success',  # 新增的拜访默认为成功
            'lng': request.data.get('lng'),
            'lat': request.data.get('lat'),
            'address': request.data.get('address', ''),
            'core_value': request.data.get('core_value', ''),
            'system_users': request.data.get('system_users', []),
            'client_contacts': request.data.get('client_contacts', []),
            'attachments': request.data.get('attachments', []),
            'created_by': 1,  # TODO: 从request.user获取
            'created_by_name': '当前用户',
            'created_at': timezone.now().isoformat(),
            'updated_at': timezone.now().isoformat(),
        }
        
        # 添加到缓存
        if client_id not in _visit_cache:
            _visit_cache[client_id] = []
        _visit_cache[client_id].insert(0, visit)  # 插入到开头
        
        return DetailResponse(data=visit)
    
    # GET 请求 - 获取列表
    # 如果缓存中没有，初始化一些模拟数据
    if client_id not in _visit_cache:
        addresses = [
            {'address': '北京市朝阳区xxx大厦', 'lng': 116.397128, 'lat': 39.916527},
            {'address': '上海市浦东新区xxx路', 'lng': 121.487899, 'lat': 31.239677},
            {'address': '深圳市南山区xxx科技园', 'lng': 113.930793, 'lat': 22.533014},
            {'address': '广州市天河区xxx中心', 'lng': 113.331528, 'lat': 23.147466},
        ]
        
        visits = []
        for i in range(random.randint(2, 4)):
            visit_time = timezone.now() - timedelta(days=random.randint(0, 30), hours=random.randint(9, 18))
            addr = random.choice(addresses)
            visit = {
                'id': i + 1,
                'client_id': client_id,
                'visit_time': visit_time.isoformat(),
                'duration': random.randint(30, 120),
                'location_status': random.choice(['success', 'fail', 'denied', 'offline']),
                'lng': addr['lng'],
                'lat': addr['lat'],
                'address': addr['address'],
                'core_value': random.choice(['', '客户需求明确', '合作意向强烈', '需要进一步沟通']),
                'system_users': [
                    {'id': random.randint(1, 5), 'name': f'销售{random.randint(1, 5)}'},
                ],
                'client_contacts': [
                    {'id': 1, 'name': f'联系人{client_id}', 'mobile': f'138{client_id:08d}', 'position': '总经理'},
                ],
                'attachments': [] if random.random() > 0.4 else [
                    {
                        'name': f'拜访照片{i+1}.jpg',
                        'url': f'/uploads/attachments/{client_id}/visit_{i+1}.jpg',
                        'type': 'image/jpeg',
                    }
                ],
                'created_by': random.randint(1, 5),
                'created_by_name': f'销售{random.randint(1, 5)}',
                'created_at': visit_time.isoformat(),
                'updated_at': visit_time.isoformat(),
            }
            visits.append(visit)
        
        # 按时间倒序排列
        visits.sort(key=lambda x: x['created_at'], reverse=True)
        _visit_cache[client_id] = visits
    else:
        visits = _visit_cache[client_id]
    
    return DetailResponse(data={
        'results': visits,
        'total': len(visits),
    })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # 暂时允许匿名访问，用于测试
def get_contract_list(request, pk):
    """
    获取合同列表或创建合同
    GET /crm/client/{id}/contracts - 获取列表
    POST /crm/client/{id}/contracts - 创建合同
    """
    client_id = int(pk)
    
    if request.method == 'POST':
        # 创建合同
        contract = {
            'id': random.randint(1000, 9999),
            'client_id': client_id,
            'contract_no': f'HT{client_id:06d}{random.randint(1, 999):03d}',
            'amount': request.data.get('amount', 0),
            'term': request.data.get('term', ''),
            'service_type': request.data.get('service_type', ''),
            'client_subject': request.data.get('client_subject', ''),
            'status': 'pending',
            'attachments': request.data.get('attachments', []),
            'created_at': timezone.now().isoformat(),
            'updated_at': timezone.now().isoformat(),
        }
        
        # 添加到缓存
        if client_id not in _contract_cache:
            _contract_cache[client_id] = []
        _contract_cache[client_id].insert(0, contract)  # 插入到开头
        
        return DetailResponse(data=contract)
    
    # GET 请求 - 获取列表
    try:
        # 从数据库查询合同数据
        contract_queryset = Contract.objects.filter(customer_id=client_id).select_related('case').order_by('-create_datetime')
        
        contracts = []
        for contract in contract_queryset:
            contract_data = {
                'id': contract.id,
                'client_id': contract.customer_id,
                'contract_no': contract.contract_no,
                'amount': float(contract.amount) if contract.amount else 0,
                'contract_amount': float(contract.amount) if contract.amount else 0,  # 前端可能使用这个字段
                'term': contract.term or '',
                'service_type': contract.service_type or '',
                'client_subject': contract.client_subject or '',
                'client_entity': contract.client_subject or '',  # 前端使用这个字段名
                'status': contract.status,
                'attachments': contract.attachments or [],
                'confirmed_at': contract.confirmed_at.isoformat() if contract.confirmed_at else None,
                'confirmed_by': contract.confirmed_by_id if contract.confirmed_by else None,
                'created_at': contract.create_datetime.isoformat() if contract.create_datetime else None,
                'create_time': contract.create_datetime.isoformat() if contract.create_datetime else None,  # 前端使用这个字段名
                'updated_at': contract.update_datetime.isoformat() if contract.update_datetime else None,
                'update_time': contract.update_datetime.isoformat() if contract.update_datetime else None,  # 前端使用这个字段名
            }
            
            # 如果有关联的案件，添加案件信息
            if contract.case:
                contract_data['case_id'] = contract.case.id
                contract_data['case_no'] = getattr(contract.case, 'case_no', None) or getattr(contract.case, 'case_number', None) or ''
                contract_data['case_name'] = getattr(contract.case, 'case_name', None) or ''
                contract_data['case_type'] = getattr(contract.case, 'case_type', None) or ''
                contract_data['case_status'] = getattr(contract.case, 'status', None) or ''
            
            contracts.append(contract_data)
        
        return DetailResponse(data={
            'results': contracts,
            'total': len(contracts),
        })
    except Exception as e:
        return ErrorResponse(msg=f'获取合同列表失败: {str(e)}')


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # 暂时允许匿名访问，用于测试
def get_recovery_payment_list(request, pk):
    """
    获取回款记录列表或创建回款记录
    GET /crm/client/{id}/recovery-payments - 获取列表
    POST /crm/client/{id}/recovery-payments - 创建记录
    """
    client_id = int(pk)
    
    if request.method == 'POST':
        # 创建回款记录
        payment = {
            'id': random.randint(1000, 9999),
            'client_id': client_id,
            'pay_time': request.data.get('pay_time', timezone.now().isoformat()),
            'amount': request.data.get('amount', 0),
            'collection_category': request.data.get('collection_category', 'arbitration'),
            'voucher_attachments': request.data.get('voucher_attachments', []),
            'created_by': 1,  # TODO: 从request.user获取
            'created_by_name': '当前用户',
            'created_at': timezone.now().isoformat(),
        }
        
        # 添加到缓存
        if client_id not in _payment_cache:
            _payment_cache[client_id] = []
        _payment_cache[client_id].insert(0, payment)  # 插入到开头
        
        return DetailResponse(data=payment)
    
    # GET 请求 - 获取列表
    try:
        # 从数据库查询回款记录
        payment_queryset = RecoveryPayment.objects.filter(customer_id=client_id).select_related('created_by').order_by('-create_datetime')
        
        payments = []
        for payment in payment_queryset:
            payment_data = {
                'id': payment.id,
                'client_id': payment.customer_id,
                'pay_time': payment.pay_time.isoformat() if payment.pay_time else None,
                'payment_time': payment.pay_time.isoformat() if payment.pay_time else None,  # 前端使用这个字段名
                'amount': float(payment.amount) if payment.amount else 0,
                'collection_category': payment.collection_category,
                'voucher_attachments': payment.voucher_attachments or [],
                'voucher_images': payment.voucher_attachments or [],  # 前端使用这个字段名
                'created_by': payment.created_by_id if payment.created_by else None,
                'created_by_name': payment.created_by.name if payment.created_by else None,
                'created_at': payment.create_datetime.isoformat() if payment.create_datetime else None,
                'create_time': payment.create_datetime.isoformat() if payment.create_datetime else None,  # 前端使用这个字段名
            }
            payments.append(payment_data)
        
        return DetailResponse(data={
            'results': payments,
            'total': len(payments),
        })
    except Exception as e:
        return ErrorResponse(msg=f'获取回款记录列表失败: {str(e)}')


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # 暂时允许匿名访问，用于测试
def get_legal_fee_list(request, pk):
    """
    获取律师费用列表或创建费用记录
    GET /crm/client/{id}/legal-fees - 获取列表
    POST /crm/client/{id}/legal-fees - 创建记录
    """
    client_id = int(pk)
    
    if request.method == 'POST':
        # 创建律师费用
        fee = {
            'id': random.randint(1000, 9999),
            'client_id': client_id,
            'pay_time': request.data.get('pay_time', timezone.now().isoformat()),
            'amount': request.data.get('amount', 0),
            'voucher_attachments': request.data.get('voucher_attachments', []),
            'created_by': 1,  # TODO: 从request.user获取
            'created_by_name': '当前用户',
            'created_at': timezone.now().isoformat(),
        }
        
        # 添加到缓存
        if client_id not in _legal_fee_cache:
            _legal_fee_cache[client_id] = []
        _legal_fee_cache[client_id].insert(0, fee)  # 插入到开头
        
        return DetailResponse(data=fee)
    
    # GET 请求 - 获取列表
    try:
        # 从数据库查询律师费用记录
        fee_queryset = LegalFee.objects.filter(customer_id=client_id).select_related('created_by').order_by('-create_datetime')
        
        fees = []
        for fee in fee_queryset:
            fee_data = {
                'id': fee.id,
                'client_id': fee.customer_id,
                'pay_time': fee.pay_time.isoformat() if fee.pay_time else None,
                'payment_time': fee.pay_time.isoformat() if fee.pay_time else None,  # 前端使用这个字段名
                'amount': float(fee.amount) if fee.amount else 0,
                'voucher_attachments': fee.voucher_attachments or [],
                'voucher_images': fee.voucher_attachments or [],  # 前端使用这个字段名
                'created_by': fee.created_by_id if fee.created_by else None,
                'created_by_name': fee.created_by.name if fee.created_by else None,
                'created_at': fee.create_datetime.isoformat() if fee.create_datetime else None,
                'create_time': fee.create_datetime.isoformat() if fee.create_datetime else None,  # 前端使用这个字段名
            }
            fees.append(fee_data)
        
        return DetailResponse(data={
            'results': fees,
            'total': len(fees),
        })
    except Exception as e:
        return ErrorResponse(msg=f'获取律师费用列表失败: {str(e)}')


@api_view(['POST'])
@permission_classes([AllowAny])  # 暂时允许匿名访问，用于测试
def create_recovery_payment(request):
    """
    创建回款记录
    POST /crm/client/payment - 创建回款记录
    请求体需包含 client_id
    """
    try:
        client_id = request.data.get('client_id')
        if not client_id:
            return ErrorResponse(msg='缺少客户ID')
        
        client_id = int(client_id)
        
        # 从数据库创建回款记录
        payment = RecoveryPayment.objects.create(
            customer_id=client_id,
            pay_time=parse_datetime(request.data.get('payment_time')) or timezone.now(),
            amount=request.data.get('amount', 0),
            collection_category=request.data.get('collection_category', 'arbitration'),
            voucher_attachments=request.data.get('attachments', []),
            created_by_id=request.user.id if request.user.is_authenticated else None,
        )
        
        payment_data = {
            'id': payment.id,
            'client_id': payment.customer_id,
            'pay_time': payment.pay_time.isoformat() if payment.pay_time else None,
            'payment_time': payment.pay_time.isoformat() if payment.pay_time else None,  # 前端使用这个字段名
            'amount': float(payment.amount) if payment.amount else 0,
            'collection_category': payment.collection_category,
            'voucher_attachments': payment.voucher_attachments or [],
            'voucher_images': payment.voucher_attachments or [],  # 前端使用这个字段名
            'created_by': payment.created_by_id if payment.created_by else None,
            'created_by_name': payment.created_by.name if payment.created_by else None,
            'created_at': payment.create_datetime.isoformat() if payment.create_datetime else None,
            'create_time': payment.create_datetime.isoformat() if payment.create_datetime else None,  # 前端使用这个字段名
        }
        
        return DetailResponse(data=payment_data)
    except Exception as e:
        return ErrorResponse(msg=f'创建回款记录失败: {str(e)}')


@api_view(['POST'])
@permission_classes([AllowAny])  # 暂时允许匿名访问，用于测试
def create_legal_fee(request):
    """
    创建律师费用记录
    POST /crm/client/legal-fee - 创建律师费用记录
    请求体需包含 client_id
    """
    try:
        client_id = request.data.get('client_id')
        if not client_id:
            return ErrorResponse(msg='缺少客户ID')
        
        client_id = int(client_id)
        
        # 从数据库创建律师费用记录
        fee = LegalFee.objects.create(
            customer_id=client_id,
            pay_time=parse_datetime(request.data.get('payment_time')) or timezone.now(),
            amount=request.data.get('amount', 0),
            voucher_attachments=request.data.get('attachments', []),
            created_by_id=request.user.id if request.user.is_authenticated else None,
        )
        
        fee_data = {
            'id': fee.id,
            'client_id': fee.customer_id,
            'pay_time': fee.pay_time.isoformat() if fee.pay_time else None,
            'payment_time': fee.pay_time.isoformat() if fee.pay_time else None,  # 前端使用这个字段名
            'amount': float(fee.amount) if fee.amount else 0,
            'voucher_attachments': fee.voucher_attachments or [],
            'voucher_images': fee.voucher_attachments or [],  # 前端使用这个字段名
            'created_by': fee.created_by_id if fee.created_by else None,
            'created_by_name': fee.created_by.name if fee.created_by else None,
            'created_at': fee.create_datetime.isoformat() if fee.create_datetime else None,
            'create_time': fee.create_datetime.isoformat() if fee.create_datetime else None,  # 前端使用这个字段名
        }
        
        return DetailResponse(data=fee_data)
    except Exception as e:
        return ErrorResponse(msg=f'创建律师费用记录失败: {str(e)}')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transfer_log_list(request, pk):
    """
    获取转交日志列表
    GET /crm/client/{id}/transfer-logs
    """
    client_id = int(pk)
    logs = (
        TransferLog.objects.filter(customer_id=client_id)
        .select_related('from_user', 'to_user', 'approval_task')
        .prefetch_related('approval_task__histories')
        .order_by('-create_datetime')
    )

    results = []
    for log in logs:
        history = None
        if log.approval_task:
            histories = list(log.approval_task.histories.all())
            if histories:
                history = max(
                    histories,
                    key=lambda history_item: history_item.approval_time or log.create_datetime
                )

        results.append({
            'id': log.id,
            'client_id': client_id,
            'from_user_id': log.from_user_id,
            'from_user_name': log.from_user.name if log.from_user else '',
            'to_user_id': log.to_user_id,
            'to_user_name': log.to_user.name if log.to_user else '',
            'transfer_reason': log.transfer_reason,
            'status': log.status,
            'create_time': log.create_datetime.isoformat() if log.create_datetime else None,
            'approver_name': history.approver.name if history and history.approver else '',
            'approval_time': history.approval_time.isoformat() if history and history.approval_time else None,
        })

    return DetailResponse(data={
        'results': results,
        'total': len(results),
    })


# ==================== POST 接口（创建操作） ====================

@api_view(['POST'])
@permission_classes([AllowAny])  # 暂时允许匿名访问，用于测试
def confirm_contract(request, pk, contract_id):
    """
    确认合同
    POST /crm/client/{id}/contracts/{contract_id}/confirm
    """
    client_id = int(pk)
    contract_id = int(contract_id)

    try:
        user = request.user
        customer = Customer.objects.filter(id=client_id, is_deleted=False).first()
        if not customer:
            return ErrorResponse(msg='客户不存在')

        contract = Contract.objects.filter(id=contract_id, customer_id=client_id).first()
        if not contract:
            return ErrorResponse(msg='合同不存在')

        case_payload = {
            "case_name": request.data.get("case_name"),
            "case_type": request.data.get("case_type"),
            "case_description": request.data.get("case_description"),
            "plaintiff_name": request.data.get("plaintiff_name"),
            "plaintiff_credit_code": request.data.get("plaintiff_credit_code"),
            "plaintiff_address": request.data.get("plaintiff_address"),
            "plaintiff_legal_representative": request.data.get("plaintiff_legal_representative"),
            "defendant_name": request.data.get("defendant_name"),
            "defendant_credit_code": request.data.get("defendant_credit_code"),
            "defendant_address": request.data.get("defendant_address"),
            "defendant_legal_representative": request.data.get("defendant_legal_representative"),
            "contract_amount": request.data.get("contract_amount") or contract.amount,
            "lawyer_fee": request.data.get("lawyer_fee"),
            "litigation_request": request.data.get("litigation_request"),
            "facts_and_reasons": request.data.get("facts_and_reasons"),
            "jurisdiction": request.data.get("jurisdiction"),
            "filing_date": request.data.get("filing_date"),
            "petitioner": request.data.get("petitioner"),
            "draft_person": request.data.get("draft_person"),
        }

        effective_case = CustomerPlan.objects.filter(
            customer_id=client_id,
            plan_type="effective_case",
            is_deleted=False
        ).order_by("-create_datetime").first()

        with transaction.atomic():
            if contract.status != "confirmed":
                contract.status = "confirmed"
                contract.confirmed_at = timezone.now()
                contract.confirmed_by = user
                contract.save(update_fields=["status", "confirmed_at", "confirmed_by"])

            if not contract.case_id:
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
            "id": contract.id,
            "client_id": customer.id,
            "status": contract.status,
            "confirmed_at": contract.confirmed_at.isoformat() if contract.confirmed_at else None,
            "confirmed_by": contract.confirmed_by_id,
            "case_id": contract.case_id,
        })
    except Exception as e:
        return ErrorResponse(msg=f"确认合同失败: {str(e)}")


@api_view(['POST'])
@permission_classes([AllowAny])  # 暂时允许匿名访问，用于测试
def update_ai_tags(request, pk):
    """
    更新AI标记（手动修正）
    POST /crm/client/{id}/ai-tags
    """
    client_id = int(pk)
    
    # 模拟更新成功
    result = {
        'id': client_id,
        'grade': request.data.get('grade'),
        'grade_source': 'manual',
        'collection_category': request.data.get('collection_category', []),
        'preservation_status': request.data.get('preservation_status'),
        'updated_at': timezone.now().isoformat(),
    }
    
    return DetailResponse(data=result)
