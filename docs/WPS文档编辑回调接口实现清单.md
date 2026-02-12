# WPS 文档编辑回调接口完整实现清单

根据 WPS 官方文档，整理所有需要实现的回调接口。

**参考文档**:
- [文档编辑回调接口](https://solution.wps.cn/docs/callback/save.html#%E5%87%86%E5%A4%87%E4%B8%8A%E4%BC%A0%E9%98%B6%E6%AE%B5)
- [用户信息接口](https://solution.wps.cn/docs/callback/user.html)
- [扩展能力接口](https://solution.wps.cn/docs/callback/extend.html)
- [错误码说明](https://solution.wps.cn/docs/callback/error-code.html)

---

## 📋 一、文档预览接口

### ✅ 1. 获取文件下载地址

**接口**: `GET /v3/3rd/files/:file_id/download`

**说明**: 获取文件的下载地址

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_get_file_download_url`

---

### ✅ 2. 获取文件信息

**接口**: `GET /v3/3rd/files/:file_id`

**说明**: 获取文件的基本信息（名称、大小、版本等）

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_get_file_info`

---

### ✅ 3. 获取文件权限

**接口**: `GET /v3/3rd/files/:file_id/permission`

**说明**: 获取当前用户对文件的权限（read/write）

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_get_file_permission`

---

## 📝 二、文档编辑接口

### 🔄 三阶段保存接口（WPS官方推荐）

#### ✅ 1. 准备上传阶段

**接口**: `GET /v3/3rd/files/:file_id/upload/prepare`

**说明**: 三阶段保存的第一步，用于协商摘要算法

**参数**:
| 字段 | 位置 | 必须 | 类型 | 说明 |
|------|------|------|------|------|
| file_id | Path | 是 | string | 文档 ID |

**返回值**:
```json
{
  "code": 0,
  "data": {
    "digest_types": ["sha1", "sha256", "md5"]
  },
  "message": ""
}
```

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_upload_prepare`

---

#### ✅ 2. 获取上传地址

**接口**: `POST /v3/3rd/files/:file_id/upload/`

**说明**: 三阶段保存的第二步，返回文件上传地址和参数

**参数**:
| 字段 | 位置 | 必须 | 类型 | 说明 |
|------|------|------|------|------|
| file_id | Path | 是 | string | 文档 ID |
| request.file_id | Body | 是 | string | 文档 ID |
| request.name | Body | 是 | string | 文档名称 |
| request.size | Body | 是 | integer | 文档大小（字节） |
| request.digest | Body | 是 | object | 文档校验和 `{"sha1": "xxx"}` |
| request.is_manual | Body | 是 | boolean | 是否手动保存 |
| send_back_params | Body | 否 | map | 额外参数 |

**返回值**:
```json
{
  "code": 0,
  "data": {
    "upload_url": "https://your-server.com/api/case/v3/3rd/files/238/upload/commit",
    "upload_method": "POST",
    "headers": {
      "X-Upload-Token": "token",
      "Content-Type": "application/octet-stream"
    },
    "send_back_params": {}
  },
  "message": ""
}
```

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_upload_get_url`

---

#### ✅ 3. 完成上传阶段

**接口**: `POST /v3/3rd/files/:file_id/upload/commit`

**说明**: 三阶段保存的第三步，确认上传完成并保存文档信息

**参数**:
| 字段 | 位置 | 必须 | 类型 | 说明 |
|------|------|------|------|------|
| file_id | Path | 是 | string | 文档 ID |
| request.file_id | Body | 是 | string | 文档 ID |
| request.name | Body | 是 | string | 文档名称 |
| request.size | Body | 是 | integer | 文档大小（字节） |
| request.digest | Body | 是 | object | 文档校验和 `{"sha1": "xxx"}` |
| request.is_manual | Body | 是 | boolean | 是否手动保存 |
| response.status_code | Body | 是 | integer | 上传响应状态码 |
| response.headers | Body | 否 | map | 上传响应头 |
| response.body | Body | 否 | string | 上传响应体（base64） |
| send_back_params | Body | 否 | map | 额外参数 |

**返回值**:
```json
{
  "code": 0,
  "data": {
    "id": "238",
    "name": "文档名称.docx",
    "version": 180,
    "size": 18961,
    "create_time": 1670218748,
    "modify_time": 1670328304,
    "creator_id": "404",
    "modifier_id": "404"
  },
  "message": ""
}
```

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_upload_commit`

---

### ⚠️ 单阶段提交接口（已弃用，但保持兼容）

**接口**: `POST /v3/3rd/files/:file_id/upload`

**说明**: 单阶段提交在对接协议上比较简单，但 WPS 官方已暂停新接入，建议使用三阶段保存

**参数**:
| 字段 | 位置 | 必须 | 类型 | 说明 |
|------|------|------|------|------|
| file_id | Path | 是 | string | 文档 ID |
| file | Form | 是 | file | 文档实体 |
| name | Form | 是 | string | 文档名称 |
| size | Form | 是 | integer | 文档大小（字节） |
| sha1 | Form | 是 | string | 文档校验和（SHA1） |
| is_manual | Form | 是 | boolean | 是否手动保存 |
| attachment_size | Form | 否 | integer | 文档内包含的附件大小（字节） |
| content_type | Form | 否 | string | 文档的 MIME 类型 |

**返回值**:
```json
{
  "code": 0,
  "data": {
    "id": "238",
    "name": "文档名称.docx",
    "version": 180,
    "size": 18961,
    "create_time": 1670218748,
    "modify_time": 1670328304,
    "creator_id": "404",
    "modifier_id": "404"
  },
  "message": ""
}
```

**状态**: ✅ **已实现**（路径已修改为 `/upload`）

**实现位置**: `case_management/wps_callback_views.py::wps_save_file`

---

### ✅ 4. 重命名文件

**接口**: `PUT /v3/3rd/files/:file_id/name`

**说明**: 重命名文档

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_rename_file`

---

### ✅ 5. 获取水印配置

**接口**: `GET /v3/3rd/files/:file_id/watermark`

**说明**: 获取文档的水印配置

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_get_file_watermark`

---

## 👥 三、用户信息接口

### ✅ 批量获取用户信息

**接口**: `GET /v3/3rd/users?user_ids=id1&user_ids=id2&user_ids=id3`

**说明**: 获取指定用户的名称和头像，在协同场景下使用（查看历史改动，在线协同用户头像等）

**参数**:
| 字段 | 位置 | 必须 | 类型 | 说明 |
|------|------|------|------|------|
| user_ids | Query | 是 | string, repeat | 多个用户的 ID，可重复传递 |

**返回值**:
```json
{
  "code": 0,
  "data": [
    {
      "id": "1",
      "name": "user name1",
      "avatar_url": "https://example.com/avatar1.jpg"
    },
    {
      "id": "2",
      "name": "user name2",
      "avatar_url": "https://example.com/avatar2.jpg"
    },
    {
      "id": "3",
      "name": "user name3",
      "avatar_url": ""
    }
  ]
}
```

**返回值字段说明**:
| 字段 | 必须 | 类型 | 说明 |
|------|------|------|------|
| id | 是 | string | 用户 ID |
| name | 是 | string | 用户昵称 |
| avatar_url | 否 | string | 用户头像 URL，需要是https链接 |

**重要提示**:
- 该接口的实现需确保可以接收到多个 `user_ids` 参数
- 返回值根据传入的 `user_ids` 返回对应 `id` 的用户信息数组，不要写死
- 写死可能会导致某些功能异常

**常见功能异常场景**:
1. 用户打开文档，显示当前用户不存在，无法打开文档
2. 用户插入图片，显示当前用户不存在，无法成功插入图片
3. 评论用户信息无法显示
4. 回复评论无法正常显示回复人
5. 协作记录对应的用户信息不存在，无法回滚
6. 对应的用户版本信息异常等

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_get_users`

---

## 🔧 四、扩展能力接口（智能文档/多维表格）

### ✅ 1. 上传附件对象

**接口**: `PUT /v3/3rd/object/:key?name=xxx`

**说明**: 智能文档/多维表格 插入图片需要实现该接口

**参数**:
| 字段 | 位置 | 必须 | 类型 | 说明 |
|------|------|------|------|------|
| key | Path | 是 | string | 附件对象 ID |
| name | Query | 是 | string | 附件名 |
| - | Body | 是 | binary | 附件实体（二进制数据） |

**返回值**:
```json
{
  "code": 0,
  "data": {}
}
```

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_upload_object`

---

### ✅ 2. 获取附件对象下载地址

**接口**: `GET /v3/3rd/object/:key/url`

**说明**: 智能文档/多维表格 预览图片需要实现该接口

**参数**:
| 字段 | 位置 | 必须 | 类型 | 说明 |
|------|------|------|------|------|
| key | Path | 是 | string | 附件对象 ID |
| scale_max_fit_width | Query | 否 | int | 缩略图最大拟合宽度 |
| scale_max_fit_height | Query | 否 | int | 缩略图最大拟合高度 |
| scale_long_edge | Query | 否 | int | 缩略图限定长边长度 |

**返回值**:
```json
{
  "code": 0,
  "data": {
    "url": "https://foo.bar.com/object/9/180"
  }
}
```

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_get_object_url`

---

### ✅ 3. 拷贝附件对象

**接口**: `POST /v3/3rd/object/copy`

**说明**: 智能文档/多维表格 拷贝图片需要实现该接口

**参数**:
| 字段 | 位置 | 必须 | 类型 | 说明 |
|------|------|------|------|------|
| key_dict | Body | 是 | map<string, string> | 附件对象 ID 键值对, 如 `<源附件对象 ID:目标附件对象 ID>` |

**请求示例**:
```json
{
  "key_dict": {
    "7e0649753ad6474d995f1f525babcb94": "42265cf9fd2b4816a7df9a41ab4d0726"
  }
}
```

**返回值**:
```json
{
  "code": 0,
  "data": {}
}
```

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_copy_object`

---

## 📢 五、事件通知接口

### ✅ 事件通知

**接口**: `POST /v3/3rd/notify`

**说明**: 接收 WPS 的各种事件通知（文档打开、关闭、保存等）

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_notify`

---

## 🌐 六、直接访问路由

### ✅ WPS直接访问路由

**接口**: `GET /office/:office_type/:file_id`

**说明**: WPS SDK 直接访问文档的路由（推荐方式）

**参数**:
| 字段 | 位置 | 必须 | 类型 | 说明 |
|------|------|------|------|------|
| office_type | Path | 是 | string | 文档类型 (w/s/p/pdf) |
| file_id | Path | 是 | string | 文档 ID |

**响应头要求**:
- `Content-Disposition: inline; filename="xxx.docx"` - 必须是 inline
- `X-Frame-Options: SAMEORIGIN` - 不能是 DENY

**状态**: ✅ **已实现**

**实现位置**: `case_management/wps_callback_views.py::wps_office_view`

---

## 📊 接口实现状态总结

### ✅ 已实现的接口（共 15 个）

| 分类 | 接口数量 | 接口列表 |
|------|---------|---------|
| 文档预览 | 3 | 下载地址、文件信息、文件权限 |
| 文档编辑 | 6 | 三阶段保存(3个)、单阶段提交、重命名、水印 |
| 用户信息 | 1 | 批量获取用户信息 |
| 扩展能力 | 3 | 上传附件、获取下载地址、拷贝附件 |
| 事件通知 | 1 | 事件通知 |
| 直接访问 | 1 | WPS直接访问路由 |

### ✅ 实现完成度：100%

所有 WPS 官方要求的回调接口均已实现！

---

## 🔧 路由配置

所有接口路由配置在 `case_management/urls.py`:

```python
# 文档预览和编辑
path('v3/3rd/files/<int:file_id>/download', wps_get_file_download_url, name='wps_get_file_download_url'),
path('v3/3rd/files/<int:file_id>', wps_get_file_info, name='wps_get_file_info'),
path('v3/3rd/files/<int:file_id>/permission', wps_get_file_permission, name='wps_get_file_permission'),
path('v3/3rd/files/<int:file_id>/name', wps_rename_file, name='wps_rename_file'),
path('v3/3rd/files/<int:file_id>/watermark', wps_get_file_watermark, name='wps_get_file_watermark'),

# 单阶段提交接口（已弃用，但保持兼容）
path('v3/3rd/files/<int:file_id>/upload', wps_save_file, name='wps_save_file'),

# 三阶段保存接口（WPS官方推荐）
path('v3/3rd/files/<int:file_id>/upload/prepare', wps_upload_prepare, name='wps_upload_prepare'),
path('v3/3rd/files/<int:file_id>/upload/', wps_upload_get_url, name='wps_upload_get_url'),
path('v3/3rd/files/<int:file_id>/upload/commit', wps_upload_commit, name='wps_upload_commit'),

# 用户信息
path('v3/3rd/users', wps_get_users, name='wps_get_users'),

# 扩展能力接口（智能文档/多维表格）
path('v3/3rd/object/<str:key>', wps_upload_object, name='wps_upload_object'),
path('v3/3rd/object/<str:key>/url', wps_get_object_url, name='wps_get_object_url'),
path('v3/3rd/object/copy', wps_copy_object, name='wps_copy_object'),

# 事件通知
path('v3/3rd/notify', wps_notify, name='wps_notify'),

# WPS直接访问路由（推荐方式）
path('office/<str:office_type>/<str:file_id>/', wps_office_view, name='wps_office_view'),
```

---

## ⚠️ 错误码说明

根据 WPS 官方文档，标准错误码如下：

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| 0 | 200 | 成功 |
| 40001 | 403 | 签名验证失败 |
| 40002 | 400 | 参数错误 |
| 40003 | 403 | 权限不足 |
| 40004 | 404 | 文件不存在 |
| 40005 | 400 | 无效参数 |
| 50000 | 500 | 服务器内部错误 |

**注意**: 所有接口都应返回统一的错误码格式：
```json
{
  "code": 40001,
  "message": "错误描述"
}
```

---

## 📝 实现细节

### 1. 签名验证

所有回调接口都需要验证 WPS 签名（WPS-2 签名算法）：
- 使用 `verify_wps_signature()` 函数验证
- 签名验证失败返回 `code: 40001`

### 2. 用户认证

需要用户信息的接口从 Token 中获取：
- 使用 `get_user_from_token()` 函数获取
- Token 无效返回 `code: 40003`

### 3. 文件ID一致性

遵循「文件ID一致性」原则：
- 接口中文件「请求ID」和「返回ID」需保持一致
- 文件ID不一致可能影响某些功能的正常使用

### 4. 三阶段保存流程

1. **准备阶段**: 协商摘要算法
2. **获取上传地址**: 返回上传URL和参数
3. **完成上传**: 确认上传完成并保存文档

### 5. 扩展能力存储

附件对象存储在：
- 路径: `media/wps/attachments/{key}/`
- 使用 Django 的 `default_storage` 管理

---

## ✅ 检查清单

- [x] 实现文档预览接口（3个）
- [x] 实现三阶段保存接口（3个）
- [x] 实现单阶段提交接口（兼容）
- [x] 实现文件重命名接口
- [x] 实现水印配置接口
- [x] 实现用户信息接口（批量查询）
- [x] 实现扩展能力接口（3个）
- [x] 实现事件通知接口
- [x] 实现直接访问路由
- [x] 添加路由配置
- [x] 统一错误码格式
- [x] 实现签名验证
- [x] 实现用户认证

---

## 📚 参考文档

- [WPS 文档编辑回调接口](https://solution.wps.cn/docs/callback/save.html#%E5%87%86%E5%A4%87%E4%B8%8A%E4%BC%A0%E9%98%B6%E6%AE%B5)
- [WPS 用户信息接口](https://solution.wps.cn/docs/callback/user.html)
- [WPS 扩展能力接口](https://solution.wps.cn/docs/callback/extend.html)
- [WPS 错误码说明](https://solution.wps.cn/docs/callback/error-code.html)

---

**最后更新**: 2025-11-05

**状态**: ✅ 所有接口已实现完成
