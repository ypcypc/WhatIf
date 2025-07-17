# API 参考文档

WhatIf AI Galgame 后端 API 完整参考文档，包含所有可用的端点、请求格式和响应示例。

## 基础信息

- **基础 URL**: `http://localhost:8000`
- **API 版本**: `v1`
- **内容类型**: `application/json`
- **字符编码**: `UTF-8`

## 认证

当前版本不需要认证，所有 API 端点都是公开访问的。

## 通用响应格式

### 成功响应
```json
{
  "data": { /* 响应数据 */ },
  "status": "success",
  "timestamp": "2025-07-16T12:00:00Z"
}
```

### 错误响应
```json
{
  "error": {
    "code": "error_code",
    "message": "错误描述",
    "details": "详细错误信息"
  },
  "status": "error",
  "timestamp": "2025-07-16T12:00:00Z"
}
```

## Anchor Service API

### 1. 锚点上下文构造

构造指定锚点的上下文文本，用于 LLM 处理。

**端点**: `POST /api/v1/anchor/context`

#### 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| current_anchor | AnchorInfo | 是 | 当前锚点信息 |
| previous_anchor | AnchorInfo | 是 | 前一个锚点信息 |
| include_tail | boolean | 否 | 是否包含尾部内容，默认 false |
| is_last_anchor_in_chapter | boolean | 否 | 是否为章节最后一个锚点，默认 false |

#### AnchorInfo 结构

| 字段 | 类型 | 描述 |
|------|------|------|
| node_id | string | 节点标识符 |
| chunk_id | string | 文本块标识符 |
| chapter_id | integer | 章节标识符 |

#### 请求示例

```bash
curl -X POST "http://localhost:8000/api/v1/anchor/context" \
  -H "Content-Type: application/json" \
  -d '{
    "current_anchor": {
      "node_id": "a1_5",
      "chunk_id": "ch1_23",
      "chapter_id": 1
    },
    "previous_anchor": {
      "node_id": "a1_4",
      "chunk_id": "ch1_15",
      "chapter_id": 1
    },
    "include_tail": false,
    "is_last_anchor_in_chapter": false
  }'
```

#### 响应示例

```json
{
  "context": "前文内容...当前锚点内容...",
  "chunk_count": 8,
  "total_length": 1250
}
```

#### 状态码

- `200` - 成功
- `400` - 请求参数错误
- `404` - 锚点不存在
- `500` - 服务器内部错误

### 2. 获取第一个文本块

获取故事的第一个文本块，用于开始阅读。

**端点**: `GET /api/v1/anchor/chunk/first`

#### 请求示例

```bash
curl -X GET "http://localhost:8000/api/v1/anchor/chunk/first"
```

#### 响应示例

```json
{
  "chunk_id": "ch1_1",
  "text": "第一章 第一个朋友\n好暗。乌漆麻黑的，什么都看不见。这里是哪里？不对，发生什么事了。",
  "chapter_id": 1,
  "next_chunk_id": "ch1_2",
  "is_last_in_chapter": false,
  "is_last_overall": false
}
```

#### 状态码

- `200` - 成功
- `404` - 没有可用的文本块
- `500` - 服务器内部错误

### 3. 获取下一个文本块

根据当前文本块 ID 获取下一个文本块。

**端点**: `POST /api/v1/anchor/chunk/next`

#### 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| current_chunk_id | string | 是 | 当前文本块 ID |

#### 请求示例

```bash
curl -X POST "http://localhost:8000/api/v1/anchor/chunk/next" \
  -H "Content-Type: application/json" \
  -d '{
    "current_chunk_id": "ch1_1"
  }'
```

#### 响应示例

```json
{
  "chunk_id": "ch1_2",
  "text": "印象中好像被人左一句贤者右一句大贤者耍弄……\n想到这里，我的意识清醒过来。",
  "chapter_id": 1,
  "next_chunk_id": "ch1_3",
  "is_last_in_chapter": false,
  "is_last_overall": false
}
```

#### 状态码

- `200` - 成功
- `400` - 请求参数错误
- `404` - 文本块不存在或已是最后一个
- `500` - 服务器内部错误

### 4. 获取指定文本块

根据文本块 ID 获取特定的文本块内容。

**端点**: `GET /api/v1/anchor/chunk/{chunk_id}`

#### 路径参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| chunk_id | string | 是 | 文本块标识符 |

#### 请求示例

```bash
curl -X GET "http://localhost:8000/api/v1/anchor/chunk/ch1_5"
```

#### 响应示例

