# 智能文档填充功能使用说明

## 功能概述

智能文档填充功能基于现有的人工录入生成文书功能进行优化，实现了以下核心功能：

1. **文档转换器** - 将Word模板转换为带格式的Markdown/XML
2. **智能填充服务** - 使用DeepSeek大模型智能填充内容
3. **文档重建器** - 将填充后的内容重新生成为Word文档
4. **主控制器** - 整合所有功能模块
5. **API接口** - 为前端提供调用接口

## 核心特性

### 1. 无占位符依赖
- 不需要在模板中预设占位符
- AI智能识别填充位置
- 自动理解文档结构和上下文

### 2. 格式保持
- 通过Markdown/XML转换保持原有格式
- 保留字体、段落、表格等格式信息
- 支持复杂文档结构

### 3. 智能理解
- 大模型理解文档结构和上下文
- 智能匹配案例要素信息
- 自动填充相关内容

### 4. 灵活扩展
- 支持多种文档格式和结构
- 易于维护和扩展
- 模板修改简单

## 文件结构

```
backend/case_management/
├── document_converter.py      # 文档转换器模块
├── intelligent_filler.py      # 智能填充服务模块
├── document_rebuilder.py      # 文档重建器模块
├── smart_document_filler.py   # 主控制器模块
├── views.py                   # API接口（已优化）
└── SMART_DOCUMENT_FILLER_README.md  # 使用说明
```

## 使用方法

### 1. 后端API调用

#### 智能填充单个文档
```python
from case_management.smart_document_filler import smart_fill_document

# 填充单个文档
result = smart_fill_document(
    template_path="backend/template/起诉状.docx",
    case_data={
        "案件编号": "2024民初1234号",
        "案件名称": "张三诉李四合同纠纷案",
        "原告名称": "张三",
        "被告名称": "李四",
        # ... 其他案例信息
    },
    output_path="output/起诉状_填充版.docx",
    use_xml=False  # 使用Markdown格式
)
```

#### 智能填充所有模板
```python
from case_management.smart_document_filler import smart_fill_all_templates

# 填充所有模板
result = smart_fill_all_templates(
    case_data={
        "案件编号": "2024民初1234号",
        "案件名称": "张三诉李四合同纠纷案",
        # ... 其他案例信息
    },
    output_dir="smart_output"
)
```

#### 智能生成文档
```python
from case_management.smart_document_filler import generate_smart_documents

# 智能生成文档（结合AI生成和模板填充）
result = generate_smart_documents(
    case_data={
        "案件编号": "2024民初1234号",
        "案件名称": "张三诉李四合同纠纷案",
        # ... 其他案例信息
    },
    output_dir="smart_output"
)
```

### 2. 前端API调用

#### 智能填充所有模板
```javascript
// 调用智能填充所有模板API
const response = await caseApi.smartFillAllTemplates(caseId, {
  output_dir: 'smart_output'
})
```

#### 智能生成文档
```javascript
// 调用智能生成文档API
const response = await caseApi.generateSmartDocuments(caseId, {
  output_dir: 'smart_output'
})
```

#### 智能填充单个文档
```javascript
// 调用智能填充单个文档API
const response = await caseApi.smartFillDocument(caseId, {
  template_path: 'backend/template/起诉状.docx',
  output_path: 'output/起诉状_填充版.docx',
  use_xml: false
})
```

## 工作流程

### 1. 文档转换流程
```
Word模板 → 文档转换器 → 结构化Markdown/XML → 保留格式信息
```

### 2. 智能填充流程
```
结构化内容 + 案例要素 → DeepSeek大模型 → 智能填充内容
```

### 3. 文档重建流程
```
填充后内容 → 文档重建器 → Word文档 → 保持原有格式
```

## 配置要求

### 1. 环境依赖
```bash
pip install python-docx lxml requests
```

### 2. DeepSeek API配置
确保在环境变量中设置DeepSeek API密钥：
```bash
export DEEPSEEK_API_KEY=your-deepseek-api-key
```

### 3. 模板文件
将Word模板文件放置在 `backend/template/` 目录下。

## 功能优势

### 1. 相比传统占位符方式
- **无需预设占位符** - 模板制作更简单
- **智能理解上下文** - 填充更准确
- **格式保持更好** - 减少格式丢失

### 2. 相比纯AI生成
- **基于真实模板** - 更符合实际需求
- **格式更规范** - 保持法律文书标准
- **可定制性强** - 支持自定义模板

### 3. 相比人工录入
- **效率更高** - 自动化处理
- **错误更少** - AI智能匹配
- **一致性更好** - 标准化处理

## 注意事项

### 1. 模板要求
- 使用Word格式（.docx或.doc）
- 保持清晰的文档结构
- 避免过于复杂的格式

### 2. 案例数据
- 确保案例信息完整
- 字段名称要规范
- 数值类型要正确

### 3. 性能考虑
- 大文档处理时间较长
- 建议分批处理
- 注意API调用限制

## 错误处理

### 1. 常见错误
- **模板文件不存在** - 检查文件路径
- **API调用失败** - 检查网络和密钥
- **格式转换错误** - 检查模板格式

### 2. 调试方法
- 查看日志输出
- 检查中间文件
- 验证案例数据

## 扩展开发

### 1. 添加新的文档类型
在 `document_converter.py` 中添加新的转换逻辑。

### 2. 优化填充算法
在 `intelligent_filler.py` 中调整提示词和填充逻辑。

### 3. 支持更多格式
在 `document_rebuilder.py` 中添加新的重建逻辑。

## 技术支持

如有问题，请检查：
1. 日志文件中的错误信息
2. API调用是否成功
3. 模板文件是否完整
4. 案例数据是否正确

## 更新日志

- **v1.0.0** - 初始版本，实现基础智能填充功能
- **v1.1.0** - 优化格式保持，支持复杂文档结构
- **v1.2.0** - 添加批量处理功能，提升处理效率
