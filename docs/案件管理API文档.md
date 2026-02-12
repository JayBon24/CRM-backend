# 案件管理 API 文档

## 创建案件

### 接口地址
```
POST /api/case/cases/
```

### 请求头
```
Content-Type: application/json
Authorization: Bearer <token>  // 如需认证
```

## 字段说明

### 必填字段 ✅

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `case_number` | string(100) | 案例编号 | "2024民初001号" |
| `case_name` | string(200) | 案例名称 | "某公司诉某公司合同纠纷案" |
| `case_type` | string(50) | 案例类型 | "合同纠纷" |

### 可选字段（有默认值）

| 字段名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `case_status` | string(50) | "待处理" | 案例状态 |

### 可选字段（基础信息）

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `case_description` | text | 案例描述 | "本案涉及买卖合同纠纷..." |
| `case_date` | date | 案例日期 | "2024-01-15" |
| `case_result` | text | 案例结果 | "原告胜诉" |
| `case_notes` | text | 案例备注 | "需要补充证据材料" |

### 可选字段（原告信息）

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `plaintiff_name` | string(200) | 原告名称 | "北京某某科技有限公司" |
| `plaintiff_credit_code` | string(100) | 原告统一社会信用代码 | "91110000123456789X" |
| `plaintiff_address` | string(500) | 原告地址 | "北京市朝阳区某某街道1号" |
| `plaintiff_legal_representative` | string(100) | 原告法定代表人 | "张三" |

### 可选字段（被告信息）

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `defendant_name` | string(200) | 被告名称 | "上海某某贸易有限公司" |
| `defendant_credit_code` | string(100) | 被告统一社会信用代码 | "91310000987654321Y" |
| `defendant_address` | string(500) | 被告地址 | "上海市浦东新区某某路2号" |
| `defendant_legal_representative` | string(100) | 被告法定代表人 | "李四" |

### 可选字段（案件详情）

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `draft_person` | string(50) | 拟稿人 | "王律师" |
| `contract_amount` | decimal(20,2) | 合同金额 | 1000000.00 |
| `lawyer_fee` | decimal(20,2) | 律师费 | 50000.00 |
| `litigation_request` | text | 诉讼请求 | "请求判令被告支付..." |
| `facts_and_reasons` | text | 事实与理由 | "原告与被告于2023年..." |
| `jurisdiction` | string(200) | 管辖法院 | "北京市朝阳区人民法院" |
| `petitioner` | string(100) | 申请人 | "张三" |
| `filing_date` | date | 立案日期 | "2024-01-20" |

### 只读字段（系统自动生成）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | integer | 案件ID（主键） |
| `create_datetime` | datetime | 创建时间 |
| `update_datetime` | datetime | 更新时间 |
| `is_deleted` | boolean | 是否删除（软删除标记） |

## 请求示例

### 最小请求（仅必填字段）

```json
POST /api/case/cases/
Content-Type: application/json

{
  "case_number": "2024民初001号",
  "case_name": "某公司诉某公司合同纠纷案",
  "case_type": "合同纠纷"
}
```

### 完整请求示例

```json
POST /api/case/cases/
Content-Type: application/json

{
  "case_number": "2024民初001号",
  "case_name": "北京某某科技有限公司诉上海某某贸易有限公司买卖合同纠纷案",
  "case_type": "合同纠纷",
  "case_status": "进行中",
  "case_description": "本案涉及买卖合同纠纷，原告主张被告未按约定支付货款",
  "case_date": "2024-01-15",
  
  "plaintiff_name": "北京某某科技有限公司",
  "plaintiff_credit_code": "91110000123456789X",
  "plaintiff_address": "北京市朝阳区某某街道1号",
  "plaintiff_legal_representative": "张三",
  
  "defendant_name": "上海某某贸易有限公司",
  "defendant_credit_code": "91310000987654321Y",
  "defendant_address": "上海市浦东新区某某路2号",
  "defendant_legal_representative": "李四",
  
  "draft_person": "王律师",
  "contract_amount": 1000000.00,
  "lawyer_fee": 50000.00,
  "litigation_request": "1. 请求判令被告支付货款人民币1,000,000.00元；\n2. 请求判令被告承担本案诉讼费用。",
  "facts_and_reasons": "原告与被告于2023年6月签订《买卖合同》，约定原告向被告供应货物...",
  "jurisdiction": "北京市朝阳区人民法院",
  "petitioner": "北京某某科技有限公司",
  "filing_date": "2024-01-20",
  "case_notes": "需要补充供货凭证"
}
```

## 响应示例

### 成功响应 (200 OK)

```json
{
  "code": 2000,
  "msg": "创建成功",
  "data": {
    "id": 50,
    "case_number": "2024民初001号",
    "case_name": "北京某某科技有限公司诉上海某某贸易有限公司买卖合同纠纷案",
    "case_type": "合同纠纷",
    "case_status": "进行中",
    "case_description": "本案涉及买卖合同纠纷，原告主张被告未按约定支付货款",
    "case_date": "2024-01-15",
    "case_result": null,
    "case_notes": "需要补充供货凭证",
    
    "draft_person": "王律师",
    "plaintiff_name": "北京某某科技有限公司",
    "plaintiff_credit_code": "91110000123456789X",
    "plaintiff_address": "北京市朝阳区某某街道1号",
    "plaintiff_legal_representative": "张三",
    
    "defendant_name": "上海某某贸易有限公司",
    "defendant_credit_code": "91310000987654321Y",
    "defendant_address": "上海市浦东新区某某路2号",
    "defendant_legal_representative": "李四",
    
    "contract_amount": "1000000.00",
    "lawyer_fee": "50000.00",
    "litigation_request": "1. 请求判令被告支付货款人民币1,000,000.00元；\n2. 请求判令被告承担本案诉讼费用。",
    "facts_and_reasons": "原告与被告于2023年6月签订《买卖合同》，约定原告向被告供应货物...",
    "jurisdiction": "北京市朝阳区人民法院",
    "petitioner": "北京某某科技有限公司",
    "filing_date": "2024-01-20",
    
    "create_datetime": "2024-10-29 15:30:00",
    "update_datetime": "2024-10-29 15:30:00",
    "is_deleted": false
  }
}
```

