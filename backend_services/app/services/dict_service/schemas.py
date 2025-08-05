"""
Dictionary Service Data Schemas

Pydantic models for request/response validation and serialization.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DictQueryType(str, Enum):
    """Dictionary query types."""
    CHARACTER = "character"
    GLOSSARY = "glossary"


class SegmentResponse(BaseModel):
    """Response model for text segment retrieval."""
    
    anchor: str = Field(..., description="Anchor identifier")
    text: str = Field(..., description="Text content")
    start_offset: int = Field(..., description="Start position in source")
    end_offset: int = Field(..., description="End position in source")
    chapter: Optional[str] = Field(None, description="Chapter identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "anchor": "A01_001",
                "text": "这是一个示例文本片段...",
                "start_offset": 0,
                "end_offset": 100,
                "chapter": "chapter_01",
                "metadata": {"source": "novel.txt", "language": "zh"}
            }
        }


class DictLookupRequest(BaseModel):
    """Request model for dictionary lookups."""
    
    terms: List[str] = Field(..., description="Terms to look up")
    language: Optional[str] = Field("zh", description="Target language")
    include_pronunciation: bool = Field(False, description="Include pronunciation guide")
    
    class Config:
        json_schema_extra = {
            "example": {
                "terms": ["词汇", "语法"],
                "language": "zh",
                "include_pronunciation": True
            }
        }


class DictLookupResponse(BaseModel):
    """Response model for dictionary lookups."""
    
    term: str = Field(..., description="Original term")
    definitions: List[str] = Field(..., description="List of definitions")
    pronunciation: Optional[str] = Field(None, description="Pronunciation guide")
    part_of_speech: Optional[str] = Field(None, description="Part of speech")
    examples: List[str] = Field(default_factory=list, description="Usage examples")
    
    class Config:
        json_schema_extra = {
            "example": {
                "term": "词汇",
                "definitions": ["指语言中词和短语的总和", "词的集合"],
                "pronunciation": "cí huì",
                "part_of_speech": "名词",
                "examples": ["扩大词汇量", "学习新词汇"]
            }
        }


class AnchorInfo(BaseModel):
    """Model for anchor metadata."""
    
    anchor: str = Field(..., description="Anchor identifier")
    chapter: Optional[str] = Field(None, description="Chapter identifier")
    section: Optional[str] = Field(None, description="Section identifier")
    character_count: int = Field(..., description="Character count in segment")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "anchor": "A01_001",
                "chapter": "chapter_01",
                "section": "intro",
                "character_count": 150,
                "created_at": "2024-01-01T00:00:00Z"
            }
        }


class DictQueryRequest(BaseModel):
    """Request model for dictionary queries."""
    
    type: DictQueryType = Field(..., description="Query type: character or glossary")
    id: str = Field(..., description="ID of the character or glossary term")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "character",
                "id": "c_san_shang_wu"
            }
        }


class CharacterResponse(BaseModel):
    """Response model for character queries."""
    
    id: str = Field(..., description="Character ID")
    name: str = Field(..., description="Character name")
    aliases: List[str] = Field(default_factory=list, description="Character aliases")
    race: Optional[str] = Field(None, description="Character race")
    gender: Optional[str] = Field(None, description="Character gender")
    debut_chapter: Optional[int] = Field(None, description="First appearance chapter")
    appearance_chapters: List[int] = Field(default_factory=list, description="Chapters where character appears")
    abilities: List[str] = Field(default_factory=list, description="Character abilities")
    description: Optional[str] = Field(None, description="Character description")
    relationships: Dict[str, str] = Field(default_factory=dict, description="Character relationships")
    is_protagonist: bool = Field(False, description="Whether character is a protagonist")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "c_san_shang_wu",
                "name": "三上悟",
                "aliases": ["利姆路", "史莱姆"],
                "race": "史莱姆",
                "gender": "男",
                "debut_chapter": 1,
                "appearance_chapters": [1, 3, 5],
                "abilities": ["捕食者", "大贤者"],
                "description": "转生为史莱姆的主角",
                "relationships": {"维尔德拉": "朋友"},
                "is_protagonist": True,
                "created_at": "2025-07-13 22:41:36.264342",
                "updated_at": "2025-07-13 22:41:36.264342"
            }
        }


class GlossaryResponse(BaseModel):
    """Response model for glossary queries."""
    
    id: str = Field(..., description="Glossary term ID")
    term: str = Field(..., description="Glossary term")
    definition: str = Field(..., description="Term definition")
    category: Optional[str] = Field(None, description="Term category")
    related_terms: List[str] = Field(default_factory=list, description="Related terms")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "g_slime",
                "term": "史莱姆",
                "definition": "一种胶状魔物，具有极强的适应能力",
                "category": "魔物",
                "related_terms": ["魔物", "转生"]
            }
        }


class BatchCharacterRequest(BaseModel):
    """Request model for batch character queries."""
    
    character_ids: List[str] = Field(..., description="List of character IDs to query")
    include_relationships: bool = Field(True, description="Include relationship information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "character_ids": ["c_san_shang_wu", "c_veldora", "c_great_sage"],
                "include_relationships": True
            }
        }


class BatchCharacterResponse(BaseModel):
    """Response model for batch character queries."""
    
    characters: Dict[str, CharacterResponse] = Field(..., description="Character data mapped by ID")
    not_found: List[str] = Field(default_factory=list, description="IDs that were not found")
    
    class Config:
        json_schema_extra = {
            "example": {
                "characters": {
                    "c_san_shang_wu": {
                        "id": "c_san_shang_wu",
                        "name": "三上悟",
                        "aliases": ["利姆路", "史莱姆"],
                        "race": "史莱姆",
                        "gender": "男",
                        "is_protagonist": True
                    }
                },
                "not_found": ["c_unknown"]
            }
        } 