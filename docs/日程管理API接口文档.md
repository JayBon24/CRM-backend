# 日程管理API接口文档

## 概述
本文档描述了日程管理系统的API接口，包括日程的增删改查、提醒设置、与客户计划的联动等功能。

## 基础信息

- **基础路径**: `/api/customer/`
- **所属模块**: `customer_management`（客户管理模块）
- **鉴权方式**: JWT Token（请求头：`Authorization: Bearer <token>` 或 `Authorization: JWT <token>`）
- **统一响应格式**:
  - 成功: `code=2000`
  - 失败: `code=4000`

---

## 数据模型

### Schedule（日程）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | Integer | 自动 | 日程ID |
| title | String(200) | 是 | 日程标题 |
| description | Text | 否 | 日程描述 |
| schedule_type | String(50) | 是 | 日程类型：meeting(会议)、court(开庭)、deadline(截止日期)、reminder(提醒)、other(其他) |
| start_time | DateTime | 是 | 开始时间 |
| end_time | DateTime | 否 | 结束时间 |
| location | String(500) | 否 | 地点 |
| participants | Text | 否 | 参与人员（JSON格式存储） |
| status | String(20) | 是 | 状态：pending(待处理)、in_progress(进行中)、completed(已完成)、cancelled(已取消) |
| priority | String(20) | 是 | 优先级：low(低)、medium(中)、high(高)、urgent(紧急) |
| is_all_day | Boolean | 否 | 是否全天事件，默认False |
| reminder_enabled | Boolean | 否 | 是否启用提醒，默认True |
| reminder_time | Integer | 否 | 提前提醒时间（分钟），默认30 |
| reminder_method | String(50) | 否 | 提醒方式：system(系统通知)、email(邮件)、sms(短信)、wechat(微信)，支持多选用逗号分隔 |
| related_type | String(50) | 否 | 关联类型：case(案件)、customer(客户)、customer_plan(客户计划)、visit(拜访记录) |
| related_id | Integer | 否 | 关联对象ID |
| recurrence_rule | Text | 否 | 重复规则（JSON格式，支持按日/周/月/年重复） |
| attachments | Text | 否 | 附件列表（JSON格式存储） |
| remark | Text | 否 | 备注 |
| create_datetime | DateTime | 自动 | 创建时间 |
| update_datetime | DateTime | 自动 | 更新时间 |
| creator | ForeignKey | 自动 | 创建人 |
| modifier | ForeignKey | 自动 | 修改人 |
| is_deleted | Boolean | 自动 | 软删除标记 |

### ScheduleReminder（日程提醒记录）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | Integer | 自动 | 提醒记录ID |
| schedule | ForeignKey | 是 | 关联的日程 |
| remind_time | DateTime | 是 | 提醒时间 |
| remind_method | String(50) | 是 | 提醒方式 |
| is_sent | Boolean | 否 | 是否已发送，默认False |
| sent_time | DateTime | 否 | 发送时间 |
| send_result | Text | 否 | 发送结果 |
| create_datetime | DateTime | 自动 | 创建时间 |

---

## API接口

### 1. 获取日程列表

