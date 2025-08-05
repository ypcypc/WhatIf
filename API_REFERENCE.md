# WhatIf API Reference

> Complete API documentation for WhatIf Interactive Galgame System  
> Version: 0.1.0  
> Base URL: `http://localhost:8000`

## 📋 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Game Service APIs](#game-service-apis)
4. [LLM Service APIs](#llm-service-apis)
5. [Anchor Service APIs](#anchor-service-apis)
6. [Save Service APIs](#save-service-apis)
7. [Dict Service APIs](#dict-service-apis)
8. [Error Handling](#error-handling)
9. [Data Models](#data-models)

## Overview

The WhatIf API provides a RESTful interface for interactive visual novel gameplay. All endpoints return JSON responses and follow standard HTTP status codes.

### Base URLs
- Development: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Response Format
```json
{
  "data": {},      // Response data
  "message": "",   // Status message
  "error": null    // Error details if any
}
```

## Authentication

Currently, the API does not require authentication. Future versions will implement API key authentication.

## Game Service APIs

The main orchestration service for game flow.

### Start New Game

Initialize a new game session.

**Endpoint:** `POST /api/v1/game/start`

**Request Body:**
```json
{
  "session_id": "player_123",
  "protagonist": "c_san_shang_wu",
  "chapter_id": 1,
  "anchor_index": 0
}
```

**Response:**
```json
{
  "session_id": "player_123",
  "script": [
    {
      "type": "narration",
      "content": "在一个充满魔法的世界里...",
      "metadata": {}
    },
    {
      "type": "dialogue",
      "content": "你好，我是利姆路。",
      "speaker": "利姆路",
      "metadata": {}
    },
    {
      "type": "interaction",
      "content": "你想要做什么？",
      "choice_id": "ch1_choice_1",
      "default_reply": "打个招呼"
    }
  ],
  "context": "原文内容...",
  "current_anchor": {
    "node_id": "a1_1",
    "chapter_id": 1,
    "chunk_id": "ch1_1"
  },
  "game_state": {
    "deviation": 0.15,
    "affinity": {},
    "flags": {},
    "variables": {}
  },
  "turn_number": 1,
  "message": "Game started successfully"
}
```

### Process Game Turn

Process a player's choice and generate the next story segment.

**Endpoint:** `POST /api/v1/game/turn`

**Request Body:**
```json
{
  "session_id": "player_123",
  "chapter_id": 1,
  "anchor_index": 5,
  "player_choice": "选择相信她的话",
  "current_anchor_id": "a1_5",
  "previous_anchor_index": 4,
  "include_tail": false,
  "is_last_anchor_in_chapter": false
}
```

**Response:**
```json
{
  "session_id": "player_123",
  "script": [
    {
      "type": "narration",
      "content": "你决定相信她，尽管心中仍有疑虑..."
    },
    {
      "type": "dialogue",
      "content": "我选择相信你。",
      "speaker": "主角"
    },
    {
      "type": "interaction",
      "content": "接下来你想要...",
      "choice_id": "ch1_choice_6",
      "default_reply": "继续对话"
    }
  ],
  "updated_state": {
    "deviation": 0.18,
    "affinity": {"female_lead": 75},
    "flags": {"trust_established": true},
    "variables": {}
  },
  "turn_number": 6,
  "context_used": "使用的原文内容...",
  "anchor_info": {
    "chapter_id": 1,
    "anchor_index": 5,
    "chunk_id": "ch1_223",
    "current_anchor_id": "a1_5",
    "next_anchor_id": "a1_7",
    "previous_anchor_id": "a1_3",
    "context_stats": {
      "total_length": 2500,
      "chunks_included": 3
    }
  },
  "generation_metadata": {
    "model": "gpt-4o-mini",
    "temperature": 0.8,
    "usage": {
      "prompt_tokens": 1200,
      "completion_tokens": 300,
      "total_tokens": 1500
    }
  }
}
```

### Get Session Status

Retrieve current status of a game session.

**Endpoint:** `GET /api/v1/game/sessions/{session_id}/status`

**Response:**
```json
{
  "session_id": "player_123",
  "status": "active",
  "protagonist": "c_san_shang_wu",
  "created_at": "2025-07-30T10:00:00Z",
  "last_active": "2025-07-30T10:30:00Z",
  "turn_count": 15
}
```

### Health Check

Check the health status of all game services.

**Endpoint:** `GET /api/v1/game/health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-30T10:00:00Z",
  "components": {
    "llm_service": {
      "status": "healthy",
      "openai_available": true,
      "model": "gpt-4o-mini"
    },
    "anchor_service": {
      "status": "healthy",
      "data_available": true,
      "first_chunk_available": true
    }
  },
  "version": "1.0.0",
  "description": "WhatIf AI Galgame - Complete Game Service"
}
```

## LLM Service APIs

AI generation and memory management service.

### Generate Story Script

Generate a story script based on context and player input.

**Endpoint:** `POST /api/v1/llm/generate`

**Request Body:**
```json
{
  "session_id": "player_123",
  "context": "原文内容和上下文",
  "player_choice": "玩家的选择",
  "anchor_id": "a1_5",
  "anchor_info": {
    "brief": "接受坦派斯特命名",
    "type": "transformation",
    "characters": ["char_001", "char_003"]
  },
  "options": {
    "temperature": 0.8,
    "max_tokens": 500
  }
}
```

**Response:**
```json
{
  "script": [
    {
      "type": "narration",
      "content": "生成的叙述内容..."
    }
  ],
  "globals": {
    "deviation": 0.18,
    "affinity": {"char_003": 50},
    "flags": {"named": true},
    "variables": {}
  },
  "turn_number": 5,
  "session_id": "player_123",
  "generated_at": "2025-07-30T10:00:00Z",
  "deviation_reasoning": "偏差值增加因为...",
  "new_deviation": 0.18,
  "metadata": {
    "prompt_length": 1500,
    "context_length": 1000,
    "generation_time": "2025-07-30T10:00:00Z",
    "usage": {
      "prompt_tokens": 1200,
      "completion_tokens": 300
    }
  }
}
```

### Create Session

Create a new LLM session.

**Endpoint:** `POST /api/v1/llm/sessions`

**Request Body:**
```json
{
  "session_id": "player_123",
  "protagonist": "c_san_shang_wu"
}
```

### Get Session Info

Get session information from LLM service.

**Endpoint:** `GET /api/v1/llm/sessions/{session_id}`

### LLM Health Check

**Endpoint:** `GET /api/v1/llm/health`

## Anchor Service APIs

Text segmentation and context management.

### Get Anchor Context

Retrieve context for a specific anchor position.

**Endpoint:** `GET /api/v1/anchor/context/{chapter_id}/{anchor_index}`

**Query Parameters:**
- `include_tail` (boolean): Include chapter tail content
- `is_last_anchor` (boolean): Is this the last anchor in chapter
- `previous_anchor_index` (integer): Previous anchor for context

**Response:**
```json
{
  "context": "组装的上下文文本...",
  "current_anchor": {
    "node_id": "a1_5",
    "chapter_id": 1,
    "chunk_id": "ch1_223"
  },
  "context_stats": {
    "total_length": 2500,
    "has_prefix": true,
    "has_tail": false,
    "chunks_included": 3,
    "start_chunk_id": "ch1_221",
    "end_chunk_id": "ch1_223"
  }
}
```

### Build Anchor Context

Build context from anchor specifications.

**Endpoint:** `POST /api/v1/anchor/context/build`

**Request Body:**
```json
{
  "current_anchor": {
    "node_id": "a1_5",
    "chapter_id": 1,
    "chunk_id": "ch1_223"
  },
  "previous_anchor": {
    "node_id": "a1_3",
    "chapter_id": 1,
    "chunk_id": "ch1_150"
  },
  "include_tail": false,
  "is_last_anchor_in_chapter": false
}
```

### Get Chunk Text

Retrieve raw text for a specific chunk.

**Endpoint:** `GET /api/v1/anchor/chunks/{chunk_id}`

**Response:**
```json
{
  "chunk_id": "ch1_223",
  "text": "文本内容...",
  "length": 500,
  "chapter_id": 1
}
```

### Get First Chunk

Get the first available chunk (for testing).

**Endpoint:** `GET /api/v1/anchor/first-chunk`

## Save Service APIs

Game state persistence and recovery.

### Save Snapshot

Save current game state snapshot.

**Endpoint:** `POST /api/v1/save/snapshot`

**Request Body:**
```json
{
  "session_id": "player_123",
  "turn_number": 10,
  "globals": {
    "deviation": 0.2,
    "affinity": {"char_003": 75},
    "flags": {"trust": true},
    "variables": {}
  },
  "recent_events": []
}
```

### Load Snapshot

Load a saved game state.

**Endpoint:** `GET /api/v1/save/snapshot/{session_id}`

**Response:**
```json
{
  "session_id": "player_123",
  "protagonist": "c_san_shang_wu",
  "globals": {
    "deviation": 0.2,
    "affinity": {"char_003": 75},
    "flags": {"trust": true},
    "variables": {}
  },
  "summary": "故事摘要...",
  "recent": [],
  "created_at": "2025-07-30T10:00:00Z",
  "updated_at": "2025-07-30T10:30:00Z"
}
```

### List Saves

List available save files.

**Endpoint:** `GET /api/v1/save/list`

**Query Parameters:**
- `limit` (integer): Maximum number of saves to return
- `offset` (integer): Pagination offset

### Save Event

Append event to event stream.

**Endpoint:** `POST /api/v1/save/events`

## Dict Service APIs

Text dictionary and retrieval service.

### Get Dictionary

Retrieve dictionary for a specific chapter.

**Endpoint:** `GET /api/v1/dict/dictionary/{dict_id}`

**Response:**
```json
{
  "dict_id": "chapter_1",
  "segments": [
    {
      "segment_id": "ch1_1",
      "text": "段落文本...",
      "index": 0
    }
  ],
  "total_segments": 50,
  "metadata": {
    "chapter_title": "第一章",
    "word_count": 5000
  }
}
```

### Get Segment

Retrieve a specific text segment.

**Endpoint:** `GET /api/v1/dict/segments/{dict_id}/{segment_id}`

### List Dictionaries

List available dictionaries.

**Endpoint:** `GET /api/v1/dict/list`

## Error Handling

### Error Response Format
```json
{
  "detail": {
    "message": "Error description",
    "error": "Detailed error information",
    "code": "ERROR_CODE",
    "timestamp": "2025-07-30T10:00:00Z"
  }
}
```

### Common Error Codes
- `400` - Bad Request: Invalid input parameters
- `404` - Not Found: Resource not found
- `422` - Unprocessable Entity: Validation error
- `500` - Internal Server Error: Server-side error

### Error Examples

**Session Not Found:**
```json
{
  "detail": {
    "message": "Session not found",
    "session_id": "invalid_123",
    "code": "SESSION_NOT_FOUND"
  }
}
```

**LLM Generation Failed:**
```json
{
  "detail": {
    "message": "Failed to generate script",
    "error": "OpenAI API error: rate limit exceeded",
    "code": "LLM_GENERATION_FAILED"
  }
}
```

## Data Models

### ScriptUnit
```json
{
  "type": "narration|dialogue|interaction",
  "content": "string",
  "speaker": "string|null",
  "choice_id": "string|null",
  "default_reply": "string|null",
  "metadata": {}
}
```

### GlobalState
```json
{
  "deviation": 0.15,
  "affinity": {
    "character_id": 50
  },
  "flags": {
    "flag_name": true
  },
  "variables": {
    "var_name": "value"
  }
}
```

### Anchor
```json
{
  "node_id": "a1_5",
  "chapter_id": 1,
  "chunk_id": "ch1_223"
}
```

### TurnEvent
```json
{
  "t": 5,
  "role": "user|assistant",
  "anchor": "a1_5",
  "choice": "player choice text",
  "script": [],
  "deviation_delta": 0.05,
  "affinity_changes": {},
  "metadata": {}
}
```

## Rate Limiting

Currently no rate limiting is implemented. Future versions will include:
- 100 requests per minute per session
- 1000 requests per hour per IP
- Burst allowance for game turns

## Webhooks

Planned for future releases:
- Session start/end notifications
- Achievement unlocked events
- Error notifications

---

*This API reference reflects the WhatIf system as of version 0.1.0*