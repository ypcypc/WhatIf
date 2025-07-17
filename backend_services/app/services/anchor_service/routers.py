"""
FastAPI router for anchor service.

This module provides HTTP endpoints for anchor-based text assembly.
Includes proper error handling, dependency injection, and API documentation.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from .models import AssembleRequest, AssembleResponse, NextChunkRequest, ChunkResponse, AnchorContextRequest, AnchorContextResponse
from .repositories import AnchorRepository
from .services import AnchorService


# Create router with prefix and tags for API organization
router = APIRouter(
    prefix="/anchor",
    tags=["anchor"],
    responses={
        404: {"description": "Resource not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)


def get_anchor_service() -> AnchorService:
    """
    Dependency function to create AnchorService instance.
    
    Uses dependency injection to construct:
    AnchorRepository(data_path) → AnchorService
    
    Returns:
        Configured AnchorService instance
    """
    repo = AnchorRepository()
    return AnchorService(repo)


@router.post(
    "/assemble",
    response_model=AssembleResponse,
    summary="Assemble text from anchor points",
    description="""
    Assemble text content from a list of anchor points.
    
    Features:
    - Cross-chapter handling with automatic span segmentation
    - Optional chapter introduction inclusion
    - Returns both assembled text and span metadata for highlighting
    
    The service processes anchors in O(N) time with minimal database queries.
    """,
    response_description="Assembled text with span metadata for frontend highlighting"
)
def assemble_text(
    request: AssembleRequest,
    service: AnchorService = Depends(get_anchor_service)
) -> AssembleResponse:
    """
    Assemble text from anchor points.
    
    Args:
        request: AssembleRequest containing anchors and options
        service: AnchorService instance (injected)
        
    Returns:
        AssembleResponse with assembled text and spans
        
    Raises:
        HTTPException: 
            - 400: Invalid anchor data or empty anchor list
            - 404: Referenced chunks not found in database
            - 500: Database or internal server error
    """
    try:
        # Validate anchors exist in database
        validation_errors = service.validate_anchors(request.anchors)
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Some anchor chunks were not found",
                    "errors": validation_errors
                }
            )
        
        # Perform assembly
        result = service.assemble_by_anchors(
            anchors=request.anchors,
            include_intro=request.include_chapter_intro
        )
        
        return result
        
    except ValueError as e:
        # Handle business logic errors (e.g., invalid chapter)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid request", "error": str(e)}
        )
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.post(
    "/validate",
    response_model=dict,
    summary="Validate anchor points",
    description="Validate that all anchor points exist in the database without assembling text."
)
def validate_anchors(
    request: AssembleRequest,
    service: AnchorService = Depends(get_anchor_service)
) -> dict:
    """
    Validate anchor points without assembling text.
    
    Useful for pre-validation before expensive assembly operations.
    
    Args:
        request: AssembleRequest containing anchors to validate
        service: AnchorService instance (injected)
        
    Returns:
        Validation result with any errors found
    """
    try:
        validation_errors = service.validate_anchors(request.anchors)
        stats = service.get_assembly_stats(request.anchors)
        
        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Validation failed", "error": str(e)}
        )


@router.get(
    "/chunk/first",
    response_model=ChunkResponse,
    summary="Get first chunk of the story",
    description="Get the first chunk (ch1_1) to start reading the story."
)
def get_first_chunk(
    service: AnchorService = Depends(get_anchor_service)
) -> ChunkResponse:
    """
    Get the first chunk of the story.
    
    Args:
        service: AnchorService instance (injected)
        
    Returns:
        ChunkResponse for the first chunk
        
    Raises:
        HTTPException:
            - 404: First chunk not found
            - 500: Internal server error
    """
    try:
        result = service.get_first_chunk()
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "First chunk not found", "error": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get first chunk", "error": str(e)}
        )


@router.get(
    "/chunk/{chunk_id}",
    response_model=ChunkResponse,
    summary="Get specific chunk",
    description="Get a specific chunk by its ID with navigation metadata."
)
def get_chunk(
    chunk_id: str,
    service: AnchorService = Depends(get_anchor_service)
) -> ChunkResponse:
    """
    Get a specific chunk by ID.
    
    Args:
        chunk_id: Chunk identifier (e.g., "ch1_5")
        service: AnchorService instance (injected)
        
    Returns:
        ChunkResponse with chunk data and navigation info
        
    Raises:
        HTTPException:
            - 400: Invalid chunk ID format
            - 404: Chunk not found
            - 500: Internal server error
    """
    try:
        result = service.get_chunk(chunk_id)
        return result
        
    except ValueError as e:
        if "Invalid chunk_id format" in str(e) or "Chunk not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Chunk not found", "error": str(e)}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Invalid request", "error": str(e)}
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get chunk", "error": str(e)}
        )


@router.post(
    "/chunk/next",
    response_model=ChunkResponse,
    summary="Get next chunk in sequence",
    description="Get the next chunk after the current one for sequential reading."
)
def get_next_chunk(
    request: NextChunkRequest,
    service: AnchorService = Depends(get_anchor_service)
) -> ChunkResponse:
    """
    Get the next chunk in sequence.
    
    Args:
        request: NextChunkRequest with current chunk ID
        service: AnchorService instance (injected)
        
    Returns:
        ChunkResponse for the next chunk
        
    Raises:
        HTTPException:
            - 400: Invalid current chunk ID or reached end of story
            - 404: Current chunk not found
            - 500: Internal server error
    """
    try:
        result = service.get_next_chunk(request.current_chunk_id)
        return result
        
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Current chunk not found", "error": str(e)}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Invalid request or end of story", "error": str(e)}
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get next chunk", "error": str(e)}
        )


@router.post(
    "/context",
    response_model=AnchorContextResponse,
    summary="Build context for anchor",
    description="""
    Build context around a specific anchor following the described logic:
    
    1. 定位当前锚点在章节中的位置
    2. 提取"前文" (从上一锚点结束后 或 章节开头 到当前锚点前)
    3. 追加锚点本身
    4. 视情况再加"尾部" (如果是章节最后锚点且需要)
    
    This endpoint implements the exact logic described for LLM context construction.
    """,
    response_description="Built context with metadata for LLM processing"
)
def build_anchor_context(
    request: AnchorContextRequest,
    service: AnchorService = Depends(get_anchor_service)
) -> AnchorContextResponse:
    """
    Build context for a specific anchor.
    
    Args:
        request: AnchorContextRequest with anchor and context options
        service: AnchorService instance (injected)
        
    Returns:
        AnchorContextResponse with built context and metadata
        
    Raises:
        HTTPException:
            - 400: Invalid anchor data
            - 404: Anchor chunks not found
            - 500: Internal server error
    """
    try:
        # Validate current anchor exists
        if not service.repo.chunk_exists(request.current_anchor.chunk_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": f"Current anchor chunk not found: {request.current_anchor.chunk_id}"}
            )
        
        # Validate previous anchor if provided
        if request.previous_anchor and not service.repo.chunk_exists(request.previous_anchor.chunk_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": f"Previous anchor chunk not found: {request.previous_anchor.chunk_id}"}
            )
        
        # Build context
        result = service.build_anchor_context(
            current_anchor=request.current_anchor,
            previous_anchor=request.previous_anchor,
            include_tail=request.include_tail,
            is_last_anchor_in_chapter=request.is_last_anchor_in_chapter
        )
        
        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid request", "error": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to build context", "error": str(e)}
        )


@router.get(
    "/health",
    summary="Health check endpoint",
    description="Simple health check for the anchor service."
)
def health_check() -> dict:
    """
    Health check endpoint.
    
    Returns:
        Simple health status
    """
    return {
        "status": "healthy",
        "service": "anchor_service",
        "version": "1.0.0"
    }