```
GET /api/customer/schedules/
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | Integer | 否 | 页码，默认1 |
| limit | Integer | 否 | 每页数量，默认20 |
| schedule_type | String | 否 | 日程类型筛选 |
| status | String | 否 | 状态筛选 |
| priority | String | 否 | 优先级筛选 |
| start_time_after | DateTime | 否 | 开始时间范围（起） |
| start_time_before | DateTime | 否 | 开始时间范围（止） |
| related_type | String | 否 | 关联类型筛选 |
| related_id | Integer | 否 | 关联对象ID筛选 |
| search | String | 否 | 搜索关键词（标题、描述、地点） |
| ordering | String | 否 | 排序字段，如：-start_time |

**响应示例：**

```json
{
  "code": 2000,
  "msg": "获取成功",
  "data": {
    "count": 100,
    "next": "http://api.example.com/api/schedule/schedules/?page=2",
    "previous": null,
    "results": [
      {
        "id": 1,
        "title": "与客户A洽谈合同",
        "description": "讨论合同细节和付款方式",
        "schedule_type": "meeting",
        "start_time": "2025-12-27T14:00:00+08:00",
        "end_time": "2025-12-27T16:00:00+08:00",
        "location": "公司会议室A",
        "participants": [
          {"name": "张三", "role": "律师"},
          {"name": "李四", "role": "客户"}
        ],
        "status": "pending",
        "priority": "high",
        "is_all_day": false,
        "reminder_enabled": true,
        "reminder_time": 30,
        "reminder_method": "system,email",
        "related_type": "customer",
        "related_id": 10,
        "recurrence_rule": null,
        "attachments": [],
        "remark": "",
        "create_datetime": "2025-12-26T10:00:00+08:00",
        "update_datetime": "2025-12-26T10:00:00+08:00",
        "creator": {
          "id": 1,
          "username": "admin",
          "name": "管理员"
        }
      }
    ]
  }
}
```

---

### 2. 获取日程详情

```
GET /api/customer/schedules/{id}/
```

**路径参数：**
- `id`: 日程ID

**响应示例：**

```json
{
  "code": 2000,
  "msg": "获取成功",
  "data": {
    "id": 1,
    "title": "与客户A洽谈合同",
    "description": "讨论合同细节和付款方式",
    "schedule_type": "meeting",
    "start_time": "2025-12-27T14:00:00+08:00",
    "end_time": "2025-12-27T16:00:00+08:00",
    "location": "公司会议室A",
    "participants": [
      {"name": "张三", "role": "律师"},
      {"name": "李四", "role": "客户"}
    ],
    "status": "pending",
    "priority": "high",
    "is_all_day": false,
    "reminder_enabled": true,
    "reminder_time": 30,
    "reminder_method": "system,email",
    "related_type": "customer",
    "related_id": 10,
    "related_info": {
      "id": 10,
      "name": "客户A公司",
      "contact_person": "李四"
    },
    "recurrence_rule": null,
    "attachments": [],
    "remark": "",
    "reminders": [
      {
        "id": 1,
        "remind_time": "2025-12-27T13:30:00+08:00",
        "remind_method": "system",
        "is_sent": false
      }
    ],
    "create_datetime": "2025-12-26T10:00:00+08:00",
    "update_datetime": "2025-12-26T10:00:00+08:00",
    "creator": {
      "id": 1,
      "username": "admin",
      "name": "管理员"
    }
  }
}
```

---

### 3. 创建日程

```
POST /api/customer/schedules/
```

**请求体：**

```json
{
  "title": "与客户A洽谈合同",
  "description": "讨论合同细节和付款方式",
  "schedule_type": "meeting",
  "start_time": "2025-12-27T14:00:00+08:00",
  "end_time": "2025-12-27T16:00:00+08:00",
  "location": "公司会议室A",
  "participants": [
    {"name": "张三", "role": "律师"},
    {"name": "李四", "role": "客户"}
  ],
  "status": "pending",
  "priority": "high",
  "is_all_day": false,
  "reminder_enabled": true,
  "reminder_time": 30,
  "reminder_method": "system,email",
  "related_type": "customer",
  "related_id": 10,
  "remark": ""
}
```

**响应示例：**

```json
{
  "code": 2000,
  "msg": "创建成功",
  "data": {
    "id": 1,
    "title": "与客户A洽谈合同",
    ...
  }
}
```

---

### 4. 更新日程

```
PUT /api/customer/schedules/{id}/
PATCH /api/customer/schedules/{id}/
```

**路径参数：**
- `id`: 日程ID

**请求体：**（PATCH支持部分更新）

```json
{
  "title": "与客户A洽谈合同（修改）",
  "status": "completed",
  "remark": "会议已完成"
}
```

**响应示例：**

```json
{
  "code": 2000,
  "msg": "更新成功",
  "data": {
    "id": 1,
    "title": "与客户A洽谈合同（修改）",
    "status": "completed",
    ...
  }
}
```

---

### 5. 删除日程

```
DELETE /api/customer/schedules/{id}/
```

**路径参数：**
- `id`: 日程ID

**响应示例：**

```json
{
  "code": 2000,
  "msg": "删除成功",
  "data": {}
}
```

---

### 6. 批量删除日程

```
POST /api/customer/schedules/batch_delete/
```

**请求体：**

```json
{
  "ids": [1, 2, 3, 4, 5]
}
```

**响应示例：**

```json
{
  "code": 2000,
  "msg": "批量删除成功，共删除 5 条记录",
  "data": {
    "deleted_count": 5
  }
}
```

---

### 7. 更新日程状态

```
POST /api/customer/schedules/{id}/update_status/
```

**路径参数：**
- `id`: 日程ID

**请求体：**

```json
{
  "status": "completed"
}
```

**响应示例：**

```json
{
  "code": 2000,
  "msg": "状态更新成功",
  "data": {
    "id": 1,
    "status": "completed",
    ...
  }
}
```

---

### 8. 获取今日日程

```
GET /api/customer/schedules/today/
```

**响应示例：**

```json
{
  "code": 2000,
  "msg": "获取成功",
  "data": {
    "date": "2025-12-26",
    "total_count": 5,
    "by_status": {
      "pending": 3,
      "in_progress": 1,
      "completed": 1
    },
    "schedules": [
      {
        "id": 1,
        "title": "与客户A洽谈合同",
        "start_time": "2025-12-26T14:00:00+08:00",
        "end_time": "2025-12-26T16:00:00+08:00",
        "status": "pending",
        "priority": "high"
      }
    ]
  }
}
```

---

### 9. 获取本周日程

```
GET /api/customer/schedules/this_week/
```

**响应示例：**

```json
{
  "code": 2000,
  "msg": "获取成功",
  "data": {
    "week_start": "2025-12-23",
    "week_end": "2025-12-29",
    "total_count": 15,
    "by_day": {
      "2025-12-23": 2,
      "2025-12-24": 3,
      "2025-12-25": 1,
      "2025-12-26": 5,
      "2025-12-27": 4
    },
    "schedules": [...]
  }
}
```

---

### 10. 获取日程统计

```
GET /api/customer/schedules/statistics/
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | Date | 否 | 统计开始日期 |
| end_date | Date | 否 | 统计结束日期 |

