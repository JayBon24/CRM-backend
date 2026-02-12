# WPS文档集成功能 - 后端任务文档

## 一、功能概述

为案件管理系统集成WPS Office在线文档编辑功能，支持用户在线查看和编辑Word文档（.docx），无需下载和安装本地软件。通过WPS Office Web SDK实现文档在线预览、编辑、保存等功能。

## 二、技术选型

### 2.1 WPS Office Web SDK方案

**核心方案：WPS Office Web SDK**

**技术特点：**
- 支持在线查看和编辑Word、Excel、PPT文档
- 无需安装本地软件，浏览器直接使用
- 支持多人协同编辑（高级功能）
- 提供丰富的API接口
- 支持私有化部署（企业版）

**官方文档：**
- WPS Office Web SDK文档：https://open.wps.cn/docs/office
- 开发指南：https://open.wps.cn/docs/office/quickstart

### 2.2 集成方式

**方案一：公有云接入（推荐用于快速开发）**
- 优点：快速集成，无需部署服务器
- 缺点：需要网络连接，数据经过WPS服务器
- 适用：开发测试、小型项目

**方案二：私有化部署（推荐用于生产环境）**
- 优点：数据完全本地化，安全性高
- 缺点：需要部署WPS服务器，配置复杂
- 适用：生产环境、大型项目

### 2.3 技术架构

```
前端（Vue3）
    ↓
WPS Office Web SDK（浏览器端）
    ↓
后端API（Django）
    ↓
文档存储（本地文件系统/对象存储）
```

## 三、后端核心功能

### 3.1 文档在线编辑接口

**接口定义：**
```
POST /api/case/document/wps/preview-config/
GET /api/case/document/wps/edit-config/
```

**功能描述：**
生成WPS Office Web SDK所需的配置信息，包括文档URL、权限配置、回调地址等。

**请求参数：**
```json
{
  "documentId": 123,
  "mode": "edit",  // "view" 或 "edit"
  "userId": 456,
  "userName": "张三"
}
```

**响应数据：**
```json
{
  "code": 2000,
  "msg": "配置生成成功",
  "data": {
    "documentId": 123,
    "wpsConfig": {
      "fileUrl": "https://example.com/api/case/document/wps/file/123",
      "fileId": "123",
      "appId": "your_wps_app_id",
      "token": "wps_token_xxx",
      "mode": "edit",  // "view" 或 "edit"
      "userId": "456",
      "userName": "张三",
      "callbackUrl": "https://example.com/api/case/document/wps/callback/",
      "downloadUrl": "https://example.com/api/case/document/wps/download/123",
      "saveUrl": "https://example.com/api/case/document/wps/save/123"
    }
  }
}
```

**实现要点：**

1. **文档URL生成**
   - 生成文档的临时访问URL（带签名，防止未授权访问）
   - URL有效期：2小时（可配置）
   - 支持HTTPS和HTTP协议

2. **权限配置**
   - 根据用户角色设置编辑权限
   - 支持只读模式（view）和编辑模式（edit）
   - 记录用户操作日志

3. **Token生成**
   - 生成WPS所需的访问令牌
   - Token包含用户信息、文档ID、过期时间
   - 使用JWT或自定义签名算法

### 3.2 文档文件提供接口

**接口定义：**
```
GET /api/case/document/wps/file/<document_id>/
```

**功能描述：**
提供文档文件给WPS Web SDK，支持文件下载和流式传输。

**实现要点：**

1. **文件读取**
   - 从数据库查询文档信息
   - 检查用户权限
   - 读取物理文件

2. **文件传输**
   - 支持Range请求（断点续传）
   - 设置正确的Content-Type
   - 设置Content-Disposition头
   - 支持大文件流式传输

3. **安全控制**
   - URL签名验证
   - Token验证
   - 访问时间限制
   - 记录访问日志

**响应头设置：**
```python
response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
response['Content-Disposition'] = f'inline; filename="{filename}"'
response['Access-Control-Allow-Origin'] = '*'
response['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
response['Access-Control-Allow-Headers'] = 'Range'
```

### 3.3 文档保存接口

**接口定义：**
```
POST /api/case/document/wps/save/<document_id>/
```

**功能描述：**
接收WPS编辑后的文档内容，保存到服务器。

**请求参数：**
```
Content-Type: multipart/form-data

file: [文档文件]
documentId: 123
```

