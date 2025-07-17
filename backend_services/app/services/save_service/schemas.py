"""
Save Service Data Schemas

Pydantic models for game state, save/load operations, and metadata.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class GameState(BaseModel):
    """Main game state model."""
    
    anchor: str = Field(..., description="Current story anchor")
    diff_score: float = Field(0.0, description="Current deviation score")
    chapter: str = Field(..., description="Current chapter")
    scene: str = Field(..., description="Current scene identifier")
    character_states: Dict[str, Any] = Field(default_factory=dict, description="Character relationship states")
    inventory: List[str] = Field(default_factory=list, description="Player inventory items")
    flags: Dict[str, bool] = Field(default_factory=dict, description="Story flags and switches")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Custom game variables")
    history: List[str] = Field(default_factory=list, description="Story progression history")
    
    class Config:
        json_schema_extra = {
            "example": {
                "anchor": "A03_015",
                "diff_score": 0.25,
                "chapter": "chapter_03",
                "scene": "forest_encounter",
                "character_states": {"alice": {"relationship": 75, "trust": 60}},
                "inventory": ["magic_sword", "healing_potion"],
                "flags": {"met_wizard": True, "forest_cleared": False},
                "variables": {"day": 3, "weather": "sunny"},
                "history": ["A01_001", "A01_015", "A02_003"]
            }
        }


class SaveRequest(BaseModel):
    """Request model for saving game state."""
    
    slot_name: str = Field(..., description="Save slot identifier")
    game_state: GameState = Field(..., description="Game state to save")
    description: Optional[str] = Field(None, description="Save description")
    screenshot: Optional[str] = Field(None, description="Base64 encoded screenshot")
    
    class Config:
        json_schema_extra = {
            "example": {
                "slot_name": "autosave_001",
                "game_state": {
                    "anchor": "A03_015",
                    "diff_score": 0.25,
                    "chapter": "chapter_03",
                    "scene": "forest_encounter"
                },
                "description": "在森林中遇到神秘人物",
                "screenshot": "data:image/png;base64,..."
            }
        }


class SaveInfo(BaseModel):
    """Save slot information model."""
    
    slot_name: str = Field(..., description="Save slot identifier")
    description: Optional[str] = Field(None, description="Save description")
    chapter: str = Field(..., description="Chapter when saved")
    scene: str = Field(..., description="Scene when saved")
    diff_score: float = Field(..., description="Deviation score when saved")
    play_time: int = Field(..., description="Total play time in seconds")
    save_count: int = Field(..., description="Number of times saved")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    file_size: int = Field(..., description="Save file size in bytes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "slot_name": "save_001",
                "description": "森林探险的开始",
                "chapter": "chapter_03",
                "scene": "forest_entrance",
                "diff_score": 0.15,
                "play_time": 7200,
                "save_count": 5,
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
                "file_size": 2048
            }
        }


class LoadResponse(BaseModel):
    """Response model for loading game state."""
    
    game_state: GameState = Field(..., description="Loaded game state")
    save_info: SaveInfo = Field(..., description="Save metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "game_state": {
                    "anchor": "A03_015",
                    "diff_score": 0.25,
                    "chapter": "chapter_03",
                    "scene": "forest_encounter"
                },
                "save_info": {
                    "slot_name": "save_001",
                    "description": "森林探险的开始",
                    "play_time": 7200
                }
            }
        }


class SaveResponse(BaseModel):
    """Response model for save operations."""
    
    success: bool = Field(..., description="Save operation success")
    slot_name: str = Field(..., description="Save slot identifier")
    message: str = Field(..., description="Operation result message")
    save_info: SaveInfo = Field(..., description="Updated save metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "slot_name": "save_001",
                "message": "游戏进度已保存",
                "save_info": {
                    "slot_name": "save_001",
                    "description": "森林探险的开始",
                    "play_time": 7200
                }
            }
        }


class BackupInfo(BaseModel):
    """Backup information model."""
    
    backup_id: str = Field(..., description="Backup identifier")
    save_slots: List[str] = Field(..., description="Included save slots")
    created_at: datetime = Field(..., description="Backup creation time")
    file_size: int = Field(..., description="Backup file size")
    compressed: bool = Field(..., description="Whether backup is compressed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "backup_id": "backup_20240101_120000",
                "save_slots": ["save_001", "save_002", "autosave_001"],
                "created_at": "2024-01-01T12:00:00Z",
                "file_size": 10240,
                "compressed": True
            }
        } 