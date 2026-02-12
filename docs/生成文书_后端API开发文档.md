# 案件文档管理系统 - 后端API开发文档

## 目录
1. [数据库表设计](#数据库表设计)
2. [API接口列表](#api接口列表)
3. [接口详细说明](#接口详细说明)
4. [业务逻辑说明](#业务逻辑说明)
5. [错误码定义](#错误码定义)

---

## 数据库表设计

### 1. case_folder (案件目录表)

用于存储每个案件的目录结构。

```sql
CREATE TABLE case_folder (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    case_id BIGINT NOT NULL COMMENT '案件ID',
    parent_id BIGINT DEFAULT NULL COMMENT '父目录ID，NULL表示根目录',
    folder_name VARCHAR(100) NOT NULL COMMENT '目录名称（中文显示名）',
    folder_path VARCHAR(500) NOT NULL COMMENT '完整路径（英文），如：/case_documents/complaint',
    folder_type VARCHAR(50) DEFAULT 'custom' COMMENT '目录类型：fixed-固定目录, custom-自定义目录',
    sort_order INT DEFAULT 0 COMMENT '排序序号',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除：0-否，1-是',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_case_id (case_id),
    INDEX idx_parent_id (parent_id),
    INDEX idx_folder_path (case_id, folder_path),
    UNIQUE KEY uk_case_folder_path (case_id, folder_path, is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='案件目录结构表';
```

### 2. case_document (案件文档表)

用于存储案件相关的所有文档。

```sql
CREATE TABLE case_document (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    case_id BIGINT NOT NULL COMMENT '案件ID',
    folder_id BIGINT DEFAULT NULL COMMENT '所属目录ID',
    folder_path VARCHAR(500) DEFAULT NULL COMMENT '目录路径（冗余字段，便于查询）',
    
    document_name VARCHAR(200) NOT NULL COMMENT '文档显示名称',
    document_type VARCHAR(50) COMMENT '文档类型：template-模板生成, upload-上传, ai-AI生成, parse-解析源文件',
    
    file_name VARCHAR(200) NOT NULL COMMENT '实际文件名（含扩展名）',
    file_path VARCHAR(500) NOT NULL COMMENT '文件存储相对路径',
    file_size BIGINT COMMENT '文件大小（字节）',
    file_ext VARCHAR(20) COMMENT '文件扩展名（如：.docx, .pdf）',
    mime_type VARCHAR(100) COMMENT 'MIME类型',
    
    template_id BIGINT DEFAULT NULL COMMENT '关联的模板ID（如果是模板生成）',
    version INT DEFAULT 1 COMMENT '版本号（同一文档的不同版本）',
    
    storage_type VARCHAR(20) DEFAULT 'local' COMMENT '存储类型：local-本地, oss-阿里云, minio等',
    storage_url VARCHAR(500) COMMENT '存储完整URL（如果使用云存储）',
    
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除：0-否，1-是',
    created_by BIGINT COMMENT '创建人ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_case_id (case_id),
    INDEX idx_folder_id (folder_id),
    INDEX idx_folder_path (case_id, folder_path),
    INDEX idx_template_id (template_id),
    INDEX idx_document_type (document_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='案件文档表';
```

### 3. 固定目录配置（代码常量）

固定目录不需要单独的数据表，直接在后端代码中定义为常量配置。

**Python/Django 示例**：

```python
# constants.py 或 settings.py

CASE_FOLDER_TEMPLATES = [
    {
        'folder_name': '案件文书',
        'folder_path': '/case_documents',
        'sort_order': 1,
        'description': '存放模板生成的各类法律文书'
    },
    {
        'folder_name': '正卷目录',
        'folder_path': '/main_volume',
        'sort_order': 2,
        'description': '存放案件正卷相关文档'
    },
    {
        'folder_name': '副卷目录',
        'folder_path': '/sub_volume',
        'sort_order': 3,
        'description': '存放案件副卷相关文档'
    },
    {
        'folder_name': '执行案内目录',
        'folder_path': '/execution_files',
        'sort_order': 4,
        'description': '存放执行阶段相关文档'
    },
    {
        'folder_name': '临时文件',
        'folder_path': '/temp_files',
        'sort_order': 5,
        'description': '存放临时性文件'
    }
]
```

**Java/Spring Boot 示例**：

```java
public class CaseFolderConstants {
    public static final List<FolderTemplate> FOLDER_TEMPLATES = Arrays.asList(
        new FolderTemplate("案件文书", "/case_documents", 1, "存放模板生成的各类法律文书"),
        new FolderTemplate("正卷目录", "/main_volume", 2, "存放案件正卷相关文档"),
        new FolderTemplate("副卷目录", "/sub_volume", 3, "存放案件副卷相关文档"),
        new FolderTemplate("执行案内目录", "/execution_files", 4, "存放执行阶段相关文档"),
        new FolderTemplate("临时文件", "/temp_files", 5, "存放临时性文件")
    );
    
    @Data
    @AllArgsConstructor
    public static class FolderTemplate {
        private String folderName;
        private String folderPath;
        private Integer sortOrder;
        private String description;
    }
}
```

---

## API接口列表

### 文档管理相关

| 接口名称 | 请求方法 | 路径 | 说明 |
|---------|---------|------|------|
| 获取案件文档树 | GET | `/api/case/cases/{case_id}/document_tree/` | 获取案件的完整目录树结构 |
| 获取案件文档列表 | GET | `/api/case/cases/{case_id}/documents/` | 获取案件的文档列表（可按目录筛选） |
| 上传文档 | POST | `/api/case/cases/{case_id}/upload_document/` | 上传文档到指定目录 |
| 下载文档 | GET | `/api/case/documents/{document_id}/download/` | 下载指定文档 |
| 删除文档 | DELETE | `/api/case/documents/{document_id}/` | 删除指定文档 |
| 移动文档 | PUT | `/api/case/documents/{document_id}/move/` | 移动文档到其他目录 |
| 重命名文档 | PUT | `/api/case/documents/{document_id}/rename/` | 重命名文档 |

### 模板生成相关

| 接口名称 | 请求方法 | 路径 | 说明 |
|---------|---------|------|------|
| 获取模板列表 | GET | `/api/case/templates/` | 获取所有可用模板 |
| 检查已生成文书 | POST | `/api/case/cases/{case_id}/check_generated_documents/` | 检查模板是否已生成文书 |
| 生成文书 | POST | `/api/case/templates/generate_documents/` | 根据模板生成文书 |

### 文档解析相关

| 接口名称 | 请求方法 | 路径 | 说明 |
|---------|---------|------|------|
| 解析文档 | POST | `/api/case/cases/parse_document/` | 解析文档/文字并提取案件信息 |

---

## 接口详细说明

### 1. 获取案件文档树

**请求**
```
GET /api/case/cases/{case_id}/document_tree/
```

**响应**
```json
{
  "code": 2000,
  "msg": "success",
  "data": [
    {
      "id": 1,
      "label": "案件文书",
      "path": "/case_documents",
      "type": "folder",
      "children": [
        {
          "id": 101,
          "label": "起诉状.docx",
          "path": "/case_documents/complaint_20250101.docx",
          "type": "file",
          "document_id": 1001,
          "file_size": 45678,
          "created_at": "2025-01-01 10:00:00"
        }
      ]
    },
    {
      "id": 2,
      "label": "正卷目录",
      "path": "/main_volume",
      "type": "folder",
      "children": []
    }
  ]
}
```

### 2. 获取案件文档列表

**请求**
```
GET /api/case/cases/{case_id}/documents/?folder_path=/case_documents
```

**查询参数**
- `folder_path`: (可选) 目录路径，不传则返回所有文档
- `document_type`: (可选) 文档类型筛选
- `page`: (可选) 页码，默认1
- `page_size`: (可选) 每页数量，默认20

**响应**
```json
{
  "code": 2000,
  "msg": "success",
  "data": {
    "total": 10,
    "page": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1001,
        "case_id": 1,
        "folder_path": "/case_documents",
        "document_name": "起诉状",
        "document_type": "template",
        "file_name": "complaint_20250101.docx",
        "file_path": "uploads/cases/1/documents/complaint_20250101.docx",
        "file_size": 45678,
        "file_ext": ".docx",
        "template_id": 1,
        "version": 1,
        "storage_url": "http://example.com/uploads/cases/1/documents/complaint_20250101.docx",
        "created_by": 100,
        "created_at": "2025-01-01 10:00:00"
      }
    ]
  }
}
```

### 3. 上传文档

**请求**
```
POST /api/case/cases/{case_id}/upload_document/
Content-Type: multipart/form-data
```

**请求体**
```
folder_path: /case_documents
file: (binary)
document_name: 证据材料1
```

**响应**
```json
{
  "code": 2000,
  "msg": "上传成功",
  "data": {
    "id": 1002,
    "document_name": "证据材料1",
    "file_name": "evidence_20250101.pdf",
    "file_path": "uploads/cases/1/documents/evidence_20250101.pdf",
    "file_size": 123456,
    "storage_url": "http://example.com/uploads/cases/1/documents/evidence_20250101.pdf"
  }
}
```

### 4. 检查已生成文书

**请求**
```
POST /api/case/cases/{case_id}/check_generated_documents/
Content-Type: application/json
```

**请求体**
```json
{
  "template_ids": [1, 2, 3],
  "folder_path": "/case_documents"
}
```

**响应 - 不存在**
```json
{
  "code": 2000,
  "msg": "success",
  "data": {
    "exists": false,
    "existing_documents": []
  }
}
```

**响应 - 存在**
```json
{
  "code": 2000,
  "msg": "success",
  "data": {
    "exists": true,
    "existing_documents": [
      "起诉状.docx",
      "证据清单.docx"
    ]
  }
}
```

### 5. 生成文书

**请求**
```
POST /api/case/templates/generate_documents/
Content-Type: application/json
```

**请求体**
```json
{
  "case_id": 1,
  "template_ids": [1, 2, 3],
  "folder_path": "/case_documents"
}
```

**响应**
```json
{
  "code": 2000,
  "msg": "生成成功",
  "data": {
    "success_count": 2,
    "failed_count": 1,
    "documents": [
      {
        "id": 1003,
        "template_id": 1,
        "template_name": "起诉状",
        "document_name": "起诉状",
        "file_name": "complaint_20250101_v2.docx",
        "file_path": "uploads/cases/1/documents/complaint_20250101_v2.docx",
        "storage_url": "http://example.com/uploads/cases/1/documents/complaint_20250101_v2.docx",
        "status": "success"
      },
      {
        "id": 1004,
        "template_id": 2,
        "template_name": "证据清单",
        "document_name": "证据清单",
        "file_name": "evidence_list_20250101.docx",
        "file_path": "uploads/cases/1/documents/evidence_list_20250101.docx",
        "storage_url": "http://example.com/uploads/cases/1/documents/evidence_list_20250101.docx",
        "status": "success"
      },
      {
        "template_id": 3,
        "template_name": "答辩状",
        "status": "failed",
        "error": "模板数据不完整"
      }
    ]
  }
}
```

### 6. 解析文档

**请求 - 文件解析**
```
POST /api/case/cases/parse_document/
Content-Type: application/json
```

**请求体 - 文件**
```json
{
  "case_id": 1,
  "files": [
    {
      "name": "complaint.docx",
      "type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "size": 45678,
      "base64": "UEsDBBQABgAIAAAAIQD..."
    }
  ]
}
```

**请求体 - 文字**
```json
{
  "case_id": 1,
  "text_content": "原告：张三\n被告：李四\n..."
}
```

**响应**
```json
{
  "code": 2000,
  "msg": "解析成功",
  "data": {
    "plaintiff_name": "张三",
    "defendant_name": "李四",
    "case_type": "民事诉讼",
    "litigation_request": "请求判令被告...",
    "facts_and_reasons": "原被告之间...",
    "contract_amount": 100000,
    "lawyer_fee": 5000
  }
}
```

### 7. 下载文档

**请求**
```
GET /api/case/documents/{document_id}/download/
```

**响应**
```
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="complaint.docx"

(文件二进制流)
```

### 8. 删除文档

**请求**
```
DELETE /api/case/documents/{document_id}/
```

**响应**
```json
{
  "code": 2000,
  "msg": "删除成功"
}
```

### 9. 移动文档

**请求**
```
PUT /api/case/documents/{document_id}/move/
Content-Type: application/json
```

**请求体**
```json
{
  "target_folder_path": "/main_volume"
}
```

**响应**
```json
{
  "code": 2000,
  "msg": "移动成功",
  "data": {
    "id": 1001,
    "folder_path": "/main_volume",
    "updated_at": "2025-01-01 11:00:00"
  }
}
```

### 10. 重命名文档

**请求**
```
PUT /api/case/documents/{document_id}/rename/
Content-Type: application/json
```

**请求体**
```json
{
  "new_name": "起诉状（修改版）"
}
```

**响应**
```json
{
  "code": 2000,
  "msg": "重命名成功",
  "data": {
    "id": 1001,
    "document_name": "起诉状（修改版）",
    "updated_at": "2025-01-01 11:00:00"
  }
}
```

---

## 业务逻辑说明

### 1. 案件创建时初始化目录

当创建新案件时，系统应自动执行以下操作：

```python
def create_case_folders(case_id):
    """
    为新案件创建固定目录结构
    """
    from .constants import CASE_FOLDER_TEMPLATES  # 导入固定目录配置
    
    # 1. 为该案件创建目录记录
    for template in CASE_FOLDER_TEMPLATES:
        CaseFolder.objects.create(
            case_id=case_id,
            parent_id=None,  # 一级目录
            folder_name=template['folder_name'],
            folder_path=template['folder_path'],
            folder_type='fixed',
            sort_order=template['sort_order']
        )
    
    # 2. 在文件系统创建对应目录
    base_path = f'/uploads/cases/{case_id}'
    for template in CASE_FOLDER_TEMPLATES:
        folder_path = os.path.join(base_path, template['folder_path'].strip('/'))
        os.makedirs(folder_path, exist_ok=True)
```

### 2. 文书生成逻辑

```python
def generate_documents(case_id, template_ids, folder_path):
    """
    生成文书文档
    """
    results = {
        'success_count': 0,
        'failed_count': 0,
        'documents': []
    }
    
    for template_id in template_ids:
        try:
            # 1. 获取模板和案件信息
            template = Template.objects.get(id=template_id)
            case = Case.objects.get(id=case_id)
            
            # 2. 检查是否已存在（基于template_id和folder_path）
            existing = CaseDocument.objects.filter(
                case_id=case_id,
                template_id=template_id,
                folder_path=folder_path,
                is_deleted=0
            ).first()
            
            # 3. 生成文档
            file_content = template.render(case.to_dict())
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"{template.template_name}_{timestamp}.docx"
            
            # 4. 保存文件
            file_path = f"uploads/cases/{case_id}{folder_path}/{file_name}"
            save_file(file_path, file_content)
            
            # 5. 如果已存在，增加版本号
            version = 1
            if existing:
                version = existing.version + 1
            
            # 6. 创建文档记录
            document = CaseDocument.objects.create(
                case_id=case_id,
                folder_path=folder_path,
                document_name=template.template_name,
                document_type='template',
                file_name=file_name,
                file_path=file_path,
                file_size=len(file_content),
                file_ext='.docx',
                template_id=template_id,
                version=version,
                storage_type='local',
                storage_url=f"/media/{file_path}",
                created_by=current_user.id
            )
            
            results['success_count'] += 1
            results['documents'].append({
                'id': document.id,
                'template_id': template_id,
                'template_name': template.template_name,
                'document_name': document.document_name,
                'file_name': file_name,
                'file_path': file_path,
                'storage_url': document.storage_url,
                'status': 'success'
            })
            
        except Exception as e:
            results['failed_count'] += 1
            results['documents'].append({
                'template_id': template_id,
                'template_name': template.template_name if template else '未知模板',
                'status': 'failed',
                'error': str(e)
            })
    
    return results
```

### 3. 文档解析逻辑

```python
def parse_document(case_id, files=None, text_content=None):
    """
    解析文档或文字内容，提取案件信息
    """
    content = ''
    
    if files:
        # 解析文件（docx, pdf等）
        for file_data in files:
            base64_data = file_data['base64']
            file_type = file_data['type']
            
            # 解码base64
            file_bytes = base64.b64decode(base64_data)
            
            # 根据文件类型解析
            if 'word' in file_type or file_data['name'].endswith('.docx'):
                content += extract_text_from_docx(file_bytes)
            elif 'pdf' in file_type:
                content += extract_text_from_pdf(file_bytes)
            else:
                content += file_bytes.decode('utf-8', errors='ignore')
    
    elif text_content:
        content = text_content
    
    # 使用AI或规则提取信息
    extracted_data = ai_extract_case_info(content)
    
    # 更新案件信息
    case = Case.objects.get(id=case_id)
    for key, value in extracted_data.items():
        if hasattr(case, key):
            setattr(case, key, value)
    case.save()
    
    # 如果是文件解析，保存源文件到临时目录
    if files:
        for file_data in files:
            save_parse_source_file(case_id, file_data)
    
    return extracted_data
```

### 4. 文件存储路径规范

```
/uploads/
  └── cases/
      └── {case_id}/
          ├── case_documents/          # 案件文书
          │   ├── complaint_20250101.docx
          │   └── evidence_list_20250101.docx
          ├── main_volume/             # 正卷目录
          │   └── ...
          ├── sub_volume/              # 副卷目录
          │   └── ...
          ├── execution_files/         # 执行案内目录
          │   └── ...
          ├── temp_files/              # 临时文件
          │   └── parse_source_20250101.docx
          └── uploads/                 # 用户上传
              └── ...
```

---

## 错误码定义

| 错误码 | 说明 |
|-------|------|
| 2000 | 成功 |
| 4000 | 请求参数错误 |
| 4001 | 案件不存在 |
| 4002 | 文档不存在 |
| 4003 | 模板不存在 |
| 4004 | 目录不存在 |
| 4005 | 文件上传失败 |
| 4006 | 文件类型不支持 |
| 4007 | 文件大小超限 |
| 5000 | 服务器内部错误 |
| 5001 | 文书生成失败 |
| 5002 | 文档解析失败 |
| 5003 | 文件存储失败 |

---

## 注意事项

1. **文件安全**：
   - 验证文件类型和大小
   - 文件名需要进行安全处理（防止路径遍历）
   - 敏感文档需要权限验证

2. **性能优化**：
   - 大文件上传使用分片上传
   - 文档预览使用缓存
   - 目录树查询使用递归查询优化

3. **事务处理**：
   - 文书生成需要在事务中完成（数据库+文件系统）
   - 失败时需要回滚

4. **日志记录**：
   - 记录所有文档操作日志
   - 记录文书生成的详细信息

5. **版本管理**：
   - 同一模板重复生成时自动增加版本号
   - 保留历史版本记录

---

## 开发建议

### Django Model 示例

```python
from django.db import models

class CaseFolder(models.Model):
    """案件目录表"""
    case = models.ForeignKey('Case', on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    folder_name = models.CharField(max_length=100, verbose_name='目录名称')
    folder_path = models.CharField(max_length=500, verbose_name='完整路径')
    folder_type = models.CharField(max_length=50, default='custom', verbose_name='目录类型')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    is_deleted = models.BooleanField(default=False, verbose_name='是否删除')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'case_folder'
        verbose_name = '案件目录'
        verbose_name_plural = verbose_name
        unique_together = [['case', 'folder_path', 'is_deleted']]

class CaseDocument(models.Model):
    """案件文档表"""
    DOCUMENT_TYPE_CHOICES = [
        ('template', '模板生成'),
        ('upload', '用户上传'),
        ('ai', 'AI生成'),
        ('parse', '解析源文件'),
    ]
    
    case = models.ForeignKey('Case', on_delete=models.CASCADE, related_name='documents')
    folder = models.ForeignKey(CaseFolder, null=True, blank=True, on_delete=models.SET_NULL)
    folder_path = models.CharField(max_length=500, null=True, blank=True)
    
    document_name = models.CharField(max_length=200, verbose_name='文档名称')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    
    file_name = models.CharField(max_length=200, verbose_name='文件名')
    file_path = models.CharField(max_length=500, verbose_name='文件路径')
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name='文件大小')
    file_ext = models.CharField(max_length=20, null=True, blank=True)
    mime_type = models.CharField(max_length=100, null=True, blank=True)
    
    template = models.ForeignKey('Template', null=True, blank=True, on_delete=models.SET_NULL)
    version = models.IntegerField(default=1, verbose_name='版本号')
    
    storage_type = models.CharField(max_length=20, default='local')
    storage_url = models.CharField(max_length=500, null=True, blank=True)
    
    is_deleted = models.BooleanField(default=False)
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'case_document'
        verbose_name = '案件文档'
        verbose_name_plural = verbose_name
```

### 工具函数示例

```python
# utils/folder_helper.py

from .constants import CASE_FOLDER_TEMPLATES

def get_folder_templates():
    """获取固定目录模板配置"""
    return CASE_FOLDER_TEMPLATES

def get_folder_by_path(folder_path):
    """根据路径获取目录配置"""
    for template in CASE_FOLDER_TEMPLATES:
        if template['folder_path'] == folder_path:
            return template
    return None

def get_folder_display_name(folder_path):
    """根据路径获取目录显示名称"""
    folder = get_folder_by_path(folder_path)
    return folder['folder_name'] if folder else folder_path

def validate_folder_path(folder_path):
    """验证目录路径是否为有效的固定目录"""
    valid_paths = [t['folder_path'] for t in CASE_FOLDER_TEMPLATES]
    return folder_path in valid_paths
```

**案件创建信号示例（Django）**：

```python
# signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Case
from .utils.folder_helper import create_case_folders

@receiver(post_save, sender=Case)
def init_case_folders(sender, instance, created, **kwargs):
    """案件创建后自动初始化目录结构"""
    if created:
        create_case_folders(instance.id)
```

---

## 总结

本文档提供了完整的案件文档管理系统后端开发方案，主要特点：

1. **简化设计**：固定目录配置直接在代码中定义，无需额外数据表
2. **灵活扩展**：支持在固定目录下创建自定义子目录
3. **版本管理**：自动管理文档版本，避免重复生成覆盖
4. **安全可靠**：完善的权限验证和错误处理机制
5. **易于维护**：清晰的代码结构和完整的接口文档

---

以上就是完整的后端API开发文档，涵盖了数据库设计、接口定义、业务逻辑和实现建议。

