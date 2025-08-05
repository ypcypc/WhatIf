# WhatIf 项目使用指南

## 🚀 快速开始

### 1. 配置 API 密钥

编辑项目根目录的 `llm_config.json` 文件：

```json
{
  "api_keys": {
    "openai_api_key": "sk-你的-OpenAI-密钥",
    "google_api_key": "你的-Google-API-密钥",
    "anthropic_api_key": "你的-Anthropic-密钥"
  },
  "llm_settings": {
    "default_provider": "gemini",
    "default_model": "gemini-2.5-pro"
  }
}
```

### 2. 安装依赖

```bash
cd backend_services
poetry install
```

### 3. 启动应用

```bash
# 启动后端
cd backend_services
uvicorn app.main:app --reload --port 8000

# 启动前端
cd ..
npm run dev
```

## 🔧 配置选项

### 支持的 LLM 提供商

- **OpenAI**: `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`, `o4-mini`
- **Google Gemini**: `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-1.5-pro`

### 环境变量优先级

1. 环境变量 (最高优先级)
2. `llm_config.json` 配置文件
3. 默认设置

### API 密钥配置

您可以通过以下方式配置 API 密钥：

**方法 1: 编辑配置文件 (推荐)**
```json
{
  "api_keys": {
    "openai_api_key": "你的密钥",
    "google_api_key": "你的密钥"
  }
}
```

**方法 2: 环境变量**
```bash
export OPENAI_API_KEY="你的密钥"
export GOOGLE_API_KEY="你的密钥"
export LLM_PROVIDER="gemini"
export LLM_MODEL="gemini-2.5-pro"
```

## 🧪 测试

运行统一 LLM 系统测试：

```bash
cd backend_services
python test_unified_llm.py
```

## 📊 技术架构

### 统一 LLM 架构

- **UnifiedLLMRepository**: 统一的 LLM 仓库接口
- **Provider System**: 可插拔的 LLM 提供商系统
- **Configuration Management**: 统一配置管理
- **Backward Compatibility**: 保持与旧代码的兼容性

### 重构亮点

1. **统一配置管理**: 所有配置集中在 `llm_config.json`
2. **提供商抽象**: 轻松切换不同的 LLM 提供商
3. **代码简化**: 合并 `unified_repository.py` 到 `repositories.py`
4. **向后兼容**: 保持现有代码工作正常

## 🔒 安全注意事项

- `llm_config.json` 已添加到 `.gitignore`
- 使用 `llm_config.example.json` 作为模板
- 永远不要将真实密钥提交到代码库

## 📈 性能特性

- **动态温度调节**: 基于偏离度自动调整创造性
- **内存管理**: 智能摘要和上下文管理
- **缓存机制**: 减少重复 API 调用
- **错误恢复**: 智能降级和重试机制

---

*WhatIf - AI 驱动的交互式游戏系统*