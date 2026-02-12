# 文档HTML富文本编辑功能 - 后端任务文档

## 一、功能概述

为文档管理系统提供DOCX与HTML格式互转功能，支持前端富文本编辑器的使用。实现高质量的格式保留，确保文档在DOCX和HTML之间转换时内容和样式的完整性。

## 二、技术选型

### 2.1 推荐方案：python-docx + mammoth + htmldocx

**核心库：**
1. **mammoth**
   - 功能：DOCX → HTML
   - 优点：格式保留效果好，生成干净的HTML
   - 文档：https://github.com/mwilliamson/python-mammoth

2. **python-docx**
   - 功能：创建和修改DOCX，辅助处理
   - 优点：功能强大，文档完善
   - 文档：https://python-docx.readthedocs.io/

3. **htmldocx**
   - 功能：HTML → DOCX
   - 优点：简单易用，支持常见HTML标签
   - 文档：https://github.com/pqzx/html2docx

**方案优势：**
- ✅ 完全开源免费
- ✅ 社区活跃，文档完善
- ✅ 格式保留效果较好
- ✅ 无需外部服务或商业授权

**方案限制：**
- ⚠️ 复杂格式可能有损失（页眉页脚、复杂表格等）
- ⚠️ 不支持宏和嵌入对象
- ⚠️ 某些Word特有功能无法完美转换

### 2.2 备选方案（参考）

**方案二：LibreOffice + unoconv**
- 适用于需要更高保真度的场景
- 需要安装LibreOffice服务
- 资源占用较大

**方案三：Aspose.Words（商业）**
- 格式保留最好
- 需要商业授权
- 成本较高

## 三、核心功能点

### 3.1 DOCX转HTML接口

**接口定义：**
```
POST /api/document/convert/docx-to-html
```

**功能描述：**
将DOCX文档转换为HTML格式，供前端富文本编辑器使用。

**请求参数：**
```json
{
  "documentId": "文档ID",
  // 或
  "documentPath": "文档路径（相对或绝对）"
}
```

**响应数据：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "html": "<html>...</html>",
    "title": "文档标题",
    "images": [
      {
        "id": "image1",
        "url": "/media/images/xxx.jpg"
      }
    ]
  }
}
```

**实现要点：**

1. **文档定位**
   - 通过documentId从数据库查询文档路径
   - 或直接使用documentPath
   - 校验文档是否存在
   - 校验用户权限

2. **转换处理**
   - 使用mammoth库读取DOCX
   - 提取HTML内容
   - 提取图片资源
   - 图片保存到媒体文件目录
   - 替换HTML中的图片路径为可访问URL

3. **格式处理**
   - 保留文本格式（加粗、斜体、下划线等）
   - 保留段落格式（对齐、缩进等）
   - 保留列表格式（有序、无序）
   - 保留表格结构和样式
   - 清理不必要的Word样式标签

4. **错误处理**
   - 文件不存在：返回404
   - 文件格式错误：返回400
   - 转换失败：返回500，记录错误日志
   - 权限不足：返回403

### 3.2 HTML转DOCX接口

**接口定义：**
```
POST /api/document/convert/html-to-docx
```

**功能描述：**
将前端编辑器生成的HTML内容转换为DOCX文档并保存。

**请求参数：**
```json
{
  "documentId": "文档ID",
  "html": "<html>...</html>",
  "title": "文档标题（可选）",
  "savePath": "保存路径（可选）"
}
```

**响应数据：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "documentId": "文档ID",
    "documentPath": "文档路径",
    "fileSize": 12345,
    "updateTime": "2025-11-02T10:30:00"
  }
}
```

**实现要点：**

1. **内容校验**
   - HTML内容不为空
   - HTML格式基本校验
   - XSS安全检查
   - 内容长度限制

2. **转换处理**
   - 使用htmldocx库创建Document对象
   - 解析HTML标签并转换
   - 处理图片（下载网络图片或读取本地图片）
   - 设置文档属性（标题、作者等）
   - 应用Word样式

3. **文件保存**
   - 生成临时文件
   - 覆盖原文档或保存为新文档
   - 更新数据库记录（文件路径、大小、修改时间等）
   - 清理临时文件

4. **事务处理**
   - 确保数据库和文件系统的一致性
   - 保存失败时回滚
   - 保留文档历史版本（可选）

