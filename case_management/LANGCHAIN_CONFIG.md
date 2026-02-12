# LangChain 直接调用配置说明

## 📋 配置概述

系统已配置为直接使用 LangChain 调用各种大模型，不再依赖 OpenRouter。支持多种模型提供商和本地模型。

## 🔧 支持的模型

### 1. OpenAI 模型
- **gpt-3.5-turbo** - 推荐，性价比高
- **gpt-4** - 高质量，成本较高
- **gpt-4-turbo** - 最新版本，性能最佳

### 2. Google 模型
- **gemini-pro** - 免费，推荐
- **gemini-1.5-pro** - 高质量，免费

### 3. Anthropic 模型
- **claude-3-sonnet** - 平衡性能和成本
- **claude-3-opus** - 最高质量

### 4. Ollama 本地模型
- **llama3** - 本地运行，免费
- **llama2** - 本地运行，免费
- **qwen** - 中文优化，本地运行

## 🚀 快速开始

### 方法1：使用 Google Gemini（推荐，免费）

1. 获取 Google API 密钥：
   - 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
   - 创建 API 密钥

2. 设置环境变量：
   ```bash
   export GOOGLE_API_KEY="your_google_api_key_here"
   ```

3. 安装依赖：
   ```bash
   pip install langchain-google-genai
   ```

### 方法2：使用 OpenAI（需要付费）

1. 获取 OpenAI API 密钥：
   - 访问 [OpenAI Platform](https://platform.openai.com/api-keys)
   - 创建 API 密钥

2. 设置环境变量：
   ```bash
   export OPENAI_API_KEY="your_openai_api_key_here"
   ```

3. 安装依赖：
   ```bash
   pip install langchain-openai
   ```

### 方法3：使用 Ollama 本地模型（完全免费）

1. 安装 Ollama：
   - 访问 [Ollama 官网](https://ollama.ai/)
   - 下载并安装

2. 下载模型：
   ```bash
   ollama pull llama3
   ollama pull qwen
   ```

3. 安装依赖：
   ```bash
   pip install langchain-community
   ```

## 📝 环境变量配置

创建 `.env` 文件或设置环境变量：

```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Google
GOOGLE_API_KEY=your_google_api_key_here

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## 🔧 模型优先级

系统按以下优先级选择模型：

1. **gpt-3.5-turbo** - OpenAI GPT-3.5
2. **gemini-pro** - Google Gemini Pro（免费）
3. **claude-3-sonnet** - Anthropic Claude 3
4. **llama3** - Ollama Llama 3（本地）
5. **gpt-4** - OpenAI GPT-4
6. **claude-3-opus** - Anthropic Claude 3 Opus
7. **llama2** - Ollama Llama 2（本地）
8. **qwen** - Ollama Qwen（本地）

## 💰 成本对比

| 模型 | 类型 | 成本 | 质量 | 推荐度 |
|------|------|------|------|--------|
| gemini-pro | 免费 | 免费 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| gpt-3.5-turbo | 付费 | 低 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| llama3 | 本地 | 免费 | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| gpt-4 | 付费 | 高 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| claude-3-sonnet | 付费 | 中 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

## 🛠️ 手动指定模型

```python
from case_management.direct_langchain_ai_service import get_chat_model

# 使用特定模型
model = get_chat_model("gemini-pro")  # Google Gemini
model = get_chat_model("gpt-3.5-turbo")  # OpenAI
model = get_chat_model("llama3")  # Ollama 本地
```

## 📊 测试和验证

运行测试脚本验证配置：

```bash
python test_direct_langchain.py
```

## 🔍 故障排除

### 常见问题

1. **API密钥未设置**
   - 错误：`请设置环境变量 OPENAI_API_KEY`
   - 解决：设置相应的环境变量

2. **依赖未安装**
   - 错误：`模型 xxx 不可用，请安装相应的依赖`
   - 解决：安装对应的 LangChain 包

3. **Ollama 未运行**
   - 错误：`连接被拒绝`
   - 解决：启动 Ollama 服务

### 安装所有依赖

```bash
pip install langchain-openai langchain-google-genai langchain-anthropic langchain-community
```

## 📈 性能优化

### 1. 本地模型优化
- 使用 GPU 加速
- 调整模型参数
- 优化内存使用

### 2. 云模型优化
- 设置合理的超时时间
- 使用缓存机制
- 批量处理请求

## 🔒 安全建议

1. **API密钥安全**
   - 不要在代码中硬编码密钥
   - 使用环境变量或密钥管理服务
   - 定期轮换密钥

2. **本地模型安全**
   - 确保 Ollama 服务安全
   - 限制网络访问
   - 定期更新模型

## 📞 技术支持

如有问题，请检查：
1. API密钥是否正确设置
2. 依赖包是否正确安装
3. 网络连接是否正常
4. 模型服务是否运行

---

**总结**：直接使用 LangChain 调用大模型提供了更大的灵活性和更好的成本控制。推荐使用 Google Gemini Pro 作为免费选项，或 Ollama 本地模型作为完全免费的解决方案。
