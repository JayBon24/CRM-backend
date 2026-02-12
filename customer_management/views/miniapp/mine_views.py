# -*- coding: utf-8 -*-
"""
小程序 Tab5「我的」模块视图
提供 /api/mine/* 接口
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
import json

from customer_management.models import ApprovalTask, ApprovalHistory, Customer, TransferLog
from case_management.models import CaseManagement
from case_management.services.case_service import generate_case_number
from customer_management.services.approval_service import ApprovalService
from customer_management.services.customer_service import CustomerService
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.system.models import Users, Dept


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mine_profile(request):
    """
    获取个人资料
    GET /api/mine/profile
    """
    try:
        user = request.user
        
        # 获取组织信息
        team_name = None
        branch_name = None
        if hasattr(user, 'dept'):
            dept = user.dept
            if dept:
                team_name = dept.name if hasattr(dept, 'name') else None
                if hasattr(dept, 'parent') and dept.parent:
                    branch_name = dept.parent.name if hasattr(dept.parent, 'name') else None
        
        # 确定数据范围
        role_level = getattr(user, 'role_level', 'SALES')
        if role_level == 'HQ':
            org_scope = 'HQ'
        elif role_level == 'BRANCH':
            org_scope = 'BRANCH'
        elif role_level == 'TEAM':
            org_scope = 'TEAM'
        else:
            org_scope = 'SELF'
        
        data = {
            'user_id': str(user.id),
            'name': user.name or user.username,
            'avatar': getattr(user, 'avatar', None),
            'roleLevel': role_level,
            'orgScope': org_scope,
            'teamName': team_name,
            'branchName': branch_name,
            'email': getattr(user, 'email', None),
            'phonenumber': getattr(user, 'mobile', None),
            'deptId': getattr(user, 'dept_id', None),
            'deptName': team_name,
        }
        
        return DetailResponse(data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"获取个人资料失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_mine_profile(request):
    """
    更新个人资料
    POST /api/mine/profile/update
    """
    try:
        user = request.user
        data = request.data
        
        # 更新字段
        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            user.email = data['email']
        if 'phonenumber' in data:
            user.mobile = data['phonenumber']
        if 'dept_id' in data:
            dept_id = data.get('dept_id')
            if dept_id in ("", None):
                user.dept = None
            else:
                try:
                    dept = Dept.objects.get(id=int(dept_id), status=True)
                except (ValueError, TypeError, Dept.DoesNotExist):
                    return ErrorResponse(msg="所属部门不存在或已停用", code=4000)
                user.dept = dept
                user.dept_belong_id = dept.id
        
        user.save()
        
        # 获取组织信息
        team_name = None
        branch_name = None
        if hasattr(user, 'dept'):
            dept = user.dept
            if dept:
                team_name = dept.name if hasattr(dept, 'name') else None
                if hasattr(dept, 'parent') and dept.parent:
                    branch_name = dept.parent.name if hasattr(dept.parent, 'name') else None
        
        role_level = getattr(user, 'role_level', 'SALES')
        if role_level == 'HQ':
            org_scope = 'HQ'
        elif role_level == 'BRANCH':
            org_scope = 'BRANCH'
        elif role_level == 'TEAM':
            org_scope = 'TEAM'
        else:
            org_scope = 'SELF'
        
        return DetailResponse(data={
            'user_id': str(user.id),
            'name': user.name or user.username,
            'email': getattr(user, 'email', None),
            'phonenumber': getattr(user, 'mobile', None),
            'deptId': getattr(user, 'dept_id', None),
            'deptName': team_name,
            'teamName': team_name,
            'branchName': branch_name,
        }, msg='更新成功')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"更新个人资料失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_feedback(request):
    """
    提交反馈
    POST /api/mine/feedback
    """
    try:
        user = request.user
        data = request.data
        
        # TODO: 创建反馈记录（需要创建 Feedback 模型）
        # 这里先返回成功，后续需要创建 Feedback 模型
        
        feedback_id = f'fb_{int(timezone.now().timestamp() * 1000)}'
        
        return DetailResponse(data={
            'id': feedback_id
        }, msg='提交成功')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"提交反馈失败: {str(e)}", code=4000)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_feedback_list(request):
    """
    获取反馈列表
    GET /api/mine/feedback/list
    """
    try:
        user = request.user
        
        # TODO: 从 Feedback 模型获取反馈列表
        # 这里先返回空列表，后续需要创建 Feedback 模型
        
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 20))
        
        return DetailResponse(data={
            'rows': [],
            'total': 0
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"获取反馈列表失败: {str(e)}", code=4000)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_approval_list(request):
    """
    获取审批任务列表
    GET /api/mine/approval/list
    """
    try:
        user = request.user
        
        role_level = getattr(user, 'role_level', None) or getattr(user, 'org_scope', None)
        status = request.query_params.get('status', 'pending')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 20))
        
        # 构建查询
        if role_level == 'HQ':
            # HQ可以看到所有审批申请
            if status == 'pending':
                # 待审批：返回所有待审批的任务（不管current_approver_role是什么，HQ都能看到）
                # 这样可以兼容旧的审批任务（之前是TEAM/BRANCH审批）和新任务（直接提交给HQ）
                queryset = ApprovalTask.objects.filter(status='pending')
            else:
                # 已处理：返回所有已处理的任务（HQ可以看到所有审批历史）
                queryset = ApprovalTask.objects.filter(
                    status__in=['approved', 'rejected']
                )
        else:
            # 非HQ用户只能查看自己作为申请人的审批任务
            if status == 'pending':
                # 待审批：返回自己提交的待审批任务
                queryset = ApprovalTask.objects.filter(
                    status='pending',
                    applicant=user
                )
            else:
                # 已处理：返回自己提交的已处理任务（包括已通过和已驳回）
                queryset = ApprovalTask.objects.filter(
                    status__in=['approved', 'rejected'],
                    applicant=user
                )
        
        # 分页
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        tasks = queryset[start:end]
        
        # 构建响应数据
        rows = []
        for task in tasks:
            # 安全地获取客户信息，避免客户被删除导致的异常
            client_id = None
            client_name = None
            related_data = task.related_data or {}
            
            try:
                # 尝试访问 related_customer，如果客户不存在，会抛出 DoesNotExist 异常
                # 使用 try-except 包装，避免访问已删除的客户导致异常
                if hasattr(task, 'related_customer_id') and task.related_customer_id:
                    try:
                        # 直接访问 task.related_customer 会触发数据库查询
                        # 如果客户不存在（被删除），会抛出 Customer.DoesNotExist
                        related_customer = task.related_customer
                        if related_customer:
                            client_id = str(related_customer.id)
                            client_name = related_customer.name
                    except Exception:
                        # 如果客户不存在（被删除），忽略异常，后续从 related_data 获取
                        pass
            except Exception:
                # 外层异常捕获，确保不会中断整个循环
                pass
            
            # 如果从 related_customer 没有获取到信息，从 related_data 获取
            if not client_id and not client_name:
                if task.approval_type == 'LEAD_CLAIM':
                    client_id = str(related_data.get('client_id', ''))
                    client_name = related_data.get('name', '')
                elif task.approval_type == 'LEAD_CREATE' and related_data.get('form'):
                    client_name = related_data.get('form', {}).get('client_name', '')
            
            # 获取审批历史
            histories = ApprovalHistory.objects.filter(approval_task=task).order_by('approval_time')
            history_list = []
            for hist in histories:
                history_list.append({
                    'step_role': hist.approver_role,
                    'approver_user_id': str(hist.approver.id) if hist.approver else '',
                    'approver_user_name': hist.approver.name if hist.approver else '',
                    'decision': 'approved' if hist.action == 'approve' else 'rejected',
                    'reject_reason': hist.comment if hist.action == 'reject' else None,
                    'decided_at': hist.approval_time.strftime('%Y-%m-%d %H:%M:%S') if hist.approval_time else None,
                })
            
            # 构建 payload
            related_data = task.related_data or {}
            if task.approval_type == 'LEAD_CLAIM':
                payload = {
                    'client_id': str(related_data.get('client_id', '')),
                    'name': related_data.get('name', ''),
                    'reason': related_data.get('reason', '')
                }
            elif task.approval_type == 'LEAD_CREATE':
                payload = {
                    'form': related_data.get('form', {})
                }
            elif task.approval_type == 'HANDOVER':
                to_users = related_data.get('to_users')
                if not to_users:
                    to_user = related_data.get('to_user')
                    to_users = [to_user] if to_user else []
                payload = {
                    'client_id': str(related_data.get('client_id', '')),
                    'from_user': related_data.get('from_user', {}),
                    'to_users': to_users,
                    'reason': related_data.get('reason', '')
                }
            else:
                payload = related_data
            
            rows.append({
                'id': f'approval_{task.id}',
                'type': task.approval_type,
                'status': task.status,
                'applicant_user_id': str(task.applicant.id) if task.applicant else '',
                'applicant_user_name': task.applicant.name if task.applicant else '',
                'client_id': client_id,
                'client_name': client_name,
                'created_at': task.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if task.create_datetime else None,
                'approved_at': task.update_datetime.strftime('%Y-%m-%d %H:%M:%S') if task.status == 'approved' and task.update_datetime else None,
                'reject_reason': task.reject_reason,
                'approval_chain': task.approval_chain,
                'current_step_index': task.current_step,
                'current_approver_role': task.current_approver_role,
                'history': history_list,
                'payload': payload,
            })
        
        return DetailResponse(data={
            'rows': rows,
            'total': total
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"获取审批任务列表失败: {str(e)}", code=4000)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_task(request, id):
    """
    审批任务（通过/驳回）
    POST /api/mine/approval/{id}/approve
    """
    try:
        user = request.user
        
        # 权限检查：只有HQ角色可以审批
        role_level = getattr(user, 'role_level', None)
        if role_level != 'HQ':
            return ErrorResponse(msg="只有总所账号可以审批", code=4003)
        
        task_id = id.replace('approval_', '')
        try:
            task = ApprovalTask.objects.get(id=task_id)
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
            
            # 如果所有审批都通过，执行相应操作
            if task.status == 'approved':
                if task.approval_type == 'LEAD_CLAIM':
                    # 申领成功，更新客户状态
                    client = task.related_customer
                    if task.applicant:
                        CustomerService.set_handlers(client, [task.applicant.id], primary_id=task.applicant.id, mode="replace")
                    client.status = client.STATUS_FOLLOW_UP
                    client.sales_stage = client.calculate_sales_stage()
                    client.save()
                    case_qs = CaseManagement.objects.filter(customer=client, is_deleted=False)
                    if case_qs.exists():
                        case_qs.filter(status=CaseManagement.STATUS_PUBLIC_POOL).update(
                            status=CaseManagement.STATUS_FOLLOW_UP,
                            sales_stage=CaseManagement.SALES_STAGE_BLANK,
                        )
                    else:
                        CaseManagement.objects.create(
                            case_number=generate_case_number(),
                            case_name=f"{client.name}案件",
                            case_type="other",
                            case_status="待处理",
                            status=CaseManagement.STATUS_FOLLOW_UP,
                            sales_stage=CaseManagement.SALES_STAGE_BLANK,
                            customer=client,
                            owner_user=client.owner_user,
                            owner_user_name=client.owner_user_name,
                            is_deleted=False,
                        )
                elif task.approval_type == 'LEAD_CREATE':
                    # 新增线索：发布草稿客户
                    client = task.related_customer
                    related_data = task.related_data or {}
                    form = related_data.get('form') or {}

                    if form:
                        owner_user = client.owner_user
                        owner_user_id = form.get('owner_user_id')
                        handler_ids = form.get('handler_ids') or related_data.get("handler_ids") or []
                        if handler_ids:
                            if isinstance(handler_ids, str):
                                handler_ids = [item for item in handler_ids.split(",") if str(item).strip()]
                            if not isinstance(handler_ids, (list, tuple)):
                                handler_ids = [handler_ids]
                            handler_ids = [int(x) for x in handler_ids if str(x).isdigit()]
                        if owner_user_id:
                            try:
                                owner_user = Users.objects.get(id=owner_user_id)
                            except Users.DoesNotExist:
                                owner_user = client.owner_user

                        client.name = form.get('client_name') or client.name
                        client.contact_person = form.get('contact_name') or client.contact_person
                        client.contact_phone = form.get('mobile') or client.contact_phone
                        client.address = form.get('region') or client.address
                        client.source_channel = form.get('source_channel') or client.source_channel
                        client.referrer = form.get('referrer') or client.referrer
                        client.remark = form.get('demand_summary') or client.remark
                        client.client_grade = form.get('grade') or client.client_grade
                        if form.get('grade'):
                            client.grade_source = 'manual'

                        collection_category = form.get('collection_category')
                        if collection_category is not None:
                            client.collection_category = (
                                json.dumps(collection_category, ensure_ascii=False)
                                if isinstance(collection_category, (list, tuple))
                                else collection_category
                            )
                            client.collection_source = 'manual'

                        if owner_user:
                            client.owner_user = owner_user
                            client.owner_user_name = owner_user.name or owner_user.username
                            client.team_id = CustomerService._derive_team_id(owner_user)
                            client.branch_id = CustomerService._derive_branch_id(owner_user)
                        if handler_ids:
                            CustomerService.set_handlers(client, handler_ids, primary_id=handler_ids[0], mode="replace")

                    client.is_deleted = False
                    client.status = Customer.STATUS_PUBLIC_POOL
                    client.save()
                    case_qs = CaseManagement.objects.filter(customer=client)
                    if case_qs.exists():
                        case_qs.update(
                            is_deleted=False,
                            status=CaseManagement.STATUS_PUBLIC_POOL,
                            sales_stage=CaseManagement.SALES_STAGE_PUBLIC,
                            owner_user=client.owner_user,
                            owner_user_name=client.owner_user_name,
                        )
                    else:
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
                elif task.approval_type == 'HANDOVER':
                    # 客户转交：更新经办人信息（不改变生命周期状态）
                    client = task.related_customer
                    related_data = task.related_data or {}
                    to_users = related_data.get('to_users') or []
                    to_owner_ids = related_data.get('to_owner_ids') or related_data.get('to_owner_id') or related_data.get('to_user_id')
                    transfer_mode = related_data.get('transfer_mode') or 'append'

                    if not to_users and to_owner_ids:
                        if isinstance(to_owner_ids, str):
                            to_owner_ids = [item for item in to_owner_ids.split(",") if str(item).strip()]
                        if not isinstance(to_owner_ids, (list, tuple)):
                            to_owner_ids = [to_owner_ids]
                        to_users = [{"id": str(item)} for item in to_owner_ids]

                    if not to_users:
                        return ErrorResponse(msg="转交审批缺少目标经办人信息", code=4001)

                    to_ids = [int(item.get('id')) for item in to_users if str(item.get('id', '')).isdigit()]
                    if not to_ids:
                        return ErrorResponse(msg="转交审批缺少目标经办人信息", code=4001)

                    CustomerService.set_handlers(
                        client,
                        to_ids,
                        primary_id=client.owner_user_id if transfer_mode == "append" else to_ids[0],
                        mode=transfer_mode,
                    )

                    transfer_log_id = related_data.get('transfer_log_id')
                    if transfer_log_id:
                        TransferLog.objects.filter(id=transfer_log_id).update(status='completed')
        else:
            # 审批驳回
            if not reject_reason:
                return ErrorResponse(msg="驳回时必须填写原因", code=4001)
            ApprovalService.advance_task(task, user, 'reject', reject_reason)

            # 审批驳回后的业务处理
            if task.status == 'rejected' and task.approval_type == 'HANDOVER':
                related_data = task.related_data or {}
                transfer_log_id = related_data.get('transfer_log_id')
                if transfer_log_id:
                    TransferLog.objects.filter(id=transfer_log_id).update(status='rejected')
        
        return DetailResponse(data={
            'ok': True
        }, msg='审批成功')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(msg=f"审批失败: {str(e)}", code=4000)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def reminder_preference(request):
    """
    获取或设置提醒偏好
    GET /api/mine/settings/remind - 获取提醒偏好设置
    POST /api/mine/settings/remind - 设置提醒偏好
    """
    if request.method == 'POST':
        # 设置提醒偏好
        try:
            user = request.user
            data = request.data
            
            default_remind_advance_minutes = data.get('default_remind_advance_minutes', 30)
            
            # 验证值
            if default_remind_advance_minutes not in [15, 30]:
                return ErrorResponse(msg="提前提醒时间只能是 15 或 30 分钟", code=4001)
            
            # TODO: 保存到用户设置表
            # 这里先返回成功，后续需要创建用户设置模型
            
            return DetailResponse(data={
                'ok': True
            }, msg='设置成功')
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ErrorResponse(msg=f"设置提醒偏好失败: {str(e)}", code=4000)
    else:
        # GET 方法：获取提醒偏好设置
        try:
            user = request.user
            
            # TODO: 从用户设置表获取提醒偏好
            # 这里先返回默认值，后续需要创建用户设置模型
            
            return DetailResponse(data={
                'default_remind_advance_minutes': 30
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ErrorResponse(msg=f"获取提醒偏好失败: {str(e)}", code=4000)
