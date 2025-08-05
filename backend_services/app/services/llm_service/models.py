"""
LLM Service Data Models

Pydantic models for LLM service data structures:
- TurnEvent: Event stream entries for JSONL storage
- ScriptUnit: Individual script components (narration, dialogue, choices)
- Snapshot: Session state snapshots for quick restoration
- GenerateRequest/Response: API request/response models
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Union, Literal
from datetime import datetime
from enum import Enum


class TurnEventRole(str, Enum):
    """Event roles for turn-based interaction."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ScriptUnitType(str, Enum):
    """Types of script units."""
    NARRATION = "narration"
    DIALOGUE = "dialogue"
    INTERACTION = "interaction"


class ScriptUnit(BaseModel):
    """
    Individual script component representing a piece of generated content.
    
    Used for structured story generation with different content types.
    """
    type: ScriptUnitType = Field(..., description="Type of script unit")
    content: str = Field(..., description="Text content of the unit")
    speaker: Optional[str] = Field(None, description="Speaker name for dialogue")
    choice_id: Optional[str] = Field(None, description="Choice identifier for choices")
    default_reply: Optional[str] = Field(None, description="Default suggested response for choice units")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "dialogue",
                "content": "你好，陌生人，欢迎来到这个神秘的世界。",
                "speaker": "神秘老人",
                "choice_id": None,
                "metadata": {"emotion": "friendly", "importance": "high"}
            }
        }
    )


class TurnEvent(BaseModel):
    """
    Event stream entry for JSONL storage.
    
    Records all player actions and system responses in chronological order.
    """
    t: int = Field(..., description="Turn number/timestamp")
    role: TurnEventRole = Field(..., description="Event role (user/assistant/system)")
    anchor: Optional[str] = Field(None, description="Anchor ID for user actions")
    choice: Optional[str] = Field(None, description="Choice made by user")
    script: Optional[List[ScriptUnit]] = Field(None, description="Generated script units")
    deviation_delta: Optional[float] = Field(None, description="Deviation score change")
    affinity_changes: Optional[Dict[str, float]] = Field(None, description="Character affinity changes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "t": 1,
                "role": "user",
                "anchor": "a1_1",
                "choice": "canon",
                "script": None,
                "deviation_delta": 0.0,
                "affinity_changes": None,
                "metadata": {"session_id": "sess_123", "timestamp": "2024-01-01T12:00:00Z"}
            }
        }
    )


class GlobalState(BaseModel):
    """
    Global game state variables.
    
    Tracks story progression, character relationships, and player choices.
    """
    deviation: float = Field(0.0, description="Story deviation score (0-100)")
    affinity: Dict[str, float] = Field(default_factory=dict, description="Character affinity scores")
    flags: Dict[str, bool] = Field(default_factory=dict, description="Story flags and switches")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Custom game variables")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "deviation": 25.0,
                "affinity": {"c_jing": 20.0, "c_san_shang_wu": 15.0},
                "flags": {"met_old_man": True, "found_sword": False},
                "variables": {"current_chapter": 1, "health": 100}
            }
        }
    )


class Snapshot(BaseModel):
    """
    Session state snapshot for quick restoration.
    
    Combines recent events with summarized history to maintain context
    while controlling memory usage.
    """
    session_id: str = Field(..., description="Session identifier")
    protagonist: str = Field(..., description="Main character identifier")
    globals: GlobalState = Field(default_factory=GlobalState, description="Global game state")
    summary: Optional[str] = Field(None, description="Summarized conversation history")
    recent: List[TurnEvent] = Field(default_factory=list, description="Recent events (last 50)")
    created_at: datetime = Field(default_factory=datetime.now, description="Snapshot creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    version: int = Field(1, description="Snapshot version for migration")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_123",
                "protagonist": "c_san_shang_wu",
                "globals": {
                    "deviation": 25.0,
                    "affinity": {"c_jing": 20.0},
                    "flags": {"met_old_man": True},
                    "variables": {"current_chapter": 1}
                },
                "summary": "玩家整体表现仁慈，与精结下了友谊...",
                "recent": [{"t": 21, "role": "user", "anchor": "a1_5", "choice": "help"}],
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:30:00Z",
                "version": 1
            }
        }


class GenerateRequest(BaseModel):
    """
    Request model for LLM generation.
    
    Combines context from anchor_service with session state for generation.
    """
    session_id: str = Field(..., description="Session identifier")
    context: str = Field(..., description="Context from anchor_service")
    player_choice: Optional[str] = Field(None, description="Player's choice/action")
    anchor_id: Optional[str] = Field(None, description="Current anchor ID")
    anchor_info: Optional[Dict[str, Any]] = Field(None, description="Detailed anchor information")
    recent_events: List[TurnEvent] = Field(default_factory=list, description="Recent events from frontend")
    options: Dict[str, Any] = Field(default_factory=dict, description="Generation options")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_123",
                "context": "你走到了一个岔路口。左边是一条黑暗的小径，右边是一条光明的大道。",
                "player_choice": "选择左边的黑暗小径",
                "anchor_id": "a1_3",
                "recent_events": [
                    {"t": 1, "role": "user", "anchor": "a1_1", "choice": "start"}
                ],
                "options": {"temperature": 0.8, "max_tokens": 500}
            }
        }


class GenerateResponse(BaseModel):
    """
    Response model for LLM generation.
    
    Returns generated script and updated global state.
    """
    script: List[ScriptUnit] = Field(..., description="Generated script units")
    globals: GlobalState = Field(..., description="Updated global state")
    turn_number: int = Field(..., description="Current turn number")
    session_id: str = Field(..., description="Session identifier")
    generated_at: datetime = Field(default_factory=datetime.now, description="Generation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Generation metadata")
    deviation_reasoning: Optional[str] = Field(None, description="Reasoning about deviation level evaluation")
    new_deviation: Optional[float] = Field(None, description="New deviation level after applying delta")
    
    class Config:
        json_schema_extra = {
            "example": {
                "script": [
                    {
                        "type": "narration",
                        "content": "你沿着黑暗的小径前行，周围的树木似乎在窃窃私语。",
                        "speaker": None,
                        "choice_id": None,
                        "metadata": {"mood": "mysterious"}
                    },
                    {
                        "type": "choice",
                        "content": "你想要继续前行吗？",
                        "speaker": None,
                        "choice_id": "continue_path",
                        "metadata": {"options": ["继续前行", "返回岔路口"]}
                    }
                ],
                "globals": {
                    "deviation": 30.0,
                    "affinity": {"c_jing": 18.0},
                    "flags": {"chose_dark_path": True},
                    "variables": {"current_location": "dark_path"}
                },
                "turn_number": 2,
                "session_id": "sess_123",
                "generated_at": "2024-01-01T12:05:00Z",
                "metadata": {"model": "gpt-4o-mini", "temperature": 0.8}
            }
        }


class SessionInfo(BaseModel):
    """
    Session information model.
    
    Provides basic session metadata and status.
    """
    session_id: str = Field(..., description="Session identifier")
    protagonist: str = Field(..., description="Main character identifier")
    created_at: datetime = Field(..., description="Session creation time")
    last_active: datetime = Field(..., description="Last activity time")
    turn_count: int = Field(..., description="Total number of turns")
    status: Literal["active", "paused", "completed"] = Field(..., description="Session status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_123",
                "protagonist": "c_san_shang_wu",
                "created_at": "2024-01-01T12:00:00Z",
                "last_active": "2024-01-01T12:30:00Z",
                "turn_count": 5,
                "status": "active"
            }
        } 