```json
{
  "chunk_id": "ch1_5",
  "text": "脑袋一片混乱。喂喂喂，给我等一下啦。借点时间，我需要冷静。",
  "chapter_id": 1,
  "next_chunk_id": "ch1_6",
  "is_last_in_chapter": false,
  "is_last_overall": false
}
```

#### 状态码

- `200` - 成功
- `404` - 文本块不存在
- `500` - 服务器内部错误

### 5. 批量文本组装

获取指定范围内的文本块并组装成完整文本。

**端点**: `POST /api/v1/anchor/assemble`

#### 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| chapter_id | integer | 是 | 章节 ID |
| start_chunk_id | string | 是 | 起始文本块 ID |
| end_chunk_id | string | 是 | 结束文本块 ID |

#### 请求示例

```bash
curl -X POST "http://localhost:8000/api/v1/anchor/assemble" \
  -H "Content-Type: application/json" \
  -d '{
    "chapter_id": 1,
    "start_chunk_id": "ch1_5",
    "end_chunk_id": "ch1_10"
  }'
```

#### 响应示例

```json
{
  "assembled_text": "脑袋一片混乱。喂喂喂，给我等一下啦...",
  "chunk_count": 6,
  "total_length": 892,
  "start_chunk_id": "ch1_5",
  "end_chunk_id": "ch1_10"
}
```

#### 状态码

- `200` - 成功
- `400` - 请求参数错误
- `404` - 指定的文本块不存在
- `500` - 服务器内部错误

## LLM Service API

### 1. 文本生成

基于输入的上下文和提示词生成文本内容。

**端点**: `POST /api/v1/llm/generate`

#### 请求参数

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|--------|------|
| prompt | string | 是 | - | 提示词 |
| context | string | 否 | null | 上下文内容 |
| model | string | 否 | "gpt-3.5-turbo" | 使用的模型 |
| max_tokens | integer | 否 | 1000 | 最大生成长度 |
| temperature | float | 否 | 0.7 | 随机性控制 (0.0-2.0) |
| stream | boolean | 否 | false | 是否流式输出 |

#### 请求示例

```bash
curl -X POST "http://localhost:8000/api/v1/llm/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "请基于以下上下文生成后续内容：",
    "context": "在一个黑暗的夜晚，主人公发现自己身处一个陌生的地方...",
    "model": "gpt-3.5-turbo",
    "max_tokens": 500,
    "temperature": 0.8
  }'
```

#### 响应示例

```json
{
  "generated_text": "主人公小心翼翼地向前摸索，试图找到出路...",
  "model_used": "gpt-3.5-turbo",
  "tokens_used": 156,
  "finish_reason": "stop"
}
```

#### 状态码

- `200` - 成功
- `400` - 请求参数错误
- `401` - API 密钥无效
- `429` - 请求频率超限
- `500` - 服务器内部错误

### 2. 对话接口

进行多轮对话交互。

**端点**: `POST /api/v1/llm/chat`

#### 请求参数

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|--------|------|
| messages | ChatMessage[] | 是 | - | 对话消息列表 |
| model | string | 否 | "gpt-3.5-turbo" | 使用的模型 |
| temperature | float | 否 | 0.7 | 随机性控制 |
| max_tokens | integer | 否 | null | 最大生成长度 |

#### ChatMessage 结构

| 字段 | 类型 | 描述 |
|------|------|------|
| role | string | 角色: "system", "user", "assistant" |
| content | string | 消息内容 |

#### 请求示例

