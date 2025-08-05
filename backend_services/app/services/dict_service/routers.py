"""
Dictionary Service API Routes

Provides REST endpoints for:
- Text segment retrieval by anchor
- Dictionary lookups
- Content indexing operations
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

from .services import DictService
from .schemas import (
    SegmentResponse, DictLookupRequest, DictLookupResponse, 
    DictQueryRequest, CharacterResponse, GlossaryResponse,
    BatchCharacterRequest, BatchCharacterResponse
)

# Create router with prefix
router = APIRouter(prefix="/dict", tags=["dictionary"])

# Dependency injection
def get_dict_service() -> DictService:
    """Get dictionary service instance."""
    return DictService()

@router.get("/segment/{anchor}", response_model=SegmentResponse)
async def get_segment(
    anchor: str,
    dict_service: DictService = Depends(get_dict_service)
) -> SegmentResponse:
    """
    Retrieve text segment by anchor point.
    
    Args:
        anchor: Anchor identifier (e.g., "A01", "B02_03")
        
    Returns:
        SegmentResponse with text content and metadata
    """
    try:
        return await dict_service.fetch_segment(anchor)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/lookup", response_model=List[DictLookupResponse])
async def lookup_terms(
    request: DictLookupRequest,
    dict_service: DictService = Depends(get_dict_service)
) -> List[DictLookupResponse]:
    """
    Look up terms in dictionary.
    
    Args:
        request: Dictionary lookup request with terms
        
    Returns:
        List of dictionary entries
    """
    try:
        return await dict_service.lookup_terms(request.terms, request.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Dictionary lookup failed")

@router.get("/anchors")
async def list_anchors(
    chapter: Optional[str] = None,
    dict_service: DictService = Depends(get_dict_service)
) -> List[str]:
    """
    Get list of available anchors.
    
    Args:
        chapter: Optional chapter filter
        
    Returns:
        List of anchor identifiers
    """
    try:
        return await dict_service.list_anchors(chapter)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve anchors")


@router.post("/query")
async def query_dict(
    request: DictQueryRequest,
    dict_service: DictService = Depends(get_dict_service)
):
    """
    Query dictionary for character or glossary data.
    
    Args:
        request: Dictionary query request with type and id
        
    Returns:
        CharacterResponse or GlossaryResponse based on type
    """
    try:
        if request.type == "character":
            result = await dict_service.query_character(request.id)
            if result is None:
                raise HTTPException(status_code=404, detail=f"Character not found: {request.id}")
            return result
        elif request.type == "glossary":
            result = await dict_service.query_glossary(request.id)
            if result is None:
                raise HTTPException(status_code=404, detail=f"Glossary term not found: {request.id}")
            return result
        else:
            raise HTTPException(status_code=400, detail="Invalid query type")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/characters")
async def list_characters(
    dict_service: DictService = Depends(get_dict_service)
) -> List[str]:
    """
    Get list of all character IDs.
    
    Returns:
        List of character identifiers
    """
    try:
        return await dict_service.list_characters()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve characters")


@router.get("/glossary")
async def list_glossary(
    dict_service: DictService = Depends(get_dict_service)
) -> List[str]:
    """
    Get list of all glossary term IDs.
    
    Returns:
        List of glossary term identifiers
    """
    try:
        return await dict_service.list_glossary()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve glossary terms")


@router.post("/characters/batch", response_model=BatchCharacterResponse)
async def batch_query_characters(
    request: BatchCharacterRequest,
    dict_service: DictService = Depends(get_dict_service)
) -> BatchCharacterResponse:
    """
    Query multiple characters by their IDs in a single request.
    
    This endpoint is optimized for scenarios where you need to get information
    about multiple characters at once, such as loading all characters appearing
    in a chapter or scene.
    
    Args:
        request: Batch character query request with list of character IDs
        
    Returns:
        BatchCharacterResponse with character data mapped by ID and list of not found IDs
    """
    try:
        result = await dict_service.batch_query_characters(
            character_ids=request.character_ids,
            include_relationships=request.include_relationships
        )
        return BatchCharacterResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch character query failed: {str(e)}") 