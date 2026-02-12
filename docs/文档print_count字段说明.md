# 文档 print_count 字段说明（修订版）

## 字段定义

### DocumentTemplate.print_count

- **类型**：整数（IntegerField）
- **默认值**：1
- **用途**：配置该模板对应的文书**默认需要打印的份数**
- **特性**：配置字段，除非用户手动修改，否则永久不变
- **示例**：起诉状默认打印3份、答辩状默认打印5份等

### CaseDocument.print_count

- **类型**：整数（IntegerField）
- **默认值**：1
- **用途**：记录文档**首次创建时**模板配置的默认打印份数
- **特性**：只在创建时设置一次，更新文档时**永不改变**
- **示例**：文档生成时，模板配置的是3份，则记录为3

## 核心逻辑

### ✅ 创建时：记录模板配置的打印份数

```python
# 模板配置
template = DocumentTemplate.objects.get(id=1)
template.print_count = 3  # 配置：该文书默认打印3份

# 首次生成文档
doc = CaseDocument.objects.create(
    template_id=template.id,
    print_count=template.print_count,  # ✅ 记录：3份
    ...
)
```

### ❌ 更新时：保持原值不变

```python
# 即使模板配置被修改
template.print_count = 5  # 管理员改成打印5份

# 重新生成同一文档（覆盖）
existing_doc.file_path = new_path
existing_doc.file_size = new_size
# ❌ 不修改 print_count，仍然保持首次创建时的 3
existing_doc.save()

# 结果：existing_doc.print_count 仍然是 3
```

## 完整示例

### 业务场景

```python
# 1. 管理员配置模板
template = DocumentTemplate.objects.get(template_name='起诉状')
template.print_count = 3  # 配置：起诉状默认打印3份
template.save()

# 2. 首次生成文档（2025-01-15）
doc = generate_document(case_id=50, template_id=template.id)
print(f"文档配置的打印份数: {doc.print_count}")  # 输出：3

# 3. 管理员修改模板配置（2025-06-20）
template.print_count = 5  # 改成打印5份
template.save()

# 4. 重新生成同一文档（覆盖，2025-10-30）
doc = generate_document(case_id=50, template_id=template.id)
print(f"文档配置的打印份数: {doc.print_count}")  # 输出：3（保持首次创建时的配置）
print(f"文档文件已更新: {doc.update_datetime}")  # 2025-10-30

# 5. 对比
print(f"文档的打印份数配置: {doc.print_count}")       # 3（首次创建时的配置）
print(f"模板当前的打印份数配置: {template.print_count}") # 5（当前配置）
```

## 字段含义对比

### 正确理解 ✅

| 字段 | 含义 | 更新时机 | 是否变化 |
|------|------|----------|----------|
| `DocumentTemplate.print_count` | 模板配置的默认打印份数 | 管理员手动修改 | 配置字段，除非手动修改否则不变 |
| `CaseDocument.print_count` | 文档首次创建时的打印份数配置 | 文档创建时记录一次 | 永久不变（历史快照） |

### 错误理解 ❌

| 字段 | ~~错误理解~~ |
|------|------------|
| `DocumentTemplate.print_count` | ~~模板被打印的总次数（统计值）~~ |
| `CaseDocument.print_count` | ~~文档被打印的次数（统计值）~~ |

**注意**：这两个字段都是**配置字段**，不是**统计字段**！

## 业务意义

### 1. 配置管理

模板管理员可以配置每个文书的默认打印份数：

```python
# 不同文书有不同的打印份数要求
templates = [
    {'name': '起诉状', 'print_count': 3},
    {'name': '答辩状', 'print_count': 5},
    {'name': '证据清单', 'print_count': 2},
    {'name': '送达回证', 'print_count': 10},
]

for t in templates:
    template = DocumentTemplate.objects.get(template_name=t['name'])
    template.print_count = t['print_count']
    template.save()
    print(f"{t['name']} 配置为打印 {t['print_count']} 份")
```

