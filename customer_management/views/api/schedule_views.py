from datetime import datetime, timedelta
from calendar import monthrange
from django.db.models import Q, Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated

from dvadmin.utils.json_response import DetailResponse, SuccessResponse, ErrorResponse
from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.system.models import Users, Dept
from customer_management.models import Schedule, ScheduleReminder
from customer_management.serializers import (
    ScheduleSerializer,
    ScheduleListSerializer,
    ScheduleDetailSerializer,
    ScheduleCreateSerializer,
    ScheduleUpdateSerializer,
    CreateFromCustomerPlanSerializer,
    BatchDeleteSerializer,
    UpdateStatusSerializer,
    SendSMSSerializer,
    SendEmailSerializer,
)
from customer_management.services.notification_service import SMSService, EmailService
from customer_management.mixins import RoleBasedFilterMixin


class ScheduleViewSet(RoleBasedFilterMixin, CustomModelViewSet):
    """
    日程管理ViewSet
    
    自动根据用户角色过滤数据范围：
    - HQ（总所管理）：查看全所日程
    - BRANCH（分所管理）：查看本分所日程
    - TEAM（团队管理）：查看本团队日程
    - SALES（销售）：仅查看本人日程
    """
    queryset = Schedule.objects.filter(is_deleted=False)
    serializer_class = ScheduleSerializer
    
    # 配置字段名（日程表的创建人字段是 creator）
    owner_field = 'creator'
    # Schedule 模型没有 team_id 和 branch_id 字段，禁用这些过滤
    team_field = None
    branch_field = None
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['schedule_type', 'status', 'priority', 'related_type', 'related_id']
    
    # 只返回JSON，不渲染HTML模板
    from rest_framework.renderers import JSONRenderer
    renderer_classes = [JSONRenderer]
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['id', 'start_time', 'priority', 'create_datetime']
    ordering = ['-start_time']
    
    permission_classes = []
    extra_filter_class = []
    
    def get_queryset(self):
        """自定义查询集，只按创建人过滤"""
        queryset = Schedule.objects.filter(is_deleted=False)
        
        user = self.request.user
        if not user or not user.is_authenticated:
            return queryset.none()
        
        # 超级管理员和HQ查看所有
        if user.is_superuser:
            return queryset
        
        role_level = getattr(user, 'role_level', None)
        if role_level == 'HQ':
            return queryset
        
        # 其他角色只看自己创建的日程
        return queryset.filter(creator=user)
    
    def get_serializer_class(self):
        """根据不同的action返回不同的序列化器"""
        if self.action == 'list':
            return ScheduleListSerializer
        elif self.action == 'retrieve':
            return ScheduleDetailSerializer
        elif self.action == 'create':
            return ScheduleCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ScheduleUpdateSerializer
        return ScheduleSerializer
    
    def perform_create(self, serializer):
        """创建时自动设置创建人"""
        if self.request.user and self.request.user.is_authenticated:
            serializer.save(creator=self.request.user)
        else:
            serializer.save()
    
    def perform_update(self, serializer):
        """更新时自动设置修改人"""
        if self.request.user and self.request.user.is_authenticated:
            # modifier是CharField，需要传入用户名而不是用户对象
            serializer.save(modifier=self.request.user.username)
        else:
            serializer.save()
    
    def get_queryset(self):
        """自定义查询集，支持时间范围筛选"""
        queryset = super().get_queryset()
        
        # 时间范围筛选
        start_time_after = self.request.query_params.get('start_time_after')
        start_time_before = self.request.query_params.get('start_time_before')
        
        if start_time_after:
            try:
                # 解析带时区的时间字符串
                from dateutil import parser
                dt = parser.parse(start_time_after)
                queryset = queryset.filter(start_time__gte=dt)
            except Exception:
                # 如果解析失败，使用原始字符串
                queryset = queryset.filter(start_time__gte=start_time_after)
        
        if start_time_before:
            try:
                # 解析带时区的时间字符串
                from dateutil import parser
                dt = parser.parse(start_time_before)
                queryset = queryset.filter(start_time__lte=dt)
            except Exception:
                # 如果解析失败，使用原始字符串
                queryset = queryset.filter(start_time__lte=start_time_before)
        
        return queryset

    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        """批量删除日程"""
        serializer = BatchDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ids = serializer.validated_data['ids']
        deleted_count = Schedule.objects.filter(
            id__in=ids,
            is_deleted=False
        ).update(is_deleted=True)
        
        return SuccessResponse(
            data={'deleted_count': deleted_count},
            msg=f"批量删除成功，共删除 {deleted_count} 条记录"
        )
    
    @action(detail=False, methods=['post'])
    def batch_update_status(self, request):
        """批量更新日程状态"""
        ids = request.data.get('ids', [])
        new_status = request.data.get('status')
        
        if not ids:
            return ErrorResponse(msg="缺少必要参数：ids")
        
        if not new_status or new_status not in dict(Schedule.STATUS_CHOICES):
            return ErrorResponse(msg="无效的状态值")
        
        updated_count = Schedule.objects.filter(
            id__in=ids,
            is_deleted=False
        ).update(status=new_status)
        
        return SuccessResponse(
            data={'updated_count': updated_count},
            msg=f"批量更新成功，共更新 {updated_count} 条记录"
        )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """更新日程状态"""
        instance = self.get_object()
        serializer = UpdateStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        instance.status = serializer.validated_data['status']
        instance.save()
        
        return DetailResponse(
            data=ScheduleDetailSerializer(instance).data,
            msg="状态更新成功"
        )
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """获取今日日程"""
        today = timezone.now().date()
        schedules = self.get_queryset().filter(
            start_time__date=today
        )
        
        # 统计
        by_status = {}
        for status_value, status_label in Schedule.STATUS_CHOICES:
            count = schedules.filter(status=status_value).count()
            if count > 0:
                by_status[status_value] = count
        
        serializer = ScheduleListSerializer(schedules, many=True)
        
        return SuccessResponse(data={
            'date': today.strftime('%Y-%m-%d'),
            'total_count': schedules.count(),
            'by_status': by_status,
            'schedules': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def this_week(self, request):
        """获取本周日程"""
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        schedules = self.get_queryset().filter(
            start_time__date__gte=week_start,
            start_time__date__lte=week_end
        )
        
        # 按日期统计
        by_day = {}
        for i in range(7):
            day = week_start + timedelta(days=i)
            count = schedules.filter(start_time__date=day).count()
            if count > 0:
                by_day[day.strftime('%Y-%m-%d')] = count
        
        serializer = ScheduleListSerializer(schedules, many=True)
        
        return SuccessResponse(data={
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_end': week_end.strftime('%Y-%m-%d'),
            'total_count': schedules.count(),
            'by_day': by_day,
            'schedules': serializer.data
        })


    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取日程统计"""
        queryset = self.get_queryset()
        
        # 时间范围筛选
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(start_time__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__date__lte=end_date)
        
        # 按类型统计
        by_type = {}
        for type_value, type_label in Schedule.SCHEDULE_TYPE_CHOICES:
            count = queryset.filter(schedule_type=type_value).count()
            if count > 0:
                by_type[type_value] = count
        
        # 按状态统计
        by_status = {}
        for status_value, status_label in Schedule.STATUS_CHOICES:
            count = queryset.filter(status=status_value).count()
            if count > 0:
                by_status[status_value] = count
        
        # 按优先级统计
        by_priority = {}
        for priority_value, priority_label in Schedule.PRIORITY_CHOICES:
            count = queryset.filter(priority=priority_value).count()
            if count > 0:
                by_priority[priority_value] = count
        
        # 即将到来的日程数量（未来7天）
        upcoming_count = queryset.filter(
            start_time__gte=timezone.now(),
            start_time__lte=timezone.now() + timedelta(days=7),
            status='pending'
        ).count()
        
        # 逾期日程数量
        overdue_count = queryset.filter(
            start_time__lt=timezone.now(),
            status='pending'
        ).count()
        
        return SuccessResponse(data={
            'total_count': queryset.count(),
            'by_type': by_type,
            'by_status': by_status,
            'by_priority': by_priority,
            'upcoming_count': upcoming_count,
            'overdue_count': overdue_count
        })
    
    @action(detail=False, methods=['post'])
    def create_from_customer_plan(self, request):
        """从客户计划创建日程"""
        serializer = CreateFromCustomerPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # 创建日程
        schedule = Schedule.objects.create(
            title=data['plan_title'],
            description=data.get('plan_description', ''),
            schedule_type='reminder',
            start_time=data['plan_time'],
            status='pending',
            priority='medium',
            reminder_enabled=True,
            reminder_time=data.get('reminder_time', 60),
            reminder_method='system',
            related_type='customer_plan',
            related_id=data['customer_id'],
            creator=request.user if request.user.is_authenticated else None
        )
        
        return DetailResponse(
            data=ScheduleDetailSerializer(schedule).data,
            msg="日程创建成功"
        )

    @action(detail=False, methods=['get'])
    def by_related(self, request):
        """获取关联对象的日程列表"""
        related_type = request.query_params.get('related_type')
        related_id = request.query_params.get('related_id')
        
        if not related_type or not related_id:
            return ErrorResponse(msg="缺少必要参数：related_type 和 related_id")
        
        schedules = self.get_queryset().filter(
            related_type=related_type,
            related_id=related_id
        )
        
        serializer = ScheduleListSerializer(schedules, many=True)
        return SuccessResponse(data=serializer.data)
    
    @action(detail=True, methods=['get'])
    def reminders(self, request, pk=None):
        """获取日程提醒记录"""
        schedule = self.get_object()
        
        # 获取该日程的提醒记录
        reminders = ScheduleReminder.objects.filter(
            schedule=schedule
        ).order_by('-create_datetime')
        
        reminders_data = []
        for reminder in reminders:
            reminders_data.append({
                'id': reminder.id,
                'remind_time': reminder.remind_time.isoformat() if reminder.remind_time else None,
                'remind_method': reminder.remind_method,
                'is_sent': reminder.is_sent,
                'sent_at': reminder.sent_at.isoformat() if reminder.sent_at else None,
                'status': reminder.status,
                'error_message': reminder.error_message
            })
        
        return SuccessResponse(data={
            'schedule_id': schedule.id,
            'schedule_title': schedule.title,
            'reminders': reminders_data
        })
    
    @action(detail=False, methods=['get'])
    def upcoming_reminders(self, request):
        """获取即将到来的提醒"""
        hours = int(request.query_params.get('hours', 24))
        
        now = timezone.now()
        end_time = now + timedelta(hours=hours)
        
        schedules = self.get_queryset().filter(
            start_time__gte=now,
            start_time__lte=end_time,
            reminder_enabled=True,
            status='pending'
        ).order_by('start_time')
        
        reminders = []
        for schedule in schedules:
            # 计算提醒时间
            remind_time = schedule.start_time - timedelta(minutes=schedule.reminder_time or 30)
            
            # 计算距离提醒的时间
            time_until = remind_time - now
            hours_until = int(time_until.total_seconds() // 3600)
            minutes_until = int((time_until.total_seconds() % 3600) // 60)
            
            time_until_str = ""
            if hours_until > 0:
                time_until_str = f"{hours_until}小时"
            if minutes_until > 0:
                time_until_str += f"{minutes_until}分钟"
            if not time_until_str:
                time_until_str = "即将提醒"
            
            reminders.append({
                'schedule_id': schedule.id,
                'schedule_title': schedule.title,
                'start_time': schedule.start_time,
                'remind_time': remind_time,
                'time_until_remind': time_until_str
            })
        
        return SuccessResponse(data={
            'count': len(reminders),
            'reminders': reminders
        })
    
    @action(detail=False, methods=['get'])
    def calendar_view(self, request):
        """日历视图数据"""
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        if not year or not month:
            return ErrorResponse(msg="缺少必要参数：year 和 month")
        
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return ErrorResponse(msg="year 和 month 必须是整数")
        
        # 获取该月的第一天和最后一天
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, last_day).date()
        
        schedules = self.get_queryset().filter(
            start_time__date__lte=end_date
        ).filter(
            Q(end_time__date__gte=start_date) | Q(end_time__isnull=True)
        )
        
        # 按日期组织数据
        days = []
        for day in range(1, last_day + 1):
            current_date = datetime(year, month, day).date()
            day_schedules = schedules.filter(
                start_time__date__lte=current_date
            ).filter(
                Q(end_time__date__gte=current_date) | Q(end_time__isnull=True, start_time__date=current_date)
            )
            
            days.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'schedules': ScheduleListSerializer(day_schedules, many=True).data,
                'count': day_schedules.count()
            })
        
        return SuccessResponse(data={
            'year': year,
            'month': month,
            'days': days
        })

    
    @action(detail=False, methods=['post'], url_path='notification/sms/send')
    def send_sms(self, request):
        """发送短信通知"""
        serializer = SendSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        result = SMSService.send_sms(
            phone=data['phone'],
            template_code=data['template_code'],
            params=data['params']
        )
        
        if result['success']:
            return SuccessResponse(data=result, msg="短信发送成功")
        else:
            return ErrorResponse(msg=result['message'])
    
    @action(detail=False, methods=['post'], url_path='notification/email/send')
    def send_email(self, request):
        """发送邮件通知"""
        serializer = SendEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        result = EmailService.send_email(
            to=data['to'],
            subject=data['subject'],
            content=data['content'],
            template=data.get('template')
        )
        
        if result['success']:
            return SuccessResponse(data=result, msg="邮件发送成功")
        else:
            return ErrorResponse(msg=result['message'])



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_team_schedule(request):
    """
    获取团队日程数据
    """
    user = request.user
    
    # 获取参数
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    
    if not start_date_str or not end_date_str:
        return ErrorResponse(msg="缺少必要参数：start_date 和 end_date")
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return ErrorResponse(msg="日期格式错误，请使用 YYYY-MM-DD 格式")
    
    # 查询所有未删除的日程
    queryset = Schedule.objects.filter(
        is_deleted=False,
        start_time__date__gte=start_date,
        start_time__date__lte=end_date
    ).select_related('creator').order_by('start_time')

    # 角色与范围过滤（支持前端透传 team_id / branch_id）
    role_level = getattr(user, 'role_level', None)
    team_id = request.query_params.get('team_id')
    branch_id = request.query_params.get('branch_id')

    if team_id:
        queryset = queryset.filter(
            Q(creator__team_id=team_id) |
            Q(creator__dept_id=team_id)
        )
    elif branch_id:
        try:
            branch_dept_ids = Dept.recursion_all_dept(int(branch_id))
        except Exception:
            branch_dept_ids = [branch_id]
        queryset = queryset.filter(
            Q(creator__branch_id__in=branch_dept_ids) |
            Q(creator__dept_id__in=branch_dept_ids)
        )
    else:
        if role_level == 'SALES':
            queryset = queryset.filter(creator_id=user.id)
        elif role_level == 'TEAM':
            resolved_team_id = getattr(user, 'team_id', None) or getattr(user, 'dept_id', None)
            if resolved_team_id:
                queryset = queryset.filter(
                    Q(creator__team_id=resolved_team_id) |
                    Q(creator__dept_id=resolved_team_id)
                )
        elif role_level == 'BRANCH':
            resolved_branch_id = getattr(user, 'branch_id', None) or getattr(user, 'dept_id', None)
            if resolved_branch_id:
                try:
                    branch_dept_ids = Dept.recursion_all_dept(int(resolved_branch_id))
                except Exception:
                    branch_dept_ids = [resolved_branch_id]
                queryset = queryset.filter(
                    Q(creator__branch_id__in=branch_dept_ids) |
                    Q(creator__dept_id__in=branch_dept_ids)
                )
    
    # 按日期组织数据
    days = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        day_schedules = queryset.filter(start_time__date=current_date)
        
        schedules_data = []
        for schedule in day_schedules:
            creator = schedule.creator
            user_name = ''
            user_avatar = ''
            user_id = None
            
            if creator:
                user_id = creator.id
                user_name = getattr(creator, 'name', '') or getattr(creator, 'username', '') or ''
                user_avatar = getattr(creator, 'avatar', '') or ''
            
            schedule_data = ScheduleListSerializer(schedule).data
            schedule_data['user_id'] = user_id
            schedule_data['user_name'] = user_name
            schedule_data['user_avatar'] = user_avatar
            schedules_data.append(schedule_data)
        
        days.append({
            'date': date_str,
            'schedules': schedules_data,
            'count': len(schedules_data)
        })
        
        current_date += timedelta(days=1)
    
    return SuccessResponse(data={'days': days})