**响应示例：**

```json
{
  "code": 2000,
  "msg": "获取成功",
  "data": {
    "total_count": 100,
    "by_type": {
      "meeting": 40,
      "court": 20,
      "deadline": 15,
      "reminder": 20,
      "other": 5
    },
    "by_status": {
      "pending": 50,
      "in_progress": 10,
      "completed": 35,
      "cancelled": 5
    },
    "by_priority": {
      "low": 20,
      "medium": 40,
      "high": 30,
      "urgent": 10
    },
    "upcoming_count": 25,
    "overdue_count": 5
  }
}
```

---

### 11. 从客户计划创建日程

```
POST /api/customer/schedules/create_from_customer_plan/
```

**请求体：**

```json
{
  "customer_id": 10,
  "plan_title": "回访客户A",
  "plan_time": "2025-12-28T10:00:00+08:00",
  "plan_description": "定期回访，了解客户需求",
  "reminder_time": 60
}
```

**响应示例：**

```json
{
  "code": 2000,
  "msg": "日程创建成功",
  "data": {
    "id": 20,
    "title": "回访客户A",
    "schedule_type": "reminder",
    "start_time": "2025-12-28T10:00:00+08:00",
    "related_type": "customer_plan",
    "related_id": 10,
    "reminder_enabled": true,
    "reminder_time": 60,
    ...
  }
}
```

---

### 12. 获取关联对象的日程列表

```
GET /api/customer/schedules/by_related/
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| related_type | String | 是 | 关联类型：case、customer、customer_plan |
| related_id | Integer | 是 | 关联对象ID |

**响应示例：**

```json
{
  "code": 2000,
  "msg": "获取成功",
  "data": [
    {
      "id": 1,
      "title": "与客户A洽谈合同",
      "start_time": "2025-12-27T14:00:00+08:00",
      "status": "pending",
      ...
    }
  ]
}
```

---

### 13. 获取即将到来的提醒

```
GET /api/customer/schedules/upcoming_reminders/
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| hours | Integer | 否 | 未来多少小时内的提醒，默认24 |

