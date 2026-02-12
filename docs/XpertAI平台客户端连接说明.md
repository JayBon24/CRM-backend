# XpertAI平台客户端连接说明

## 概述

本文档说明如何连接和使用 XpertAI 智能体平台客户端，基于 `xpert_integration.py` 模块实现。

## 连接配置

### 1. API 配置获取优先级

配置获取按以下优先级顺序：

1. **构造函数参数** - 直接传入 `api_url` 和 `api_key`
2. **Django 配置** - 从 `settings.XPERT_API_URL` 和 `settings.LANGGRAPH_API_KEY` 获取
3. **环境变量** - 从系统环境变量 `LANGGRAPH_API_KEY` 获取
4. **默认值** - API URL 默认为 `https://api.mtda.cloud/api/ai/`

### 2. API Key 验证

- API Key 是**必需**的，如果所有方式都未提供，会抛出 `ValueError` 异常
- 错误提示：`"API密钥未提供，请设置api_key参数、LANGGRAPH_API_KEY配置或环境变量"`

## 客户端初始化

### 核心依赖

- 使用 `langgraph_sdk` 的 `client.get_client()` 方法创建客户端
- 需要传入 `url` 和 `api_key` 两个参数

### 初始化流程

1. 按优先级获取 API URL 和 API Key
2. 验证 API Key 是否存在
3. 调用 SDK 创建客户端实例
4. 记录初始化成功日志

## 连接测试

### 测试方法

- 使用 `test_connection()` 异步方法测试连接
- 通过尝试获取专家列表（limit=1）来验证连接是否正常
- 返回布尔值：`True` 表示连接成功，`False` 表示连接失败

### 测试原理

通过调用 `get_experts()` 方法，如果能成功获取专家列表，说明：
- API URL 正确
- API Key 有效
- 网络连接正常
- 平台服务可用

## 主要功能模块

### 1. 专家管理

- **获取专家列表** - 支持分页（limit/offset）
- **获取单个专家** - 根据专家ID查询
- **专家信息包含**：ID、名称、描述、指令、模型、元数据、创建时间等

### 2. 对话线程管理

- **创建线程** - 支持自定义线程ID和元数据
- **线程复用** - 通过相同的 `thread_id` 实现多轮对话上下文
- **线程元数据** - 可存储对话ID、用户ID等信息

### 3. 专家调用

- **同步调用** - `ask_expert()` 方法（内部使用异步）
- **异步调用** - `run_expert()` 方法
- **流式调用** - 支持实时流式响应，通过回调函数处理数据块

### 4. 流式响应处理

- **流式API** - 使用 `client.runs.stream()` 方法
- **数据格式** - 支持多种数据格式（message、event、component等）
- **去重机制** - 使用 MD5 哈希避免重复发送相同内容
- **超时控制** - 默认120秒超时，可配置
- **资源管理** - 使用 `aclose()` 确保流正确关闭

## 关键特性

### 1. 多轮对话支持

- 通过 `conversation_id` 参数关联对话
- 使用 `thread_id` 实现上下文保持
- 同一对话使用相同的 thread，实现上下文连续性

### 2. 错误处理

- 详细的日志记录（INFO、WARNING、ERROR）
- 异常捕获和错误信息返回
- 备用专家ID机制（当获取专家列表失败时）

### 3. 数据提取

- 从组件数据中提取法规文档信息
- 支持去重（使用字典结构）
- 提取文档名称和文件URL

## 访问接口

### 后端 HTTP 接口列表

以下接口在代码中调用了 XpertAI 平台：

#### 1. 文档分析接口

**接口路径：** `POST /api/case/cases/expert_analyze/`

**所在文件：** `case_management/views.py` (CaseManagementViewSet)

**功能：** AI专家解析文档，提取占位符信息

**调用方法：** `analyze_documents_with_expert()`

**请求参数：**
- `case_id`: 案例ID
- `files`: 文件列表（包含 base64 编码的文件内容）
- `templates`: 模板列表（包含模板ID和占位符信息）

