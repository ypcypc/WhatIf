"""
LLM Service API Routes

Provides REST endpoints for:
- Story script generation
- Session management
- Health monitoring
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
import logging
from functools import lru_cache

from .services import LLMService
from .models import (
    GenerateRequest, GenerateResponse, SessionInfo, 
    TurnEvent, Snapshot
)

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/api/v1/llm", tags=["llm"])

# Dependency injection with caching to avoid recreation overhead
@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    """Get LLM service instance (cached)."""
    return LLMService()


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Generate story script",
    description="""
    Generate story script based on context from anchor_service and player choice.
    
    This is the main endpoint for story generation, implementing the core
    business flow described in the architecture:
    1. Reads/creates session snapshot
    2. Builds enhanced prompt with context and history
    3. Calls ChatGPT 4.1 mini for structured generation
    4. Updates global state and affinity
    5. Saves events to JSONL stream
    6. Returns structured script with updated state
    
    Features:
    - Automatic session management
    - Event streaming with JSONL persistence
    - Snapshot-based state management
    - LangChain integration for summarization
    - Global state tracking (deviation, affinity, flags)
    """,
    response_description="Generated script with updated global state"
)
async def generate_script(
    request: GenerateRequest,
    llm_service: LLMService = Depends(get_llm_service)
) -> GenerateResponse:
    """
    Generate story script based on context and player choice.
    
    Args:
        request: Generation request with context and player choice
        llm_service: LLM service instance (injected)
        
    Returns:
        GenerateResponse with script and updated state
        
    Raises:
        HTTPException:
            - 400: Invalid request data
            - 500: Generation failed
    """
    try:
        logger.info(f"Generating script for session {request.session_id}")
        
        # Validate request
        if not request.context.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Context cannot be empty"
            )
        
        # Generate script
        result = await llm_service.generate_story_script(request)
        
        logger.info(f"Successfully generated script for session {request.session_id}")
        return result
        
    except ValueError as e:
        logger.error(f"Invalid request for session {request.session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid request", "error": str(e)}
        )
    except Exception as e:
        logger.error(f"Generation failed for session {request.session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Script generation failed", "error": str(e)}
        )


@router.post(
    "/sessions",
    response_model=Snapshot,
    summary="Create new session",
    description="Create a new story session with initial state."
)
async def create_session(
    session_id: str,
    protagonist: str = "c_san_shang_wu",
    llm_service: LLMService = Depends(get_llm_service)
) -> Snapshot:
    """
    Create a new story session.
    
    Args:
        session_id: Unique session identifier
        protagonist: Main character identifier
        llm_service: LLM service instance (injected)
        
    Returns:
        Initial session snapshot
        
    Raises:
        HTTPException:
            - 400: Invalid session data
            - 500: Session creation failed
    """
    try:
        logger.info(f"Creating session {session_id} for protagonist {protagonist}")
        
        if not session_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID cannot be empty"
            )
        
        result = await llm_service.create_session(session_id, protagonist)
        
        logger.info(f"Successfully created session {session_id}")
        return result
        
    except ValueError as e:
        logger.error(f"Invalid session data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid session data", "error": str(e)}
        )
    except Exception as e:
        logger.error(f"Session creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Session creation failed", "error": str(e)}
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionInfo,
    summary="Get session information",
    description="Get information about a specific session."
)
async def get_session(
    session_id: str,
    llm_service: LLMService = Depends(get_llm_service)
) -> SessionInfo:
    """
    Get session information.
    
    Args:
        session_id: Session identifier
        llm_service: LLM service instance (injected)
        
    Returns:
        Session information
        
    Raises:
        HTTPException:
            - 404: Session not found
            - 500: Failed to retrieve session
    """
    try:
        logger.info(f"Getting session info for {session_id}")
        
        result = await llm_service.get_session_info(session_id)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Session not found", "session_id": session_id}
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session info for {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to retrieve session", "error": str(e)}
        )


@router.get(
    "/sessions",
    response_model=List[SessionInfo],
    summary="List sessions",
    description="List recent sessions with pagination support."
)
async def list_sessions(
    limit: int = 10,
    llm_service: LLMService = Depends(get_llm_service)
) -> List[SessionInfo]:
    """
    List recent sessions.
    
    Args:
        limit: Maximum number of sessions to return
        llm_service: LLM service instance (injected)
        
    Returns:
        List of session information
        
    Raises:
        HTTPException:
            - 400: Invalid limit parameter
            - 500: Failed to list sessions
    """
    try:
        if limit <= 0 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100"
            )
        
        logger.info(f"Listing sessions with limit {limit}")
        
        result = await llm_service.list_sessions(limit)
        
        logger.info(f"Found {len(result)} sessions")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to list sessions", "error": str(e)}
        )


@router.get(
    "/sessions/{session_id}/events",
    response_model=List[TurnEvent],
    summary="Get session events",
    description="Get events for a specific session with optional pagination."
)
async def get_session_events(
    session_id: str,
    from_turn: int = 0,
    llm_service: LLMService = Depends(get_llm_service)
) -> List[TurnEvent]:
    """
    Get events for a session.
    
    Args:
        session_id: Session identifier
        from_turn: Starting turn number (inclusive)
        llm_service: LLM service instance (injected)
        
    Returns:
        List of events
        
    Raises:
        HTTPException:
            - 400: Invalid parameters
            - 500: Failed to retrieve events
    """
    try:
        if from_turn < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_turn must be non-negative"
            )
        
        logger.info(f"Getting events for session {session_id} from turn {from_turn}")
        
        result = await llm_service.get_session_events(session_id, from_turn)
        
        logger.info(f"Retrieved {len(result)} events for session {session_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get events for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to retrieve events", "error": str(e)}
        )


@router.get(
    "/health",
    summary="Health check endpoint",
    description="Check service health and component status."
)
async def health_check(
    llm_service: LLMService = Depends(get_llm_service)
) -> dict:
    """
    Health check endpoint.
    
    Returns:
        Health status for service components
    """
    try:
        logger.info("Performing health check")
        
        result = await llm_service.health_check()
        
        # Set HTTP status based on health
        if result.get("status") != "healthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "message": "Health check failed"
            }
        )


@router.get(
    "/status",
    summary="Service status",
    description="Get basic service status information."
)
def get_status() -> dict:
    """
    Get basic service status.
    
    Returns:
        Service status information
    """
    return {
        "service": "llm_service",
        "version": "1.0.0",
        "status": "running",
        "description": "LLM Service for story generation and session management"
    } 