**响应示例：**

```json
{
  "code": 2000,
  "msg": "获取成功",
  "data": {
    "count": 5,
    "reminders": [
      {
        "schedule_id": 1,
        "schedule_title": "与客户A洽谈合同",
        "start_time": "2025-12-27T14:00:00+08:00",
        "remind_time": "2025-12-27T13:30:00+08:00",
        "time_until_remind": "7小时30分钟"
      }
    ]
  }
}
```

---

### 14. 日历视图数据

```
GET /api/schedule/schedules/calendar_view/
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| year | Integer | 是 | 年份 |
| month | Integer | 是 | 月份 |

**响应示例：**

```json
{
  "code": 2000,
  "msg": "获取成功",
  "data": {
    "year": 2025,
    "month": 12,
    "days": [
      {
        "date": "2025-12-01",
        "schedules": [
          {
            "id": 1,
            "title": "会议",
            "start_time": "2025-12-01T10:00:00+08:00",
            "schedule_type": "meeting",
            "priority": "high"
          }
        ],
        "count": 1
      },
      {
        "date": "2025-12-02",
        "schedules": [],
        "count": 0
      }
    ]
  }
}
```

---

## 错误处理

所有API都返回统一的错误格式：

```json
{
  "code": 4000,
  "msg": "错误描述",
  "data": {}
}
```

### 常见错误码

| 错误码 | 说明 |
|--------|------|
| 4000 | 通用错误 |
| 4001 | 参数错误 |
| 4003 | 权限不足 |
| 4004 | 资源不存在 |
| 4005 | 时间冲突 |

---

## 使用场景

### 1. 日程列表页面
- 展示用户的所有日程
- 支持按类型、状态、优先级筛选
- 支持按时间范围查询
- 支持搜索功能

### 2. 日程详情页面
- 查看日程的完整信息
- 显示关联的案件或客户信息
- 显示提醒设置和发送记录

### 3. 日程创建/编辑
- 创建新日程
- 设置提醒时间和方式
- 关联案件或客户
- 添加参与人员和附件

### 4. 日历视图
- 月视图展示日程分布
- 周视图展示详细安排
- 日视图展示当天时间线

### 5. 客户管理联动
- 在客户管理中创建计划时自动同步到日程
- 支持从客户详情页查看相关日程
- 计划提醒自动创建日程提醒

---

## 数据字典

### schedule_type（日程类型）
- `meeting`: 会议
- `court`: 开庭
- `deadline`: 截止日期
- `reminder`: 提醒
- `other`: 其他

### status（状态）
- `pending`: 待处理
- `in_progress`: 进行中
- `completed`: 已完成
- `cancelled`: 已取消

### priority（优先级）
- `low`: 低
- `medium`: 中
- `high`: 高
- `urgent`: 紧急

### reminder_method（提醒方式）
- `system`: 系统通知
- `email`: 邮件
- `sms`: 短信
- `wechat`: 微信

### related_type（关联类型）
- `case`: 案件
- `customer`: 客户
- `customer_plan`: 客户计划
- `visit`: 拜访记录

---

## 附录

### 重复规则格式（recurrence_rule）

```json
{
  "frequency": "daily",  // daily/weekly/monthly/yearly
  "interval": 1,         // 间隔
  "end_date": "2026-12-31",  // 结束日期
  "count": 10,           // 重复次数
  "by_weekday": [1, 3, 5],  // 按星期（1-7）
  "by_monthday": [1, 15]    // 按月中的日期
}
```

### 参与人员格式（participants）

```json
[
  {
    "name": "张三",
    "role": "律师",
    "phone": "13800138000",
    "email": "zhangsan@example.com"
  }
]
```

### 附件格式（attachments）

```json
[
  {
    "name": "会议资料.pdf",
    "url": "/media/schedules/meeting_doc.pdf",
    "size": 1024000,
    "upload_time": "2025-12-26T10:00:00+08:00"
  }
]
```


---

### 15. 发送短信通知

```
POST /api/customer/schedules/notification/sms/send/
```

**请求体：**

```json
{
  "phone": "13800138000",
  "template_code": "SCHEDULE_REMINDER",
  "params": {
    "title": "客户拜访",
    "time": "2025-12-26 15:00"
  }
}
```

**响应示例：**

```json
{
  "code": 2000,
  "msg": "短信发送成功",
  "data": {
    "success": true,
    "message": "短信发送成功",
    "phone": "13800138000",
    "template_code": "SCHEDULE_REMINDER",
    "send_time": "2025-12-26T10:30:00+08:00"
  }
}
```

---

### 16. 发送邮件通知

```
POST /api/customer/schedules/notification/email/send/
```

**请求体：**

```json
{
  "to": "user@example.com",
  "subject": "日程提醒: 客户拜访",
  "content": "您有一个日程即将开始...",
  "template": "schedule_reminder"
}
```

**响应示例：**

```json
{
  "code": 2000,
  "msg": "邮件发送成功",
  "data": {
    "success": true,
    "message": "邮件发送成功",
    "to": "user@example.com",
    "subject": "日程提醒: 客户拜访"
  }
}
```

---

## 通知服务说明

### 短信服务（腾讯云SMS）

#### 配置要求
需要在 `conf/env.py` 中配置腾讯云SMS相关参数：

```python
# 腾讯云SMS配置
TENCENT_SMS_APP_ID = 'your_app_id'
TENCENT_SMS_APP_KEY = 'your_app_key'
TENCENT_SMS_SIGN = '您的签名'
```

#### 短信模板
- `SCHEDULE_REMINDER`: 日程提醒模板
  - 参数：`title`（日程标题）、`time`（日程时间）

#### 使用示例

```python
from customer_management.services.notification_service import SMSService

