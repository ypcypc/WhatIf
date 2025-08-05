# 统一 LLM 提供商系统使用指南

## 🎯 概述

WhatIf 项目现在支持统一的 LLM 提供商系统，可以无缝切换使用不同的 AI 模型：
- **OpenAI**: GPT-4, GPT-4o, GPT-4o-mini, o4-mini
- **Google Gemini**: Gemini 2.5 Pro, Gemini 2.5 Flash
- **可扩展架构**: 轻松添加更多提供商

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend_services
poetry install
```

这会自动安装包含 Gemini 支持的所有依赖：
- `langchain-google-genai = "^2.1.8"`
- `google-genai = "^1.0.0"`

### 2. 配置 API 密钥

**选项 A: 使用环境变量**
```bash
# 安全推荐：创建 api_keys.env 文件
cp api_keys.env.example api_keys.env

# 编辑 api_keys.env 添加您的密钥
export GOOGLE_API_KEY="您的-Google-API-密钥"
export OPENAI_API_KEY="您的-OpenAI-API-密钥"

# 加载环境变量
source api_keys.env
```

**选项 B: 直接设置环境变量**
```bash
export GOOGLE_API_KEY="您的-Google-API-密钥"
export LLM_PROVIDER="gemini"
export LLM_MODEL="gemini-2.5-pro"
```

### 3. 启动应用

```bash
# 启动后端
uvicorn app.main:app --reload --port 8000

# 启动前端
cd ..
npm run dev
```

## 🔧 配置选项

### 环境变量

| 变量名 | 默认值 | 说明 |
|-------|-------|------|
| `LLM_PROVIDER` | `"openai"` | 使用的 LLM 提供商 (`openai`, `gemini`) |
| `LLM_MODEL` | `"gpt-4o-mini"` | 具体的模型名称 |
| `GOOGLE_API_KEY` | - | Google Gemini API 密钥 |
| `OPENAI_API_KEY` | - | OpenAI API 密钥 |

### 支持的模型

#### OpenAI 模型
- `gpt-4o-mini` (推荐，性价比高)
- `gpt-4o` (最新功能)
- `gpt-4-turbo` (平衡性能)
- `o4-mini` (推理专用)

#### Gemini 模型
- `gemini-2.5-pro` (推荐，最新版本)
- `gemini-2.5-flash` (速度优化)
- `gemini-1.5-pro` (稳定版本)
- `gemini-1.5-flash` (快速版本)

## 🔄 运行时切换

### 通过 API 切换 (开发中)
```python
# 在运行时切换到 Gemini
POST /api/v1/llm/switch-provider
{
    "provider": "gemini",
    "model": "gemini-2.5-pro"
}
```

### 通过代码切换
```python
from app.services.llm_service.providers import switch_provider

# 切换到 Gemini 2.5 Pro
provider = switch_provider("gemini", "gemini-2.5-pro")

# 切换回 OpenAI
provider = switch_provider("openai", "gpt-4o-mini")
```

## 🧪 测试验证

### 运行测试脚本
```bash
cd backend_services
python test_unified_llm.py
```

这会测试：
- ✅ 提供商工厂功能
- ✅ 多个提供商创建
- ✅ 统一仓库操作
- ✅ 文本生成测试
- ✅ 摘要生成测试

### 预期输出
```
🧪 Unified LLM Provider System Test
============================================================
OpenAI API Key: ✅
Gemini API Key: ✅

🏭 Testing LLM Provider Factory
==================================================
Available providers:
  - openai: gpt-4o-mini (Available: True)
  - gemini: gemini-2.5-pro (Available: True)

🔧 Testing Provider Creation
==================================================
✅ OpenAI provider created: gpt-4o-mini
   Health: healthy
✅ Gemini provider created: gemini-2.5-pro
   Health: healthy

🗃️ Testing Unified Repository
==================================================
✅ Repository created with provider: gemini
   Current provider: gemini
   Current model: gemini-2.5-pro
   Health status: healthy

✍️ Testing Text Generation
==================================================
Context: 主角走进了一个神秘的房间，里面光线昏暗。
Player choice: 仔细观察房间
Using provider: gemini

📜 Generated Script:
  1. [narration] 主角小心翼翼地步入房间...
  2. [dialogue] 主角: "这里有什么..."
  3. [interaction] 接下来你要做什么？
