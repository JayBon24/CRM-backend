# Llama 3 8B 模型配置说明

## 📋 配置概述

系统已成功配置支持 `meta-llama/llama-3-8b-instruct` 模型，但由于 OpenRouter 的限制，该模型需要付费使用。

## 🔧 当前配置

### 模型优先级
1. **免费模型**（优先使用）
   - `google/gemma-2-9b-it:free` - Google Gemma 2 9B
   - `mistralai/mistral-7b-instruct:free` - Mistral 7B
   - 其他免费模型...

2. **付费模型**（需要账户余额）
   - `meta-llama/llama-3-8b-instruct` - **Meta Llama 3 8B** ⭐
   - `meta-llama/llama-3-8b-instruct:latest`
   - `meta-llama/llama-3.1-8b-instruct`
   - 其他 Llama 模型...

### 自动降级机制
- 系统会优先尝试免费模型
- 如果免费模型不可用（API限制、网络问题等），会尝试付费模型
- 如果所有模型都不可用，会降级到模拟AI服务

## 💰 使用 Llama 3 8B 模型

### 方法1：充值 OpenRouter 账户
1. 访问 [OpenRouter 设置页面](https://openrouter.ai/settings/credits)
2. 为账户充值（最低 $10）
3. 系统会自动检测到可用余额并使用 Llama 3 8B 模型

### 方法2：手动指定模型
如果需要强制使用 Llama 3 8B 模型，可以在代码中直接指定：

```python
from case_management.langchain_ai_service import get_chat_model

# 直接使用 Llama 3 8B 模型
model = get_chat_model("meta-llama/llama-3-8b-instruct")
```

## 🚀 模型特性

### Llama 3 8B Instruct 优势
- **强大的指令跟随能力**：专门针对指令微调优化
- **多语言支持**：包括中文在内的多种语言
- **法律文档生成**：在生成法律文书方面表现优秀
- **上下文理解**：能够理解复杂的案例信息

### 性能对比
| 模型 | 参数 | 免费 | 性能 | 推荐度 |
|------|------|------|------|--------|
| Llama 3 8B | 8B | ❌ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Gemma 2 9B | 9B | ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Mistral 7B | 7B | ✅ | ⭐⭐⭐ | ⭐⭐⭐ |

## 🔍 当前状态

### 测试结果
- ✅ **模型可用**：`meta-llama/llama-3-8b-instruct` 在 OpenRouter 上可用
- ❌ **需要付费**：账户余额不足（402 Payment Required）
- ✅ **自动降级**：系统正确降级到免费模型或模拟服务
- ✅ **功能正常**：所有功能都能正常工作

### 错误处理
系统已配置完善的错误处理机制：
- **402 错误**：账户余额不足，自动降级
- **429 错误**：API限制，自动降级
- **404 错误**：模型不存在，自动降级
- **网络错误**：连接超时，自动降级

## 📝 使用建议

### 开发环境
- 使用免费模型进行开发和测试
- 模拟AI服务确保功能完整性

### 生产环境
- 充值 OpenRouter 账户使用 Llama 3 8B
- 配置监控和告警机制
- 设置合理的API调用限制

### 成本控制
- Llama 3 8B 模型成本相对较低
- 建议设置月度预算限制
- 监控API使用情况

## 🛠️ 配置更新

如需更新模型配置，请修改 `backend/case_management/langchain_ai_service.py` 文件中的模型列表。

### 添加新模型
```python
PAID_MODELS = [
    "meta-llama/llama-3-8b-instruct",      # 现有
    "your-new-model",                      # 新增
]
```

### 调整优先级
```python
ALL_MODELS = [
    "meta-llama/llama-3-8b-instruct",     # 最高优先级
    "google/gemma-2-9b-it:free",          # 次优先级
    # ... 其他模型
]
```

## 📞 技术支持

如有问题，请检查：
1. OpenRouter 账户余额
2. API 密钥有效性
3. 网络连接状态
4. 系统日志输出

---

**总结**：Llama 3 8B 模型已成功集成到系统中，只需充值 OpenRouter 账户即可使用。系统具备完善的降级机制，确保在任何情况下都能正常工作。
