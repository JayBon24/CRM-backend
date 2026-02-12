# AI服务配置说明

## 概述

本系统已集成LangChain和OpenRouter，支持多种AI模型调用方式。系统采用优先级降级策略：

1. **LangChain + OpenRouter** (最高优先级)
2. **DeepSeek API** (中等优先级)  
3. **模拟AI服务** (最低优先级，兜底方案)

## 配置方式

### 1. LangChain + OpenRouter 配置

OpenRouter API密钥请通过环境变量配置：
```
API Key: your-openrouter-api-key
Base URL: https://openrouter.ai/api/v1
```

**免费模型支持**：
- ✅ **google/gemma-2-9b-it:free** (推荐，已测试可用)
- ✅ **mistralai/mistral-7b-instruct:free** (备选，已测试可用)
- ❌ meta-llama/llama-3.1-8b-instruct:free (不可用)
- ❌ meta-llama/llama-3.1-70b-instruct:free (不可用)
- ❌ microsoft/phi-3-mini-128k-instruct:free (不可用)
- ❌ huggingface/zephyr-7b-beta:free (不可用)

**系统会自动选择最佳可用的免费模型**，无需手动配置。

### 2. DeepSeek API 配置

在环境变量中设置：
```bash
export DEEPSEEK_API_KEY="your-deepseek-api-key"
```

### 3. 模拟AI服务

当所有真实AI服务都不可用时，系统会自动使用模拟AI服务，确保功能正常运行。

## 功能特性

### 1. 文档生成
- 支持生成11种法律文书
- 使用案例数据填充模板
- 支持批量生成和单个生成
- **使用免费AI模型，无需付费**

### 2. AI对话
- 支持法律问题咨询
- 支持文档上传和分析
- 智能触发文书生成
- **基于Google Gemma 2和Mistral 7B模型**

### 3. 智能模型选择
- 自动测试多个免费模型
- 选择最佳可用模型
- 支持模型降级和切换

### 4. 错误处理
- 自动降级机制
- 详细的错误日志
- 用户友好的错误提示

## 使用说明

### 1. 启用真实AI服务

要使用真实的AI服务，需要：

1. **OpenRouter方式**：
   - 访问 https://openrouter.ai/settings/credits
   - 充值账户余额
   - 系统将自动使用LangChain + OpenRouter

2. **DeepSeek方式**：
   - 获取DeepSeek API密钥
   - 设置环境变量 `DEEPSEEK_API_KEY`
   - 系统将使用DeepSeek API

### 2. 测试AI服务

运行测试脚本验证配置：
```bash
cd backend
python -c "
from case_management.langchain_ai_service import test_langchain_connection
print('LangChain连接测试:', test_langchain_connection())
"
```

## 技术架构

### 1. LangChain集成
- 使用 `langchain-openai` 包
- 支持多种模型切换
- 统一的提示词管理

### 2. 降级策略
```python
# 优先级顺序
if LANGCHAIN_AI_AVAILABLE:
    # 尝试LangChain + OpenRouter
elif DEEPSEEK_API_AVAILABLE:
    # 尝试DeepSeek API
else:
    # 使用模拟AI服务
```

### 3. 错误处理
- 网络错误自动重试
- API限制错误处理
- 账户余额不足处理

## 注意事项

1. **API密钥安全**：请妥善保管API密钥，不要提交到版本控制系统
2. **费用控制**：建议设置API使用限制，避免意外费用
3. **模型选择**：可以根据需要切换不同的AI模型
4. **日志监控**：建议监控AI服务调用日志，及时发现问题

## 故障排除

### 1. 402 Payment Required
- 检查OpenRouter账户余额
- 确认API密钥正确

### 2. 404 Not Found
- 检查模型名称是否正确
- 确认API端点可用

### 3. 网络超时
- 检查网络连接
- 调整超时设置

### 4. 降级到模拟服务
- 检查所有AI服务配置
- 查看错误日志确定原因
