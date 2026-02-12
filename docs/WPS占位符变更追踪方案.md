# WPS占位符变更追踪方案

## 📋 需求概述

当用户通过WPS编辑由模板生成的docx文档时，需要追踪哪些占位符被用户修改了。

### 当前架构
- **模板位置**：`media/case_templates/` 目录下的docx模板文件
- **占位符格式**：`{{ key }}` 或 `{{ key | 默认值 }}`
- **生成流程**：使用 `PlaceholderTemplateService` 从模板生成文档
- **编辑方式**：用户通过WPS在线编辑器编辑文档
- **保存流程**：WPS通过回调接口保存文档（`wps_upload_commit` 或 `wps_save`）

---

## 🎯 解决方案对比

### 方案一：文档对比方案（推荐 ⭐⭐⭐⭐⭐）

**原理**：保存原始生成的文档副本，与WPS保存后的文档进行对比，找出差异。

**优点**：
- ✅ 准确性高，能准确识别所有修改
- ✅ 不依赖WPS API，完全自主控制
- ✅ 可以追踪非占位符内容的修改（如格式、新增段落等）
- ✅ 可以识别占位符被删除的情况

**缺点**：
- ⚠️ 需要存储原始文档副本，增加存储空间
- ⚠️ 文档对比需要解析docx，性能开销较大
- ⚠️ 复杂格式对比可能不准确（如表格、图片等）

**实现步骤**：
1. 生成文档时，保存原始文档副本到 `media/cases/{case_id}/originals/{document_id}.docx`
2. WPS保存时，解析保存后的文档，提取所有文本内容
3. 解析原始文档，提取所有文本内容
4. 对比两个文档，找出差异
5. 识别差异中的占位符（通过正则匹配 `{{ key }}` 格式）
6. 提取占位符的原始值和当前值，记录变更

**技术实现**：
```python
from docx import Document
import re

def extract_placeholders_from_docx(file_path):
    """从docx文件中提取所有占位符"""
    doc = Document(file_path)
    placeholders = {}
    
    # 遍历所有段落
    for para in doc.paragraphs:
        text = para.text
        # 匹配占位符 {{ key }} 或 {{ key | 默认值 }}
        matches = re.findall(r'\{\{\s*([^}|]+)(?:\s*\|\s*([^}]+))?\s*\}\}', text)
        for match in matches:
            key = match[0].strip()
            default = match[1].strip() if match[1] else None
            placeholders[key] = {
                'text': text,
                'default': default
            }
    
    # 遍历所有表格
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text = cell.text
                matches = re.findall(r'\{\{\s*([^}|]+)(?:\s*\|\s*([^}]+))?\s*\}\}', text)
                for match in matches:
                    key = match[0].strip()
                    placeholders[key] = {
                        'text': text,
                        'default': match[1].strip() if match[1] else None
                    }
    
    return placeholders

def compare_documents(original_path, modified_path):
    """对比两个文档，找出占位符变更"""
    original_placeholders = extract_placeholders_from_docx(original_path)
    modified_placeholders = extract_placeholders_from_docx(modified_path)
    
    changes = []
    
    # 找出被修改的占位符
    for key in original_placeholders:
        original_value = original_placeholders[key]
        if key in modified_placeholders:
            modified_value = modified_placeholders[key]
            if original_value != modified_value:
                changes.append({
                    'key': key,
                    'original': original_value['text'],
                    'modified': modified_value['text'],
                    'type': 'modified'
                })
        else:
            # 占位符被删除
            changes.append({
                'key': key,
                'original': original_value['text'],
                'modified': None,
                'type': 'deleted'
            })
    
    # 找出新增的占位符
    for key in modified_placeholders:
        if key not in original_placeholders:
            changes.append({
                'key': key,
                'original': None,
                'modified': modified_placeholders[key]['text'],
                'type': 'added'
            })
    
    return changes
```

---

### 方案二：占位符值提取对比方案（推荐 ⭐⭐⭐⭐）

**原理**：在生成文档时保存原始占位符数据，WPS保存时解析文档提取占位符值，与原始数据对比。

**优点**：
- ✅ 不需要存储原始文档副本，节省存储空间
- ✅ 实现相对简单，只需解析当前文档
- ✅ 性能开销较小，只解析一次文档

**缺点**：
- ⚠️ 如果占位符被完全删除，可能无法识别
- ⚠️ 如果用户修改了占位符格式（如 `{{ key }}` 改为其他格式），无法识别
- ⚠️ 需要确保生成文档时保存了原始数据

