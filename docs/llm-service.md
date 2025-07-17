# LLM Service 文档

LLM Service 是 WhatIf AI Galgame 系统中负责大语言模型集成和 AI 文本生成的核心服务。

## 概述

LLM Service 提供了与各种大语言模型的集成接口，支持：
- OpenAI GPT 系列模型
- 文本生成和对话
- 上下文管理
- 流式响应
- 模型配置管理

## 核心功能

### 1. 文本生成
基于输入的上下文和提示词，生成高质量的文本内容。

### 2. 对话管理
维护多轮对话的上下文，支持连续的交互式对话。

### 3. 模型切换
支持在不同的 LLM 模型之间切换，适应不同的使用场景。

### 4. 流式输出
支持流式文本生成，提供实时的响应体验。

## API 接口

### 1. 文本生成

**端点**: `POST /api/v1/llm/generate`

生成基于输入上下文的文本内容。

#### 请求体
```json
{
  "prompt": "请基于以下上下文生成后续内容：",
  "context": "故事的前文内容...",
  "model": "gpt-3.5-turbo",
  "max_tokens": 1000,
  "temperature": 0.7,
  "stream": false
}
```

#### 响应
```json
{
  "generated_text": "生成的文本内容...",
  "model_used": "gpt-3.5-turbo",
  "tokens_used": 856,
  "finish_reason": "stop"
}
```

### 2. 对话接口

**端点**: `POST /api/v1/llm/chat`

进行多轮对话交互。

#### 请求体
```json
{
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业的视觉小说作家助手。"
    },
    {
      "role": "user", 
      "content": "请帮我续写这个故事片段..."
    }
  ],
  "model": "gpt-4",
  "temperature": 0.8
}
```

#### 响应
```json
{
  "message": {
    "role": "assistant",
    "content": "基于你提供的故事片段，我建议..."
  },
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 200,
    "total_tokens": 320
  }
}
```

### 3. 流式生成

**端点**: `POST /api/v1/llm/stream`

支持服务器发送事件 (SSE) 的流式文本生成。

#### 请求体
```json
{
  "prompt": "续写故事：",
  "context": "前文内容...",
  "model": "gpt-3.5-turbo",
  "stream": true
}
```

#### 响应 (SSE 格式)
```
data: {"delta": "在", "finish_reason": null}

data: {"delta": "那个", "finish_reason": null}

data: {"delta": "黑暗", "finish_reason": null}

data: {"delta": "的", "finish_reason": null}

data: {"delta": "夜晚", "finish_reason": "stop"}
```

### 4. 模型信息

**端点**: `GET /api/v1/llm/models`

获取可用的 LLM 模型列表。

#### 响应
```json
{
  "models": [
    {
      "id": "gpt-3.5-turbo",
      "name": "GPT-3.5 Turbo",
      "description": "快速且经济的模型",
      "max_tokens": 4096,
      "available": true
    },
    {
      "id": "gpt-4",
      "name": "GPT-4",
      "description": "最先进的推理能力",
      "max_tokens": 8192,
      "available": true
    }
  ]
}
```

## 数据结构

### GenerateRequest
```python
class GenerateRequest(BaseModel):
    prompt: str                    # 提示词
    context: Optional[str] = None  # 上下文
    model: str = "gpt-3.5-turbo"  # 模型名称
    max_tokens: int = 1000         # 最大生成长度
    temperature: float = 0.7       # 随机性控制
    stream: bool = False           # 是否流式输出
```

### ChatMessage
```python
class ChatMessage(BaseModel):
    role: str      # 角色: system, user, assistant
    content: str   # 消息内容
```

### ChatRequest
```python
class ChatRequest(BaseModel):
    messages: List[ChatMessage]    # 对话历史
    model: str = "gpt-3.5-turbo"  # 使用的模型
    temperature: float = 0.7       # 温度参数
    max_tokens: Optional[int]      # 最大生成长度
```

### GenerateResponse
```python
class GenerateResponse(BaseModel):
    generated_text: str     # 生成的文本
    model_used: str        # 使用的模型
    tokens_used: int       # 消耗的 token 数
    finish_reason: str     # 结束原因
```

## 实现架构

### 分层架构
```
Router Layer (routers.py)
    ↓
Service Layer (services.py)
    ↓
Repository Layer (repositories.py)
    ↓
External APIs (OpenAI, etc.)
```

### 核心组件