**响应数据：**
```json
{
  "code": 2000,
  "msg": "保存成功",
  "data": {
    "documentId": 123,
    "filePath": "documents/original/2025/11/123_20251102103000.docx",
    "fileSize": 12345,
    "updateTime": "2025-11-02T10:30:00",
    "version": 2
  }
}
```

**实现要点：**

1. **文件接收**
   - 接收上传的文档文件
   - 验证文件格式（.docx）
   - 验证文件大小（限制50MB）
   - 检查磁盘空间

2. **文件保存**
   - 备份原文档（版本管理）
   - 保存新文档
   - 更新数据库记录（文件路径、大小、修改时间）
   - 更新版本号

3. **版本管理**
   - 自动创建版本备份
   - 保留最近N个版本（可配置）
   - 记录版本变更信息

4. **事务处理**
   - 确保数据库和文件系统的一致性
   - 保存失败时回滚
   - 清理临时文件

### 3.4 WPS回调接口

**接口定义：**
```
POST /api/case/document/wps/callback/
```

**功能描述：**
接收WPS服务器的回调通知，处理文档编辑事件（如保存、关闭等）。

**回调数据格式：**
```json
{
  "event": "file_save",  // "file_save", "file_close", "file_error"
  "fileId": "123",
  "userId": "456",
  "timestamp": "2025-11-02T10:30:00",
  "data": {
    "fileUrl": "https://wps-server.com/files/xxx.docx",
    "error": null
  }
}
```

**实现要点：**

1. **事件处理**
   - 文件保存事件：触发自动备份
   - 文件关闭事件：清理临时文件
   - 文件错误事件：记录错误日志

2. **回调验证**
   - 验证回调来源（签名验证）
   - 防止伪造回调
   - 记录所有回调日志

### 3.5 文档下载接口

**接口定义：**
```
GET /api/case/document/wps/download/<document_id>/
```

**功能描述：**
提供文档下载功能，支持WPS编辑后的文档下载。

**实现要点：**

1. **权限检查**
   - 检查用户下载权限
   - 记录下载日志

2. **文件传输**
   - 支持断点续传
   - 设置下载文件名
   - 设置正确的Content-Type

## 四、数据库设计

### 4.1 文档表扩展（现有表添加字段）

**建议添加字段：**
```sql
ALTER TABLE case_document ADD COLUMN IF NOT EXISTS wps_file_id VARCHAR(100) COMMENT 'WPS文件ID';
ALTER TABLE case_document ADD COLUMN IF NOT EXISTS wps_edit_token VARCHAR(500) COMMENT 'WPS编辑令牌';
ALTER TABLE case_document ADD COLUMN IF NOT EXISTS wps_edit_url VARCHAR(500) COMMENT 'WPS编辑URL';
ALTER TABLE case_document ADD COLUMN IF NOT EXISTS last_edit_time DATETIME COMMENT '最后编辑时间';
ALTER TABLE case_document ADD COLUMN IF NOT EXISTS last_editor_id BIGINT COMMENT '最后编辑人ID';
ALTER TABLE case_document ADD COLUMN IF NOT EXISTS wps_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用WPS编辑';
```

### 4.2 WPS编辑记录表（新增）

**表结构：**
```sql
CREATE TABLE IF NOT EXISTS wps_edit_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    document_id BIGINT NOT NULL COMMENT '文档ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    user_name VARCHAR(100) COMMENT '用户名',
    file_id VARCHAR(100) COMMENT 'WPS文件ID',
    edit_token VARCHAR(500) COMMENT '编辑令牌',
    edit_mode VARCHAR(20) DEFAULT 'edit' COMMENT '编辑模式：view/edit',
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '开始编辑时间',
    end_time DATETIME COMMENT '结束编辑时间',
    save_count INT DEFAULT 0 COMMENT '保存次数',
    status VARCHAR(20) DEFAULT 'editing' COMMENT '状态：editing/completed/cancelled',
    ip_address VARCHAR(50) COMMENT 'IP地址',
    user_agent VARCHAR(500) COMMENT '用户代理',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES case_document(id) ON DELETE CASCADE,
    INDEX idx_document_id (document_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='WPS编辑记录表';
```

### 4.3 WPS回调日志表（新增）