5. **错误处理**
   - HTML解析失败：返回400
   - 文件保存失败：返回500
   - 磁盘空间不足：返回507
   - 权限不足：返回403

### 3.3 图片上传接口

**接口定义：**
```
POST /api/document/upload-image
```

**功能描述：**
处理编辑器中上传的图片，保存到服务器并返回访问URL。

**请求参数：**
```
Content-Type: multipart/form-data

file: [图片文件]
documentId: "文档ID"（可选，用于关联）
```

**响应数据：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "url": "https://example.com/media/images/xxx.jpg",
    "alt": "图片描述",
    "href": "图片链接"
  }
}
```

**实现要点：**

1. **文件校验**
   - 检查文件类型（jpg, png, gif, webp等）
   - 检查文件大小（建议限制5MB以内）
   - 检查图片尺寸（可选）
   - 病毒扫描（生产环境）

2. **文件处理**
   - 生成唯一文件名（UUID + 扩展名）
   - 图片压缩优化（可选）
   - 保存到媒体文件目录
   - 生成缩略图（可选）

3. **记录保存**
   - 保存图片记录到数据库
   - 关联文档ID（如果提供）
   - 记录上传时间、用户等信息

4. **返回URL**
   - 生成可访问的图片URL
   - 支持CDN加速（生产环境）

## 四、数据库设计

### 4.1 文档表（现有表扩展）

**建议添加字段：**
```sql
ALTER TABLE documents ADD COLUMN IF NOT EXISTS html_cache TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS html_cache_time TIMESTAMP;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS edit_mode VARCHAR(20) DEFAULT 'preview';
```

**字段说明：**
- `html_cache`: 缓存的HTML内容（可选，用于提高加载速度）
- `html_cache_time`: 缓存时间
- `edit_mode`: 编辑模式（preview/edit）

### 4.2 文档图片表（新增）

**表结构：**
```sql
CREATE TABLE IF NOT EXISTS document_images (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    document_id BIGINT,
    image_url VARCHAR(500),
    image_path VARCHAR(500),
    file_size INT,
    width INT,
    height INT,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by BIGINT,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    INDEX idx_document_id (document_id)
);
```

### 4.3 文档版本表（可选）

**表结构：**
```sql
CREATE TABLE IF NOT EXISTS document_versions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    document_id BIGINT,
    version_number INT,
    file_path VARCHAR(500),
    html_content TEXT,
    file_size INT,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    remark VARCHAR(200),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    INDEX idx_document_id (document_id)
);
```

## 五、文件存储结构

### 5.1 目录结构

```
media/
├── documents/
│   ├── original/          # 原始DOCX文件
│   │   └── {year}/{month}/
│   │       └── xxx.docx
│   ├── versions/          # 历史版本
│   │   └── {document_id}/
│   │       ├── v1.docx
│   │       ├── v2.docx
│   │       └── ...
│   └── temp/              # 临时文件
│       └── xxx_temp.docx
└── images/
    └── documents/         # 文档图片
        └── {year}/{month}/
            └── xxx.jpg
```

### 5.2 文件命名规则

**DOCX文件：**
- 格式：`{document_id}_{timestamp}.docx`
- 示例：`12345_20251102103000.docx`

**图片文件：**
- 格式：`{uuid}.{ext}`
- 示例：`a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg`

## 六、核心代码模块

### 6.1 转换服务模块

**模块：document_converter.py**

**功能：**
- DOCX转HTML核心逻辑
- HTML转DOCX核心逻辑
- 格式处理和优化

**主要方法：**
```python
class DocumentConverter:
    def docx_to_html(self, docx_path: str) -> dict:
        """
        DOCX转HTML
        返回：{
            'html': str,
            'images': list,
            'title': str
        }
        """
        pass
    
    def html_to_docx(self, html_content: str, output_path: str) -> str:
        """
        HTML转DOCX
        返回：文件路径
        """
        pass
    
    def extract_images(self, docx_path: str, output_dir: str) -> list:
        """
        提取DOCX中的图片
        返回：图片列表
        """
        pass
    
    def clean_html(self, html: str) -> str:
        """
        清理HTML，移除不必要的标签和样式
        """
        pass
    
    def apply_word_styles(self, document) -> None:
        """
        应用Word样式到Document对象
        """
        pass
