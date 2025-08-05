"""
LLM Service API Schemas

Pydantic models for API requests, responses, and configurations.
Re-exports core models from models.py and adds API-specific schemas.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

# Re-export core models from models.py
from .models import (
    # Core data models
    TurnEvent, ScriptUnit, GlobalState, Snapshot, SessionInfo,
    TurnEventRole, ScriptUnitType,
    
    # API models
    GenerateRequest, GenerateResponse
)

# API-specific schemas and helpers

class CreateSessionRequest(BaseModel):
    """Request model for session creation."""
    
    session_id: str = Field(..., description="Unique session identifier")
    protagonist: str = Field("c_san_shang_wu", description="Main character identifier")
    initial_state: Optional[GlobalState] = Field(None, description="Initial global state")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess_123",
                "protagonist": "c_san_shang_wu",
                "initial_state": {
                    "deviation": 0.0,
                    "affinity": {},
                    "flags": {},
                    "variables": {}
                }
            }
        }
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    message: str = Field(..., description="Error message")
    error: Optional[str] = Field(None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Request validation failed",
                "error": "Context cannot be empty",
                "code": "VALIDATION_ERROR",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
    )


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: Literal["healthy", "unhealthy", "degraded"] = Field(..., description="Overall health status")
    components: Dict[str, Any] = Field(..., description="Component health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "components": {
                    "llm": {"openai_available": True, "openai_status": "healthy"},
                    "storage": {"sessions_dir": True, "snapshots_dir": True},
                    "session_management": {"event_repo": "available", "snapshot_repo": "available"}
                },
                "timestamp": "2024-01-01T12:00:00Z",
                "version": "1.0.0"
            }
        }
    )


class StatusResponse(BaseModel):
    """Service status response model."""
    
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    status: str = Field(..., description="Service status")
    description: str = Field(..., description="Service description")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "service": "llm_service",
                "version": "1.0.0",
                "status": "running",
                "description": "LLM Service for story generation and session management"
            }
        }
    )


class SessionEventQuery(BaseModel):
    """Query parameters for session events."""
    
    from_turn: int = Field(0, description="Starting turn number (inclusive)", ge=0)
    to_turn: Optional[int] = Field(None, description="Ending turn number (inclusive)", ge=0)
    limit: int = Field(100, description="Maximum number of events to return", ge=1, le=1000)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "from_turn": 0,
                "to_turn": 10,
                "limit": 50
            }
        }
    )


# Legacy schemas for backward compatibility
# These are deprecated and will be removed in future versions

class ChatRequest(BaseModel):
    """
    Legacy chat request model.
    
    DEPRECATED: Use GenerateRequest instead.
    """
    
    prompt: str = Field(..., description="Input prompt for the model")
    vendor: Literal["openai", "dashscope", "doubao"] = Field("openai", description="LLM vendor")
    model: Optional[str] = Field(None, description="Specific model name")
    diff_score: float = Field(0.0, description="Story deviation score")
    context: Optional[str] = Field(None, description="Additional context")
    max_tokens: int = Field(8192, description="Maximum tokens to generate (controlled by llm_settings.py)")
    temperature: float = Field(0.7, description="Sampling temperature")
    stream: bool = Field(False, description="Enable streaming response")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "玩家选择了向左走...",
                "vendor": "openai",
                "model": "gpt-4o-mini",
                "diff_score": 0.2,
                "context": "这是一个冒险游戏场景",
                "max_tokens": 500,
                "temperature": 0.8,
                "stream": False
            }
        }
    )


class ChatResponse(BaseModel):
    """
    Legacy chat response model.
    
    DEPRECATED: Use GenerateResponse instead.
    """
    
    content: str = Field(..., description="Generated response content")
    vendor: str = Field(..., description="LLM vendor used")
    model: str = Field(..., description="Model name used")
    usage: Dict[str, int] = Field(..., description="Token usage statistics")
    diff_score: float = Field(..., description="Updated deviation score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    generated_at: datetime = Field(default_factory=datetime.now, description="Generation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "你沿着左边的小径走去，发现了一个神秘的洞穴...",
                "vendor": "openai",
                "model": "gpt-4o-mini",
                "usage": {"prompt_tokens": 150, "completion_tokens": 200, "total_tokens": 350},
                "diff_score": 0.25,
                "metadata": {"chain_id": "story_generation", "temperature": 0.8},
                "generated_at": "2024-01-01T12:00:00Z"
            }
        }


class StreamChunk(BaseModel):
    """
    Legacy streaming chunk model.
    
    DEPRECATED: Streaming is not supported in the new architecture.
    """
    
    delta: str = Field(..., description="Incremental content")
    finish_reason: Optional[str] = Field(None, description="Reason for completion")
    chunk_id: int = Field(..., description="Chunk sequence number")


class ModelInfo(BaseModel):
    """
    Legacy model information.
    
    DEPRECATED: Model management is simplified in the new architecture.
    """
    
    vendor: str = Field(..., description="Model vendor")
    model_id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Human-readable model name")
    max_tokens: int = Field(..., description="Maximum context length")
    supports_streaming: bool = Field(..., description="Streaming support")
    cost_per_1k_tokens: float = Field(..., description="Cost per 1000 tokens")
    
    class Config:
        json_schema_extra = {
            "example": {
                "vendor": "openai",
                "model_id": "gpt-4o-mini",
                "name": "GPT-4o Mini",
                "max_tokens": 4096,
                "supports_streaming": True,
                "cost_per_1k_tokens": 0.002
            }
        }


class ChainConfig(BaseModel):
    """
    Legacy chain configuration.
    
    DEPRECATED: Chain management is handled internally in the new architecture.
    """
    
    chain_type: str = Field(..., description="Type of chain to use")
    prompt_template: str = Field(..., description="Prompt template")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Template variables")
    memory_enabled: bool = Field(False, description="Enable conversation memory")
    retrieval_enabled: bool = Field(False, description="Enable retrieval augmentation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "chain_type": "story_generation",
                "prompt_template": "基于以下情况生成故事: {context}\n玩家行动: {action}\n偏差值: {diff}",
                "variables": {"context": "fantasy_world", "theme": "adventure"},
                "memory_enabled": True,
                "retrieval_enabled": False
            }
        } 