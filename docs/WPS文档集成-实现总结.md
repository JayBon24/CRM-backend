# WPS文档集成功能 - 实现总结

## 一、已完成的工作

### 1.1 核心服务模块

✅ **WPS配置服务模块** (`case_management/utils/wps_service.py`)
- 生成WPS编辑配置
- Token生成和验证
- URL签名生成和验证

✅ **WPS文档处理模块** (`case_management/utils/wps_document_handler.py`)
- 文档文件提供（支持断点续传）
- 文档保存处理
- 版本管理（自动备份）

✅ **WPS回调处理模块** (`case_management/utils/wps_callback_handler.py`)
- 处理WPS回调事件
- 记录编辑日志
- 更新文档状态

### 1.2 API视图

✅ **WPS API视图** (`case_management/wps_views.py`)
- `wps_preview_config` - 获取预览配置
- `wps_edit_config` - 获取编辑配置
- `wps_get_file` - 获取文档文件
- `wps_save_document` - 保存文档
- `wps_download_document` - 下载文档
- `wps_callback` - 处理WPS回调

### 1.3 数据库模型

✅ **CaseDocument模型扩展**
- 添加WPS相关字段：
  - `wps_file_id` - WPS文件ID
  - `wps_edit_token` - WPS编辑令牌
  - `wps_edit_url` - WPS编辑URL
  - `last_edit_time` - 最后编辑时间
  - `last_editor_id` - 最后编辑人ID
  - `wps_enabled` - 是否启用WPS编辑

✅ **新增模型**
- `WPSEditRecord` - WPS编辑记录表
- `WPSCallbackLog` - WPS回调日志表

### 1.4 配置更新

✅ **settings.py** - 添加WPS配置项
✅ **conf/env.py** - 添加WPS环境变量配置
✅ **requirements.txt** - 添加PyJWT依赖
✅ **urls.py** - 添加WPS API路由

## 二、需要执行的后续步骤

### 2.1 安装依赖

```bash
pip install PyJWT==2.8.0
# 或
pip install -r requirements.txt
```

### 2.2 创建数据库迁移文件

```bash
# 激活虚拟环境后执行
python manage.py makemigrations case_management --name add_wps_fields
```

### 2.3 执行数据库迁移

```bash
python manage.py migrate case_management
```

### 2.4 配置WPS参数

在 `conf/env.py` 或环境变量中配置：

```python
# WPS配置
WPS_APP_ID = 'your_wps_app_id'  # 从WPS开放平台获取
WPS_APP_SECRET = 'your_wps_app_secret'  # 从WPS开放平台获取
WPS_SERVER_URL = 'https://wwo.wps.cn'  # 或私有化部署地址
WPS_CALLBACK_URL = ''  # 可选，会自动生成
WPS_ENABLED = True  # 是否启用WPS编辑
```

### 2.5 注册WPS开放平台

1. 访问 https://open.wps.cn/
2. 注册账号并创建应用
3. 获取 `AppID` 和 `AppSecret`
4. 配置回调地址（如果需要）

## 三、API接口说明

### 3.1 获取WPS编辑配置

**接口：** `POST /api/case/document/wps/edit-config/`

**请求参数：**
```json
{
  "documentId": 123,
  "mode": "edit"  // "view" 或 "edit"
}
```

**响应：**
```json
{
  "code": 2000,
  "msg": "配置生成成功",
  "data": {
    "documentId": 123,
    "wpsConfig": {
      "fileUrl": "https://example.com/api/case/document/wps/file/123?...",
      "fileId": "123",
      "appId": "your_wps_app_id",
      "token": "jwt_token_xxx",
      "mode": "edit",
      "userId": "456",
      "userName": "张三",
      "callbackUrl": "https://example.com/api/case/document/wps/callback/",
      "saveUrl": "https://example.com/api/case/document/wps/save/123/",
      "downloadUrl": "https://example.com/api/case/document/wps/download/123/"
    }
  }
}
```