**实现步骤**：
1. 在 `CaseDocument` 模型中添加字段 `original_placeholder_data`（JSON字段）
2. 生成文档时，保存占位符的原始值到数据库
3. WPS保存时，解析保存后的文档，提取所有占位符及其值
4. 对比原始数据和当前数据，找出被修改的占位符
5. 记录变更到数据库或日志

**数据库设计**：
```python
# models.py
class CaseDocument(models.Model):
    # ... 现有字段 ...
    
    original_placeholder_data = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        verbose_name="原始占位符数据",
        help_text="生成文档时使用的占位符原始值，用于追踪变更"
    )
    
    placeholder_changes = models.JSONField(
        default=list,
        null=True,
        blank=True,
        verbose_name="占位符变更记录",
        help_text="记录用户修改的占位符及其变更历史"
    )
```

**技术实现**：
```python
def extract_placeholder_values_from_docx(file_path):
    """从docx文件中提取占位符的实际值（不是占位符本身）"""
    doc = Document(file_path)
    placeholder_values = {}
    
    # 提取所有文本内容
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                full_text.append(cell.text)
    
    # 使用占位符解析器提取占位符
    from .placeholder_parser import PlaceholderParser
    parser = PlaceholderParser()
    
    # 解析文档内容，找出占位符及其对应的值
    # 注意：这里需要智能匹配，因为占位符已经被替换成了实际值
    # 需要通过位置推断或上下文匹配
    
    return placeholder_values

def track_placeholder_changes(document, saved_file_path):
    """追踪占位符变更"""
    original_data = document.original_placeholder_data or {}
    
    # 解析保存后的文档，提取当前占位符值
    current_values = extract_placeholder_values_from_docx(saved_file_path)
    
    changes = []
    for key, original_value in original_data.items():
        current_value = current_values.get(key)
        if current_value and current_value != original_value:
            changes.append({
                'key': key,
                'original': original_value,
                'modified': current_value,
                'changed_at': datetime.now().isoformat()
            })
    
    # 更新变更记录
    if changes:
        document.placeholder_changes = changes
        document.save(update_fields=['placeholder_changes'])
    
    return changes
```

---

### 方案三：智能占位符匹配方案（推荐 ⭐⭐⭐⭐）

**原理**：在生成文档时，为每个占位符添加特殊标记（如隐藏文本或书签），保存时通过标记识别占位符位置并提取值。

**优点**：
- ✅ 准确识别占位符位置，不受格式影响
- ✅ 可以追踪占位符的位置变化
- ✅ 可以识别占位符被删除的情况

**缺点**：
- ⚠️ 需要修改文档生成逻辑，添加标记
- ⚠️ 标记可能影响文档格式（如果使用隐藏文本）
- ⚠️ 实现复杂度较高

**实现步骤**：
1. 生成文档时，为每个占位符添加隐藏标记（如 `{{__MARKER_key__}}`）
2. 使用书签或隐藏文本标记占位符位置
3. WPS保存时，解析文档中的标记
4. 通过标记识别占位符，提取其当前值
5. 对比原始值，记录变更

**技术实现**：
```python
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def add_placeholder_marker(doc, placeholder_key, placeholder_value):
    """为占位符添加隐藏标记"""
    # 方法1：使用隐藏文本
    # 方法2：使用书签
    # 方法3：使用自定义XML属性
    
    # 示例：使用隐藏文本
    for para in doc.paragraphs:
        for run in para.runs:
            if placeholder_value in run.text:
                # 添加隐藏文本标记
                hidden_run = para.add_run(f"{{{{__MARKER_{placeholder_key}__}}}}")
                hidden_run.font.hidden = True
```

---

### 方案四：WPS回调追踪方案（不推荐 ⚠️）

**原理**：利用WPS的回调机制获取文档变更信息。

**优点**：
- ✅ 如果WPS支持，实现最简单

**缺点**：
- ❌ WPS回调接口可能不提供详细的变更信息
- ❌ 依赖WPS API，无法自主控制
- ❌ 需要查看WPS文档确认是否支持

**结论**：需要查阅WPS官方文档，确认是否有相关回调接口。根据当前项目已实现的WPS回调，**没有发现专门追踪占位符变更的回调接口**。

---

## 🏆 推荐方案：方案一 + 方案二 混合方案

### 方案组合说明

