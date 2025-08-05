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


@router.post(
    "/debug-content-tests",
    summary="Debug content tests",
    description="Run progressive content tests to diagnose 500 errors and content filtering issues"
)
async def debug_content_tests(llm_service: LLMService = Depends(get_llm_service)):
    """
    运行内容调试测试，用于诊断Gemini API 500错误
    
    这个端点会运行一系列渐进式测试：
    1. 简单英文内容
    2. 简单日文内容  
    3. 短的游戏内容
    4. 包含敏感关键词的内容
    5. 中等长度的游戏内容
    
    用于找到触发500错误或内容过滤的具体原因
    """
    try:
        # 获取LLM provider来运行测试
        provider = llm_service.llm_repo.provider
        
        if hasattr(provider, 'run_progressive_content_tests'):
            logger.info("Starting debug content tests...")
            test_results = await provider.run_progressive_content_tests()
            
            return {
                "status": "completed",
                "timestamp": "2025-07-31",
                "test_results": test_results,
                "summary": {
                    "total_tests": len(test_results),
                    "passed": sum(1 for r in test_results.values() if r.get("success")),
                    "failed": sum(1 for r in test_results.values() if not r.get("success"))
                }
            }
        else:
            return {
                "status": "error",
                "message": "Debug content tests not available for current provider"
            }
            
    except Exception as e:
        logger.error(f"Debug content tests failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Debug tests failed: {str(e)}"
        )


@router.post(
    "/test-simplified-generation",
    summary="Test simplified script generation", 
    description="Test script generation with simplified content to avoid 500 errors"
)
async def test_simplified_generation(
    content: str = "我变成了史莱姆，遇到了一只友善的龙。我们决定成为朋友。",
    max_units: int = 3,
    target_length: int = 1000,
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    测试简化的脚本生成
    
    使用简化的输入和格式要求，测试是否能避免Gemini API的500错误
    """
    try:
        provider = llm_service.llm_repo.provider
        
        if hasattr(provider, 'generate_simplified_script'):
            logger.info(f"Testing simplified generation with content length: {len(content)}")
            
            result = await provider.generate_simplified_script(
                simplified_content=content,
                max_units=max_units,
                target_length=target_length
            )
            
            return {
                "status": "completed",
                "input_length": len(content),
                "max_units": max_units,
                "target_length": target_length,
                "result": result
            }
        else:
            return {
                "status": "error", 
                "message": "Simplified generation not available for current provider"
            }
            
    except Exception as e:
        logger.error(f"Simplified generation test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Simplified generation test failed: {str(e)}"
        )


@router.get(
    "/debug-current-config",
    summary="Debug current LLM configuration",
    description="Show exactly which provider and model are currently being used"
)
async def debug_current_config(llm_service: LLMService = Depends(get_llm_service)):
    """
    调试当前LLM配置，显示实际使用的provider和model
    
    这个端点会显示：
    1. 环境变量设置
    2. 统一配置文件内容
    3. 实际使用的provider和model
    4. 配置加载路径
    """
    try:
        import os
        from backend_services.app.core.config import load_unified_config
        
        # 获取环境变量
        env_vars = {
            "LLM_PROVIDER": os.getenv("LLM_PROVIDER"),
            "LLM_MODEL": os.getenv("LLM_MODEL"),
            "GOOGLE_API_KEY": "***" + os.getenv("GOOGLE_API_KEY", "")[-4:] if os.getenv("GOOGLE_API_KEY") else None,
            "OPENAI_API_KEY": "***" + os.getenv("OPENAI_API_KEY", "")[-4:] if os.getenv("OPENAI_API_KEY") else None,
        }
        
        # 获取统一配置
        try:
            unified_config = load_unified_config()
            llm_provider_config = unified_config.get("llm_provider", {})
        except Exception as e:
            unified_config = {"error": str(e)}
            llm_provider_config = {}
        
        # 获取当前实际使用的provider信息
        provider = llm_service.llm_repo.provider
        current_provider_info = {
            "provider_type": type(provider).__name__,
            "model_name": getattr(provider, 'model_name', 'Unknown'),
            "config": {
                "provider": getattr(provider.config, 'provider', 'Unknown') if hasattr(provider, 'config') else 'Unknown',
                "model_name": getattr(provider.config, 'model_name', 'Unknown') if hasattr(provider, 'config') else 'Unknown',
                "temperature": getattr(provider.config, 'temperature', 'Unknown') if hasattr(provider, 'config') else 'Unknown',
            }
        }
        
        # 获取LangChain模型的实际配置
        model_info = {}
        if hasattr(provider, 'model'):
            model = provider.model
            model_info = {
                "model_class": type(model).__name__,
                "model_attribute": getattr(model, 'model', 'Unknown'),
                "temperature": getattr(model, 'temperature', 'Unknown'),
                "max_output_tokens": getattr(model, 'max_output_tokens', 'Unknown'),
            }
        
        return {
            "status": "success",
            "timestamp": "2025-07-31T15:30:00Z",
            "environment_variables": env_vars,
            "unified_config": {
                "default_provider": llm_provider_config.get("default_provider"),
                "default_model": llm_provider_config.get("default_model"),
                "providers": llm_provider_config.get("providers", {})
            },
            "current_provider": current_provider_info,
            "langchain_model": model_info,
            "diagnosis": {
                "expected_model": "gemini-2.5-flash",
                "actual_model": getattr(provider.config, 'model_name', 'Unknown') if hasattr(provider, 'config') else 'Unknown',
                "model_match": (getattr(provider.config, 'model_name', '') == 'gemini-2.5-flash') if hasattr(provider, 'config') else False
            }
        }
        
    except Exception as e:
        logger.error(f"Debug config failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Debug config failed: {str(e)}"
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