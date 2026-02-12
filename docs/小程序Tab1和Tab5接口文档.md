# 小程序 Tab1（客户）和 Tab5（我的）接口文档

## 概述

本文档描述了小程序 Tab1「客户」和 Tab5「我的」两个功能模块所需的后端接口规范。

- **基础路径前缀**: `/api/`（小程序后台管理使用此前缀）
- **鉴权方式**: JWT Token（请求头：`Authorization: Bearer <token>` 或 `Authorization: JWT <token>`）
- **统一响应格式**:
  - 成功: `code=2000`
  - 失败: `code=4000` 或其他错误码
  - 响应结构: `{ "code": 2000, "msg": "success", "data": {...} }`

---

## 一、Tab1「客户」模块接口

### 1.1 获取客户列表

**接口地址**: `GET /api/crm/client/list`

**请求参数**（Query Parameters）:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | Integer | 否 | 页码，默认1 |
| pageSize | Integer | 否 | 每页数量，默认20 |
| status | String | 否 | 生命周期状态：PUBLIC_POOL（公海）、FOLLOW_UP（跟进）、CASE（交案）、PAYMENT（回款）、WON（赢单） |
| sales_stage | String | 否 | 展业状态：PUBLIC_POOL（公海）、BLANK（空白）、MEETING（面谈）、CASE（交案）、PAYMENT（回款）、WON（赢单） |
| keyword | String | 否 | 搜索关键词（客户名称/手机号） |
| grade | String | 否 | 客户等级：A、B、C、D |
| collection_category | String | 否 | 催收类别：arbitration（仲裁）、mediation（调解）、litigation（诉讼），支持多选（逗号分隔） |
| owner_user_id | Integer | 否 | 经办人ID |
| team_id | Integer | 否 | 团队ID |
| branch_id | Integer | 否 | 分所ID |
| recycle_risk_level | String | 否 | 回收风险等级：none、low、medium、high |
| order_by | String | 否 | 排序字段：last_followup（最近跟进）、create_time（创建时间）、last_visit（最近拜访），默认create_time |
| order_direction | String | 否 | 排序方向：asc（升序）、desc（降序），默认desc |

**响应示例**:

```json
{
  "code": 2000,
  "msg": "success",
  "data": {
    "rows": [
      {
        "id": 1,
        "status": "FOLLOW_UP",
        "sales_stage": "MEETING",
        "client_name": "北京科技有限公司",
        "contact_name": "张三",
        "mobile": "13800138000",
        "region": "北京市/朝阳区",
        "grade": "A",
        "grade_source": "ai",
        "collection_category": ["arbitration", "litigation"],
        "preservation_status": "preserved",
        "court": "北京市朝阳区人民法院",
        "lawyer": "李律师",
        "owner_user_id": 10,
        "owner_user_name": "销售员A",
        "org_scope": "TEAM",
        "team_name": "销售一组",
        "branch_name": "北京分所",
        "followup_count": 5,
        "visit_count": 3,
        "valid_visit_count": 2,
        "last_followup_at": "2025-01-15 14:30:00",
        "last_visit_at": "2025-01-14 10:00:00",
        "next_plan_at": "2025-01-20 09:00:00",
        "recycle_risk_level": "low",
        "recycle_deadline": "2025-02-15 00:00:00",
        "create_time": "2025-01-01 10:00:00",
        "update_time": "2025-01-15 14:30:00"
      }
    ],
    "total": 100,
    "page": 1,
    "pageSize": 20
  }
}
```

**字段说明**:
- `sales_stage`: 后端计算的展业状态（根据 `valid_visit_count` 等字段计算）
- `recycle_risk_level`: 后端计算的回收风险等级
- `recycle_deadline`: 后端计算的回收截止时间
- `followup_count`: 跟进记录总数
- `visit_count`: 拜访记录总数
- `valid_visit_count`: 有效拜访记录数（用于判断 sales_stage）

---

### 1.2 获取客户详情

**接口地址**: `GET /api/crm/client/{id}`

**路径参数**:
- `id`: 客户ID

**响应示例**:

```json
{
  "code": 2000,
  "msg": "success",
  "data": {
    "id": 1,
    "status": "FOLLOW_UP",
    "sales_stage": "MEETING",
    "client_name": "北京科技有限公司",
    "contact_name": "张三",
    "mobile": "13800138000",
    "region": "北京市/朝阳区",
    "source_channel": "线上推广",
    "referrer": "朋友介绍",
    "demand_summary": "需要处理劳动争议案件",
    "grade": "A",
    "grade_source": "ai",
    "collection_category": ["arbitration", "litigation"],
    "preservation_status": "preserved",
    "court": "北京市朝阳区人民法院",
    "lawyer": "李律师",
    "owner_user_id": 10,
    "owner_user_name": "销售员A",
    "org_scope": "TEAM",
    "team_name": "销售一组",
    "branch_name": "北京分所",
    "followup_count": 5,
    "visit_count": 3,
    "valid_visit_count": 2,
    "last_followup_at": "2025-01-15 14:30:00",
    "last_visit_at": "2025-01-14 10:00:00",
    "next_plan_at": "2025-01-20 09:00:00",
    "recycle_risk_level": "low",
    "recycle_deadline": "2025-02-15 00:00:00",
    "ai_tags": {
      "grade": {
        "value": "A",
        "source": "ai",
        "updated_at": "2025-01-10 10:00:00",
        "updated_by": "system"
      },
      "collection_category": {
        "value": ["arbitration", "litigation"],
        "primary": "arbitration",
        "source": "ai",
        "updated_at": "2025-01-10 10:00:00"
      },
      "preservation_status": {
        "value": "preserved",
        "progress": "已完成",
        "updated_at": "2025-01-12 14:00:00"
      },
      "court": {
        "value": "北京市朝阳区人民法院",
        "candidates": ["北京市朝阳区人民法院", "北京市第一中级人民法院"],
        "updated_at": "2025-01-11 09:00:00"
      },
      "lawyer": {
        "value": "李律师",
        "updated_at": "2025-01-11 09:00:00"
      }
    },
    "create_time": "2025-01-01 10:00:00",
    "update_time": "2025-01-15 14:30:00"
  }
}
```

---

### 1.3 创建客户/线索

**接口地址**: `POST /api/crm/client`

**请求体**:

```json
{
  "client_name": "北京科技有限公司",
  "contact_name": "张三",
  "mobile": "13800138000",
  "region": "北京市/朝阳区",
  "source_channel": "线上推广",
  "referrer": "朋友介绍",
  "demand_summary": "需要处理劳动争议案件",
  "owner_user_id": 10,
  "grade": "A",
  "ai_trace_id": "trace_123456"
}
```

**响应示例**:

```json
{
  "code": 2000,
  "msg": "创建成功",
  "data": {
    "id": 1,
    "client_name": "北京科技有限公司",
    "create_time": "2025-01-15 10:00:00"
  }
}
```

---

### 1.4 更新客户信息

**接口地址**: `PUT /api/crm/client/{id}`

**路径参数**:
- `id`: 客户ID

**请求体**（支持部分更新）:

```json
{
  "client_name": "北京科技有限公司（更新）",
  "mobile": "13900139000",
  "grade": "B",
  "ai_trace_id": "trace_789012"
}
```

**响应示例**:

```json
{
  "code": 2000,
  "msg": "更新成功",
  "data": {
    "id": 1,
    "update_time": "2025-01-15 15:00:00"
  }
}
```

---

### 1.5 申领公海客户

**接口地址**: `POST /api/crm/client/{id}/apply`

**路径参数**:
- `id`: 客户ID

**请求体**:

```json
{
  "reason": "我有相关经验，可以更好地服务该客户"
}
```

**响应示例**:

```json
{
  "code": 2000,
  "msg": "申领成功，等待审批",
  "data": {
    "apply_id": "apply_123456",
    "status": "pending"
  }
}
```

**说明**:
- 申领后会创建审批任务，需要等待审批通过
- 只有 SALES 和 TEAM 角色可以申领
- HQ 和 BRANCH 角色不能申领

---

### 1.6 分配客户（管理权限）

**接口地址**: `POST /api/crm/client/{id}/assign`

**路径参数**:
- `id`: 客户ID

**请求体**:

```json
{
  "owner_user_id": 20,
  "user_name": "销售员B",
  "target_user_role_level": "SALES",
  "reason": "根据业务需要重新分配"
}
```

**响应示例**:

```json
{
  "code": 2000,
  "msg": "分配成功",
  "data": {
    "id": 1,
    "owner_user_id": 20,
    "owner_user_name": "销售员B"
  }
}
```

**说明**:
- 只有管理角色（TEAM/BRANCH/HQ）可以分配
- 不能分配给 HQ 和 BRANCH 角色，只能分配给 TEAM 和 SALES
- 后端需要校验 `target_user_role_level`，如果是 HQ 或 BRANCH 则拒绝

---

### 1.7 审批客户申领

**接口地址**: `POST /api/crm/client/approve/{apply_id}`

