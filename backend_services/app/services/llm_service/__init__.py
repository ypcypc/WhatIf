"""
LLM Service Module

Handles LLM generation, session management, and story script generation.
Provides APIs for interactive fiction with event streaming, snapshot persistence,
and integration with anchor_service.

Architecture:
- Event-driven design with JSONL streaming
- Snapshot-based session management
- LangChain integration for summarization
- OpenAI GPT-4o-mini for structured generation
- Microservice architecture with anchor_service integration
"""

# Core models
from .models import (
    TurnEvent, ScriptUnit, GlobalState, Snapshot, SessionInfo,
    TurnEventRole, ScriptUnitType,
    GenerateRequest, GenerateResponse
)

# API schemas
from .schemas import (
    CreateSessionRequest, ErrorResponse, HealthResponse, StatusResponse,
    SessionEventQuery,
    # Legacy schemas for backward compatibility
    ChatRequest, ChatResponse, StreamChunk, ModelInfo, ChainConfig
)

# Repositories
from .repositories import (
    EventStreamRepository, SnapshotRepository, LLMRepository, SessionRepository
)

# Services
from .services import LLMService

# Routers
from .routers import router

__all__ = [
    # Core models
    "TurnEvent", "ScriptUnit", "GlobalState", "Snapshot", "SessionInfo",
    "TurnEventRole", "ScriptUnitType",
    "GenerateRequest", "GenerateResponse",
    
    # API schemas
    "CreateSessionRequest", "ErrorResponse", "HealthResponse", "StatusResponse",
    "SessionEventQuery",
    
    # Legacy schemas
    "ChatRequest", "ChatResponse", "StreamChunk", "ModelInfo", "ChainConfig",
    
    # Repositories
    "EventStreamRepository", "SnapshotRepository", "LLMRepository", "SessionRepository",
    
    # Services
    "LLMService",
    
    # Router
    "router"
]

# Version info
__version__ = "1.0.0"
__author__ = "LLM Service Team"
__description__ = "LLM Service for interactive fiction and story generation" 