**表结构：**
```sql
CREATE TABLE IF NOT EXISTS wps_callback_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    document_id BIGINT COMMENT '文档ID',
    file_id VARCHAR(100) COMMENT 'WPS文件ID',
    event_type VARCHAR(50) NOT NULL COMMENT '事件类型',
    event_data JSON COMMENT '事件数据',
    callback_data TEXT COMMENT '回调原始数据',
    status VARCHAR(20) DEFAULT 'success' COMMENT '处理状态：success/failed',
    error_message TEXT COMMENT '错误信息',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_document_id (document_id),
    INDEX idx_event_type (event_type),
    INDEX idx_created_time (created_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='WPS回调日志表';
```

## 五、核心代码模块

### 5.1 WPS配置服务模块

**模块：wps_service.py**

**功能：**
- 生成WPS配置信息
- Token生成和验证
- URL签名生成

**主要方法：**
```python
class WPSService:
    def generate_edit_config(self, document_id: int, user_id: int, 
                            mode: str = 'edit') -> dict:
        """
        生成WPS编辑配置
        返回：{
            'fileUrl': str,
            'fileId': str,
            'appId': str,
            'token': str,
            'mode': str,
            'userId': str,
            'userName': str,
            'callbackUrl': str,
            'saveUrl': str,
            'downloadUrl': str
        }
        """
        pass
    
    def generate_token(self, document_id: int, user_id: int, 
                      expires_in: int = 7200) -> str:
        """
        生成WPS访问令牌
        expires_in: 过期时间（秒），默认2小时
        """
        pass
    
    def verify_token(self, token: str) -> dict:
        """
        验证WPS令牌
        返回：{
            'valid': bool,
            'document_id': int,
            'user_id': int,
            'expires_at': datetime
        }
        """
        pass
    
    def generate_signed_url(self, document_id: int, expires_in: int = 7200) -> str:
        """
        生成带签名的文档URL
        expires_in: 过期时间（秒），默认2小时
        """
        pass
```

### 5.2 WPS文档处理模块

**模块：wps_document_handler.py**

**功能：**
- 文档文件提供
- 文档保存处理
- 版本管理

**主要方法：**
```python
class WPSDocumentHandler:
    def get_document_file(self, document_id: int, user_id: int) -> HttpResponse:
        """
        获取文档文件（用于WPS加载）
        返回：HttpResponse with file content
        """
        pass
    
    def save_document(self, document_id: int, file_content: bytes, 
                     user_id: int) -> dict:
        """
        保存WPS编辑后的文档
        返回：{
            'documentId': int,
            'filePath': str,
            'fileSize': int,
            'version': int
        }
        """
        pass
    
    def create_version_backup(self, document_id: int) -> str:
        """
        创建版本备份
        返回：备份文件路径
        """
        pass
    
    def check_document_permission(self, document_id: int, 
                                 user_id: int, permission: str = 'read') -> bool:
        """
        检查文档权限
        permission: 'read', 'write', 'delete'
        """
        pass
```

### 5.3 WPS回调处理模块

**模块：wps_callback_handler.py**

**功能：**
- 处理WPS回调事件
- 记录编辑日志
- 更新文档状态

**主要方法：**
```python
class WPSCallbackHandler:
    def handle_callback(self, callback_data: dict) -> dict:
        """
        处理WPS回调
        返回：{
            'success': bool,
            'message': str
        }
        """
        pass
    
    def handle_file_save(self, file_id: str, event_data: dict) -> None:
        """处理文件保存事件"""
        pass
    
    def handle_file_close(self, file_id: str, event_data: dict) -> None:
        """处理文件关闭事件"""
        pass
    
    def handle_file_error(self, file_id: str, event_data: dict) -> None:
        """处理文件错误事件"""
        pass
    
    def verify_callback_signature(self, callback_data: dict, 
                                 signature: str) -> bool:
        """验证回调签名"""
        pass
```

## 六、API视图实现

### 6.1 视图模块结构

**模块：views/wps_views.py**

**路由定义：**
```python
# WPS配置接口
path('document/wps/preview-config/', wps_preview_config, name='wps_preview_config'),
path('document/wps/edit-config/', wps_edit_config, name='wps_edit_config'),

# 文档文件接口
path('document/wps/file/<int:document_id>/', wps_get_file, name='wps_get_file'),

# 文档保存接口
path('document/wps/save/<int:document_id>/', wps_save_document, name='wps_save_document'),

# WPS回调接口
path('document/wps/callback/', wps_callback, name='wps_callback'),

# 文档下载接口
path('document/wps/download/<int:document_id>/', wps_download_document, name='wps_download_document'),
```

