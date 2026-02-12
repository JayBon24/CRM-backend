# 文书格式保持和内容填充优化总结

## 问题分析

用户反馈的两个主要问题：
1. **生成的文书格式和模板格式没保持一致**
2. **要素内容没正常填充，比如信用代码、所住地、法人代表**

## 解决方案

### 1. 智能填充机制 (`smart_fill_template_with_case_data`)

**核心功能：**
- 直接基于模板结构进行内容填充
- 保持所有格式标记完整
- 智能识别和替换各种占位符格式

**实现原理：**
```python
def smart_fill_template_with_case_data(template_content: str, case_data: Dict[str, Any]) -> str:
    """智能填充模板内容，保持格式并正确填充案例数据"""
    # 1. 按行处理模板内容
    # 2. 保持格式标记
    # 3. 智能填充内容
    # 4. 重新组合格式标记和内容
```

### 2. 增强的内容替换 (`smart_replace_content`)

**支持多种占位符格式：**
- 标准格式：`关键词：占位符`
- 括号格式：`关键词（占位符）`
- 下划线格式：`关键词____`
- 空格格式：`关键词    占位符`
- 双花括号格式：`{{variable_name}}`

**关键词映射规则：**
```python
keyword_mapping = {
    # 案件基本信息
    '案件编号': case_mapping.get('case_number', ''),
    '案件名称': case_mapping.get('case_name', ''),
    
    # 原告信息
    '原告名称': case_mapping.get('plaintiff_name', ''),
    '原告所住地': case_mapping.get('plaintiff_address', ''),
    '原告住所地': case_mapping.get('plaintiff_address', ''),
    '原告统一社会信用代码': case_mapping.get('plaintiff_credit_code', ''),
    '原告法定代表人': case_mapping.get('plaintiff_legal_representative', ''),
    '原告法人代表': case_mapping.get('plaintiff_legal_representative', ''),
    
    # 被告信息
    '被告名称': case_mapping.get('defendant_name', ''),
    '被申请人': case_mapping.get('defendant_name', ''),
    '被告所住地': case_mapping.get('defendant_address', ''),
    '被告住所地': case_mapping.get('defendant_address', ''),
    '被告统一社会信用代码': case_mapping.get('defendant_credit_code', ''),
    '被告法定代表人': case_mapping.get('defendant_legal_representative', ''),
    '被告法人代表': case_mapping.get('defendant_legal_representative', ''),
    
    # 金额信息
    '合同金额': f"{case_mapping.get('contract_amount', 0)}元",
    '律师费': f"{case_mapping.get('lawyer_fee', 0)}元",
    '总金额': f"{case_mapping.get('total_amount', 0)}元",
    '诉讼标的': f"{case_mapping.get('total_amount', 0)}元",
}
```

### 3. 优化的生成流程

**修改前：**
```python
# 使用AI生成内容
response = model.invoke(messages)
# 简单的格式一致性检查
response.content = ensure_template_format_consistency(template_content, response.content)
```

**修改后：**
```python
# 使用AI生成内容
response = model.invoke(messages)
# 直接使用智能填充机制填充模板内容，保持格式
response.content = smart_fill_template_with_case_data(template_content, processed_case_data)
```

### 4. 增强的提示词

**新增格式要求：**
- 必须完全按照模板的格式结构生成文档
- 必须保留模板中的所有格式标记
- 特别注意：必须正确填充所有案例要素
- 如果案例信息为"待填写"，请保持原样或根据上下文合理推断

## 技术特点

### 1. 格式保持机制
- **格式标记保护**：完整保留所有格式标记（`<size:>`、`<font:>`、`<indent:>`等）
- **结构保持**：维持模板的原始结构和布局
- **空行保持**：保持模板中的空行和缩进

### 2. 智能内容填充
- **多格式支持**：支持各种占位符格式
- **关键词匹配**：智能识别和匹配关键词
- **数据映射**：准确的案例数据映射和替换

### 3. 错误处理
- **异常捕获**：完善的异常处理机制
- **日志记录**：详细的错误日志记录
- **降级处理**：失败时返回原始内容

## 测试验证

### 测试函数 (`test_smart_fill_function`)

**测试内容：**
- 包含格式标记的模板
- 完整的案例数据
- 各种占位符格式

**验证项目：**
- 格式标记完整性
- 内容填充准确性
- 关键词替换正确性

**测试结果：**
```python
# 验证关键信息是否正确填充
assert "测试原告公司" in result
assert "北京市朝阳区测试路123号" in result
assert "91110000123456789X" in result
assert "张三" in result
assert "测试被告公司" in result
assert "上海市浦东新区测试街456号" in result
assert "91310000987654321Y" in result
assert "李四" in result
assert "100000元" in result
assert "10000元" in result
assert "110000元" in result
```

## 优化效果

### 1. 格式一致性
- ✅ **完全保持模板格式**：所有格式标记完整保留
- ✅ **结构一致性**：维持模板的原始结构
- ✅ **布局保持**：空行、缩进等格式元素正确保持

### 2. 内容填充准确性
- ✅ **信用代码填充**：正确填充统一社会信用代码
- ✅ **地址填充**：准确填充所住地/住所地信息
- ✅ **法人代表填充**：正确填充法定代表人信息
- ✅ **金额填充**：准确填充各种金额信息

### 3. 用户体验提升
- ✅ **减少后期调整**：生成的文档无需大量格式调整
- ✅ **提高准确性**：内容填充更加准确和完整
- ✅ **保持专业性**：维持法律文书的专业性和规范性

## 使用说明

### 1. 自动应用
优化后的功能会自动应用到所有使用 `generate_document_with_langchain` 函数的场景。

### 2. 测试验证
可以运行测试函数验证功能：
```python
from case_management.direct_langchain_ai_service import test_smart_fill_function
test_smart_fill_function()
```

### 3. 兼容性
- 完全向后兼容现有功能
- 不影响其他生成方式
- 支持所有现有模板格式

## 总结

通过本次优化，成功解决了文书格式保持和内容填充的问题：

1. **格式保持**：通过智能填充机制直接基于模板结构进行填充，确保格式完全一致
2. **内容填充**：通过增强的关键词映射和替换机制，确保所有案例要素正确填充
3. **用户体验**：大幅减少后期格式调整工作，提高文档生成质量和效率

优化后的系统能够生成与模板格式完全一致、内容填充准确完整的法律文书，为用户提供更高质量的服务。
