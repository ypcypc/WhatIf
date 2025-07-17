"""
Pydantic models for anchor service.

These models define the data structures for anchor processing:
- Anchor: Single anchor point from nodes_detail
- AssembleRequest: Request payload for assembling text
- Span: Internal span structure for processed ranges  
- AssembleResponse: Response containing assembled text and spans
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Anchor(BaseModel):
    """
    Single anchor point from nodes_detail.
    
    Frontend only needs node_id/chunk_id/chapter_id (without full text).
    """
    node_id: str = Field(..., description="Node identifier")
    chunk_id: str = Field(..., description="Text chunk identifier") 
    chapter_id: int = Field(..., description="Chapter identifier", ge=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "a1_1",
                "chunk_id": "ch1_23", 
                "chapter_id": 1
            }
        }


class AssembleRequest(BaseModel):
    """
    Request payload for assembling text from anchors.
    """
    anchors: List[Anchor] = Field(..., description="List of anchor points", min_length=1)
    include_chapter_intro: bool = Field(
        default=False, 
        description="Whether to include chapter introduction at the beginning"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "anchors": [
                    {"node_id": "a1_1", "chunk_id": "ch1_23", "chapter_id": 1},
                    {"node_id": "a3_1", "chunk_id": "ch3_28", "chapter_id": 3}
                ],
                "include_chapter_intro": True
            }
        }


class Span(BaseModel):
    """
    Internal span structure representing a processed text range.
    
    Used for frontend highlighting and debugging.
    """
    chapter_id: int = Field(..., description="Chapter identifier", ge=1)
    start_id: str = Field(..., description="Starting chunk identifier")
    end_id: str = Field(..., description="Ending chunk identifier") 
    text: str = Field(..., description="Assembled text content")
    
    class Config:
        json_schema_extra = {
            "example": {
                "chapter_id": 1,
                "start_id": "ch1_1",
                "end_id": "ch1_23", 
                "text": "第一章 第一个朋友..."
            }
        }


class AssembleResponse(BaseModel):
    """
    Response containing assembled text and spans for highlighting.
    """
    text: str = Field(..., description="Complete assembled text")
    spans: List[Span] = Field(..., description="List of spans for frontend highlighting")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "第一章 第一个朋友 ...（省略）",
                "spans": [
                    {
                        "chapter_id": 1,
                        "start_id": "ch1_1", 
                        "end_id": "ch1_23",
                        "text": "..."
                    },
                    {
                        "chapter_id": 3,
                        "start_id": "ch3_28",
                        "end_id": "ch3_174", 
                        "text": "..."
                    }
                ]
            }
        }


class NextChunkRequest(BaseModel):
    """
    Request for getting the next chunk in sequence.
    """
    current_chunk_id: str = Field(..., description="Current chunk ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_chunk_id": "ch1_5"
            }
        }


class AnchorContextRequest(BaseModel):
    """
    Request for building context around a specific anchor.
    """
    current_anchor: Anchor = Field(..., description="Current anchor point")
    previous_anchor: Optional[Anchor] = Field(default=None, description="Previous anchor point (optional)")
    include_tail: bool = Field(default=False, description="Whether to include tail content after anchor")
    is_last_anchor_in_chapter: bool = Field(default=False, description="Whether this is the last anchor in chapter")
    
    class Config:
        json_schema_extra = {
            "example": {
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
                "include_tail": False,
                "is_last_anchor_in_chapter": False
            }
        }


class AnchorContextResponse(BaseModel):
    """
    Response containing the built context for an anchor.
    """
    context: str = Field(..., description="Built context text")
    current_anchor: Anchor = Field(..., description="The anchor this context was built for")
    context_stats: dict = Field(..., description="Statistics about the context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "context": "前文内容...锚点内容...尾部内容...",
                "current_anchor": {
                    "node_id": "a1_5",
                    "chunk_id": "ch1_23", 
                    "chapter_id": 1
                },
                "context_stats": {
                    "total_length": 1250,
                    "has_prefix": True,
                    "has_tail": False,
                    "chunks_included": 5
                }
            }
        }


class ChunkResponse(BaseModel):
    """
    Response containing a single chunk's text and metadata.
    """
    chunk_id: str = Field(..., description="Chunk identifier")
    chapter_id: int = Field(..., description="Chapter identifier")
    text: str = Field(..., description="Text content")
    is_last_in_chapter: bool = Field(..., description="Whether this is the last chunk in chapter")
    is_last_overall: bool = Field(..., description="Whether this is the last chunk overall")
    next_chunk_id: str = Field(None, description="Next chunk ID if available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "ch1_5",
                "chapter_id": 1,
                "text": "脑袋一片混乱。喂喂喂，给我等一下啦。借点时间，我需要冷静。",
                "is_last_in_chapter": False,
                "is_last_overall": False,
                "next_chunk_id": "ch1_6"
            }
        }