### 3.2 获取文档文件

**接口：** `GET /api/case/document/wps/file/<document_id>/?expires=xxx&signature=xxx&user_id=xxx`

用于WPS SDK加载文档文件。

### 3.3 保存文档

**接口：** `POST /api/case/document/wps/save/<document_id>/`

**请求：** `multipart/form-data`
- `file`: 文档文件

**响应：**
```json
{
  "code": 2000,
  "msg": "保存成功",
  "data": {
    "documentId": 123,
    "filePath": "documents/original/2025/11/123_20251102103000.docx",
    "fileSize": 12345,
    "version": 2
  }
}
```

### 3.4 下载文档

**接口：** `GET /api/case/document/wps/download/<document_id>/`

### 3.5 WPS回调

**接口：** `POST /api/case/document/wps/callback/`

WPS服务器会调用此接口，通知文档编辑事件。

## 四、文件结构

```
case_management/
├── utils/
│   ├── wps_service.py          # WPS配置服务
│   ├── wps_document_handler.py # 文档处理
│   └── wps_callback_handler.py # 回调处理
├── wps_views.py                # WPS API视图
├── models.py                   # 模型（已扩展）
└── urls.py                     # 路由（已更新）

application/
└── settings.py                 # 配置（已更新）

conf/
└── env.py                      # 环境变量（已更新）

requirements.txt                # 依赖（已更新）
```

## 五、注意事项

### 5.1 权限控制

- 所有API接口需要用户认证（`@permission_classes([IsAuthenticated])`）
- 文档访问和编辑需要相应的权限检查
- URL签名验证防止未授权访问

### 5.2 版本管理

- 文档保存时自动创建版本备份
- 保留最近5个版本（可配置）
- 备份文件存储在 `media/documents/versions/<document_id>/`

### 5.3 错误处理

- 所有接口都有完善的错误处理
- 错误日志记录到日志文件
- 返回友好的错误信息

### 5.4 安全性

- URL签名验证
- Token验证（JWT）
- 文件大小限制（50MB）
- 文件格式验证（仅支持.docx）

## 六、测试建议

### 6.1 单元测试

- 测试Token生成和验证
- 测试URL签名生成和验证
- 测试文档保存和版本备份

### 6.2 接口测试

- 测试获取配置接口
- 测试文档文件提供接口
- 测试文档保存接口
- 测试权限控制

### 6.3 集成测试

- 测试完整的编辑流程
- 测试版本管理
- 测试回调处理

## 七、前端对接

前端需要调用 `wps_edit_config` 接口获取配置，然后使用WPS Office Web SDK初始化编辑器。

参考前端任务文档：`docs/WPS文档集成-前端任务文档.md`

## 八、后续优化

1. **性能优化**
   - 大文件异步处理
   - 缓存WPS配置
   - 优化数据库查询

2. **功能扩展**
   - 支持Excel和PPT文档
   - 多人协同编辑
   - 文档评论和批注
   - 文档历史版本对比

3. **监控和告警**
   - 编辑成功率监控
   - 错误率告警
   - 性能指标监控

## 九、常见问题

### Q1: 如何获取WPS AppID和AppSecret？

A: 访问 https://open.wps.cn/ 注册账号，创建应用后获取。

### Q2: 回调地址如何配置？

A: 回调地址需要是公网可访问的HTTPS地址。可以在环境变量中配置，也可以让系统自动生成。

### Q3: 文档保存失败怎么办？

A: 检查文件大小是否超过限制（50MB）、文件格式是否正确（.docx）、用户是否有编辑权限。

### Q4: Token过期怎么办？

A: Token默认有效期2小时。如果过期，前端需要重新获取配置。

## 十、技术支持

如有问题，请参考：
- 后端任务文档：`docs/WPS文档集成-后端任务文档.md`
- 前端任务文档：`docs/WPS文档集成-前端任务文档.md`
- WPS官方文档：https://open.wps.cn/docs/office

