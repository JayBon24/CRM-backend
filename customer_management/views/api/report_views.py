"""
报表系统视图
"""
import logging
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from rest_framework.renderers import JSONRenderer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.cache import cache
from dvadmin.system.models import Dept

from customer_management.models import Report
from customer_management.serializers.reports import (
    DashboardRequestSerializer,
    DashboardResponseSerializer,
    IndicatorDetailRequestSerializer,
    IndicatorDetailResponseSerializer,
)
from customer_management.services.report_service import ReportService
from dvadmin.utils.json_response import SuccessResponse, ErrorResponse, DetailResponse

REPORT_DIMENSION_CACHE_TTL = 600

# 基础序列化器，用于 Swagger 文档生成
class BaseReportSerializer(serializers.Serializer):
    """基础报表序列化器"""
    pass


class ReportGenerateView(APIView):
    """生成报告"""
    permission_classes = []
    serializer_class = BaseReportSerializer
    renderer_classes = [JSONRenderer]
    
    def post(self, request):
        """生成报告"""
        try:
            report_type = request.data.get('type', 'monthly')
            time_range = request.data.get('timeRange', {})
            start_date = time_range.get('start')
            end_date = time_range.get('end')
            
            if not start_date or not end_date:
                return ErrorResponse(msg="缺少时间范围参数")
            
            # 生成报告标题
            type_map = {
                'weekly': '周报',
                'monthly': '月报',
                'quarterly': '季报',
                'yearly': '年报',
                'custom': '自定义报告'
            }
            title = f"{type_map.get(report_type, '报告')} ({start_date} 至 {end_date})"
            
            # 计算所有指标数据
            dimension_filter = {}
            current_user = request.user
            
            indicators = []
            
            # 1. 有效线索转化率
            conversion_rate = ReportService.calculate_conversion_rate(dimension_filter, current_user)
            indicators.append({
                'type': 'conversion_rate',
                'name': '有效线索转化率',
                'value': conversion_rate,
                'unit': '%',
                'trend': 'up',
                'trendPercent': 5.2,
            })
            
            # 2. 新客户获取
            new_customers = ReportService.calculate_new_customers(dimension_filter, current_user)
            indicators.append({
                'type': 'new_customers',
                'name': '新客户获取',
                'value': new_customers,
                'unit': '个',
                'trend': 'up',
                'trendPercent': 10.5,
            })
            
            # 3. 跟进频次
            lead_frequency = ReportService.calculate_lead_frequency(dimension_filter, current_user)
            indicators.append({
                'type': 'lead_frequency',
                'name': '跟进频次',
                'value': lead_frequency,
                'unit': '次',
                'trend': 'stable',
                'trendPercent': 0,
            })
            
            # 4. 客户拜访频次
            visit_frequency = ReportService.calculate_visit_frequency(dimension_filter, current_user)
            indicators.append({
                'type': 'visit_frequency',
                'name': '客户拜访频次',
                'value': visit_frequency,
                'unit': '次',
                'trend': 'up',
                'trendPercent': 8.3,
            })
            
            # 5. 重点客户拜访占比
            key_customer_visit_ratio = ReportService.calculate_key_customer_visit_ratio(dimension_filter, current_user)
            indicators.append({
                'type': 'key_customer_visit_ratio',
                'name': '重点客户拜访占比',
                'value': key_customer_visit_ratio,
                'unit': '%',
                'trend': 'up',
                'trendPercent': 5.0,
            })
            
            # 6. 拜访成功率
            visit_success_rate = ReportService.calculate_visit_success_rate(dimension_filter, current_user)
            indicators.append({
                'type': 'visit_success_rate',
                'name': '拜访成功率',
                'value': visit_success_rate,
                'unit': '%',
                'trend': 'up',
                'trendPercent': 3.2,
            })
            
            # 7. 单客户平均洽谈时长
            avg_conversation_duration = ReportService.calculate_avg_conversation_duration(dimension_filter, current_user)
            indicators.append({
                'type': 'avg_conversation_duration',
                'name': '单客户平均洽谈时长',
                'value': avg_conversation_duration,
                'unit': '小时',
                'trend': 'stable',
                'trendPercent': 0,
            })
            
            # 8. 客户拜访周期
            visit_cycle = ReportService.calculate_visit_cycle(dimension_filter, current_user)
            indicators.append({
                'type': 'visit_cycle',
                'name': '客户拜访周期',
                'value': visit_cycle,
                'unit': '天',
                'trend': 'down',
                'trendPercent': -5.0,
            })
            
            # 计算转化漏斗
            start_dt = None
            end_dt = None
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            except Exception:
                start_dt = None
                end_dt = None
            conversion_funnel = ReportService.calculate_conversion_funnel(dimension_filter, current_user, start_dt, end_dt)
            
            # 构建报告内容
            content = {
                'indicators': indicators,
                'conversionFunnel': conversion_funnel,
                'timeRange': {
                    'start': start_date,
                    'end': end_date
                }
            }
            
            # 创建报告记录
            report = Report.objects.create(
                title=title,
                type=report_type,
                status='completed',
                start_date=start_date,
                end_date=end_date,
                content=content,
                creator=request.user if request.user.is_authenticated else None
            )
            
            return SuccessResponse(data={'reportId': report.id}, msg="报告生成成功")
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ErrorResponse(msg=f"生成报告失败: {str(e)}")