### 2. 历史追溯

可以看到文档生成时的打印份数配置：

```python
document = CaseDocument.objects.get(id=123)
template = document.template

print(f"文档生成时配置: {document.print_count} 份")
print(f"模板当前配置: {template.print_count} 份")

if document.print_count != template.print_count:
    print(f"⚠️ 配置已变更：{document.print_count} → {template.print_count}")
else:
    print("✅ 配置未变")
```

### 3. 打印提示

在打印文档时，可以提示用户默认打印份数：

```python
document = CaseDocument.objects.get(id=123)
print(f"建议打印份数: {document.print_count} 份")

# 前端显示
# 打印文档
# 默认份数: [3] ← 显示 document.print_count
# [打印] [取消]
```

### 4. 批量打印

批量打印时自动计算总份数：

```python
documents = CaseDocument.objects.filter(case_id=50)
total_copies = sum(doc.print_count for doc in documents)
print(f"本案件所有文书共需打印: {total_copies} 份")

# 示例输出：
# 起诉状: 3份
# 答辩状: 5份
# 证据清单: 2份
# 总计: 10份
```

## 代码实现

### 模型定义

```python
class DocumentTemplate(CoreModel, SoftDeleteModel):
    template_name = models.CharField(max_length=255, verbose_name="模板名称")
    print_count = models.IntegerField(
        default=1, 
        verbose_name="默认打印份数", 
        help_text="该文书默认需要打印的份数（如3份、5份等）"
    )
    # ... 其他字段

class CaseDocument(CoreModel, SoftDeleteModel):
    document_name = models.CharField(max_length=255, verbose_name="文档名称")
    template_id = models.IntegerField(verbose_name="模板ID")
    print_count = models.IntegerField(
        default=1,
        verbose_name="默认打印份数",
        help_text="该文档的默认打印份数（从模板继承）"
    )
    # ... 其他字段
```

### 生成文档时的逻辑

```python
def fill_and_save_by_record(self, case_id, template_record, data, request=None):
    # 获取模板配置的默认打印份数
    template_print_count = getattr(template_record, 'print_count', 1)
    
    # 创建文档时记录
    doc = CaseDocument.objects.create(
        case_id=case_id,
        template_id=template_record.id,
        print_count=template_print_count,  # ✅ 记录模板配置的打印份数
        ...
    )
    return doc
```

### 更新文档时的逻辑

```python
def save_docx_document(self, case_id, ..., template_print_count=1):
    # 查找已存在的文档
    existing_doc = CaseDocument.objects.filter(
        case_id=case_id,
        template_id=template_id
    ).first()
    
    if existing_doc:
        # ❌ 更新时不修改 print_count
        existing_doc.file_path = new_path
        existing_doc.file_size = new_size
        # print_count 保持不变
        existing_doc.save()
        
        logger.info(f"文档已更新，print_count保持={existing_doc.print_count}")
    else:
        # ✅ 创建时记录
        doc = CaseDocument.objects.create(
            print_count=template_print_count,
            ...
        )
        logger.info(f"文档已创建，print_count={doc.print_count}")
```

## 数据库示例

### 场景演示

