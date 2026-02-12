# AI 管理模块

## 📋 模块说明

AI 管理模块负责处理所有 AI 相关的功能，包括：
- AI 对话（Chat）
- 文档生成（Document Generation）
- 法规检索（Regulation Search）
- 法律检索（Legal Search）

## 🏗️ 目录结构

```
ai_management/
├── models/              # 数据模型层
│   └── chat_history.py  # AI 对话历史模型
├── serializers/         # 序列化器层
│   ├── chat_serializer.py
│   ├── document_serializer.py
│   └── search_serializer.py
├── services/            # 业务逻辑层
│   ├── ai_service.py
│   ├── chat_service.py
│   ├── document_service.py
│   └── search_service.py
├── views/               # 视图层（控制器）
│   └── api/
│       ├── chat_views.py
│       ├── document_views.py
│       └── search_views.py
├── urls/                # 路由配置
│   ├── api_router.py
│   └── admin_router.py
└── utils/               # 工具类
    ├── prompt_builder.py
    └── response_parser.py
```

## 🔌 API 接口

### AI 对话接口

- **POST** `/api/ai/chat/chat/` - AI 对话
- **GET** `/api/ai/chat/history/` - 获取对话历史

### 文档生成接口

- **POST** `/api/ai/document/generate/` - 生成文档

### 检索接口

- **POST** `/api/ai/search/regulation/` - 法规检索
- **POST** `/api/ai/search/legal/` - 法律检索

## 📝 使用说明

### 1. AI 对话示例

```python
# 请求
POST /api/ai/chat/chat/
{
    "message": "请帮我分析一下这个案件",
    "context_type": "case",
    "context_id": 123,
    "uploaded_files": []
}

# 响应
{
    "code": 2000,
    "msg": "success",
    "data": {
        "response": "AI响应内容",
        "model_name": "gpt-4"
    }
}
```

### 2. 文档生成示例

```python
# 请求
POST /api/ai/document/generate/
{
    "document_type": "起诉状",
    "case_id": 123,
    "case_data": {...}
}
```

## 🔄 代码迁移计划

当前 AI 相关代码分散在 `case_management` 模块中，后续需要迁移：

1. **服务层代码**：
   - `case_management/ai_service.py` → `ai_management/services/ai_service.py`
   - `case_management/langchain_ai_service.py` → `ai_management/services/langchain_service.py`

2. **视图代码**：
   - `case_management/views.py` 中的 `ai_chat` action → `ai_management/views/api/chat_views.py`
   - `case_management/regulation_search_views.py` → `ai_management/views/api/search_views.py`

## 🚀 开发指南

1. **添加新的 AI 功能**：
   - 在 `services/` 目录下创建对应的服务类
   - 在 `views/api/` 目录下创建对应的视图
   - 在 `urls/api_router.py` 中注册路由

2. **添加新的模型**：
   - 在 `models/` 目录下创建模型文件
   - 运行 `python manage.py makemigrations ai_management`
   - 运行 `python manage.py migrate`

3. **测试接口**：
   - 访问 Swagger 文档：`http://localhost:8000/`
   - 或使用 Postman 等工具测试

## 📚 相关文档

- [AI模块创建指南](../docs/AI模块创建指南.md)
- [项目目录结构说明](../docs/项目目录结构说明.md)