**路径参数**:
- `apply_id`: 申领申请ID

**请求体**:

```json
{
  "approved": true,
  "reject_reason": ""
}
```

或

```json
{
  "approved": false,
  "reject_reason": "该客户已分配给其他销售"
}
```

**响应示例**:

```json
{
  "code": 2000,
  "msg": "审批成功",
  "data": {
    "apply_id": "apply_123456",
    "status": "approved"
  }
}
```

**说明**:
- 审批通过后，客户状态从 PUBLIC_POOL 转为 FOLLOW_UP
- 审批链：TEAM → BRANCH → HQ（层层审批）

---

## 二、Tab5「我的」模块接口

### 2.1 获取个人资料

**接口地址**: `GET /api/mine/profile`

**响应示例**:

```json
{
  "code": 2000,
  "msg": "success",
  "data": {
    "user_id": "10",
    "name": "张三",
    "avatar": "https://example.com/avatar.jpg",
    "roleLevel": "SALES",
    "orgScope": "SELF",
    "teamName": "销售一组",
    "branchName": "北京分所",
    "email": "zhangsan@example.com",
    "phonenumber": "13800138000"
  }
}
```

**字段说明**:
- `roleLevel`: 角色层级：SALES（销售）、TEAM（团队管理）、BRANCH（分所管理）、HQ（总所管理）
- `orgScope`: 数据范围：SELF（本人）、TEAM（本团队）、BRANCH（本分所）、HQ（全所）

---

### 2.2 更新个人资料

**接口地址**: `POST /api/mine/profile/update`

**请求体**（支持部分更新）:

```json
{
  "name": "张三（更新）",
  "email": "zhangsan_new@example.com",
  "phonenumber": "13900139000"
}
```

**响应示例**:

```json
{
  "code": 2000,
  "msg": "更新成功",
  "data": {
    "user_id": "10",
    "name": "张三（更新）",
    "email": "zhangsan_new@example.com",
    "phonenumber": "13900139000"
  }
}
```

---

### 2.3 提交反馈

**接口地址**: `POST /api/mine/feedback`

**说明**: 前端代码中使用的是 `/mine/feedback`，但根据小程序后台管理路径前缀规范，应统一使用 `/api/mine/feedback`

**请求体**:

```json
{
  "type": "bug",
  "content": "客户列表页面加载缓慢",
  "images": ["https://example.com/image1.jpg"],
  "contact": "13800138000",
  "context": {
    "client_id": "1",
    "field": "grade"
  }
}
```

**字段说明**:
- `type`: 反馈类型：bug（Bug反馈）、suggestion（建议）、ai_tag_feedback（AI标记反馈）
- `context`: 可选，上下文信息（如关联的客户ID、字段名等）

**响应示例**:

```json
{
  "code": 2000,
  "msg": "提交成功",
  "data": {
    "id": "fb_123456"
  }
}
```

---

### 2.4 获取反馈列表

**接口地址**: `GET /api/mine/feedback/list`

**说明**: 前端代码中使用的是 `/mine/feedback/list`，但根据小程序后台管理路径前缀规范，应统一使用 `/api/mine/feedback/list`

**请求参数**（Query Parameters）:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | Integer | 否 | 页码，默认1 |
| pageSize | Integer | 否 | 每页数量，默认20 |

**响应示例**:

```json
{
  "code": 2000,
  "msg": "success",
  "data": {
    "rows": [
      {
        "id": "fb_123456",
        "type": "bug",
        "content": "客户列表页面加载缓慢",
        "images": ["https://example.com/image1.jpg"],
        "contact": "13800138000",
        "context": {
          "client_id": "1",
          "field": "grade"
        },
        "status": "open",
        "created_at": "2025-01-15 10:00:00"
      }
    ],
    "total": 10
  }
}
```

---

### 2.5 获取审批任务列表

**接口地址**: `GET /api/mine/approval/list`

**说明**: 前端代码中使用的是 `/mine/approval/list`，但根据小程序后台管理路径前缀规范，应统一使用 `/api/mine/approval/list`

**请求参数**（Query Parameters）:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | String | 是 | pending（待审批）或 handled（已处理） |
| page | Integer | 否 | 页码，默认1 |
| pageSize | Integer | 否 | 每页数量，默认20 |

**响应示例**:

```json
{
  "code": 2000,
  "msg": "success",
  "data": {
    "rows": [
      {
        "id": "approval_123456",
        "type": "LEAD_CLAIM",
        "status": "pending",
        "applicant_user_id": "10",
        "applicant_user_name": "销售员A",
        "client_id": "1",
        "client_name": "北京科技有限公司",
        "created_at": "2025-01-15 10:00:00",
        "approval_chain": ["TEAM", "BRANCH", "HQ"],
        "current_step_index": 0,
        "current_approver_role": "TEAM",
        "history": [],
        "payload": {
          "client_id": "1",
          "name": "北京科技有限公司",
          "reason": "我有相关经验，可以更好地服务该客户"
        }
      }
    ],
    "total": 5
  }
}
```

**字段说明**:
- `type`: 审批类型：LEAD_CLAIM（线索申领）、LEAD_CREATE（销售新增自有线索审核）、CLIENT_TRANSFER（客户转交）
- `status`: 审批状态：pending（待审批）、approved（已通过）、rejected（已驳回）
- `approval_chain`: 审批链（按顺序）
- `current_step_index`: 当前审批步骤索引
- `current_approver_role`: 当前应由哪个角色审批
- `history`: 审批历史记录
- `payload`: 审批内容（根据 type 不同，结构不同）

**审批类型 payload 结构**:

1. **LEAD_CLAIM**:
```json
{
  "type": "LEAD_CLAIM",
  "payload": {
    "client_id": "1",
    "name": "北京科技有限公司",
    "reason": "申领原因"
  }
}
```

2. **LEAD_CREATE**:
```json
{
  "type": "LEAD_CREATE",
  "payload": {
    "form": {
      "client_name": "新客户",
      "contact_name": "联系人",
      "mobile": "13800138000",
      ...
    }
  }
}
```

3. **CLIENT_TRANSFER**:
```json
{
  "type": "CLIENT_TRANSFER",
  "payload": {
    "client_id": "1",
    "from_user": {
      "id": "10",
      "name": "销售员A"
    },
    "to_user": {
      "id": "20",
      "name": "销售员B"
    },
    "reason": "转交原因"
  }
}
```

**说明**:
- `status=pending` 时，只返回"当前应由我这个层级审批"的任务
- `status=handled` 时，返回"我本层级已处理过"的任务（即便后续还有上级审批）+ 最终已结束任务
- 只有 TEAM/BRANCH/HQ 可以审批，SALES 不能审批

---

### 2.6 审批任务（通过/驳回）

**接口地址**: `POST /api/mine/approval/{id}/approve`

**说明**: 前端代码中使用的是 `/mine/approval/{id}/approve`，但根据小程序后台管理路径前缀规范，应统一使用 `/api/mine/approval/{id}/approve`

**路径参数**:
- `id`: 审批任务ID

**请求体**:

```json
{
  "approved": true,
  "reject_reason": ""
}
```

或

```json
{
  "approved": false,
  "reject_reason": "该客户已分配给其他销售"
}
```

**响应示例**:

```json
{
  "code": 2000,
  "msg": "审批成功",
  "data": {
    "ok": true
  }
}
```

**说明**:
- 审批通过后，如果还有上级审批，则流转到下一级
- 如果所有审批都通过，则执行相应操作（如申领成功、转交成功等）
- 审批驳回后，任务状态变为 rejected，不再流转

---

### 2.7 获取提醒偏好设置

**接口地址**: `GET /api/mine/settings/remind`

**说明**: 前端代码中使用的是 `/mine/settings/remind`，但根据小程序后台管理路径前缀规范，应统一使用 `/api/mine/settings/remind`

**响应示例**:

```json
{
  "code": 2000,
  "msg": "success",
  "data": {
    "default_remind_advance_minutes": 30
  }
}
```

**字段说明**:
- `default_remind_advance_minutes`: 提前提醒时间（分钟），可选值：15、30

---

### 2.8 设置提醒偏好

**接口地址**: `POST /api/mine/settings/remind`

**说明**: 前端代码中使用的是 `/mine/settings/remind`，但根据小程序后台管理路径前缀规范，应统一使用 `/api/mine/settings/remind`

**请求体**:

```json
{
  "default_remind_advance_minutes": 15
}
```

**响应示例**:

```json
{
  "code": 2000,
  "msg": "设置成功",
  "data": {
    "ok": true
  }
}
```

---

## 三、权限说明

### 3.1 角色层级（RoleLevel）

- **SALES（销售）**: 仅销售职能，只能查看和操作自己的客户
- **TEAM（团队管理）**: 基层管理 + 销售职能，可以查看团队内客户，也可以作为经办人推进自己的客户
- **BRANCH（分所管理）**: 仅管理职能，可以查看本分所客户，不能申领和作为经办人
- **HQ（总所管理）**: 仅管理职能，可以查看全所客户，不能申领和作为经办人