# 发送日程提醒短信
result = SMSService.send_schedule_reminder(
    phone='13800138000',
    title='客户拜访',
    time='2025-12-26 15:00'
)
```

### 邮件服务

#### 配置要求
需要在 `application/settings.py` 中配置邮件服务器：

```python
# 邮件配置
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.example.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@example.com'
EMAIL_HOST_PASSWORD = 'your_password'
DEFAULT_FROM_EMAIL = 'noreply@example.com'
```

#### 邮件模板
- `schedule_reminder`: 日程提醒模板

#### 使用示例

```python
from customer_management.services.notification_service import EmailService

# 发送日程提醒邮件
result = EmailService.send_schedule_reminder(
    to='user@example.com',
    title='客户拜访',
    time='2025-12-26 15:00',
    description='与客户讨论合作事宜'
)
```

### 定时任务/调度系统

建议使用 Celery 实现定时扫描和发送提醒：

```python
# 示例：每分钟扫描即将到来的日程
@celery_app.task
def check_schedule_reminders():
    """检查并发送日程提醒"""
    from customer_management.models import Schedule, ScheduleReminder
    from customer_management.services.notification_service import NotificationService
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    
    # 查询需要提醒的日程
    schedules = Schedule.objects.filter(
        reminder_enabled=True,
        status='pending',
        start_time__gte=now,
        start_time__lte=now + timedelta(hours=1)
    )
    
    for schedule in schedules:
        # 检查是否已发送提醒
        remind_time = schedule.start_time - timedelta(minutes=schedule.reminder_time or 30)
        
        if now >= remind_time:
            # 发送提醒
            methods = schedule.reminder_method.split(',')
            
            for method in methods:
                method = method.strip()
                
                # 创建提醒记录
                reminder = ScheduleReminder.objects.create(
                    schedule=schedule,
                    remind_time=remind_time,
                    remind_method=method
                )
                
                # 发送通知
                if method == 'sms':
                    # 发送短信
                    pass
                elif method == 'email':
                    # 发送邮件
                    pass
                
                # 更新提醒记录
                reminder.is_sent = True
                reminder.sent_time = now
                reminder.save()
```

### 提醒记录更新

系统会自动记录每次提醒的发送情况：

- `is_sent`: 是否已发送
- `sent_time`: 发送时间
- `send_result`: 发送结果（成功/失败原因）

可以通过日程详情接口查看提醒记录。