**返回数据：**
- `matched_placeholders`: 匹配的占位符列表
- `matched_templates`: 匹配的模板列表
- `parsed_data`: 解析后的数据

**文档发送流程：**

1. **前端准备文件数据**
   - 将文件转换为 Base64 编码
   - 构建文件对象，包含以下字段：
     ```json
     {
       "name": "文件名.docx",
       "type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
       "base64": "base64编码的文件内容"
     }
     ```

2. **后端接收并验证**
   - 接收 `files` 数组和 `templates` 数组
   - 验证文件列表不为空
   - 验证模板列表不为空

3. **创建 XpertAI 客户端**
   - 初始化 `XpertAIClient` 实例
   - 配置 API URL 和 API Key

4. **文件上传到 XpertAI 平台**
   - 遍历 `files` 数组中的每个文件
   - 对每个文件执行以下步骤：
     - 解码 Base64 内容：`base64.b64decode(file_data)`
     - 构建文件上传请求：
       - URL: `{api_url}v1/file`
       - 方法: `POST`
       - Headers: `{'x-api-key': api_key}`
       - Files: `{'file': (file_name, file_content, file_type)}`
     - 上传成功后获得文件ID（`upload_result.get('id')`）
     - 将文件ID添加到 `uploaded_files` 数组

5. **准备专家输入数据**
   - 构建模板信息字符串（包含模板ID、名称、占位符列表）
   - 创建专家输入对象：
     ```python
     expert_input = {
         "input": "分析提示词（包含模板信息）",
         "files": uploaded_files  # 文件ID数组
     }
     ```

6. **调用专家进行分析**
   - 使用流式API调用：`client.runs.stream(thread_id, assistant_id, expert_input)`
   - 处理流式响应，提取分析结果
   - 解析返回的JSON格式数据

7. **返回解析结果**
   - 提取 `matched_placeholders`（匹配的占位符）
   - 提取 `matched_templates`（匹配的模板）
   - 返回给前端

**关键点说明：**

- **文件格式要求**：文件必须以 Base64 编码形式发送
- **上传接口**：使用 XpertAI 平台的 `/v1/file` 接口上传文件
- **文件ID传递**：上传成功后，使用文件ID（而非文件内容）传递给专家
- **异步处理**：文件上传和专家调用都是异步操作
- **流式响应**：专家分析结果通过流式API返回，需要逐步处理数据块

---

#### 2. 法规检索接口（同步）

**接口路径：** `POST /api/case/regulation-search/regulations/`

**所在文件：** `case_management/regulation_search_views.py` (RegulationSearchViewSet)

**功能：** 搜索法规内容

**调用方法：** `search_regulations()`

**请求参数：**
- `query`: 搜索关键词
- `filters`: 筛选条件（法规类型、生效日期、发布部门等）
- `config`: 配置信息

**返回数据：**
- `results`: 法规搜索结果列表
- `total`: 结果总数
- `query`: 查询内容

---

#### 3. 法规检索接口（流式）

**接口路径：** `POST /api/case/regulation-search/regulations-stream/`

**所在文件：** `case_management/regulation_search_views.py` (RegulationSearchViewSet)

**功能：** 流式搜索法规，实时返回结果

**调用方法：** `search_regulations()` (带 stream_callback)

**请求参数：**
- `query`: 搜索关键词
- `filters`: 筛选条件
- `conversation_id`: 对话ID（可选，用于多轮对话）

**响应格式：** Server-Sent Events (SSE)
- `type: chunk` - 数据块
- `type: complete` - 完成
- `type: error` - 错误

---

#### 4. 智能对话接口（流式）

**接口路径：** `POST /api/case/regulation-conversations/{conversation_id}/ask-expert/`

**所在文件：** `case_management/regulation_search_views.py` (RegulationConversationViewSet)

**功能：** 使用Xpert平台专家进行智能对话

**调用方法：** `ask_expert_for_chat()`

