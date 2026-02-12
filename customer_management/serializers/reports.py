"""
报表系统序列化器
"""
from rest_framework import serializers


class DimensionFilterSerializer(serializers.Serializer):
    """维度过滤序列化器"""
    scope = serializers.ChoiceField(
        choices=['SELF', 'TEAM', 'BRANCH', 'HQ'],
        default='SELF',
        help_text="数据范围"
    )
    dimension = serializers.ChoiceField(
        choices=['NONE', 'PERSONNEL', 'BRANCH', 'SOURCE', 'GRADE', 'CATEGORY'],
        default='NONE',
        help_text="维度类型"
    )
    userId = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="查看具体人员的数据"
    )
    branchId = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="查看具体分所的数据"
    )
    teamId = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="查看具体团队的数据"
    )


class DashboardRequestSerializer(serializers.Serializer):
    """看板数据请求序列化器"""
    dimensionFilter = DimensionFilterSerializer(required=False)


class TimeRangeSerializer(serializers.Serializer):
    """时间范围序列化器"""
    start = serializers.DateField(help_text="开始日期")
    end = serializers.DateField(help_text="结束日期")
    granularity = serializers.ChoiceField(
        choices=['day', 'week', 'month', 'quarter', 'year'],
        default='day',
        help_text="时间粒度"
    )


class IndicatorDetailRequestSerializer(serializers.Serializer):
    """指标详情请求序列化器"""
    indicatorType = serializers.ChoiceField(
        choices=[
            'conversion_rate',
            'new_customers',
            'lead_frequency',
            'visit_frequency',
            'key_customer_visit_ratio',
            'visit_success_rate',
            'avg_conversation_duration',
            'visit_cycle',
        ],
        help_text="指标类型"
    )
    timeRange = TimeRangeSerializer(help_text="时间范围")
    comparisonMode = serializers.ChoiceField(
        choices=['yoy', 'mom', 'none'],
        default='none',
        help_text="对比模式"
    )
    dimensionFilter = DimensionFilterSerializer(required=False)
    dimensionType = serializers.ChoiceField(
        choices=['NONE', 'PERSONNEL', 'BRANCH', 'SOURCE', 'GRADE', 'CATEGORY'],
        required=False,
        allow_null=True,
        default='NONE',
        help_text="维度拆分类型"
    )


class BreakdownItemSerializer(serializers.Serializer):
    """维度拆分项序列化器"""
    label = serializers.CharField(help_text="标签")
    value = serializers.FloatField(help_text="值")
    percent = serializers.FloatField(help_text="占比百分比")


class IndicatorSerializer(serializers.Serializer):
    """指标序列化器"""
    type = serializers.CharField(help_text="指标类型")
    value = serializers.FloatField(help_text="指标值")
    unit = serializers.CharField(help_text="单位")
    trend = serializers.ChoiceField(
        choices=['up', 'down', 'stable'],
        help_text="趋势"
    )
    trendPercent = serializers.FloatField(help_text="趋势百分比")
    breakdown = BreakdownItemSerializer(many=True, required=False, help_text="维度拆分数据")


class ConversionStageSerializer(serializers.Serializer):
    """转化漏斗阶段序列化器"""
    name = serializers.CharField(help_text="阶段名称")
    value = serializers.IntegerField(help_text="数量")
    percent = serializers.FloatField(help_text="百分比")


class ConversionFunnelSerializer(serializers.Serializer):
    """转化漏斗序列化器"""
    stages = ConversionStageSerializer(many=True, help_text="各阶段数据")


class DashboardResponseSerializer(serializers.Serializer):
    """看板数据响应序列化器"""
    indicators = IndicatorSerializer(many=True, help_text="指标列表")
    conversionFunnel = ConversionFunnelSerializer(help_text="转化漏斗")
    updateTime = serializers.DateTimeField(help_text="更新时间")


class TrendDataItemSerializer(serializers.Serializer):
    """趋势数据项序列化器"""
    time = serializers.CharField(help_text="时间")
    value = serializers.FloatField(help_text="值")
    comparisonValue = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="对比值"
    )


class IndicatorDetailSerializer(serializers.Serializer):
    """指标详情序列化器"""
    type = serializers.CharField(help_text="指标类型")
    value = serializers.FloatField(help_text="指标值")
    avgValue = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="平均值"
    )
    unit = serializers.CharField(help_text="单位")
    trend = serializers.ChoiceField(
        choices=['up', 'down', 'stable'],
        help_text="趋势"
    )
    trendPercent = serializers.FloatField(help_text="趋势百分比")


class IndicatorDetailResponseSerializer(serializers.Serializer):
    """指标详情响应序列化器"""
    indicator = IndicatorDetailSerializer(help_text="指标信息")
    timeRange = TimeRangeSerializer(help_text="时间范围")
    comparisonMode = serializers.CharField(help_text="对比模式")
    trendData = TrendDataItemSerializer(many=True, help_text="趋势数据")
    dimensionData = BreakdownItemSerializer(
        many=True,
        required=False,
        help_text="维度数据"
    )
