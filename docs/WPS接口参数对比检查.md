# WPS 接口参数对比检查

对照 WPS 官方文档，检查实现的接口参数和返回值是否完全一致。

## 📋 一、三阶段保存接口

### 1. 准备上传阶段 `GET /v3/3rd/files/:file_id/upload/prepare`

#### ✅ 请求参数对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| file_id (Path) | ✅ file_id (Path) | ✅ 一致 |

#### ✅ 返回值对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| code: 0 | ✅ code: 0 | ✅ 一致 |
| data.digest_types: string[] | ✅ data.digest_types: ["sha1", "sha256", "md5"] | ✅ 一致 |
| message: "" | ✅ message: "" | ✅ 一致 |

**结论**: ✅ **完全一致**

---

### 2. 获取上传地址 `POST /v3/3rd/files/:file_id/upload/`

#### ⚠️ 请求参数对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| file_id (Path) | ✅ file_id (Path) | ✅ 一致 |
| request.file_id (Body) | ✅ request.file_id | ✅ 一致 |
| request.name (Body) | ✅ request.name | ✅ 一致 |
| request.size (Body) | ✅ request.size | ✅ 一致 |
| request.digest (Body) | ✅ request.digest | ✅ 一致 |
| request.is_manual (Body) | ✅ request.is_manual | ✅ 一致 |
| send_back_params (Body) | ✅ send_back_params | ✅ 一致 |

#### ⚠️ 返回值对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| code: 0 | ✅ code: 0 | ✅ 一致 |
| data.upload_url | ✅ data.upload_url | ✅ 一致 |
| data.upload_method | ⚠️ "POST" | ⚠️ 应该是 "PUT" |
| data.headers | ✅ data.headers | ✅ 一致 |
| data.send_back_params | ✅ data.send_back_params | ✅ 一致 |

**问题**: upload_method 应该是 "PUT" 而不是 "POST"

**结论**: ⚠️ **需要修改 upload_method**

---

### 3. 完成上传阶段 `POST /v3/3rd/files/:file_id/upload/commit`

#### ⚠️ 请求参数对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| file_id (Path) | ✅ file_id (Path) | ✅ 一致 |
| request.file_id (Body) | ✅ request.file_id | ✅ 一致 |
| request.name (Body) | ✅ request.name | ✅ 一致 |
| request.size (Body) | ✅ request.size | ✅ 一致 |
| request.digest (Body) | ✅ request.digest | ✅ 一致 |
| request.is_manual (Body) | ✅ request.is_manual | ✅ 一致 |
| response.status_code (Body) | ✅ response.status_code | ✅ 一致 |
| response.headers (Body) | ✅ response.headers | ✅ 一致 |
| response.body (Body) | ✅ response.body | ✅ 一致 |
| send_back_params (Body) | ✅ send_back_params | ✅ 一致 |

#### ✅ 返回值对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| code: 0 | ✅ code: 0 | ✅ 一致 |
| data.id | ✅ data.id | ✅ 一致 |
| data.name | ✅ data.name | ✅ 一致 |
| data.version | ✅ data.version | ✅ 一致 |
| data.size | ✅ data.size | ✅ 一致 |
| data.create_time | ✅ data.create_time | ✅ 一致 |
| data.modify_time | ✅ data.modify_time | ✅ 一致 |
| data.creator_id | ✅ data.creator_id | ✅ 一致 |
| data.modifier_id | ✅ data.modifier_id | ✅ 一致 |

**结论**: ✅ **完全一致**

---

## 👥 二、用户信息接口

### `GET /v3/3rd/users?user_ids=id1&user_ids=id2`

#### ✅ 请求参数对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| user_ids (Query, repeat) | ✅ user_ids (Query, getlist) | ✅ 一致 |

#### ⚠️ 返回值对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| code: 0 | ✅ code: 0 | ✅ 一致 |
| data: array | ✅ data: array | ✅ 一致 |
| data[].id (必须) | ✅ data[].id | ✅ 一致 |
| data[].name (必须) | ✅ data[].name | ✅ 一致 |
| data[].avatar_url (可选) | ⚠️ 包含logined字段 | ❌ 不应包含logined |

**问题**: 返回的用户对象包含了 `logined` 字段，但官方文档没有这个字段

**结论**: ⚠️ **需要移除 logined 字段**

---

## 🔧 三、扩展能力接口

### 1. 上传附件对象 `PUT /v3/3rd/object/:key?name=xxx`

#### ✅ 请求参数对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| key (Path) | ✅ key (Path) | ✅ 一致 |
| name (Query) | ✅ name (Query) | ✅ 一致 |
| 文件内容 (Body, binary) | ✅ request.body | ✅ 一致 |

#### ✅ 返回值对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| code: 0 | ✅ code: 0 | ✅ 一致 |
| data: {} | ✅ data: {} | ✅ 一致 |

**结论**: ✅ **完全一致**

---

### 2. 获取附件下载地址 `GET /v3/3rd/object/:key/url`

#### ✅ 请求参数对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| key (Path) | ✅ key (Path) | ✅ 一致 |
| scale_max_fit_width (Query, 可选) | ✅ scale_max_fit_width | ✅ 一致 |
| scale_max_fit_height (Query, 可选) | ✅ scale_max_fit_height | ✅ 一致 |
| scale_long_edge (Query, 可选) | ✅ scale_long_edge | ✅ 一致 |

#### ✅ 返回值对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| code: 0 | ✅ code: 0 | ✅ 一致 |
| data.url | ✅ data.url | ✅ 一致 |

**结论**: ✅ **完全一致**

---

### 3. 拷贝附件对象 `POST /v3/3rd/object/copy`

#### ✅ 请求参数对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| key_dict (Body, map) | ✅ key_dict (Body) | ✅ 一致 |

#### ✅ 返回值对比

| 官方文档 | 当前实现 | 状态 |
|---------|---------|------|
| code: 0 | ✅ code: 0 | ✅ 一致 |
| data: {} | ✅ data: {} | ✅ 一致 |

**结论**: ✅ **完全一致**

---

## 📝 需要修复的问题

1. **upload_method 应该是 "PUT"** - 已修复 ✅
2. **用户信息接口不应包含 logined 字段** - 已修复 ✅
3. **需要添加临时文件上传接口** - 用于接收三阶段保存中的文件上传

---

**最后更新**: 2025-11-05