### 错误响应

#### 字段验证失败 (400 Bad Request)

```json
{
  "code": 4000,
  "msg": "字段验证失败",
  "data": {
    "case_number": ["该字段不能为空"],
    "case_name": ["该字段不能为空"],
    "case_type": ["该字段不能为空"]
  }
}
```

#### 案例编号重复 (400 Bad Request)

```json
{
  "code": 4000,
  "msg": "案例编号已存在",
  "data": null
}
```

#### 未授权 (401 Unauthorized)

```json
{
  "code": 4010,
  "msg": "未授权访问",
  "data": null
}
```

## 案例类型参考

常见的案例类型包括：

- `合同纠纷`
- `侵权责任纠纷`
- `劳动争议`
- `知识产权纠纷`
- `婚姻家庭纠纷`
- `继承纠纷`
- `物权纠纷`
- `债权纠纷`
- `公司纠纷`
- `其他`

## 案例状态参考

常见的案例状态包括：

- `待处理` (默认)
- `进行中`
- `已结案`
- `已归档`
- `已撤诉`
- `调解中`
- `上诉中`
- `执行中`

## 相关接口

### 获取案件列表
```
GET /api/case/cases/
```

### 获取案件详情
```
GET /api/case/cases/{id}/
```

### 更新案件
```
PUT /api/case/cases/{id}/
PATCH /api/case/cases/{id}/  // 部分更新
```

### 删除案件（软删除）
```
DELETE /api/case/cases/{id}/
```

### 获取案件文档树
```
GET /api/case/cases/{id}/document_tree/
```

## 前端集成示例

### JavaScript (Fetch API)

```javascript
// 创建案件
async function createCase(caseData) {
  const response = await fetch('/api/case/cases/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(caseData)
  });
  
  const result = await response.json();
  
  if (result.code === 2000) {
    console.log('案件创建成功:', result.data);
    return result.data;
  } else {
    console.error('创建失败:', result.msg);
    throw new Error(result.msg);
  }
}

// 使用示例
const newCase = await createCase({
  case_number: '2024民初001号',
  case_name: '某公司诉某公司合同纠纷案',
  case_type: '合同纠纷',
  plaintiff_name: '北京某某科技有限公司',
  defendant_name: '上海某某贸易有限公司',
  contract_amount: 1000000.00
});
```

### Vue 3 + Axios

```javascript
import axios from 'axios'

export const caseAPI = {
  // 创建案件
  async create(caseData) {
    try {
      const response = await axios.post('/api/case/cases/', caseData)
      if (response.data.code === 2000) {
        ElMessage.success('案件创建成功')
        return response.data.data
      }
    } catch (error) {
      ElMessage.error(error.response?.data?.msg || '创建失败')
      throw error
    }
  },
  
  // 获取案件列表
  async list(params) {
    const response = await axios.get('/api/case/cases/', { params })
    return response.data
  },
  
  // 获取案件详情
  async detail(id) {
    const response = await axios.get(`/api/case/cases/${id}/`)
    return response.data.data
  }
}
```

### React + Axios

```javascript
import axios from 'axios'

// 创建案件
export const createCase = async (caseData) => {
  try {
    const response = await axios.post('/api/case/cases/', caseData)
    
    if (response.data.code === 2000) {
      message.success('案件创建成功')
      return response.data.data
    }
  } catch (error) {
    message.error(error.response?.data?.msg || '创建失败')
    throw error
  }
}

// 在组件中使用
function CaseForm() {
  const handleSubmit = async (values) => {
    const newCase = await createCase({
      case_number: values.caseNumber,
      case_name: values.caseName,
      case_type: values.caseType,
      plaintiff_name: values.plaintiffName,
      defendant_name: values.defendantName,
      contract_amount: values.contractAmount
    })
    
    // 创建成功后跳转
    navigate(`/cases/${newCase.id}`)
  }
  
  return <Form onFinish={handleSubmit}>...</Form>
}
```

## 注意事项

1. ✅ **必填字段**: `case_number`、`case_name`、`case_type` 必须提供
2. ⚠️ **案例编号唯一性**: `case_number` 应该是唯一的，避免重复
3. ⚠️ **日期格式**: 日期字段使用 `YYYY-MM-DD` 格式（如：2024-01-15）
4. ⚠️ **金额字段**: `contract_amount` 和 `lawyer_fee` 使用 decimal 类型，最多20位数字，2位小数
5. ✅ **软删除**: 删除案件不会真正删除数据，只是标记 `is_deleted=true`
6. ✅ **自动创建目录**: 创建案件后，首次访问 `document_tree` 接口会自动创建预设目录

## 测试数据

```json
{
  "case_number": "TEST-2024-001",
  "case_name": "测试案件",
  "case_type": "合同纠纷",
  "plaintiff_name": "测试原告",
  "defendant_name": "测试被告",
  "contract_amount": 100000.00
}
```

---

**文档版本**: v1.0  
**最后更新**: 2024-10-29