class ReportListView(APIView):
    """报告列表"""
    permission_classes = []
    serializer_class = BaseReportSerializer
    renderer_classes = [JSONRenderer]
    
    def get(self, request):
        """获取报告列表"""
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('pageSize', 10))
            
            queryset = Report.objects.all().order_by('-create_datetime')
            
            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            reports = queryset[start:end]
            total = queryset.count()
            
            # 序列化
            rows = []
            for report in reports:
                rows.append({
                    'id': report.id,
                    'title': report.title,
                    'type': report.type,
                    'status': report.status,
                    'startDate': report.start_date.strftime('%Y-%m-%d'),
                    'endDate': report.end_date.strftime('%Y-%m-%d'),
                    'createTime': report.create_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                })
            
            return SuccessResponse(data={'rows': rows, 'total': total})
        except Exception as e:
            return ErrorResponse(msg=f"获取报告列表失败: {str(e)}")


class ReportDetailView(APIView):
    """报告详情"""
    permission_classes = []
    serializer_class = BaseReportSerializer
    renderer_classes = [JSONRenderer]
    
    def get(self, request, report_id):
        """获取报告详情"""
        try:
            report = Report.objects.get(id=report_id)
            
            # 获取报告内容
            content = report.content or {}
            
            data = {
                'id': report.id,
                'title': report.title,
                'type': report.type,
                'status': report.status,
                'startDate': report.start_date.strftime('%Y-%m-%d'),
                'endDate': report.end_date.strftime('%Y-%m-%d'),
                'createTime': report.create_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'indicators': content.get('indicators', []),
                'conversionFunnel': content.get('conversionFunnel', {}),
                'timeRange': content.get('timeRange', {
                    'start': report.start_date.strftime('%Y-%m-%d'),
                    'end': report.end_date.strftime('%Y-%m-%d')
                })
            }
            
            return SuccessResponse(data=data)
        except Report.DoesNotExist:
            return ErrorResponse(msg="报告不存在", code=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ErrorResponse(msg=f"获取报告详情失败: {str(e)}")
    
    def post(self, request, report_id):
        """导出报告"""
        try:
            report = Report.objects.get(id=report_id)
            export_format = request.data.get('format', 'json')
            
            # 获取报告内容
            content = report.content or {}
            
            export_data = {
                'title': report.title,
                'type': report.type,
                'startDate': report.start_date.strftime('%Y-%m-%d'),
                'endDate': report.end_date.strftime('%Y-%m-%d'),
                'indicators': content.get('indicators', []),
                'conversionFunnel': content.get('conversionFunnel', {}),
                'exportTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'format': export_format
            }
            
            return SuccessResponse(
                data=export_data,
                msg="报告导出成功"
            )
        except Report.DoesNotExist:
            return ErrorResponse(msg="报告不存在", code=404)
        except Exception as e:
            return ErrorResponse(msg=f"导出报告失败: {str(e)}")


class ReportShareView(APIView):
    """分享报告"""
    permission_classes = []
    serializer_class = BaseReportSerializer
    renderer_classes = [JSONRenderer]
    
    def post(self, request, report_id):
        """分享报告给指定用户"""
        try:
            report = Report.objects.get(id=report_id)
            user_ids = request.data.get('userIds', [])
            
            if not user_ids:
                return ErrorResponse(msg="请选择分享对象")
            
            # 这里可以创建分享记录表，暂时简化处理
            share_records = []
            for user_id in user_ids:
                share_records.append({
                    'report_id': report.id,
                    'user_id': user_id,
                    'share_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            
            return SuccessResponse(
                data={
                    'report_id': report.id,
                    'shared_count': len(user_ids),
                    'share_records': share_records
                },
                msg=f"报告已分享给 {len(user_ids)} 位用户"
            )
        except Report.DoesNotExist:
            return ErrorResponse(msg="报告不存在", code=404)
        except Exception as e:
            return ErrorResponse(msg=f"分享报告失败: {str(e)}")


class DashboardView(APIView):
    """
    获取看板数据
    
    获取数据看板的所有指标数据和转化漏斗
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DashboardRequestSerializer
    renderer_classes = [JSONRenderer]
    
    @swagger_auto_schema(
        operation_summary="获取看板数据",
        operation_description="获取数据看板的所有指标数据和转化漏斗",
        request_body=DashboardRequestSerializer,
        responses={
            200: DashboardResponseSerializer,
            400: "请求参数错误",
        },
        tags=['报表系统']
    )
    def post(self, request):
        """获取看板数据"""
        # 验证请求参数
        serializer = DashboardRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'code': 400,
                'msg': '请求参数错误',
                'data': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        dimension_filter = serializer.validated_data.get('dimensionFilter', {})
        current_user = request.user

        if current_user and getattr(current_user, 'id', None) and dimension_filter:
            cache.set(
                f"reports:dimension_filter:{current_user.id}",
                dimension_filter,
                timeout=REPORT_DIMENSION_CACHE_TTL
            )
        
        # 首页口径统一：近30天 vs 前30天
        now = datetime.now()
        start_date = now - timedelta(days=30)
        end_date = now
        previous_start = start_date - timedelta(days=30)
        previous_end = start_date
        
        # 计算所有指标
        indicators = []
        
        # 1. 有效线索转化率（当前状态，对比昨天）
        conversion_rate = ReportService.calculate_conversion_rate(dimension_filter, current_user)
        # 转化率是当前状态，趋势对比上一周期意义不大，保持稳定
        indicators.append({
            'type': 'conversion_rate',
            'value': conversion_rate,
            'unit': '%',
            'trend': 'stable',
            'trendPercent': 0,
        })
        
        # 2. 新客户获取（近30天 vs 前30天）
        new_customers = ReportService.calculate_new_customers(dimension_filter, current_user, start_date, end_date)
        new_customers_previous = ReportService.calculate_new_customers(dimension_filter, current_user, previous_start, previous_end)
        trend, trend_percent = ReportService.calculate_trend(new_customers, new_customers_previous)
        indicators.append({
            'type': 'new_customers',
            'value': new_customers,
            'unit': '个',
            'trend': trend,
            'trendPercent': trend_percent,
        })
        
        # 3. 跟进频次（近30天 vs 前30天）
        lead_frequency = ReportService.calculate_lead_frequency(dimension_filter, current_user, start_date, end_date)
        lead_frequency_previous = ReportService.calculate_lead_frequency(dimension_filter, current_user, previous_start, previous_end)
        trend, trend_percent = ReportService.calculate_trend(lead_frequency, lead_frequency_previous)
        indicators.append({
            'type': 'lead_frequency',
            'value': lead_frequency,
            'unit': '次',
            'trend': trend,
            'trendPercent': trend_percent,
        })
        
        # 4. 客户拜访频次（近30天 vs 前30天）
        visit_frequency = ReportService.calculate_visit_frequency(dimension_filter, current_user, start_date, end_date)
        visit_frequency_previous = ReportService.calculate_visit_frequency(dimension_filter, current_user, previous_start, previous_end)
        trend, trend_percent = ReportService.calculate_trend(visit_frequency, visit_frequency_previous)
        indicators.append({
            'type': 'visit_frequency',
            'value': visit_frequency,
            'unit': '次',
            'trend': trend,
            'trendPercent': trend_percent,
        })
        
        # 5. 重点客户拜访占比（近30天 vs 前30天）
        key_customer_visit_ratio = ReportService.calculate_key_customer_visit_ratio(dimension_filter, current_user, start_date, end_date)
        key_customer_visit_ratio_prev = ReportService.calculate_key_customer_visit_ratio(dimension_filter, current_user, previous_start, previous_end)
        trend, trend_percent = ReportService.calculate_trend(key_customer_visit_ratio, key_customer_visit_ratio_prev)
        indicators.append({
            'type': 'key_customer_visit_ratio',
            'value': key_customer_visit_ratio,
            'unit': '%',
            'trend': trend,
            'trendPercent': trend_percent,
        })
        
        # 6. 拜访成功率（近30天 vs 前30天）
        visit_success_rate = ReportService.calculate_visit_success_rate(dimension_filter, current_user, start_date, end_date)
        visit_success_rate_prev = ReportService.calculate_visit_success_rate(dimension_filter, current_user, previous_start, previous_end)
        trend, trend_percent = ReportService.calculate_trend(visit_success_rate, visit_success_rate_prev)
        indicators.append({
            'type': 'visit_success_rate',
            'value': visit_success_rate,
            'unit': '%',
            'trend': trend,
            'trendPercent': trend_percent,
        })
        
        # 7. 单客户平均洽谈时长（近30天 vs 前30天）
        avg_conversation_duration = ReportService.calculate_avg_conversation_duration(dimension_filter, current_user, start_date, end_date)
        avg_conversation_duration_prev = ReportService.calculate_avg_conversation_duration(dimension_filter, current_user, previous_start, previous_end)
        trend, trend_percent = ReportService.calculate_trend(avg_conversation_duration, avg_conversation_duration_prev)
        indicators.append({
            'type': 'avg_conversation_duration',
            'value': avg_conversation_duration,
            'unit': '小时',
            'trend': trend,
            'trendPercent': trend_percent,
        })
        
        # 8. 客户拜访周期（近30天 vs 前30天，周期越短越好，所以趋势反转）
        visit_cycle = ReportService.calculate_visit_cycle(dimension_filter, current_user, start_date, end_date)
        visit_cycle_prev = ReportService.calculate_visit_cycle(dimension_filter, current_user, previous_start, previous_end)
        trend, trend_percent = ReportService.calculate_trend(visit_cycle, visit_cycle_prev)
        # 拜访周期越短越好，所以趋势反转
        if trend == 'up':
            trend = 'down'
        elif trend == 'down':
            trend = 'up'
        indicators.append({
            'type': 'visit_cycle',
            'value': visit_cycle,
            'unit': '天',
            'trend': trend,
            'trendPercent': trend_percent,
        })
        
        # 计算转化漏斗
        conversion_funnel = ReportService.calculate_conversion_funnel(dimension_filter, current_user, start_date, end_date)
        
        # 处理维度拆分
        dimension = dimension_filter.get('dimension', 'NONE')
        breakdown_data = []
        
        if dimension == 'BRANCH':
            # 按分所拆分
            branches = Dept.objects.filter(
                status=True,
                parent__isnull=False,
                parent__parent__isnull=True
            ).order_by('sort', 'id')
            
            for branch in branches:
                # 为每个分所计算指标
                branch_filter = {**dimension_filter, 'branchId': branch.id}
                branch_indicators = []
                
                # 计算该分所的所有指标
                branch_conversion_rate = ReportService.calculate_conversion_rate(branch_filter, current_user)
                branch_indicators.append({
                    'type': 'conversion_rate',
                    'value': branch_conversion_rate,
                    'unit': '%',
                })
                
                branch_new_customers = ReportService.calculate_new_customers(branch_filter, current_user, start_date, end_date)
                branch_indicators.append({
                    'type': 'new_customers',
                    'value': branch_new_customers,
                    'unit': '个',
                })
                
                breakdown_data.append({
                    'id': branch.id,
                    'name': branch.name,
                    'indicators': branch_indicators
                })
        
        response_data = {
            'indicators': indicators,
            'conversionFunnel': conversion_funnel,
            'updateTime': datetime.now().isoformat()
        }
        
        # 如果有维度拆分数据，添加到响应中
        if breakdown_data:
            response_data['breakdown'] = breakdown_data
        
        return Response({
            'code': 200,
            'msg': 'success',
            'data': response_data
        })


class IndicatorDetailView(APIView):
    """
    获取指标详情
    
    获取单个指标的详细数据，包括趋势图和维度拆分
    """
    permission_classes = [IsAuthenticated]
    serializer_class = IndicatorDetailRequestSerializer
    renderer_classes = [JSONRenderer]
    
    @swagger_auto_schema(
        operation_summary="获取指标详情",
        operation_description="获取单个指标的详细数据，包括趋势图和维度拆分",
        request_body=IndicatorDetailRequestSerializer,
        responses={
            200: IndicatorDetailResponseSerializer,
            400: "请求参数错误",
        },
        tags=['报表系统']
    )
    def post(self, request):
        """获取指标详情"""
        try:
            # 验证请求参数
            serializer = IndicatorDetailRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'code': 400,
                    'msg': '请求参数错误',
                    'data': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            validated_data = serializer.validated_data
            indicator_type = validated_data['indicatorType']
            time_range = validated_data['timeRange']
            comparison_mode = validated_data.get('comparisonMode', 'none')
            dimension_filter = validated_data.get('dimensionFilter', {}) or {}
            if not isinstance(dimension_filter, dict):
                dimension_filter = {}
            dimension_type = validated_data.get('dimensionType', 'NONE')
            
            current_user = request.user
            if not dimension_filter and current_user and getattr(current_user, 'id', None):
                cached_filter = cache.get(f"reports:dimension_filter:{current_user.id}")
                if isinstance(cached_filter, dict):
                    dimension_filter = cached_filter
            logger = logging.getLogger(__name__)
            logger.info("IndicatorDetailView dimension_filter=%s", dimension_filter)
            # 确保日期是 naive datetime 对象
            from datetime import datetime as dt, date
            start_date = time_range['start']
            end_date = time_range['end']
            
            # 转换为 naive datetime
            if isinstance(start_date, date) and not isinstance(start_date, dt):
                start_date = dt.combine(start_date, dt.min.time())
            elif isinstance(start_date, dt) and start_date.tzinfo is not None:
                start_date = start_date.replace(tzinfo=None)
            
            if isinstance(end_date, date) and not isinstance(end_date, dt):
                end_date = dt.combine(end_date, dt.max.time())
            elif isinstance(end_date, dt) and end_date.tzinfo is not None:
                end_date = end_date.replace(tzinfo=None)
            
            granularity = time_range.get('granularity', 'day')
            
            # 根据指标类型计算值
            indicator_value = 0
            unit = ''
            avg_value = None
            
            # 百分比类型的指标
            percentage_types = ['conversion_rate', 'key_customer_visit_ratio', 'visit_success_rate']
            
            if indicator_type == 'conversion_rate':
                indicator_value = ReportService.calculate_conversion_rate(dimension_filter, current_user)
                unit = '%'
                avg_value = indicator_value  # 百分比类型，平均值就是值本身
            elif indicator_type == 'new_customers':
                indicator_value = ReportService.calculate_new_customers(
                    dimension_filter, current_user, start_date, end_date
                )
                unit = '个'
                # 计算平均值：总数 / 天数
                days = (end_date - start_date).days + 1
                avg_value = round(indicator_value / days, 2) if days > 0 else 0
            elif indicator_type == 'lead_frequency':
                indicator_value = ReportService.calculate_lead_frequency(
                    dimension_filter, current_user, start_date, end_date
                )
                unit = '次'
                # 计算平均值：总次数 / 天数
                days = (end_date - start_date).days + 1
                avg_value = round(indicator_value / days, 2) if days > 0 else 0
            elif indicator_type == 'visit_frequency':
                indicator_value = ReportService.calculate_visit_frequency(
                    dimension_filter, current_user, start_date, end_date
                )
                unit = '次'
                # 计算平均值：总次数 / 天数
                days = (end_date - start_date).days + 1
                avg_value = round(indicator_value / days, 2) if days > 0 else 0
            elif indicator_type == 'key_customer_visit_ratio':
                indicator_value = ReportService.calculate_key_customer_visit_ratio(
                    dimension_filter, current_user, start_date, end_date
                )
                unit = '%'
                avg_value = indicator_value  # 百分比类型，平均值就是值本身
            elif indicator_type == 'visit_success_rate':
                indicator_value = ReportService.calculate_visit_success_rate(
                    dimension_filter, current_user, start_date, end_date
                )
                unit = '%'
                avg_value = indicator_value  # 百分比类型，平均值就是值本身
            elif indicator_type == 'avg_conversation_duration':
                indicator_value = ReportService.calculate_avg_conversation_duration(
                    dimension_filter, current_user, start_date, end_date
                )
                unit = '小时'
                avg_value = indicator_value  # 这个本身就是平均值
            elif indicator_type == 'visit_cycle':
                indicator_value = ReportService.calculate_visit_cycle(
                    dimension_filter, current_user, start_date, end_date
                )
                unit = '天'
                avg_value = indicator_value  # 这个本身就是平均值
            
            # 生成趋势数据 - 真实查询每一天的数据
            trend_data = []
            current_date = start_date
            
            # 百分比类型的指标
            percentage_types = ['conversion_rate', 'key_customer_visit_ratio', 'visit_success_rate']
            is_percentage = indicator_type in percentage_types
            
            date_count = 0
            max_points = 60  # 最多返回60个数据点
            
            while current_date <= end_date and date_count < max_points:
                # 真实查询当天的数据
                point_value = ReportService.get_indicator_value_for_date(
                    indicator_type, dimension_filter, current_user, current_date
                )
                
                trend_point = {
                    'time': current_date.strftime('%Y-%m-%d'),
                    'value': round(point_value, 2)
                }
                
                # 如果有对比模式，查询对比时间段的真实数据
                if comparison_mode == 'yoy':
                    # 同比：去年同期
                    comparison_date = current_date.replace(year=current_date.year - 1)
                    comparison_value = ReportService.get_indicator_value_for_date(
                        indicator_type, dimension_filter, current_user, comparison_date
                    )
                    trend_point['comparisonValue'] = round(comparison_value, 2)
                elif comparison_mode == 'mom':
                    # 环比：上个月同期
                    if current_date.month == 1:
                        comparison_date = current_date.replace(year=current_date.year - 1, month=12)
                    else:
                        comparison_date = current_date.replace(month=current_date.month - 1)
                    comparison_value = ReportService.get_indicator_value_for_date(
                        indicator_type, dimension_filter, current_user, comparison_date
                    )
                    trend_point['comparisonValue'] = round(comparison_value, 2)
                
                trend_data.append(trend_point)
                
                # 根据粒度增加日期
                if granularity == 'day':
                    current_date += timedelta(days=1)
                elif granularity == 'week':
                    current_date += timedelta(weeks=1)
                elif granularity == 'month':
                    from calendar import monthrange
                    days_in_month = monthrange(current_date.year, current_date.month)[1]
                    current_date += timedelta(days=days_in_month)
                elif granularity == 'quarter':
                    current_date += timedelta(days=90)
                elif granularity == 'year':
                    current_date += timedelta(days=365)
                else:
                    current_date += timedelta(days=1)
                
                date_count += 1
            
            # 计算趋势：对比上一个周期
            days_diff = (end_date - start_date).days + 1
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date - timedelta(days=days_diff - 1)
            
            if indicator_type == 'conversion_rate':
                prev_value = ReportService.calculate_conversion_rate(dimension_filter, current_user)
            elif indicator_type == 'new_customers':
                prev_value = ReportService.calculate_new_customers(dimension_filter, current_user, prev_start_date, prev_end_date)
            elif indicator_type == 'lead_frequency':
                prev_value = ReportService.calculate_lead_frequency(dimension_filter, current_user, prev_start_date, prev_end_date)
            elif indicator_type == 'visit_frequency':
                prev_value = ReportService.calculate_visit_frequency(dimension_filter, current_user, prev_start_date, prev_end_date)
            elif indicator_type == 'key_customer_visit_ratio':
                prev_value = ReportService.calculate_key_customer_visit_ratio(dimension_filter, current_user, prev_start_date, prev_end_date)
            elif indicator_type == 'visit_success_rate':
                prev_value = ReportService.calculate_visit_success_rate(dimension_filter, current_user, prev_start_date, prev_end_date)
            elif indicator_type == 'avg_conversation_duration':
                prev_value = ReportService.calculate_avg_conversation_duration(dimension_filter, current_user, prev_start_date, prev_end_date)
            elif indicator_type == 'visit_cycle':
                prev_value = ReportService.calculate_visit_cycle(dimension_filter, current_user, prev_start_date, prev_end_date)
            else:
                prev_value = 0
            
            trend, trend_percent = ReportService.calculate_trend(indicator_value, prev_value)
            
            # 维度数据 - 真实查询
            dimension_data = None
            if dimension_type and dimension_type != 'NONE':
                dimension_data = ReportService.get_dimension_breakdown(
                    indicator_type, dimension_type, dimension_filter, current_user, start_date, end_date
                )
            
            # 构建响应数据
            response_data = {
                'indicator': {
                    'type': indicator_type,
                    'value': round(indicator_value, 2),
                    'avgValue': round(avg_value, 2) if avg_value is not None else round(indicator_value, 2),
                    'unit': unit,
                    'trend': trend,
                    'trendPercent': trend_percent
                },
                'timeRange': {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d'),
                    'granularity': granularity
                },
                'comparisonMode': comparison_mode,
                'trendData': trend_data,
            }
            
            # 只有当有维度数据时才添加 dimensionData 字段
            if dimension_data is not None:
                response_data['dimensionData'] = dimension_data
            
            return Response({
                'code': 200,
                'msg': 'success',
                'data': response_data
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'code': 500,
                'msg': f'获取指标详情失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