```

### 6.2 文件管理模块

**模块：document_file_manager.py**

**功能：**
- 文件读写操作
- 文件路径管理
- 临时文件处理

**主要方法：**
```python
class DocumentFileManager:
    def get_document_path(self, document_id: int) -> str:
        """获取文档路径"""
        pass
    
    def save_document(self, file_content: bytes, document_id: int) -> str:
        """保存文档"""
        pass
    
    def create_temp_file(self, suffix: str = '.docx') -> str:
        """创建临时文件"""
        pass
    
    def cleanup_temp_files(self) -> None:
        """清理临时文件"""
        pass
    
    def create_version_backup(self, document_id: int) -> str:
        """创建版本备份"""
        pass
```

### 6.3 图片处理模块

**模块：image_handler.py**

**功能：**
- 图片上传处理
- 图片压缩优化
- 图片URL生成

**主要方法：**
```python
class ImageHandler:
    def upload_image(self, file, document_id: int = None) -> dict:
        """
        上传图片
        返回：{
            'url': str,
            'path': str,
            'size': int
        }
        """
        pass
    
    def validate_image(self, file) -> bool:
        """校验图片文件"""
        pass
    
    def compress_image(self, image_path: str, max_size: int = 1920) -> None:
        """压缩图片"""
        pass
    
    def get_image_url(self, image_path: str) -> str:
        """生成图片URL"""
        pass
    
    def download_remote_image(self, url: str) -> str:
        """下载远程图片（HTML中的网络图片）"""
        pass
```

## 七、API视图实现

### 7.1 视图模块结构

**模块：views/document_convert.py**

**路由定义：**
```python
# DOCX转HTML
POST /api/document/convert/docx-to-html

# HTML转DOCX
POST /api/document/convert/html-to-docx

# 图片上传
POST /api/document/upload-image

# 获取转换状态（可选，用于长时间转换）
GET /api/document/convert/status/{task_id}
```

### 7.2 权限和认证

**要求：**
- 所有接口需要用户认证
- 检查用户对文档的访问权限
- 记录操作日志

**权限检查：**
```python
def check_document_permission(user_id: int, document_id: int, 
                              permission: str = 'read') -> bool:
    """
    检查用户对文档的权限
    permission: 'read', 'write', 'delete'
    """
    pass
```

## 八、格式保留策略

### 8.1 DOCX → HTML 保留的格式

**文本格式：**
- ✅ 字体（font-family）
- ✅ 字号（font-size）
- ✅ 加粗（bold）
- ✅ 斜体（italic）
- ✅ 下划线（underline）
- ✅ 删除线（strikethrough）
- ✅ 文字颜色（color）
- ✅ 高亮（background-color）

**段落格式：**
- ✅ 对齐方式（text-align）
- ✅ 行距（line-height）
- ✅ 段落间距（margin）
- ✅ 缩进（text-indent, padding）
- ⚠️ 首行缩进（可能需要特殊处理）

**列表：**
- ✅ 有序列表（ol, li）
- ✅ 无序列表（ul, li）
- ⚠️ 多级列表（需要保留嵌套关系）

**表格：**
- ✅ 表格结构（table, tr, td）
- ✅ 单元格合并（colspan, rowspan）
- ✅ 边框样式（border）
- ⚠️ 复杂表格样式（可能有损失）

**图片：**
- ✅ 图片内容
- ✅ 图片大小（width, height）
- ⚠️ 图片位置（浮动、环绕文字等）

**不支持或有限支持：**
- ❌ 页眉页脚
- ❌ 页码
- ❌ 水印
- ❌ 批注和修订
- ❌ 宏和嵌入对象
- ❌ 图表（Chart）
- ⚠️ 分栏布局
- ⚠️ 文本框

### 8.2 HTML → DOCX 保留的格式

**支持的HTML标签：**
```
<p>, <br>                          # 段落和换行
<b>, <strong>, <i>, <em>, <u>      # 文本格式
<h1> - <h6>                        # 标题
<ul>, <ol>, <li>                   # 列表
<table>, <tr>, <td>, <th>          # 表格
<img>                              # 图片
<a>                                # 链接（转为超链接）
<span> with style                  # 内联样式
<div> with style                   # 块级样式
```

**支持的CSS样式：**
```
font-family, font-size             # 字体
color, background-color            # 颜色
font-weight, font-style            # 加粗、斜体
text-decoration                    # 下划线、删除线
text-align                         # 对齐
line-height                        # 行距
margin, padding                    # 间距
border                            # 边框
```

### 8.3 格式映射表

**mammoth样式映射：**
```python
style_map = """
p[style-name='Heading 1'] => h1
p[style-name='Heading 2'] => h2
p[style-name='Heading 3'] => h3
r[style-name='Strong'] => strong
r[style-name='Emphasis'] => em
"""
```

**htmldocx样式增强：**
```python
# 自定义样式处理
def apply_custom_styles(document):
    # 设置默认字体
    document.styles['Normal'].font.name = '宋体'
    document.styles['Normal'].font.size = Pt(12)
    
    # 设置段落间距
    document.styles['Normal'].paragraph_format.space_after = Pt(0)
    
    # 设置行距
    document.styles['Normal'].paragraph_format.line_spacing = 1.5
