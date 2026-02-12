# 占位符模板管理API文档

## 概述
本文档描述了案件管理系统中模板占位符信息的管理API，包括显示、编辑和重新解析功能。

## API端点

### 1. 获取模板列表（包含占位符信息）
```
GET /api/case/templates/
```

**响应示例：**
```json
{
  "code": 2000,
  "msg": "获取成功",
  "data": [
    {
      "id": 1,
      "template_name": "起诉状模板",
      "template_type": "起诉状",
      "placeholder_summary": {
        "total_placeholders": 8,
        "unique_placeholders": 6,
        "categories": {
          "plaintiff": ["name", "address"],
          "defendant": ["name", "address"],
          "case": ["number", "type"],
          "amount": ["contract_amount", "lawyer_fee"]
        },
        "with_defaults": 2,
        "without_defaults": 6
      },
      "placeholder_list": [
        {
          "key": "plaintiff.name",
          "default_value": null,
          "full_match": "{{ plaintiff.name }}"
        },
        {
          "key": "amount.contract_amount",
          "default_value": "100000",
          "full_match": "{{ amount.contract_amount | 100000 }}"
        }
      ]
    }
  ]
}
```

### 2. 获取模板详细占位符信息
```
GET /api/case/templates/{id}/placeholders/
```

**响应示例：**
```json
{
  "code": 2000,
  "msg": "获取占位符信息成功",
  "data": {
    "template_id": 1,
    "template_name": "起诉状模板",
    "placeholder_info": {
      "placeholders": [...],
      "analysis": {...},
      "total_count": 8,
      "unique_count": 6
    }
  }
}
```

### 3. 更新模板占位符信息
```
PUT /api/case/templates/{id}/update_placeholders/
```

**请求体：**
```json
{
  "placeholder_info": {
    "placeholders": [
      {
        "key": "plaintiff.name",
        "default_value": "原告公司名称",
        "full_match": "{{ plaintiff.name }}"
      },
      {
        "key": "defendant.name",
        "default_value": "被告公司名称", 
        "full_match": "{{ defendant.name }}"
      }
    ],
    "analysis": {
      "by_category": {
        "plaintiff": ["name"],
        "defendant": ["name"]
      },
      "with_defaults": ["plaintiff.name", "defendant.name"],
      "without_defaults": []
    },
    "total_count": 2,
    "unique_count": 2
  }
}
```

**响应示例：**
```json
{
  "code": 2000,
  "msg": "占位符信息更新成功",
  "data": {
    "id": 1,
    "template_name": "起诉状模板",
    "placeholder_info": {...},
    "placeholder_summary": {...}
  }
}
```

### 4. 重新解析模板占位符
```
POST /api/case/templates/{id}/reparse_placeholders/
```

**响应示例：**
```json
{
  "code": 2000,
  "msg": "重新解析成功，发现 8 个占位符",
  "data": {
    "id": 1,
    "template_name": "起诉状模板",
    "placeholder_info": {...},
    "placeholder_summary": {...}
  }
}
```

### 5. 上传带占位符的模板
```
POST /api/case/templates/upload/
Content-Type: multipart/form-data
```

**请求参数：**
- `file`: 模板文件
- `template_name`: 模板名称
- `template_type`: 模板类型
- `description`: 模板描述

**响应示例：**
```json
{
  "code": 2000,
  "msg": "模板上传成功，解析到 8 个占位符",
  "data": {
    "id": 1,
    "template_name": "起诉状模板",
    "placeholder_info": {...},
    "placeholder_summary": {
      "total_placeholders": 8,
      "unique_placeholders": 6,
      "categories": {...},
      "with_defaults": 2,
      "without_defaults": 6
    }
  }
}
```

## 占位符格式

### 支持的占位符格式：
1. `{{ key }}` - 简单占位符
2. `{{ key | 默认值 }}` - 带默认值的占位符

### 占位符分类：
- `plaintiff.*` - 原告相关信息
- `defendant.*` - 被告相关信息  
- `case.*` - 案件相关信息
- `court.*` - 法院相关信息
- `amount.*` - 金额相关信息
- `date.*` - 日期相关信息
- `other.*` - 其他信息

## 使用场景

### 1. 模板列表页面
- 显示每个模板的占位符统计信息
- 快速了解模板的复杂度和占位符分布

### 2. 模板编辑页面
- 查看和编辑模板的详细占位符信息
- 修改占位符的默认值
- 重新解析模板文件

### 3. 模板上传
- 自动解析上传模板的占位符信息
- 提供占位符统计和分类信息

## 错误处理

所有API都返回统一的错误格式：
```json
{
  "code": 4000,
  "msg": "错误描述",
  "data": {}
}
```

常见错误：
- 模板不存在
- 占位符信息格式错误
- 文件解析失败
- 权限不足