**核心思路**：
1. **生成阶段**：保存原始占位符数据到数据库（方案二）
2. **保存阶段**：解析保存后的文档，提取占位符值，与原始数据对比（方案二）
3. **可选增强**：如果对比结果不准确，使用原始文档副本进行深度对比（方案一）

### 完整实现流程

#### 第一阶段：数据库设计

```python
# models.py - CaseDocument 模型
class CaseDocument(models.Model):
    # ... 现有字段 ...
    
    # 原始占位符数据（生成文档时保存）
    original_placeholder_data = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        verbose_name="原始占位符数据",
        help_text="生成文档时使用的占位符原始值，格式：{'key': 'value', ...}"
    )
    
    # 占位符变更记录
    placeholder_changes_history = models.JSONField(
        default=list,
        null=True,
        blank=True,
        verbose_name="占位符变更历史",
        help_text="记录每次保存时的占位符变更，格式：[{'timestamp': '...', 'changes': [...], 'user_id': ...}, ...]"
    )
    
    # 原始文档副本路径（可选，用于深度对比）
    original_file_backup = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="原始文档备份路径",
        help_text="生成文档时的原始文件备份路径，用于文档对比"
    )
```

#### 第二阶段：生成文档时保存原始数据

```python
# placeholder_template_service.py
class PlaceholderTemplateService:
    def fill_and_save_by_record(self, case_id, template, data, **kwargs):
        """填充占位符并保存文档"""
        # ... 现有生成逻辑 ...
        
        # 保存原始占位符数据
        document.original_placeholder_data = data.copy()
        
        # 可选：保存原始文档副本
        if settings.SAVE_ORIGINAL_DOCUMENT_BACKUP:
            backup_path = self._save_original_backup(document, generated_file_path)
            document.original_file_backup = backup_path
        
        document.save()
        
        return document
```

#### 第三阶段：WPS保存时追踪变更

```python
# wps_callback_views.py 或 wps_document_handler.py

from case_management.placeholder_parser import PlaceholderParser
from docx import Document
import re

class PlaceholderChangeTracker:
    """占位符变更追踪器"""
    
    def __init__(self):
        self.parser = PlaceholderParser()
    
    def extract_placeholder_values_from_docx(self, file_path):
        """从docx文件中提取占位符的实际值
        
        注意：这里需要智能匹配，因为占位符已经被替换成了实际值。
        我们通过以下策略：
        1. 解析文档，找出所有可能的占位符位置（通过上下文推断）
        2. 或者，如果文档中还有占位符格式（未完全替换），直接提取
        3. 或者，通过位置信息匹配（如果保存了位置信息）
        """
        doc = Document(file_path)
        values = {}
        
        # 策略1：查找文档中剩余的占位符格式（如果用户修改时保留了格式）
        full_text = '\n'.join([para.text for para in doc.paragraphs])
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    full_text += '\n' + cell.text
        
        # 匹配占位符格式
        placeholder_pattern = re.compile(r'\{\{\s*([^}|]+)(?:\s*\|\s*([^}]+))?\s*\}\}')
        matches = placeholder_pattern.findall(full_text)
        
        # 策略2：如果文档中没有占位符格式，需要智能推断
        # 这里需要根据原始数据的位置信息来匹配
        # 或者，通过文档结构（段落、表格）来推断
        
        return values
    
    def track_changes(self, document, saved_file_path):
        """追踪占位符变更"""
        original_data = document.original_placeholder_data or {}
        
        if not original_data:
            logger.warning(f"文档 {document.id} 没有原始占位符数据，无法追踪变更")
            return []
        
        # 提取当前文档中的占位符值
        current_values = self._smart_extract_values(document, saved_file_path, original_data)
        
        # 对比找出变更
        changes = []
        for key, original_value in original_data.items():
            current_value = current_values.get(key)
            
            # 如果找不到当前值，可能是被删除了
            if current_value is None:
                # 尝试在文档中查找该值（可能格式化了）
                current_value = self._find_value_in_document(saved_file_path, original_value)
            
            if current_value is not None and str(current_value).strip() != str(original_value).strip():
                changes.append({
                    'key': key,
                    'original': str(original_value),
                    'modified': str(current_value),
                    'changed_at': datetime.now().isoformat()
                })
        
        # 保存变更记录
        if changes:
            history = document.placeholder_changes_history or []
            history.append({
                'timestamp': datetime.now().isoformat(),
                'user_id': getattr(document, '_current_user_id', None),
                'changes': changes
            })
            document.placeholder_changes_history = history
            document.save(update_fields=['placeholder_changes_history'])
        
        return changes
    
    def _smart_extract_values(self, document, file_path, original_data):
        """智能提取占位符值
        
        策略：
        1. 先尝试解析文档中的占位符格式
        2. 如果找不到，通过位置信息匹配（需要保存位置信息）
        3. 如果还找不到，通过文档结构推断（段落、表格位置）
        """
        values = {}
        
        # 策略1：解析占位符格式
        doc = Document(file_path)
        full_text = self._extract_full_text(doc)
        
        # 查找剩余的占位符格式
        placeholder_pattern = re.compile(r'\{\{\s*([^}|]+)(?:\s*\|\s*([^}]+))?\s*\}\}')
        matches = placeholder_pattern.findall(full_text)
        for match in matches:
            key = match[0].strip()
            if key in original_data:
                # 提取占位符附近的值
                # 这里需要更复杂的逻辑来确定实际值
                pass
        
        # 策略2：通过原始值在文档中的位置推断
        # 如果原始值在文档中，且位置与生成时一致，可以推断出对应的占位符
        for key, original_value in original_data.items():
            if str(original_value) in full_text:
                # 找到值的位置，推断对应的占位符
                # 这需要更复杂的匹配算法
                pass
        
        return values
    
    def _extract_full_text(self, doc):
        """提取文档中的所有文本"""
        texts = []
        for para in doc.paragraphs:
            texts.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    texts.append(cell.text)
        return '\n'.join(texts)
    
    def _find_value_in_document(self, file_path, value):
        """在文档中查找值（可能格式化了）"""
        doc = Document(file_path)
        full_text = self._extract_full_text(doc)
        
        # 简单匹配
        if str(value) in full_text:
            return str(value)
        
        # 模糊匹配（去除空格、换行等）
        normalized_value = re.sub(r'\s+', '', str(value))
        normalized_text = re.sub(r'\s+', '', full_text)
        if normalized_value in normalized_text:
            return str(value)
        
        return None


# 在 WPS 保存接口中使用
def wps_upload_commit(request, file_id):
    """WPS完成上传"""
    # ... 现有保存逻辑 ...
    
    # 追踪占位符变更
    tracker = PlaceholderChangeTracker()
    changes = tracker.track_changes(document, saved_file_path)
    
    if changes:
        logger.info(f"检测到占位符变更: document_id={document.id}, changes={len(changes)}")
        for change in changes:
            logger.info(f"  - {change['key']}: '{change['original']}' -> '{change['modified']}'")
    
    # ... 返回响应 ...
```

