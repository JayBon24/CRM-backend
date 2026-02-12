from django.db import models
from dvadmin.utils.models import CoreModel, SoftDeleteModel


class Schedule(CoreModel, SoftDeleteModel):
    """日程模型"""
    
    # 日程类型选项
    SCHEDULE_TYPE_CHOICES = [
        ('meeting', '会议'),
        ('court', '开庭'),
        ('deadline', '截止日期'),
        ('reminder', '提醒'),
        ('other', '其他'),
    ]
    
    # 状态选项
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    # 优先级选项
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '紧急'),
    ]
    
    # 关联类型选项
    RELATED_TYPE_CHOICES = [
        ('case', '案件'),
        ('customer', '客户'),
        ('customer_plan', '客户计划'),
        ('visit', '拜访记录'),  # 新增
    ]
    
    # 基本信息
    title = models.CharField(
        max_length=200,
        verbose_name="日程标题",
        help_text="日程标题"
    )
    description = models.TextField(
        verbose_name="日程描述",
        help_text="日程描述",
        null=True,
        blank=True
    )
    schedule_type = models.CharField(
        max_length=50,
        choices=SCHEDULE_TYPE_CHOICES,
        verbose_name="日程类型",
        help_text="日程类型：meeting(会议)、court(开庭)、deadline(截止日期)、reminder(提醒)、other(其他)"
    )
    other_type_content = models.CharField(
        max_length=200,
        verbose_name="其他类型内容",
        help_text="当日程类型为'其他'时，填写具体类型内容",
        null=True,
        blank=True
    )
    
    # 时间信息
    start_time = models.DateTimeField(
        verbose_name="开始时间",
        help_text="开始时间",
        db_index=True
    )
    end_time = models.DateTimeField(
        verbose_name="结束时间",
        help_text="结束时间",
        null=True,
        blank=True
    )
    is_all_day = models.BooleanField(
        default=False,
        verbose_name="是否全天事件",
        help_text="是否全天事件"
    )
    
    # 地点和参与人
    location = models.CharField(
        max_length=500,
        verbose_name="地点",
        help_text="地点",
        null=True,
        blank=True
    )
    participants = models.JSONField(
        verbose_name="参与人员",
        help_text="参与人员（JSON格式存储）",
        null=True,
        blank=True,
        default=list
    )
    
    # 状态和优先级
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="状态",
        help_text="状态：pending(待处理)、in_progress(进行中)、completed(已完成)、cancelled(已取消)",
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name="优先级",
        help_text="优先级：low(低)、medium(中)、high(高)、urgent(紧急)",
        db_index=True
    )
    
    # 提醒设置
    reminder_enabled = models.BooleanField(
        default=True,
        verbose_name="是否启用提醒",
        help_text="是否启用提醒"
    )
    reminder_time = models.IntegerField(
        default=30,
        verbose_name="提前提醒时间（分钟）",
        help_text="提前提醒时间（分钟）",
        null=True,
        blank=True
    )
    reminder_method = models.CharField(
        max_length=100,
        verbose_name="提醒方式",
        help_text="提醒方式：system(系统通知)、email(邮件)、sms(短信)、wechat(微信)，支持多选用逗号分隔",
        null=True,
        blank=True,
        default='system'
    )
    
    # 关联信息
    related_type = models.CharField(
        max_length=50,
        choices=RELATED_TYPE_CHOICES,
        verbose_name="关联类型",
        help_text="关联类型：case(案件)、customer(客户)、customer_plan(客户计划)",
        null=True,
        blank=True,
        db_index=True
    )
    related_id = models.IntegerField(
        verbose_name="关联对象ID",
        help_text="关联对象ID",
        null=True,
        blank=True,
        db_index=True
    )
    
    # 重复规则
    recurrence_rule = models.JSONField(
        verbose_name="重复规则",
        help_text="重复规则（JSON格式，支持按日/周/月/年重复）",
        null=True,
        blank=True
    )
    
    # 附件
    attachments = models.JSONField(
        verbose_name="附件列表",
        help_text="附件列表（JSON格式存储）",
        null=True,
        blank=True,
        default=list
    )
    
    # 备注
    remark = models.TextField(
        verbose_name="备注",
        help_text="备注",
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = "schedule"
        verbose_name = "日程"
        verbose_name_plural = "日程"
        ordering = ['-start_time', '-id']
        indexes = [
            models.Index(fields=['start_time', 'status']),
            models.Index(fields=['related_type', 'related_id']),
            models.Index(fields=['creator', 'start_time']),
            models.Index(fields=['schedule_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"


class ScheduleReminder(CoreModel):
    """日程提醒记录模型"""
    
    # 提醒方式选项
    REMIND_METHOD_CHOICES = [
        ('system', '系统通知'),
        ('email', '邮件'),
        ('sms', '短信'),
        ('wechat', '微信'),
    ]
    
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name="关联的日程",
        help_text="关联的日程"
    )
    remind_time = models.DateTimeField(
        verbose_name="提醒时间",
        help_text="提醒时间",
        db_index=True
    )
    remind_method = models.CharField(
        max_length=50,
        choices=REMIND_METHOD_CHOICES,
        verbose_name="提醒方式",
        help_text="提醒方式：system(系统通知)、email(邮件)、sms(短信)、wechat(微信)"
    )
    is_sent = models.BooleanField(
        default=False,
        verbose_name="是否已发送",
        help_text="是否已发送",
        db_index=True
    )
    sent_time = models.DateTimeField(
        verbose_name="发送时间",
        help_text="发送时间",
        null=True,
        blank=True
    )
    send_result = models.TextField(
        verbose_name="发送结果",
        help_text="发送结果",
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = "schedule_reminder"
        verbose_name = "日程提醒记录"
        verbose_name_plural = "日程提醒记录"
        ordering = ['-remind_time']
        indexes = [
            models.Index(fields=['schedule', 'is_sent']),
            models.Index(fields=['remind_time', 'is_sent']),
        ]
    
    def __str__(self):
        return f"{self.schedule.title} - {self.remind_time.strftime('%Y-%m-%d %H:%M')} - {self.get_remind_method_display()}"