### 6.2 权限和认证

**要求：**
- 所有接口需要用户认证
- 检查用户对文档的访问权限
- 记录操作日志

**权限检查：**
```python
def check_wps_permission(user_id: int, document_id: int, 
                        mode: str = 'view') -> bool:
    """
    检查用户WPS编辑权限
    mode: 'view' 或 'edit'
    """
    # 1. 检查用户是否登录
    # 2. 检查用户对文档的访问权限
    # 3. 检查文档是否启用WPS编辑
    # 4. 检查编辑模式权限（edit需要写权限）
    pass
```

## 七、配置管理

### 7.1 WPS配置项

**settings.py配置：**
```python
# WPS Office Web SDK配置
WPS_CONFIG = {
    # 应用ID（从WPS开放平台获取）
    'APP_ID': env('WPS_APP_ID', default=''),
    
    # 应用密钥（从WPS开放平台获取）
    'APP_SECRET': env('WPS_APP_SECRET', default=''),
    
    # WPS服务器地址（私有化部署时需要）
    'WPS_SERVER_URL': env('WPS_SERVER_URL', default='https://wwo.wps.cn'),
    
    # 回调地址
    'CALLBACK_URL': env('WPS_CALLBACK_URL', default='https://your-domain.com/api/case/document/wps/callback/'),
    
    # 文档URL有效期（秒）
    'FILE_URL_EXPIRE': 7200,  # 2小时
    
    # Token有效期（秒）
    'TOKEN_EXPIRE': 7200,  # 2小时
    
    # 是否启用WPS编辑
    'WPS_ENABLED': env('WPS_ENABLED', default=True),
    
    # 文件大小限制（字节）
    'MAX_FILE_SIZE': 50 * 1024 * 1024,  # 50MB
    
    # 版本备份保留数量
    'VERSION_BACKUP_COUNT': 5,
    
    # 是否启用版本管理
    'VERSION_MANAGEMENT_ENABLED': True,
}
```

### 7.2 环境变量配置

**conf/env.py配置：**
```python
# WPS配置
WPS_APP_ID = os.getenv('WPS_APP_ID', '')
WPS_APP_SECRET = os.getenv('WPS_APP_SECRET', '')
WPS_SERVER_URL = os.getenv('WPS_SERVER_URL', 'https://wwo.wps.cn')
WPS_CALLBACK_URL = os.getenv('WPS_CALLBACK_URL', '')
WPS_ENABLED = os.getenv('WPS_ENABLED', 'True').lower() == 'true'
```

## 八、安全性

### 8.1 URL签名

**实现要点：**
- 文档URL包含签名参数
- 签名基于文档ID、时间戳、密钥生成
- 验证URL签名防止未授权访问

**签名算法：**
```python
def generate_url_signature(document_id: int, timestamp: int, 
                          secret: str) -> str:
    """
    生成URL签名
    """
    import hashlib
    import hmac
    
    message = f"{document_id}_{timestamp}"
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_url_signature(document_id: int, timestamp: int, 
                        signature: str, secret: str) -> bool:
    """
    验证URL签名
    """
    expected_signature = generate_url_signature(document_id, timestamp, secret)
    return hmac.compare_digest(signature, expected_signature)
```

### 8.2 Token验证

**实现要点：**
- Token包含用户ID、文档ID、过期时间
- 使用JWT或自定义加密算法
- 每次请求验证Token有效性

### 8.3 回调验证

**实现要点：**
- 验证回调来源（IP白名单）
- 验证回调签名
- 防止伪造回调请求

## 九、错误处理

### 9.1 错误分类

**客户端错误（4xx）：**
- 400: 请求参数错误
- 401: 未授权（Token无效）
- 403: 权限不足
- 404: 文档不存在
- 413: 文件过大

**服务器错误（5xx）：**
- 500: 服务器内部错误
- 503: 服务不可用（WPS服务异常）

### 9.2 错误响应格式

```json
{
  "code": 4000,
  "msg": "错误描述",
  "data": null,
  "error": {
    "type": "ValidationError",
    "detail": "详细错误信息"
  }
}
```

## 十、日志记录

### 10.1 日志内容

