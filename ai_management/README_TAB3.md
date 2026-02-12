# Tab3 AI 对话功能实现说明

## 概述

Tab3 AI 对话功能已集成到 `lsl-backend`，通过 WebSocket 提供流式对话能力。

## 已实现功能

### 1. WebSocket 接口
- **路径**: `/api/ai/ws/tab3/`
- **协议**: WebSocket (JSON)
- **客户端消息格式**:
  ```json
  {
    "type": "user_message",
    "sessionId": "可选，会话ID",
    "message": "用户消息内容"
  }
  ```
- **服务端消息格式**:
  - Token 增量: `{ "type": "token", "sessionId": "...", "textDelta": "..." }`
  - 最终答案: `{ "type": "final", "sessionId": "...", "answer": "..." }`
  - 错误: `{ "type": "error", "code": "...", "message": "..." }`

### 2. 数据库模型
- **Tab3Session**: 持久化 `sessionId` <-> `thread_id` 映射
- **表名**: `lsl_tab3_session`

### 3. 配置项

**配置文件位置**：`lsl/lsl-backend/conf/env.py`（第 85-93 行）

**关键配置项**：
- `XPERT_SDK_API_URL`: XpertAI SDK API 地址
  - **本地开发**：`http://localhost:3000/api/ai/`（当前默认值）
  - **线上环境**：`https://api.xpertai.com/api/ai/` 或你的部署地址
- `XPERT_ASSISTANT_ID`: Assistant ID（本地和线上可能不同）
- `XPERTAI_API_KEY`: API 密钥（用于鉴权，在文件第 75 行）
- `XPERT_STREAM_MODE`: 流式模式（默认 "debug"）

**当前接入状态**：
- ✅ **当前接入的是本地 XpertAI 服务**（`localhost:3000`）
- ✅ 可通过修改配置切换到线上环境

## 部署步骤

### 1. 运行数据库迁移
```bash
cd lsl/lsl-backend
python manage.py makemigrations ai_management
python manage.py migrate ai_management
```

### 2. 安装依赖
确保已安装 `langgraph-sdk`:
```bash
pip install langgraph-sdk
```

### 3. 配置环境变量

#### 3.1 本地开发配置（当前默认）

在 `conf/env.py` 中已配置：
```python
XPERT_SDK_API_URL = os.getenv("XPERT_SDK_API_URL", "http://localhost:3000/api/ai/")
XPERT_ASSISTANT_ID = os.getenv("XPERT_ASSISTANT_ID", "f9106c17-01f8-4a46-a68c-a1804c81325b")
XPERTAI_API_KEY = os.getenv("XPERTAI_API_KEY", "你的本地API密钥")
```

#### 3.2 切换到线上配置

**方法 1：直接修改 `conf/env.py`（推荐用于开发测试）**

```python
# 修改为线上地址
XPERT_SDK_API_URL = os.getenv("XPERT_SDK_API_URL", "https://api.xpertai.com/api/ai/")
XPERT_ASSISTANT_ID = os.getenv("XPERT_ASSISTANT_ID", "你的线上AssistantID")
XPERTAI_API_KEY = os.getenv("XPERTAI_API_KEY", "你的线上API密钥")
```

**方法 2：使用系统环境变量（推荐用于生产环境）**

**Windows**：
```cmd
set XPERT_SDK_API_URL=https://api.xpertai.com/api/ai/
set XPERT_ASSISTANT_ID=你的线上AssistantID
set XPERTAI_API_KEY=你的线上API密钥
```

**Linux/Mac**：
```bash
export XPERT_SDK_API_URL=https://api.xpertai.com/api/ai/
export XPERT_ASSISTANT_ID=你的线上AssistantID
export XPERTAI_API_KEY=你的线上API密钥
```

**配置优先级**：
1. 系统环境变量（最高优先级）
2. `conf/env.py` 中的 `os.getenv()` 读取
3. `conf/env.py` 中的默认值（最低优先级）

#### 3.3 接口路径说明

- **WebSocket 接口**：`/api/ai/ws/tab3/`
  - 配置位置：`ai_management/routing.py`
  - 完整 URL：`ws://your-domain/api/ai/ws/tab3/?token=xxx`
- **HTTP 历史接口**：`/api/ai/tab3/history/`
  - 配置位置：`ai_management/urls/api_router.py`
  - 方法：`GET`
  - 参数：`sessionId`（query string）

### 4. 启动服务
使用 ASGI 服务器（如 uvicorn）启动：
```bash
uvicorn application.asgi:application --host 0.0.0.0 --port 8000
```

或使用 Django 开发服务器（仅用于开发）：
```bash
python manage.py runserver
```

## 待完善功能

### 1. 工具执行层
当前 `_execute_client_tool` 为占位实现，需要：
- 实现真实的业务工具调用（如查询客户、创建工单等）
- 建议调用现有业务后端 API（`customer_management`、`case_management` 等）

### 2. 鉴权
当前 WebSocket 连接未实现完整的鉴权逻辑，需要：
- 从 query string 或 header 获取 token
- 验证 token 有效性
- 拒绝未授权连接

### 3. 错误处理与重试
- 实现断线重连机制
- 添加超时处理
- 完善错误消息

### 4. 生产环境优化
- 将 `CHANNEL_LAYERS` 从 InMemory 切换到 Redis（支持多实例）
- 添加限流
- 添加日志脱敏
- 实现取消运行功能

## 测试

### WebSocket 连接测试
可以使用 `websocat` 或类似工具测试：
```bash
websocat ws://localhost:8000/api/ai/ws/tab3/
```

发送消息：
```json
{"type": "user_message", "message": "你好"}
```

## 文件结构

```
ai_management/
├── consumers/
│   ├── __init__.py
│   └── tab3_chat.py          # WebSocket Consumer
├── models/
│   └── tab3_session.py        # 会话模型
├── routing.py                 # WebSocket 路由
├── views/
│   └── api/
│       └── tab3_views.py      # HTTP 接口（可选）
└── urls/
    └── api_router.py          # 路由配置
```

## 注意事项

1. **langgraph-sdk 版本**: 确保使用兼容的 SDK 版本
2. **异步 ORM**: 代码使用了 Django 的异步 ORM（`aget`、`asave`），需要 Django 3.1+
3. **Channels**: 需要正确配置 `CHANNEL_LAYERS`（开发环境可用 InMemory，生产环境建议 Redis）