**请求参数：**
- `question`: 用户问题
- `category`: 问题分类（question/similar-case/regulation）

**响应格式：** Server-Sent Events (SSE)
- `type: chunk` - AI回答的数据块
- `type: complete` - 对话完成，包含相关法规
- `type: error` - 错误信息

**返回数据（完成时）：**
- `related_regulations`: 相关法规文档列表（包含 name 和 fileUrl）

---

### 接口调用位置总结

| 接口路径 | 视图类 | 调用的XpertAI方法 | 响应类型 |
|---------|--------|------------------|---------|
| `/api/case/cases/expert_analyze/` | CaseManagementViewSet | `analyze_documents_with_expert()` | JSON |
| `/api/case/regulation-search/regulations/` | RegulationSearchViewSet | `search_regulations()` | JSON |
| `/api/case/regulation-search/regulations-stream/` | RegulationSearchViewSet | `search_regulations()` | SSE |
| `/api/case/regulation-conversations/{id}/ask-expert/` | RegulationConversationViewSet | `ask_expert_for_chat()` | SSE |

## 使用场景

### 1. 法规检索

- 使用 `search_regulations()` 方法
- 支持查询内容和筛选条件
- 返回文本格式的法规内容
- 支持同步和流式两种方式

### 2. 智能对话

- 使用 `ask_expert_for_chat()` 方法
- 支持问题分类（question/similar-case/regulation）
- 流式返回AI回答
- 自动提取相关法规文档

### 3. 文档分析

- 使用 `analyze_documents_with_expert()` 方法
- 支持文件上传到平台
- 提取占位符信息
- 返回匹配的占位符和模板

#### 文件上传技术实现

**上传方法：** `upload_file(file_data, file_name, file_type)`

**实现步骤：**

1. **Base64 解码**
   ```python
   file_content = base64.b64decode(file_data)
   ```

2. **构建上传请求**
   - 使用 `requests` 库发送 POST 请求
   - 上传URL：`{api_url}v1/file`
   - 请求头：包含 `x-api-key` 认证
   - 文件数据：使用 multipart/form-data 格式

3. **处理响应**
   - 成功（200/201）：返回包含文件ID的JSON对象
   - 失败：返回 `None`，记录错误日志

4. **文件ID使用**
   - 上传成功后，文件ID存储在 `upload_result['id']`
   - 文件ID数组传递给专家输入参数
   - 专家通过文件ID访问已上传的文件

**注意事项：**
- 文件大小限制：取决于 XpertAI 平台的限制
- 支持的文件类型：取决于平台支持（通常支持常见文档格式）
- 错误处理：上传失败时不会中断整个流程，但会记录警告日志

## 注意事项

### 1. 异步操作

- 所有平台交互都是异步操作
- 需要使用 `await` 关键字
- 在同步环境中需要使用 `asyncio.run()` 或事件循环

### 2. API 限制

- 注意请求频率限制
- 流式响应有超时限制（120秒）
- 大文件上传可能需要额外处理

### 3. 错误处理

- 网络错误：检查网络连接和API URL
- 认证错误：检查API Key是否正确
- 服务错误：检查平台服务状态和专家ID有效性

### 4. 资源清理

- 流式响应必须正确关闭（使用 `aclose()`）
- 避免资源泄漏
- 异常情况下也要确保资源释放

## 配置建议

### 开发环境

- 使用环境变量管理 API Key
- 在 `.env` 文件中配置（不要提交到版本控制）

### 生产环境

- 使用 Django settings 配置
- 考虑使用密钥管理服务（如 AWS Secrets Manager）
- 设置适当的日志级别

## 总结

XpertAI 客户端连接的核心是：
1. **配置获取** - 多级优先级确保灵活性
2. **SDK 初始化** - 使用 langgraph_sdk 创建客户端
3. **连接验证** - 通过实际API调用测试连接
4. **异步处理** - 所有操作都是异步的
5. **流式支持** - 支持实时数据流处理
6. **错误处理** - 完善的异常处理和日志记录