```

## 九、性能优化

### 9.1 转换性能

**优化策略：**
1. 异步处理
   - 大文件使用Celery异步任务
   - 返回任务ID，前端轮询状态
   - 进度通知（WebSocket可选）

2. 缓存机制
   - 缓存DOCX→HTML转换结果
   - 缓存有效期：检测DOCX修改时间
   - 使用Redis存储缓存

3. 图片处理
   - 图片懒转换（需要时才转换）
   - 图片压缩（减少存储和传输）
   - CDN加速（生产环境）

### 9.2 并发处理

**限制策略：**
- 单用户同时转换限制：2-3个任务
- 全局并发转换限制：根据服务器配置
- 队列管理：超出限制加入等待队列

### 9.3 资源限制

**配置：**
```python
# 最大文件大小
MAX_DOCX_SIZE = 50 * 1024 * 1024  # 50MB
MAX_IMAGE_SIZE = 5 * 1024 * 1024   # 5MB

# 超时设置
CONVERT_TIMEOUT = 60  # 60秒

# 临时文件清理
TEMP_FILE_LIFETIME = 3600  # 1小时
```

## 十、错误处理和日志

### 10.1 错误分类

**客户端错误（4xx）：**
- 400: 请求参数错误、HTML格式错误
- 403: 权限不足
- 404: 文档不存在
- 413: 文件过大

**服务器错误（5xx）：**
- 500: 转换失败、文件操作失败
- 503: 服务繁忙（队列满）
- 507: 磁盘空间不足

### 10.2 日志记录

**记录内容：**
```python
# 转换开始
logger.info(f"DOCX→HTML 转换开始: document_id={doc_id}, user_id={user_id}")

# 转换成功
logger.info(f"DOCX→HTML 转换成功: document_id={doc_id}, 耗时={elapsed}s")

# 转换失败
logger.error(f"DOCX→HTML 转换失败: document_id={doc_id}, error={error}", 
             exc_info=True)

# 图片上传
logger.info(f"图片上传: user_id={user_id}, size={size}, path={path}")
```

### 10.3 监控指标

**关键指标：**
- 转换成功率
- 平均转换时间
- 并发转换数
- 磁盘使用率
- 错误率统计

## 十一、安全性

### 11.1 输入校验

**HTML内容：**
- XSS防护：使用bleach库清理HTML
- 限制允许的标签和属性
- 移除危险的JavaScript代码
- 限制HTML大小

**文件上传：**
- 文件类型白名单
- 文件大小限制
- 文件名安全检查
- 病毒扫描（生产环境）

### 11.2 权限控制

**文档访问：**
- 检查用户对文档的读写权限
- 记录所有操作日志
- 敏感操作二次确认

**图片访问：**
- 图片URL带签名（可选）
- 防盗链（生产环境）

### 11.3 数据保护

**备份策略：**
- 转换前自动备份原文档
- 保留最近N个版本
- 定期清理过期备份

## 十二、依赖库安装

### 12.1 Python依赖

**requirements.txt：**
```txt
# 文档转换核心
mammoth==1.6.0
python-docx==1.1.0
htmldocx==0.0.6

# HTML处理
bleach==6.1.0
lxml==4.9.3

