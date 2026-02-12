# API 简洁规范（lsl-backend）

## 1. 基础约定

- **Base URL**：`http://{host}:{port}`
- **接口前缀**：
  - 系统模块：`/api/system/`
  - 案件模块：`/api/case/`

- **Content-Type**：
  - JSON：`application/json`
  - 上传：`multipart/form-data`

## 2. 鉴权（JWT）

- **请求头**：
  - `Authorization: Bearer <access_token>`
  - 或 `Authorization: JWT <access_token>`

- **登录**：`POST /api/login/`
- **退出**：`POST /api/logout/`（按项目实现）
- **刷新 token**：`POST /token/refresh/`

## 3. 统一响应结构

### 3.1 成功（分页）

> 适用于 list 接口。

```json
{
  "code": 2000,
  "page": 1,
  "limit": 20,
  "total": 123,
  "data": [],
  "msg": "获取成功"
}
```

### 3.2 成功（非分页）

> 适用于详情、创建、更新、动作类接口。

```json
{
  "code": 2000,
  "data": {},
  "msg": "success"
}
```

### 3.3 失败（统一错误）

```json
{
  "code": 4000,
  "data": null,
  "msg": "错误描述"
}
```

说明：
- 项目全局异常处理为 `dvadmin.utils.exception.CustomExceptionHandler`
- 成功响应类：`SuccessResponse/DetailResponse`
- 错误响应类：`ErrorResponse`

## 4. 分页、查询与排序

- **分页参数**（以项目分页器为准，通常使用）：
  - `page`：页码（默认 1）
  - `limit`：每页数量（默认 20）

- **查询**：
  - `search`：全文搜索关键字（由 DRF SearchFilter 支持）
  - 业务字段过滤：由 `filterset_fields` 定义

- **排序**：
  - `ordering`：排序字段（如 `-id`）

## 5. REST 命名与路径规范

- **资源使用复数名词**：`/cases/`、`/documents/`、`/templates/`、`/folders/`
- **详情**：`/resources/{id}/`
- **自定义动作**（非 CRUD）：建议 ViewSet `@action`，路径使用动词短语：
  - `POST /cases/{id}/upload_document/`
  - `GET /cases/{id}/document_tree/`
  - `PUT /documents/{id}/move/`

## 6. 文件上传/下载规范

### 6.1 上传

- `POST /api/case/cases/{case_id}/upload_document/`
- `Content-Type: multipart/form-data`
- 推荐字段：
  - `folder_path`：目标目录路径
  - `file`：文件
  - `document_name`：文档显示名（可选）

### 6.2 下载

- `GET /api/case/documents/{document_id}/download/`
- 返回二进制流
- 响应头示例：
  - `Content-Disposition: attachment; filename="xxx.docx"`

## 7. 典型接口清单（按现有实现风格）

### 7.1 案件（Cases）

- `GET /api/case/cases/`：列表
- `POST /api/case/cases/`：创建
- `GET /api/case/cases/{id}/`：详情
- `PUT /api/case/cases/{id}/`：全量更新
- `PATCH /api/case/cases/{id}/`：部分更新
- `DELETE /api/case/cases/{id}/`：删除（软删除）

### 7.2 文档与目录

- `GET /api/case/cases/{id}/document_tree/`：文档树（首次可能自动创建目录）
- `GET /api/case/cases/{id}/folders/`：目录列表
- `GET /api/case/cases/{id}/folder_documents/`：目录下文档

### 7.3 模板与占位符

- `GET /api/case/templates/`：模板列表（可包含占位符摘要）
- `GET /api/case/templates/{id}/placeholders/`：占位符详情
- `PUT /api/case/templates/{id}/update_placeholders/`：更新占位符
- `POST /api/case/templates/{id}/reparse_placeholders/`：重新解析占位符
- `POST /api/case/templates/upload/`：上传模板

### 7.4 DOCX/HTML 转换

- `POST /api/case/document/convert/docx-to-html/`
- `POST /api/case/document/convert/html-to-docx/`
- `POST /api/case/document/upload-image/`

## 8. 错误码（建议最小集合）

- `2000`：成功
- `4000`：参数/业务错误（默认）
- `401`：未认证/鉴权失败（JWT 相关）
- `5000`：服务器内部错误（如需区分可扩展）