```

## 🎮 游戏中的使用效果

### Gemini 2.5 Pro 特色
1. **多模态能力**: 支持文本、图像输入
2. **更大上下文**: 支持更长的对话历史
3. **创造性强**: 在高偏离度时表现优异
4. **成本效益**: 相比 GPT-4 更具性价比

### 与动态 Temperature 的整合
```python
# 自动根据偏离度调整创造性
deviation = 0.15  # 15% 偏离度
temperature = calculate_dynamic_temperature(deviation)
# Gemini 使用: temperature = 0.48 (适度创造性)

result = await gemini_provider.generate_structured_script(
    prompt="选择相信她",
    context="原文内容...",
    temperature=temperature  # 自动调节
)
```

## 📊 性能对比

| 特性 | OpenAI GPT-4o-mini | Gemini 2.5 Pro | 备注 |
|------|-------------------|----------------|------|
| 响应速度 | ⭐⭐⭐⭐ | ⭐⭐⭐ | OpenAI 略快 |
| 创造性 | ⭐⭐⭐ | ⭐⭐⭐⭐ | Gemini 更有创意 |
| 一致性 | ⭐⭐⭐⭐ | ⭐⭐⭐ | OpenAI 更稳定|
| 成本 | $0.15/1K tokens | $1.25/1K tokens | OpenAI 更便宜 |
| 上下文长度 | 128K tokens | 2M tokens | Gemini 更长 |
| 多模态 | 部分支持 | 全面支持 | Gemini 更强 |

## 🔒 安全注意事项

### API 密钥管理
1. **不要提交密钥**: 确保 `.env` 文件在 `.gitignore` 中
2. **使用环境变量**: 避免硬编码 API 密钥
3. **定期轮换**: 定期更新 API 密钥
4. **权限最小化**: 只给予必要的 API 权限

### 示例 `.gitignore`
```
# API Keys - 永远不要提交这些文件
api_keys.env
.env
*.key
*_key.txt
```

## 🛠️ 开发者指南

### 添加新的 LLM 提供商

1. **创建提供商类**:
```python
# providers/new_provider.py
class NewProvider(BaseLLMProvider):
    def _validate_config(self):
        # 验证配置
        pass
    
    def _initialize(self):
        # 初始化客户端
        pass
    
    async def generate_structured_script(self, ...):
        # 实现生成逻辑
        pass
```

2. **注册到工厂**:
```python
# providers/provider_factory.py
_providers = {
    LLMProvider.OPENAI: OpenAIProvider,
    LLMProvider.GEMINI: GeminiProvider,
    LLMProvider.NEW: NewProvider,  # 添加这行
}
```

3. **更新枚举**:
```python
# providers/base.py
class LLMProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    NEW = "new"  # 添加这行
```

### 自定义配置
```python
# 创建自定义配置的提供商
from app.services.llm_service.providers import LLMProviderFactory

provider = LLMProviderFactory.create_provider(
    provider="gemini",
    model="gemini-2.5-pro",
    temperature=0.9,
    max_tokens=4096,
    extra_params={
        "top_k": 30,
        "safety_settings": {...}
    }
)
```

## 🐛 故障排除

### 常见问题

**问题**: `ValueError: Google API key not found`
**解决**: 确保设置了 `GOOGLE_API_KEY` 环境变量

**问题**: `Module not found: langchain_google_genai`
**解决**: 运行 `poetry install` 安装依赖

**问题**: `Provider gemini not implemented`
**解决**: 确保导入了 `GeminiProvider` 类

**问题**: JSON 解析错误
**解决**: Gemini 有时生成非标准 JSON，已实现自动修复

### 调试技巧

1. **启用详细日志**:
```python
import logging
logging.getLogger("app.services.llm_service").setLevel(logging.DEBUG)
```

2. **查看生成详情**:
```python
result = await provider.generate_structured_script(...)
print(f"Provider: {result['metadata']['provider']}")
print(f"Model: {result['metadata']['model']}")
print(f"Generation time: {result['metadata']['generation_time']}s")
```

3. **健康检查**:
```bash
curl http://localhost:8000/api/v1/game/health
```

## 📈 监控与优化

### 性能监控
- 生成时间: 记录在 `metadata.generation_time`
- Token 使用: 记录在 `metadata.usage`
- 错误率: 通过日志监控

### 成本优化
- 根据任务选择合适的模型
- 低偏离度使用便宜模型
- 高偏离度使用创意模型

## 🚀 未来计划

- [ ] 添加 Anthropic Claude 支持
- [ ] 实现模型 A/B 测试
- [ ] 添加本地模型支持 (Ollama)
- [ ] 智能模型选择算法
- [ ] 成本和性能监控面板

---

*本指南涵盖了 WhatIf 统一 LLM 提供商系统的完整使用方法。*