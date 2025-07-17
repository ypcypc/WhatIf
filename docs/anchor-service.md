# Anchor Service 文档

Anchor Service 是 WhatIf AI Galgame 系统的核心服务之一，负责处理基于锚点的文本上下文构造和顺序阅读功能。

## 概述

Anchor Service 提供了一套完整的文本处理 API，支持：
- 锚点上下文构造
- 顺序文本块读取
- 单个文本块获取
- 批量文本组装

## 核心概念

### 锚点 (Anchor)
锚点是文本中的特定位置标记，包含以下信息：
- `node_id`: 节点标识符
- `chunk_id`: 文本块标识符  
- `chapter_id`: 章节标识符

### 文本块 (Chunk)
文本块是故事内容的基本单位，每个块包含：
- `chunk_id`: 唯一标识符
- `text`: 文本内容
- `chapter_id`: 所属章节
- `is_last_in_chapter`: 是否为章节最后一块
- `is_last_overall`: 是否为整个故事的最后一块

## API 接口

### 1. 锚点上下文构造

**端点**: `POST /api/v1/anchor/context`

构造指定锚点的上下文文本，用于 LLM 处理。

#### 请求体
```json
{
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
}
```

#### 响应
```json
{
  "context": "前文内容...当前锚点内容...",
  "chunk_count": 8,
  "total_length": 1250
}
```

#### 上下文构造逻辑

1. **前文部分**: 从 `previous_anchor` 到 `current_anchor` 之间的所有文本块
2. **当前部分**: `current_anchor` 对应的文本块内容
3. **尾部处理**: 根据 `include_tail` 决定是否包含后续内容

### 2. 顺序阅读

#### 获取第一个文本块
**端点**: `GET /api/v1/anchor/chunk/first`

```json
{
  "chunk_id": "ch1_1",
  "text": "第一章 第一个朋友\n好暗。乌漆麻黑的...",
  "chapter_id": 1,
  "next_chunk_id": "ch1_2",
  "is_last_in_chapter": false,
  "is_last_overall": false
}
```

#### 获取下一个文本块
**端点**: `POST /api/v1/anchor/chunk/next`

```json
{
  "current_chunk_id": "ch1_1"
}
```

### 3. 单个文本块获取

**端点**: `GET /api/v1/anchor/chunk/{chunk_id}`

获取指定 ID 的文本块内容。

### 4. 批量文本组装

**端点**: `POST /api/v1/anchor/assemble`

批量获取指定范围内的文本块并组装成完整文本。

```json
{
  "chapter_id": 1,
  "start_chunk_id": "ch1_5",
  "end_chunk_id": "ch1_10"
}
```

## 数据结构

### AnchorInfo
```python
class AnchorInfo(BaseModel):
    node_id: str        # 节点ID
    chunk_id: str       # 文本块ID  
    chapter_id: int     # 章节ID
```

### ChunkResponse
```python
class ChunkResponse(BaseModel):
    chunk_id: str                    # 文本块ID
    text: str                       # 文本内容
    chapter_id: int                 # 章节ID
    next_chunk_id: Optional[str]    # 下一个文本块ID
    is_last_in_chapter: bool        # 是否为章节最后一块
    is_last_overall: bool           # 是否为故事最后一块
```

### ContextResponse
```python
class ContextResponse(BaseModel):
    context: str        # 构造的上下文文本
    chunk_count: int    # 包含的文本块数量
    total_length: int   # 总字符数
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
Data Layer (JSON files)
```

### 核心组件

#### AnchorRepository
负责数据访问，提供以下方法：
- `get_first_chunk_id()`: 获取章节第一个文本块ID
- `get_chunks_in_range()`: 批量获取范围内的文本块
- `get_chunk_text()`: 获取单个文本块文本
- `chunk_exists()`: 检查文本块是否存在

#### AnchorService  
业务逻辑层，实现：
- `build_anchor_context()`: 锚点上下文构造
- `get_first_chunk()`: 获取第一个文本块
- `get_next_chunk()`: 获取下一个文本块
- `get_chunk_by_id()`: 根据ID获取文本块

## 使用示例

### Python 客户端
```python
import requests

# 构造锚点上下文
response = requests.post('http://localhost:8000/api/v1/anchor/context', json={
    "current_anchor": {
        "node_id": "a1_5",
        "chunk_id": "ch1_23",
        "chapter_id": 1
    },
    "previous_anchor": {
        "node_id": "a1_4", 
        "chunk_id": "ch1_15",
        "chapter_id": 1
    }
})

context_data = response.json()
print(f"上下文长度: {context_data['total_length']}")
```

### JavaScript/TypeScript 客户端
```typescript
// 获取第一个文本块
const firstChunk = await fetch('http://localhost:8000/api/v1/anchor/chunk/first')
  .then(res => res.json());

console.log(`第一个文本块: ${firstChunk.chunk_id}`);

// 获取下一个文本块
const nextChunk = await fetch('http://localhost:8000/api/v1/anchor/chunk/next', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ current_chunk_id: firstChunk.chunk_id })
}).then(res => res.json());
```

## 性能优化

### 数据缓存
- Repository 层实现数据缓存，避免重复读取 JSON 文件
- 内存中维护章节和文本块的索引映射

### 算法优化
- 锚点上下文构造使用 O(N) 时间复杂度算法
- 批量文本获取减少数据访问次数

### 错误处理
- 完整的异常处理机制
- 详细的错误信息返回
- 数据验证和类型检查

## 配置和部署

### 数据文件路径
服务自动检测项目根目录，支持以下数据文件：
- `data/article_data.json`: 主要文章数据
- `data/characters_data.json`: 角色数据
- `data/storylines_data.json`: 故事线数据

### 环境变量
无需特殊环境变量配置，服务会自动查找数据文件。

### 健康检查
服务启动时会验证数据文件的完整性和格式正确性。

## 故障排除

### 常见问题

1. **数据文件未找到**
   - 确保 `data/article_data.json` 文件存在
   - 检查文件路径和权限

2. **JSON 格式错误**
   - 验证 JSON 文件格式
   - 检查字符编码（应为 UTF-8）

3. **文本块不存在**
   - 检查 chunk_id 是否正确
   - 验证数据文件中是否包含对应的文本块

### 调试工具
- 使用 `/docs` 端点查看 API 文档
- 启用详细日志记录
- 使用内置的健康检查端点

---

*最后更新: 2025年7月16日*