```sql
-- 1. 初始配置
-- document_template: id=1, template_name='起诉状', print_count=3
-- case_document: 无记录

-- 2. 首次生成文档（2025-01-15）
INSERT INTO case_document (
    case_id, template_id, document_name, print_count, create_datetime
) VALUES (
    50, 1, '起诉状.docx', 3, '2025-01-15 10:00:00'  -- ✅ 记录配置：3份
);

-- 3. 管理员修改模板配置（2025-06-20）
UPDATE document_template 
SET print_count = 5  -- 改成5份
WHERE id = 1;

-- 4. 重新生成文档（覆盖，2025-10-30）
UPDATE case_document 
SET 
    file_path = 'new_path.docx',
    file_size = 12345,
    update_datetime = '2025-10-30 16:00:00'
    -- ❌ 不修改 print_count，仍然是 3
WHERE case_id = 50 AND template_id = 1;

-- 5. 查询结果
SELECT 
    cd.document_name,
    cd.print_count as doc_print_copies,        -- 3（首次创建时的配置）
    dt.print_count as template_print_copies,   -- 5（当前配置）
    cd.create_datetime,
    cd.update_datetime
FROM case_document cd
JOIN document_template dt ON cd.template_id = dt.id
WHERE cd.id = 123;

-- 结果：
-- document_name | doc_print_copies | template_print_copies | create_datetime | update_datetime
-- 起诉状.docx   | 3                | 5                     | 2025-01-15      | 2025-10-30
```

## API 使用示例

### 1. 配置模板打印份数

```http
PATCH /api/templates/1/
Content-Type: application/json

{
    "print_count": 5
}
```

### 2. 查询文档打印配置

```http
GET /api/documents/123/
```

```json
{
    "id": 123,
    "document_name": "起诉状.docx",
    "template_id": 1,
    "print_count": 3,
    "create_datetime": "2025-01-15 10:00:00",
    "update_datetime": "2025-10-30 16:00:00",
    "template_info": {
        "template_name": "起诉状",
        "current_print_count": 5,
        "config_changed": true
    }
}
```

### 3. 批量打印

```http
POST /api/cases/50/batch_print/
```

```json
{
    "documents": [
        {"id": 123, "name": "起诉状.docx", "print_count": 3},
        {"id": 124, "name": "答辩状.docx", "print_count": 5},
        {"id": 125, "name": "证据清单.docx", "print_count": 2}
    ],
    "total_copies": 10
}
```

## 常见问题

### Q1: 为什么要记录文档的 print_count？

**A:** 因为模板的配置可能会变化。记录文档生成时的配置，可以：
- 追溯历史：知道当时配置是多少
- 保持一致：避免因配置变化导致混乱
- 提示用户：打印时显示当时的默认份数

### Q2: 如果想修改文档的打印份数怎么办？

**A:** 有两种方式：
1. **手动修改单个文档**：直接更新 `case_document.print_count`
2. **修改模板配置后重新生成**：删除文档后重新生成（会使用新配置）

```python
# 方式1：手动修改
doc = CaseDocument.objects.get(id=123)
doc.print_count = 5  # 改成5份
doc.save()

# 方式2：删除后重新生成
CaseDocument.objects.filter(id=123).delete()  # 软删除
generate_document(case_id=50, template_id=1)  # 重新生成，使用新配置
```

### Q3: print_count 是否支持不同用户有不同配置？

**A:** 当前实现中，`print_count` 是模板级别的配置，所有用户共享。如果需要用户级别的配置，可以扩展：

```python
# 可以在生成文档时允许用户指定
def generate_document(case_id, template_id, custom_print_count=None):
    template = DocumentTemplate.objects.get(id=template_id)
    
    # 优先使用用户指定的，否则使用模板配置
    print_count = custom_print_count or template.print_count
    
    doc = CaseDocument.objects.create(
        print_count=print_count,
        ...
    )
```

## 注意事项

1. **这是配置字段，不是统计字段**
   - 不会自动累加
   - 需要手动配置
   - 除非用户修改，否则不变

2. **文档的 print_count 永久不变**
   - 首次创建时记录
   - 更新文档时保持不变
   - 除非手动修改

3. **默认值建议**
   - 模板：`default=1`（至少打印1份）
   - 文档：继承模板的配置

4. **业务用途**
   - 打印提示
   - 批量打印计算
   - 配置管理
   - 历史追溯

## 相关文档

- [模型字段新增说明.md](./模型字段新增说明.md)
- [文档生成时同步模板打印次数说明.md](./文档生成时同步模板打印次数说明.md)
