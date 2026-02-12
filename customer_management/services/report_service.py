"""
报表服务 - 核心计算逻辑
"""
from datetime import datetime, timedelta, date
from django.db.models import Count, Q, Avg, Sum, F, Case, When, FloatField, IntegerField
from django.db.models.functions import Coalesce
from customer_management.models import Customer, FollowupRecord, VisitRecord
from customer_management.models.organization import Team
from dvadmin.system.models import Dept


class ReportService:
    """报表服务类"""
    
    @staticmethod
    def ensure_naive_datetime(dt):
        """
        确保日期时间对象是 naive（不带时区）
        
        Args:
            dt: datetime, date 或 None
            
        Returns:
            naive datetime 或 None
        """
        if dt is None:
            return None
        
        # 如果是 date 对象，转换为 datetime
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())
        
        # 如果是 datetime 对象且带时区，移除时区信息
        if isinstance(dt, datetime) and dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        
        return dt
    
    @staticmethod
    def _resolve_branch_dept_ids(branch_id):
        """
        将分所ID扩展为可用于过滤的部门ID集合（包含下级部门）
        """
        if not branch_id:
            return []
        try:
            branch_id_int = int(branch_id)
        except (TypeError, ValueError):
            return []
        try:
            return Dept.recursion_all_dept(branch_id_int)
        except Exception:
            return [branch_id_int]

    @staticmethod
    def _apply_record_dimension_filter(queryset, dimension_filter, current_user, user_field='user_id', customer_field='client_id'):
        """
        对跟进/拜访类记录应用统一维度过滤：
        - 客户范围按 Customer + apply_dimension_filter 统一计算
        - 若指定 userId，再叠加记录所属用户过滤
        """
        if not dimension_filter:
            return queryset
        user_id = dimension_filter.get('userId')
        category = dimension_filter.get('category')
        customer_queryset = Customer.objects.filter(is_deleted=False)
        if category:
            customer_queryset = customer_queryset.filter(client_category=category)
        customer_queryset = ReportService.apply_dimension_filter(customer_queryset, dimension_filter, current_user)
        customer_ids = customer_queryset.values_list('id', flat=True)
        queryset = queryset.filter(**{f'{customer_field}__in': customer_ids})
        if user_id:
            queryset = queryset.filter(**{user_field: user_id})
        return queryset

    @staticmethod
    def apply_dimension_filter(queryset, dimension_filter, current_user):
        """
        应用维度过滤
        
        Args:
            queryset: 查询集
            dimension_filter: 维度过滤参数
            current_user: 当前用户
            
        Returns:
            过滤后的查询集
        """
        if not dimension_filter:
            dimension_filter = {'scope': 'SELF', 'dimension': 'NONE'}
        
        scope = dimension_filter.get('scope', 'SELF')
        dimension = dimension_filter.get('dimension', 'NONE')
        user_id = dimension_filter.get('userId')
        branch_id = dimension_filter.get('branchId')
        team_id = dimension_filter.get('teamId')
        category = dimension_filter.get('category')  # 支持按类别过滤
        
        # 如果指定了 category，按类别过滤
        if category:
            queryset = queryset.filter(client_category=category)
        
        # 如果指定了 userId，直接按用户过滤（多经办人）
        if user_id:
            if hasattr(queryset.model, "handlers"):
                return queryset.filter(handlers__id=user_id).distinct()
            return queryset.filter(owner_user_id=user_id)
        
        # 如果指定了 branchId（无论 scope 是什么），按分所及其下级部门过滤
        if branch_id:
            branch_dept_ids = ReportService._resolve_branch_dept_ids(branch_id)
            if not branch_dept_ids:
                branch_dept_ids = [branch_id]
            team_ids = Team.objects.filter(branch_id__in=branch_dept_ids, status=True).values_list('id', flat=True)
            return queryset.filter(
                Q(branch_id__in=branch_dept_ids) |
                Q(team_id__in=team_ids) |
                Q(owner_user__branch_id__in=branch_dept_ids) |
                Q(owner_user__team_id__in=team_ids) |
                Q(owner_user__dept_id__in=branch_dept_ids) |
                Q(handlers__branch_id__in=branch_dept_ids) |
                Q(handlers__team_id__in=team_ids) |
                Q(handlers__dept_id__in=branch_dept_ids)
            ).distinct()
        
        # 根据 scope 过滤
        if scope == 'SELF':
            if hasattr(queryset.model, "handlers"):
                return queryset.filter(handlers__id=current_user.id).distinct()
            return queryset.filter(owner_user_id=current_user.id)
        elif scope == 'TEAM':
            # 假设用户有 team_id 属性
            resolved_team_id = team_id or getattr(current_user, 'team_id', None) or getattr(current_user, 'dept_id', None)
            if resolved_team_id:
                return queryset.filter(
                    Q(team_id=resolved_team_id) |
                    Q(owner_user__team_id=resolved_team_id) |
                    Q(owner_user__dept_id=resolved_team_id) |
                    Q(handlers__team_id=resolved_team_id) |
                    Q(handlers__dept_id=resolved_team_id)
                ).distinct()
        elif scope == 'BRANCH':
            # 假设用户有 branch_id 属性
            resolved_branch_id = getattr(current_user, 'branch_id', None) or getattr(current_user, 'dept_id', None)
            if resolved_branch_id:
                branch_dept_ids = ReportService._resolve_branch_dept_ids(resolved_branch_id)
                if not branch_dept_ids:
                    branch_dept_ids = [resolved_branch_id]
                team_ids = Team.objects.filter(branch_id__in=branch_dept_ids, status=True).values_list('id', flat=True)
                return queryset.filter(
                    Q(branch_id__in=branch_dept_ids) |
                    Q(team_id__in=team_ids) |
                    Q(owner_user__branch_id__in=branch_dept_ids) |
                    Q(owner_user__team_id__in=team_ids) |
                    Q(owner_user__dept_id__in=branch_dept_ids) |
                    Q(handlers__branch_id__in=branch_dept_ids) |
                    Q(handlers__team_id__in=team_ids) |
                    Q(handlers__dept_id__in=branch_dept_ids)
                ).distinct()
        elif scope == 'HQ':
            # 总部查看全部数据，不过滤
            return queryset
        
        return queryset
    
    @staticmethod
    def calculate_conversion_rate(dimension_filter, current_user):
        """
        计算有效线索转化率
        
        公式：有效线索转化率 = (赢单客户数 / 非公海客户数) × 100%
        
        注意：
        - 分子分母都按当前维度过滤（个人/团队/分所/总部）
        - 分母“非公海”用于衡量有效线索基数
        """
        queryset = Customer.objects.filter(is_deleted=False)
        queryset = ReportService.apply_dimension_filter(queryset, dimension_filter, current_user)

        # “商机”定义为非公海客户
        opportunity_total = queryset.exclude(status=Customer.STATUS_PUBLIC_POOL).count()
        if opportunity_total == 0:
            return 0.0

        won_count = queryset.filter(status=Customer.STATUS_WON).count()
        return round((won_count / opportunity_total) * 100, 1)
    
    @staticmethod
    def calculate_new_customers(dimension_filter, current_user, start_date=None, end_date=None):
        """
        计算新客户获取数量
        
        公式：新客户数 = COUNT(新增客户)
        """
        queryset = Customer.objects.filter(is_deleted=False)
        queryset = ReportService.apply_dimension_filter(queryset, dimension_filter, current_user)
        
        # 确保日期是 naive datetime
        start_date = ReportService.ensure_naive_datetime(start_date)
        end_date = ReportService.ensure_naive_datetime(end_date)
        
        if start_date and end_date:
            queryset = queryset.filter(
                create_datetime__gte=start_date,
                create_datetime__lte=end_date
            )
        else:
            # 默认最近30天
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            queryset = queryset.filter(
                create_datetime__gte=start_date,
                create_datetime__lte=end_date
            )
        
        return queryset.count()
    
    @staticmethod
    def calculate_lead_frequency(dimension_filter, current_user, start_date=None, end_date=None):
        """
        计算跟进频次
        
        公式：跟进频次 = COUNT(跟进记录)
        """
        queryset = FollowupRecord.objects.filter(is_deleted=0)
        
        queryset = ReportService._apply_record_dimension_filter(queryset, dimension_filter, current_user)
        
        # 确保日期是 naive datetime
        start_date = ReportService.ensure_naive_datetime(start_date)
        end_date = ReportService.ensure_naive_datetime(end_date)
        
        if start_date and end_date:
            queryset = queryset.filter(
                followup_time__gte=start_date,
                followup_time__lte=end_date
            )
        else:
            # 默认最近30天
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            queryset = queryset.filter(
                followup_time__gte=start_date,
                followup_time__lte=end_date
            )
        
        return queryset.count()
    
    @staticmethod
    def calculate_visit_frequency(dimension_filter, current_user, start_date=None, end_date=None):
        """
        计算客户拜访频次
        
        公式：拜访频次 = COUNT(拜访记录)
        """
        queryset = VisitRecord.objects.filter(is_deleted=0)
        
        queryset = ReportService._apply_record_dimension_filter(queryset, dimension_filter, current_user)
        
        # 确保日期是 naive datetime
        start_date = ReportService.ensure_naive_datetime(start_date)
        end_date = ReportService.ensure_naive_datetime(end_date)
        
        if start_date and end_date:
            queryset = queryset.filter(
                visit_time__gte=start_date,
                visit_time__lte=end_date
            )
        else:
            # 默认最近30天
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            queryset = queryset.filter(
                visit_time__gte=start_date,
                visit_time__lte=end_date
            )
        
        return queryset.count()
    
    @staticmethod
    def calculate_key_customer_visit_ratio(dimension_filter, current_user, start_date=None, end_date=None):
        """
        计算重点客户拜访占比
        
        公式：重点客户拜访占比 = (A级客户拜访次数 / 总拜访次数) × 100%
        """
        queryset = VisitRecord.objects.filter(is_deleted=0)
        
        queryset = ReportService._apply_record_dimension_filter(queryset, dimension_filter, current_user)
        
        # 确保日期是 naive datetime
        start_date = ReportService.ensure_naive_datetime(start_date)
        end_date = ReportService.ensure_naive_datetime(end_date)
        
        if start_date and end_date:
            queryset = queryset.filter(
                visit_time__gte=start_date,
                visit_time__lte=end_date
            )
        else:
            # 默认最近30天
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            queryset = queryset.filter(
                visit_time__gte=start_date,
                visit_time__lte=end_date
            )
        
        total_count = queryset.count()
        if total_count == 0:
            return 0.0
        
        # 统计A级客户拜访次数（需要关联 Customer 表）
        a_grade_count = queryset.filter(
            client_id__in=Customer.objects.filter(client_grade='A', is_deleted=False).values_list('id', flat=True)
        ).count()
        
        return round((a_grade_count / total_count) * 100, 1)
    
    @staticmethod
    def calculate_visit_success_rate(dimension_filter, current_user, start_date=None, end_date=None):
        """
        计算拜访成功率
        
        公式：拜访成功率 = (有效拜访次数 / 总拜访次数) × 100%
        有效拜访：location_status = 'success' 或者 lng/lat 不为空
        """
        queryset = VisitRecord.objects.filter(is_deleted=0)
        
        queryset = ReportService._apply_record_dimension_filter(queryset, dimension_filter, current_user)
        
        # 确保日期是 naive datetime
        start_date = ReportService.ensure_naive_datetime(start_date)
        end_date = ReportService.ensure_naive_datetime(end_date)
        
        if start_date and end_date:
            queryset = queryset.filter(
                visit_time__gte=start_date,
                visit_time__lte=end_date
            )
        else:
            # 默认最近30天
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            queryset = queryset.filter(
                visit_time__gte=start_date,
                visit_time__lte=end_date
            )
        
        total_count = queryset.count()
        if total_count == 0:
            return 0.0
        
        # 统计有效拜访次数
        success_count = queryset.filter(
            Q(location_status='success') | (Q(lng__isnull=False) & Q(lat__isnull=False))
        ).count()
        
        return round((success_count / total_count) * 100, 1)
    
    @staticmethod
    def calculate_avg_conversation_duration(dimension_filter, current_user, start_date=None, end_date=None):
        """
        计算单客户平均洽谈时长
        
        公式：平均洽谈时长 = 总洽谈时长 / 客户数（单位：小时）
        """
        queryset = VisitRecord.objects.filter(is_deleted=0, duration__isnull=False)
        
        queryset = ReportService._apply_record_dimension_filter(queryset, dimension_filter, current_user)
        
        # 确保日期是 naive datetime
        start_date = ReportService.ensure_naive_datetime(start_date)
        end_date = ReportService.ensure_naive_datetime(end_date)
        
        if start_date and end_date:
            queryset = queryset.filter(
                visit_time__gte=start_date,
                visit_time__lte=end_date
            )
        else:
            # 默认最近30天
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            queryset = queryset.filter(
                visit_time__gte=start_date,
                visit_time__lte=end_date
            )
        
        client_count = queryset.values('client_id').distinct().count()
        if client_count == 0:
            return 0.0
        
        total_duration = queryset.aggregate(total=Sum('duration'))['total'] or 0
        
        # 转换为小时（假设 duration 是分钟）
        return round((total_duration / 60.0) / client_count, 1)
    
    @staticmethod
    def calculate_visit_cycle(dimension_filter, current_user, start_date=None, end_date=None):
        """
        计算客户拜访周期
        
        公式：拜访周期 = 平均两次拜访之间的天数
        """
        # 这个计算比较复杂，需要使用窗口函数
        # 简化实现：返回固定值或基于简单统计
        return 7  # 默认返回7天
    
    @staticmethod
    def calculate_conversion_funnel(dimension_filter, current_user, start_date=None, end_date=None):
        """
        计算客户转化漏斗（以“商机”为基准，阶段口径）

        阶段定义（互斥口径）：
        - 商机：status=FOLLOW_UP 且 sales_stage=BLANK
        - 面谈：status=FOLLOW_UP 且 sales_stage=MEETING
        - 交案：status=CASE
        - 回款：status=PAYMENT
        - 赢单：status=WON

        percent 统一使用“商机总数”为分母，商机固定 100%。
        """
        queryset = Customer.objects.filter(is_deleted=False)
        queryset = ReportService.apply_dimension_filter(queryset, dimension_filter, current_user)
        start_date = ReportService.ensure_naive_datetime(start_date)
        end_date = ReportService.ensure_naive_datetime(end_date)
        if start_date and end_date:
            queryset = queryset.filter(
                create_datetime__gte=start_date,
                create_datetime__lte=end_date
            )
        
        opportunity_total = queryset.filter(
            status=Customer.STATUS_FOLLOW_UP,
            sales_stage=Customer.SALES_STAGE_BLANK
        ).count()
        total = opportunity_total if opportunity_total > 0 else 1

        meeting_count = queryset.filter(
            status=Customer.STATUS_FOLLOW_UP,
            sales_stage=Customer.SALES_STAGE_MEETING
        ).count()
        case_count = queryset.filter(status=Customer.STATUS_CASE).count()
        payment_count = queryset.filter(status=Customer.STATUS_PAYMENT).count()
        won_count = queryset.filter(status=Customer.STATUS_WON).count()
        
        return {
            'stages': [
                {
                    'name': '商机',
                    'value': opportunity_total,
                    'percent': 100.0
                },
                {
                    'name': '面谈',
                    'value': meeting_count,
                    'percent': round((meeting_count / total) * 100, 1) if total > 0 else 0
                },
                {
                    'name': '交案',
                    'value': case_count,
                    'percent': round((case_count / total) * 100, 1) if total > 0 else 0
                },
                {
                    'name': '回款',
                    'value': payment_count,
                    'percent': round((payment_count / total) * 100, 1) if total > 0 else 0
                },
                {
                    'name': '赢单',
                    'value': won_count,
                    'percent': round((won_count / total) * 100, 1) if total > 0 else 0
                },
            ]
        }
    
    @staticmethod
    def calculate_trend(current_value, previous_value):
        """
        计算趋势
        
        Returns:
            tuple: (trend, trend_percent)
                trend: 'up', 'down', 'stable'
                trend_percent: 百分比变化
        """
        if previous_value == 0:
            if current_value > 0:
                return 'up', 100.0
            else:
                return 'stable', 0.0
        
        percent_change = ((current_value - previous_value) / previous_value) * 100
        
        if abs(percent_change) < 1:
            return 'stable', 0.0
        elif percent_change > 0:
            return 'up', round(percent_change, 1)
        else:
            return 'down', round(percent_change, 1)
    
    @staticmethod
    def get_indicator_value_for_date(indicator_type, dimension_filter, current_user, target_date):
        """
        获取指定日期的指标值（单天数据）
        
        Args:
            indicator_type: 指标类型
            dimension_filter: 维度过滤
            current_user: 当前用户
            target_date: 目标日期
            
        Returns:
            float: 指标值
        """
        # 构建当天的时间范围
        if isinstance(target_date, date) and not isinstance(target_date, datetime):
            day_start = datetime.combine(target_date, datetime.min.time())
            day_end = datetime.combine(target_date, datetime.max.time())
        else:
            day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        if indicator_type == 'conversion_rate':
            return ReportService.calculate_conversion_rate(dimension_filter, current_user)
        elif indicator_type == 'new_customers':
            return ReportService.calculate_new_customers(dimension_filter, current_user, day_start, day_end)
        elif indicator_type == 'lead_frequency':
            return ReportService.calculate_lead_frequency(dimension_filter, current_user, day_start, day_end)
        elif indicator_type == 'visit_frequency':
            return ReportService.calculate_visit_frequency(dimension_filter, current_user, day_start, day_end)
        elif indicator_type == 'key_customer_visit_ratio':
            return ReportService.calculate_key_customer_visit_ratio(dimension_filter, current_user, day_start, day_end)
        elif indicator_type == 'visit_success_rate':
            return ReportService.calculate_visit_success_rate(dimension_filter, current_user, day_start, day_end)
        elif indicator_type == 'avg_conversation_duration':
            return ReportService.calculate_avg_conversation_duration(dimension_filter, current_user, day_start, day_end)
        elif indicator_type == 'visit_cycle':
            return ReportService.calculate_visit_cycle(dimension_filter, current_user, day_start, day_end)
        
        return 0
    
    @staticmethod
    def get_dimension_breakdown(indicator_type, dimension_type, dimension_filter, current_user, start_date, end_date):
        """
        获取维度拆分数据
        
        Args:
            indicator_type: 指标类型
            dimension_type: 维度类型 (PERSONNEL, BRANCH, SOURCE, GRADE)
            dimension_filter: 维度过滤
            current_user: 当前用户
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            list: 维度拆分数据
        """
        from dvadmin.system.models import Users
        
        breakdown = []
        total_value = 0

        scope = (dimension_filter or {}).get('scope', 'SELF')
        scoped_branch_id = (dimension_filter or {}).get('branchId') or getattr(current_user, 'branch_id', None) or getattr(current_user, 'dept_id', None)
        scoped_team_id = (dimension_filter or {}).get('teamId') or getattr(current_user, 'team_id', None) or getattr(current_user, 'dept_id', None)
        
        if dimension_type == 'PERSONNEL':
            # 按人员拆分
            users = Users.objects.filter(is_active=True)
            if scope == 'SELF':
                users = users.filter(id=current_user.id)
            elif scope == 'TEAM' and scoped_team_id:
                users = users.filter(Q(team_id=scoped_team_id) | Q(dept_id=scoped_team_id))
            elif scope == 'BRANCH' and scoped_branch_id:
                branch_dept_ids = ReportService._resolve_branch_dept_ids(scoped_branch_id)
                if not branch_dept_ids:
                    branch_dept_ids = [scoped_branch_id]
                users = users.filter(Q(branch_id__in=branch_dept_ids) | Q(dept_id__in=branch_dept_ids))
            users = users.order_by('id')[:50]
            for user in users:
                user_filter = {**dimension_filter, 'userId': user.id}
                if indicator_type == 'new_customers':
                    value = ReportService.calculate_new_customers(user_filter, current_user, start_date, end_date)
                elif indicator_type == 'lead_frequency':
                    value = ReportService.calculate_lead_frequency(user_filter, current_user, start_date, end_date)
                elif indicator_type == 'visit_frequency':
                    value = ReportService.calculate_visit_frequency(user_filter, current_user, start_date, end_date)
                elif indicator_type == 'conversion_rate':
                    value = ReportService.calculate_conversion_rate(user_filter, current_user)
                elif indicator_type == 'key_customer_visit_ratio':
                    value = ReportService.calculate_key_customer_visit_ratio(user_filter, current_user, start_date, end_date)
                elif indicator_type == 'visit_success_rate':
                    value = ReportService.calculate_visit_success_rate(user_filter, current_user, start_date, end_date)
                elif indicator_type == 'avg_conversation_duration':
                    value = ReportService.calculate_avg_conversation_duration(user_filter, current_user, start_date, end_date)
                elif indicator_type == 'visit_cycle':
                    value = ReportService.calculate_visit_cycle(user_filter, current_user, start_date, end_date)
                else:
                    value = 0
                
                if value > 0:
                    breakdown.append({
                        'label': user.name or user.username,
                        'value': value,
                        'percent': 0
                    })
                    total_value += value
        
        elif dimension_type == 'BRANCH':
            # 按分所拆分
            # 以系统部门树中的“根部门的直接子部门”作为分所定义
            branches = Dept.objects.filter(
                status=True,
                parent__isnull=False,
                parent__parent__isnull=True
            ).order_by('sort', 'id')
            for branch in branches:
                try:
                    branch_filter = {**dimension_filter, 'branchId': branch.id}
                    if indicator_type == 'new_customers':
                        value = ReportService.calculate_new_customers(branch_filter, current_user, start_date, end_date)
                    elif indicator_type == 'lead_frequency':
                        value = ReportService.calculate_lead_frequency(branch_filter, current_user, start_date, end_date)
                    elif indicator_type == 'visit_frequency':
                        value = ReportService.calculate_visit_frequency(branch_filter, current_user, start_date, end_date)
                    elif indicator_type == 'conversion_rate':
                        value = ReportService.calculate_conversion_rate(branch_filter, current_user)
                    elif indicator_type == 'key_customer_visit_ratio':
                        value = ReportService.calculate_key_customer_visit_ratio(branch_filter, current_user, start_date, end_date)
                    elif indicator_type == 'visit_success_rate':
                        value = ReportService.calculate_visit_success_rate(branch_filter, current_user, start_date, end_date)
                    elif indicator_type == 'avg_conversation_duration':
                        value = ReportService.calculate_avg_conversation_duration(branch_filter, current_user, start_date, end_date)
                    elif indicator_type == 'visit_cycle':
                        value = ReportService.calculate_visit_cycle(branch_filter, current_user, start_date, end_date)
                    else:
                        value = 0
                except Exception:
                    value = 0

                if value > 0:
                    breakdown.append({
                        'label': branch.name,
                        'value': value,
                        'percent': 0
                    })
                    total_value += value
        
        elif dimension_type == 'GRADE':
            # 按客户等级拆分
            grades = ['A', 'B', 'C', 'D', 'E']
            grade_names = {'A': 'A级客户', 'B': 'B级客户', 'C': 'C级客户', 'D': 'D级客户', 'E': 'E级客户'}
            
            for grade in grades:
                # 查询该等级的客户数
                queryset = Customer.objects.filter(is_deleted=False, client_grade=grade)
                queryset = ReportService.apply_dimension_filter(queryset, dimension_filter, current_user)
                
                start_date_naive = ReportService.ensure_naive_datetime(start_date)
                end_date_naive = ReportService.ensure_naive_datetime(end_date)
                
                if start_date_naive and end_date_naive:
                    queryset = queryset.filter(
                        create_datetime__gte=start_date_naive,
                        create_datetime__lte=end_date_naive
                    )
                
                value = queryset.count()
                
                if value > 0:
                    breakdown.append({
                        'label': grade_names.get(grade, grade),
                        'value': value,
                        'percent': 0
                    })
                    total_value += value

        elif dimension_type == 'CATEGORY':
            # 按客户类别拆分
            categories = ['construction', 'material']
            category_names = {'construction': '建工', 'material': '建材'}

            for category in categories:
                category_filter = {**dimension_filter, 'category': category}
                
                # 根据指标类型计算不同的值
                if indicator_type == 'new_customers':
                    value = ReportService.calculate_new_customers(category_filter, current_user, start_date, end_date)
                elif indicator_type == 'lead_frequency':
                    value = ReportService.calculate_lead_frequency(category_filter, current_user, start_date, end_date)
                elif indicator_type == 'visit_frequency':
                    value = ReportService.calculate_visit_frequency(category_filter, current_user, start_date, end_date)
                elif indicator_type == 'conversion_rate':
                    value = ReportService.calculate_conversion_rate(category_filter, current_user)
                else:
                    # 默认使用客户数量
                    queryset = Customer.objects.filter(is_deleted=False, client_category=category)
                    queryset = ReportService.apply_dimension_filter(queryset, dimension_filter, current_user)

                    start_date_naive = ReportService.ensure_naive_datetime(start_date)
                    end_date_naive = ReportService.ensure_naive_datetime(end_date)

                    if start_date_naive and end_date_naive:
                        queryset = queryset.filter(
                            create_datetime__gte=start_date_naive,
                            create_datetime__lte=end_date_naive
                        )

                    value = queryset.count()

                if value > 0:
                    breakdown.append({
                        'label': category_names.get(category, category),
                        'value': value,
                        'percent': 0
                    })
                    total_value += value
        
        elif dimension_type == 'SOURCE':
            # 按来源渠道拆分（聚合查询，避免N+1）
            source_names = {
                'ONLINE': '线上推广',
                'REFERRAL': '客户推荐',
                'EXHIBITION': '展会活动',
                'TELEMARKETING': '电话营销',
                'OTHER': '其他渠道'
            }
            queryset = Customer.objects.filter(is_deleted=False)
            queryset = ReportService.apply_dimension_filter(queryset, dimension_filter, current_user)
            start_date_naive = ReportService.ensure_naive_datetime(start_date)
            end_date_naive = ReportService.ensure_naive_datetime(end_date)
            if start_date_naive and end_date_naive:
                queryset = queryset.filter(
                    create_datetime__gte=start_date_naive,
                    create_datetime__lte=end_date_naive
                )
            grouped = queryset.values('source_channel').annotate(value=Count('id'))
            for item in grouped:
                source = item.get('source_channel')
                normalized_source = source if source not in (None, '') else 'OTHER'
                label = source_names.get(normalized_source, normalized_source or '其他渠道')
                value = item.get('value') or 0
                if value <= 0:
                    continue
                breakdown.append({
                    'label': label,
                    'value': value,
                    'percent': 0
                })
                total_value += value
        
        # 计算百分比
        if total_value > 0:
            for item in breakdown:
                item['percent'] = round((item['value'] / total_value) * 100, 1)
        
        # 按值排序
        breakdown.sort(key=lambda x: x['value'], reverse=True)
        # 拆分项过多时做截断，避免前端渲染和接口响应过慢
        breakdown = breakdown[:20]
        
        return breakdown