### 3.2 数据范围（OrgScope）

- **SELF**: 本人数据
- **TEAM**: 本团队数据
- **BRANCH**: 本分所数据
- **HQ**: 全所数据

### 3.3 权限规则

1. **申领权限**: 只有 SALES 和 TEAM 可以申领公海客户，HQ 和 BRANCH 不能申领
2. **分配权限**: 只有管理角色（TEAM/BRANCH/HQ）可以分配客户，且不能分配给 HQ 和 BRANCH 角色
3. **审批权限**: 只有 TEAM/BRANCH/HQ 可以审批，SALES 不能审批
4. **审批链**: TEAM 申领时，审批链为 BRANCH → HQ（跳过自己）

---

## 四、错误响应格式

**错误响应示例**:

```json
{
  "code": 4000,
  "msg": "操作失败：不能分配给管理角色（HQ/BRANCH）",
  "data": null
}
```

**常见错误码**:
- `4000`: 通用错误
- `4001`: 参数错误
- `4003`: 权限不足
- `4004`: 资源不存在
- `4005`: 业务逻辑错误

---

## 五、注意事项

1. **时间格式**: 所有时间字段统一使用 `YYYY-MM-DD HH:mm:ss` 格式（如：`2025-01-15 14:30:00`）
2. **分页**: 列表接口统一使用 `page` 和 `pageSize` 参数，响应中包含 `total` 字段
3. **JWT 认证**: 所有接口都需要在请求头中携带 JWT Token
4. **路径前缀**: 小程序后台管理统一使用 `/api/` 前缀
5. **响应格式**: 统一使用 `{ code, msg, data }` 结构
6. **角色校验**: 后端需要根据当前用户的角色进行权限校验和数据范围过滤
7. **审批链**: 审批任务需要支持多级审批链，按角色层级依次审批

---

## 六、接口清单汇总

### Tab1「客户」模块
1. ✅ `GET /api/crm/client/list` - 获取客户列表
2. ✅ `GET /api/crm/client/{id}` - 获取客户详情
3. ✅ `POST /api/crm/client` - 创建客户/线索
4. ✅ `PUT /api/crm/client/{id}` - 更新客户信息
5. ✅ `POST /api/crm/client/{id}/apply` - 申领公海客户
6. ✅ `POST /api/crm/client/{id}/assign` - 分配客户（管理权限）
7. ✅ `POST /api/crm/client/approve/{apply_id}` - 审批客户申领

### Tab5「我的」模块
1. ✅ `GET /api/mine/profile` - 获取个人资料
2. ✅ `POST /api/mine/profile/update` - 更新个人资料
3. ✅ `POST /api/mine/feedback` - 提交反馈
4. ✅ `GET /api/mine/feedback/list` - 获取反馈列表
5. ✅ `GET /api/mine/approval/list` - 获取审批任务列表
6. ✅ `POST /api/mine/approval/{id}/approve` - 审批任务（通过/驳回）
7. ✅ `GET /api/mine/settings/remind` - 获取提醒偏好设置
8. ✅ `POST /api/mine/settings/remind` - 设置提醒偏好

---

## 七、前端代码路径更新说明

**重要**: 前端代码中部分接口路径需要更新，以统一使用 `/api/` 前缀：

### 需要更新的文件

1. **`uniapp-vue3/src/api/mine.ts`**:
   - `/mine/feedback` → `/api/mine/feedback`
   - `/mine/feedback/list` → `/api/mine/feedback/list`
   - `/mine/approval/list` → `/api/mine/approval/list`
   - `/mine/approval/${id}/approve` → `/api/mine/approval/${id}/approve`
   - `/mine/settings/remind` → `/api/mine/settings/remind`

2. **`uniapp-vue3/src/api/client.ts`**:
   - `/crm/client/list` → `/api/crm/client/list`
   - `/crm/client/${id}` → `/api/crm/client/${id}`
   - `/crm/client` → `/api/crm/client`
   - `/crm/client/${id}/apply` → `/api/crm/client/${id}/apply`
   - `/crm/client/${id}/assign` → `/api/crm/client/${id}/assign`
   - `/crm/client/approve/${apply_id}` → `/api/crm/client/approve/${apply_id}`
   - 其他 `/crm/client/*` 相关接口也需要添加 `/api/` 前缀

**注意**: 后端开发时，请确保所有接口路径都使用 `/api/` 前缀，前端代码也需要同步更新。

---

**文档版本**: v1.0  
**最后更新**: 2025-01-15