# 图片处理
Pillow==10.1.0

# 异步任务（可选）
celery==5.3.4
redis==5.0.1

# 其他工具
python-magic==0.4.27  # 文件类型检测
```

### 12.2 系统依赖

**Ubuntu/Debian：**
```bash
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev
```

**CentOS/RHEL：**
```bash
sudo yum install -y \
    python3-devel \
    libxml2-devel \
    libxslt-devel \
    zlib-devel \
    libjpeg-devel
```

## 十三、开发步骤建议

### Phase 1：环境准备（1天）
1. 创建Python虚拟环境
2. 安装依赖库
3. 配置项目结构
4. 编写基础工具类

### Phase 2：核心转换功能（3-4天）
1. 实现DocumentConverter类
2. DOCX→HTML转换逻辑
3. HTML→DOCX转换逻辑
4. 格式处理和优化
5. 单元测试

### Phase 3：图片处理（2天）
1. 实现ImageHandler类
2. DOCX图片提取
3. 图片上传处理
4. HTML图片处理
5. 测试

### Phase 4：API接口（2-3天）
1. 创建视图和路由
2. 实现三个主要接口
3. 权限和认证
4. 错误处理
5. API测试

### Phase 5：数据库和文件管理（1-2天）
1. 数据库表设计和创建
2. 文件存储结构
3. 文件管理类实现
4. 版本管理（可选）

### Phase 6：优化和测试（2-3天）
1. 性能优化（缓存、异步）
2. 安全加固
3. 日志和监控
4. 全面测试
5. 文档编写

## 十四、测试用例

### 14.1 转换功能测试

**DOCX→HTML：**
- [ ] 纯文本文档
- [ ] 带格式文本（加粗、斜体、颜色等）
- [ ] 包含列表的文档
- [ ] 包含表格的文档
- [ ] 包含图片的文档
- [ ] 复杂格式文档
- [ ] 大文件（10MB+）

**HTML→DOCX：**
- [ ] 基础HTML标签
- [ ] 带样式HTML
- [ ] 包含图片的HTML
- [ ] 包含表格的HTML
- [ ] 网络图片处理
- [ ] 特殊字符处理

### 14.2 异常情况测试

- [ ] 文件不存在
- [ ] 文件格式错误
- [ ] 权限不足
- [ ] 磁盘空间不足
- [ ] 文件过大
- [ ] 转换超时
- [ ] 网络图片下载失败
- [ ] HTML包含恶意代码

### 14.3 性能测试

- [ ] 并发转换测试（10用户）
- [ ] 大文件转换（50MB）
- [ ] 多图片文档转换
- [ ] 缓存效果测试
- [ ] 内存占用监控

## 十五、部署注意事项

### 15.1 环境配置

**必需配置：**
```python
# settings.py
MEDIA_ROOT = '/path/to/media/'
MEDIA_URL = '/media/'
MAX_UPLOAD_SIZE = 50 * 1024 * 1024

# 转换配置
DOCUMENT_CONVERT = {
    'cache_enabled': True,
    'cache_timeout': 3600,
    'async_enabled': True,
    'temp_dir': '/tmp/document_convert/',
}
```

### 15.2 定时任务

**清理任务：**
```python
# 每小时清理临时文件
@periodic_task(run_every=crontab(minute=0))
def cleanup_temp_files():
    DocumentFileManager().cleanup_temp_files()

# 每天清理过期缓存
@periodic_task(run_every=crontab(hour=2, minute=0))
def cleanup_expired_cache():
    cache.clear()
```

### 15.3 监控和告警

**监控项：**
- 转换失败率 > 5% 告警
- 平均转换时间 > 30s 告警
- 磁盘使用率 > 85% 告警
- 并发数 > 阈值 告警

## 十六、技术文档参考

- mammoth文档：https://github.com/mwilliamson/python-mammoth
- python-docx文档：https://python-docx.readthedocs.io/
- htmldocx文档：https://github.com/pqzx/html2docx
- bleach文档：https://bleach.readthedocs.io/

## 十七、后续扩展

- 支持更多格式（ODT、RTF、TXT）
- 导出PDF功能
- 文档对比功能
- OCR文字识别
- 文档协同编辑
- 版本管理和回滚
- 文档模板系统