#### LLMRepository
负责与外部 LLM API 的通信：
- `generate_text()`: 文本生成
- `chat_completion()`: 对话完成
- `stream_generate()`: 流式生成
- `get_models()`: 获取模型列表

#### LLMService
业务逻辑层，实现：
- `process_generate_request()`: 处理生成请求
- `manage_conversation()`: 管理对话上下文
- `validate_model()`: 验证模型可用性
- `calculate_tokens()`: 计算 token 使用量

## 配置管理

### 环境变量
```bash
# OpenAI API 配置
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_ORG_ID=your_org_id

# 默认模型设置
DEFAULT_MODEL=gpt-3.5-turbo
DEFAULT_MAX_TOKENS=1000
DEFAULT_TEMPERATURE=0.7

# 速率限制
RATE_LIMIT_RPM=60
RATE_LIMIT_TPM=90000
```

### 模型配置
```python
# backend_services/app/services/llm_service/config.py
SUPPORTED_MODELS = {
    "gpt-3.5-turbo": {
        "max_tokens": 4096,
        "cost_per_1k_tokens": 0.002,
        "supports_streaming": True
    },
    "gpt-4": {
        "max_tokens": 8192,
        "cost_per_1k_tokens": 0.03,
        "supports_streaming": True
    }
}
```

## 使用示例

### Python 客户端
```python
import requests

# 文本生成
response = requests.post('http://localhost:8000/api/v1/llm/generate', json={
    "prompt": "续写这个故事：",
    "context": "在一个黑暗的夜晚...",
    "model": "gpt-3.5-turbo",
    "max_tokens": 500,
    "temperature": 0.8
})

result = response.json()
print(f"生成的文本: {result['generated_text']}")
print(f"使用的 tokens: {result['tokens_used']}")
```

### JavaScript/TypeScript 客户端
```typescript
// 对话接口
const chatResponse = await fetch('http://localhost:8000/api/v1/llm/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    messages: [
      { role: 'system', content: '你是一个创意写作助手。' },
      { role: 'user', content: '帮我写一个科幻故事的开头。' }
    ],
    model: 'gpt-4',
    temperature: 0.9
  })
});

const chatResult = await chatResponse.json();
console.log('AI 回复:', chatResult.message.content);
```

### 流式生成示例
```typescript
// 使用 EventSource 处理流式响应
const eventSource = new EventSource('http://localhost:8000/api/v1/llm/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.delta) {
    // 逐步显示生成的文本
    appendToOutput(data.delta);
  }
  if (data.finish_reason === 'stop') {
    eventSource.close();
  }
};
```

## 性能优化

### 缓存策略
- 对相同输入的结果进行缓存
- 实现智能缓存失效机制
- 支持分布式缓存

### 并发控制
- 实现请求队列管理
- 支持并发限制
- 优雅的降级处理

### 成本控制
- Token 使用量监控
- 成本预算管理
- 自动模型选择

## 错误处理

### 常见错误类型
1. **API 密钥无效**
2. **模型不可用**
3. **Token 限制超出**
4. **网络连接问题**
5. **内容过滤触发**

### 错误响应格式
```json
{
  "error": {
    "code": "invalid_api_key",
    "message": "提供的 API 密钥无效",
    "type": "authentication_error"
  }
}
```

### 重试机制
- 指数退避重试
- 智能错误分类
- 熔断器模式

## 安全考虑

### API 密钥管理
- 环境变量存储
- 密钥轮换机制
- 访问权限控制

### 内容安全
- 输入内容过滤
- 输出内容检查
- 敏感信息脱敏

### 速率限制
- 用户级别限制
- IP 级别限制
- 全局速率控制

## 监控和日志

### 关键指标
- 请求响应时间
- Token 使用量
- 错误率统计
- 模型性能对比

### 日志记录
```python
# 请求日志
{
  "timestamp": "2025-07-16T12:00:00Z",
  "user_id": "user123",
  "model": "gpt-3.5-turbo",
  "tokens_used": 150,
  "response_time": 2.5,
  "status": "success"
}
```

## 故障排除

### 常见问题

1. **API 调用失败**
   - 检查 API 密钥配置
   - 验证网络连接
   - 确认模型可用性

2. **响应速度慢**
   - 检查网络延迟
   - 优化提示词长度
   - 考虑使用更快的模型

3. **Token 超限**
   - 减少输入长度
   - 调整 max_tokens 参数
   - 使用支持更多 token 的模型

### 调试工具
- API 调用日志
- 性能监控面板
- 错误统计报告

---

*最后更新: 2025年7月16日*