---

## 📝 实现建议

### 推荐实现路径

1. **第一步**：实现方案二（占位符值提取对比）
   - 添加数据库字段
   - 生成文档时保存原始数据
   - WPS保存时提取并对比

2. **第二步**：优化提取算法
   - 如果发现提取不准确，实现智能匹配算法
   - 或者实现方案三（添加标记）

3. **第三步**（可选）：添加方案一作为备用
   - 如果对比结果不准确，使用原始文档副本进行深度对比

### 注意事项

1. **性能考虑**：
   - 文档解析可能较慢，建议异步处理
   - 对于大文档，考虑分批处理

2. **准确性考虑**：
   - 占位符值提取可能不准确，特别是如果用户修改了格式
   - 建议提供手动确认机制

3. **存储考虑**：
   - 原始数据占用空间较小（JSON）
   - 原始文档副本占用空间较大，建议可选开启

4. **用户体验**：
   - 变更追踪不应影响保存速度
   - 建议异步处理，或提供进度提示

---

## 🔧 快速开始

### 1. 添加数据库字段

```python
# 创建迁移文件
python manage.py makemigrations case_management --name add_placeholder_tracking_fields
python manage.py migrate case_management
```

### 2. 修改文档生成逻辑

在 `placeholder_template_service.py` 中，生成文档后保存原始数据。

### 3. 实现变更追踪器

创建 `case_management/utils/placeholder_change_tracker.py`，实现追踪逻辑。

### 4. 集成到WPS保存流程

在 `wps_upload_commit` 或 `wps_save` 中调用追踪器。

---

## 📚 参考资料

- [WPS开放平台文档](https://solution.wps.cn/)
- [python-docx文档](https://python-docx.readthedocs.io/)
- [占位符解析器代码](./placeholder_parser.py)
- [占位符模板服务代码](./placeholder_template_service.py)

---

**文档版本**：v1.0  
**创建时间**：2025-01-XX  
**作者**：开发团队