**记录内容：**
```python
# WPS编辑开始
logger.info(f"WPS编辑开始: document_id={doc_id}, user_id={user_id}, mode={mode}")

# WPS文档保存
logger.info(f"WPS文档保存: document_id={doc_id}, user_id={user_id}, size={size}")

# WPS回调处理
logger.info(f"WPS回调处理: event={event}, file_id={file_id}")

# WPS错误
logger.error(f"WPS错误: document_id={doc_id}, error={error}", exc_info=True)
```

### 10.2 监控指标

**关键指标：**
- WPS编辑成功率
- 平均编辑时长
- 文档保存频率
- 回调处理成功率
- 错误率统计

## 十一、依赖安装

### 11.1 Python依赖

**requirements.txt：**
```txt
# WPS相关（如果需要调用WPS API）
requests==2.31.0

# JWT支持（Token生成）
PyJWT==2.8.0

# 其他工具
python-dateutil==2.8.2
```

### 11.2 系统依赖

**无特殊要求，WPS Office Web SDK运行在浏览器端，后端只需要提供API接口。**

## 十二、开发步骤建议

### Phase 1：环境准备（1天）
1. 注册WPS开放平台账号
2. 创建应用，获取AppID和AppSecret
3. 配置回调地址
4. 安装依赖库

### Phase 2：核心功能开发（3-4天）
1. 实现WPSService类（配置生成、Token生成）
2. 实现WPSDocumentHandler类（文件提供、保存）
3. 实现WPS回调处理
4. 单元测试

### Phase 3：API接口开发（2-3天）
1. 创建视图和路由
2. 实现所有API接口
3. 权限和认证
4. 错误处理
5. API测试

### Phase 4：数据库和版本管理（1-2天）
1. 数据库表设计和创建
2. 版本管理实现
3. 编辑记录追踪
4. 测试

### Phase 5：安全和优化（2天）
1. URL签名和Token验证
2. 回调验证
3. 日志和监控
4. 性能优化
5. 安全测试

### Phase 6：测试和文档（1-2天）
1. 集成测试
2. 压力测试
3. 文档编写
4. 部署准备

## 十三、测试用例

### 13.1 功能测试

**WPS配置接口：**
- [ ] 生成预览配置（view模式）
- [ ] 生成编辑配置（edit模式）
- [ ] 权限不足时返回错误
- [ ] Token生成和验证

**文档文件接口：**
- [ ] 正常文档下载
- [ ] 大文件下载（50MB+）
- [ ] 断点续传
- [ ] URL签名验证
- [ ] 过期URL拒绝访问

**文档保存接口：**
- [ ] 正常保存文档
- [ ] 版本备份创建
- [ ] 大文件保存（50MB+）
- [ ] 保存失败回滚
- [ ] 权限检查

**WPS回调接口：**
- [ ] 文件保存回调
- [ ] 文件关闭回调
- [ ] 文件错误回调
- [ ] 回调签名验证
- [ ] 异常回调处理

### 13.2 异常情况测试

- [ ] 文档不存在
- [ ] 权限不足
- [ ] Token过期
- [ ] URL签名错误
- [ ] 文件过大
- [ ] 磁盘空间不足
- [ ] 网络异常
- [ ] 并发编辑冲突

### 13.3 性能测试

- [ ] 并发编辑测试（10用户）
- [ ] 大文件处理（50MB）
- [ ] 回调处理性能
- [ ] 数据库查询优化

## 十四、部署注意事项

### 14.1 环境配置

**必需配置：**
- WPS_APP_ID和WPS_APP_SECRET
- WPS_CALLBACK_URL（必须是公网可访问的HTTPS地址）
- 文档存储路径配置
- 日志目录配置

### 14.2 网络要求

**必需条件：**
- 服务器需要能访问WPS服务器（公有云方案）
- 回调URL需要公网可访问（HTTPS）
- 防火墙开放相关端口

### 14.3 私有化部署（可选）

**如果使用私有化部署：**
- 需要部署WPS Office服务器
- 配置服务器地址和端口
- 配置SSL证书
- 配置负载均衡（如需要）

## 十五、技术文档参考

- WPS Office Web SDK文档：https://open.wps.cn/docs/office
- WPS开放平台：https://open.wps.cn/
- WPS Office Web SDK快速开始：https://open.wps.cn/docs/office/quickstart
- WPS API参考：https://open.wps.cn/docs/office/api

## 十六、后续扩展

- 支持Excel和PPT文档编辑
- 多人协同编辑功能
- 文档评论和批注
- 文档历史版本对比
- 文档权限精细化管理
- 移动端适配