```bash
curl -X POST "http://localhost:8000/api/v1/llm/chat" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

#### 响应示例

```json
{
  "message": {
    "role": "assistant",
    "content": "基于你提供的故事片段，我建议从以下几个方向来续写..."
  },
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 200,
    "total_tokens": 320
  }
}
```

### 3. 获取可用模型

获取系统支持的 LLM 模型列表。

**端点**: `GET /api/v1/llm/models`

#### 请求示例

```bash
curl -X GET "http://localhost:8000/api/v1/llm/models"
```

#### 响应示例

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

## Dict Service API

### 1. 获取字典条目

**端点**: `GET /api/v1/dict/entries`

#### 查询参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| keyword | string | 否 | 搜索关键词 |
| limit | integer | 否 | 返回条目数量限制 |
| offset | integer | 否 | 分页偏移量 |

#### 请求示例

```bash
curl -X GET "http://localhost:8000/api/v1/dict/entries?keyword=魔法&limit=10"
```

#### 响应示例

```json
{
  "entries": [
    {
      "id": 1,
      "term": "魔法",
      "definition": "超自然的力量或技能",
      "category": "fantasy"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

## Save Service API

### 1. 保存游戏状态

**端点**: `POST /api/v1/save/state`

#### 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| save_id | string | 是 | 存档 ID |
| game_state | object | 是 | 游戏状态数据 |
| metadata | object | 否 | 元数据信息 |

#### 请求示例

```bash
curl -X POST "http://localhost:8000/api/v1/save/state" \
  -H "Content-Type: application/json" \
  -d '{
    "save_id": "save_001",
    "game_state": {
      "current_chapter": 1,
      "current_chunk": "ch1_23",
      "player_choices": []
    },
    "metadata": {
      "save_time": "2025-07-16T12:00:00Z",
      "play_time": 3600
    }
  }'
```

#### 响应示例

```json
{
  "save_id": "save_001",
  "status": "saved",
  "timestamp": "2025-07-16T12:00:00Z"
}
```

### 2. 加载游戏状态

**端点**: `GET /api/v1/save/state/{save_id}`

#### 路径参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| save_id | string | 是 | 存档 ID |

#### 请求示例

```bash
curl -X GET "http://localhost:8000/api/v1/save/state/save_001"
```

#### 响应示例

```json
{
  "save_id": "save_001",
  "game_state": {
    "current_chapter": 1,
    "current_chunk": "ch1_23",
    "player_choices": []
  },
  "metadata": {
    "save_time": "2025-07-16T12:00:00Z",
    "play_time": 3600
  }
}
```

## 系统 API

### 1. 健康检查

**端点**: `GET /health`

#### 请求示例

```bash
curl -X GET "http://localhost:8000/health"
```

#### 响应示例

```json
{
  "status": "healthy",
  "services": "operational",
  "timestamp": "2025-07-16T12:00:00Z"
}
```

### 2. 系统信息

**端点**: `GET /`

#### 请求示例

```bash
curl -X GET "http://localhost:8000/"
```

#### 响应示例

```json
{
  "message": "WhatIf AI Galgame Backend Services",
  "version": "0.1.0",
  "services": ["dict_service", "llm_service", "save_service", "anchor_service"]
}
```

## 错误代码

### 通用错误代码

| 代码 | HTTP 状态 | 描述 |
|------|-----------|------|
| `invalid_request` | 400 | 请求格式错误 |
| `missing_parameter` | 400 | 缺少必需参数 |
| `invalid_parameter` | 400 | 参数值无效 |
| `not_found` | 404 | 资源不存在 |
| `method_not_allowed` | 405 | HTTP 方法不允许 |
| `internal_error` | 500 | 服务器内部错误 |

### Anchor Service 错误代码

| 代码 | HTTP 状态 | 描述 |
|------|-----------|------|
| `chunk_not_found` | 404 | 文本块不存在 |
| `anchor_not_found` | 404 | 锚点不存在 |
| `invalid_chunk_id` | 400 | 文本块 ID 格式错误 |
| `context_build_failed` | 500 | 上下文构造失败 |

### LLM Service 错误代码

| 代码 | HTTP 状态 | 描述 |
|------|-----------|------|
| `invalid_api_key` | 401 | API 密钥无效 |
| `model_not_available` | 400 | 模型不可用 |
| `token_limit_exceeded` | 400 | Token 限制超出 |
| `rate_limit_exceeded` | 429 | 请求频率超限 |
| `generation_failed` | 500 | 文本生成失败 |

## 速率限制

### 默认限制

- **每分钟请求数**: 60
- **每小时请求数**: 1000
- **每天请求数**: 10000

### 限制头部

响应中包含以下头部信息：

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1642694400
```

## SDK 和客户端库

### JavaScript/TypeScript

```bash
npm install @whatif/api-client
```

```typescript
import { WhatIfClient } from '@whatif/api-client';

const client = new WhatIfClient({
  baseURL: 'http://localhost:8000'
});

// 获取第一个文本块
const firstChunk = await client.anchor.getFirstChunk();
```

### Python

```bash
pip install whatif-api-client
```

```python
from whatif_client import WhatIfClient

client = WhatIfClient(base_url='http://localhost:8000')

# 构造锚点上下文
context = client.anchor.build_context(
    current_anchor={'node_id': 'a1_5', 'chunk_id': 'ch1_23', 'chapter_id': 1},
    previous_anchor={'node_id': 'a1_4', 'chunk_id': 'ch1_15', 'chapter_id': 1}
)
```

## 版本历史

### v0.1.0 (2025-07-16)
- 初始版本发布
- 实现 Anchor Service 核心功能
- 添加 LLM Service 基础支持
- 提供完整的 API 文档

---

*最后更新: 2025年7月16日*
