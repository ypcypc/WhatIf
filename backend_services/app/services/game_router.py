"""
Game Integration Router

This is the main entry point for the complete game interaction flow as described in CLAUDE.md.
It coordinates Anchor Service and LLM Service to provide the unified API for the frontend.

Flow:
1. 玩家输入 → 前端 UI (React)
2. → Anchor Service (FastAPI 路由) → 原文＋锚点
3. → LLM Service (FastAPI 路由) → ChatGPT-4.1-mini → 结构化脚本 + 状态变更
4. → 前端逐句渲染 → 玩家回复 → 重复
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional, Dict, Any
import logging
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from .anchor_service.services import AnchorService
from .anchor_service.repositories import AnchorRepository
from .anchor_service.models import Anchor, AnchorContextRequest

from .llm_service.services import LLMService
from .llm_service.models import GenerateRequest, GenerateResponse

from .dict_service.services import DictService
from .dict_service.schemas import BatchCharacterRequest, BatchCharacterResponse

from pydantic import BaseModel, Field
from backend_services.app.core.utils import get_data_file_path

logger = logging.getLogger(__name__)

# Create router for the main game API
router = APIRouter(prefix="/api/v1/game", tags=["game"])


# === Pydantic Models for Game API ===

class GameStartRequest(BaseModel):
    """Request to start a new game session."""
    session_id: str = Field(..., description="Unique session identifier")
    protagonist: str = Field(default="c_san_shang_wu", description="Main character identifier")
    chapter_id: int = Field(default=1, description="Starting chapter")
    anchor_index: int = Field(default=0, description="Starting anchor index in chapter")


class GameTurnRequest(BaseModel):
    """Request for a complete game turn (user action + AI response)."""
    session_id: str = Field(..., description="Session identifier")
    chapter_id: int = Field(..., description="Current chapter")
    anchor_index: int = Field(..., description="Current anchor index")
    player_choice: str = Field(..., description="Player's choice or action")
    previous_anchor_index: Optional[int] = Field(None, description="Previous anchor index for context")
    include_tail: bool = Field(default=False, description="Include chapter tail if last anchor")
    is_last_anchor_in_chapter: bool = Field(default=False, description="Is this the last anchor in chapter")
    current_anchor_id: Optional[str] = Field(None, description="Current anchor ID (e.g., 'a1_5') for storyline progression")


class GameStartResponse(BaseModel):
    """Response when starting a new game."""
    session_id: str
    script: List[Dict[str, Any]]
    context: str
    current_anchor: Dict[str, Any]
    game_state: Dict[str, Any]
    turn_number: int
    message: str = "Game started successfully"


class GameTurnResponse(BaseModel):
    """Response for a complete game turn."""
    session_id: str
    script: List[Dict[str, Any]]
    updated_state: Dict[str, Any]
    turn_number: int
    context_used: str
    anchor_info: Dict[str, Any]
    generation_metadata: Dict[str, Any]


# === Dependency Injection ===

@lru_cache(maxsize=1)
def get_anchor_service() -> AnchorService:
    """Get Anchor service instance (cached)."""
    repo = AnchorRepository()
    return AnchorService(repo)


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    """Get LLM service instance (cached)."""
    return LLMService()


@lru_cache(maxsize=1)
def get_dict_service() -> DictService:
    """Get Dictionary service instance (cached)."""
    return DictService()


@lru_cache(maxsize=1)
def get_storylines_data() -> Dict[str, Any]:
    """Get storylines data (cached)."""
    try:
        storylines_path = get_data_file_path("storylines_data.json")
        with open(storylines_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load storylines data: {e}")
        return {"storylines": [], "nodes_detail": {}}


@lru_cache(maxsize=1)
def get_characters_data() -> Dict[str, Any]:
    """Get characters data (cached)."""
    try:
        characters_path = get_data_file_path("characters_data.json")
        with open(characters_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load characters data: {e}")
        return {"merged_characters": {}, "metadata": {}}


def convert_protagonist_id(protagonist: str) -> str:
    """Convert protagonist ID to character ID format used in storylines."""
    # Map frontend protagonist IDs to storyline character IDs
    protagonist_mapping = {
        "c_san_shang_wu": "char_001",  # 三上悟/利姆路
        # Add more mappings as needed
    }
    return protagonist_mapping.get(protagonist, protagonist)


def get_next_anchor_index(current_anchor_id: str, protagonist: str = "c_san_shang_wu") -> Optional[str]:
    """Get the next anchor index based on storylines data."""
    try:
        storylines = get_storylines_data()
        # Convert protagonist ID to storyline format
        storyline_protagonist = convert_protagonist_id(protagonist)
        logger.debug(f"Looking for next anchor after {current_anchor_id} for protagonist {protagonist} (mapped to {storyline_protagonist})")
        
        # Find the storyline for the protagonist
        for storyline in storylines.get("storylines", []):
            if storyline.get("protagonist") == storyline_protagonist:
                nodes = storyline.get("nodes", [])
                logger.debug(f"Found storyline with {len(nodes)} nodes: {nodes}")
                
                # Find current anchor in the nodes list
                try:
                    current_index = nodes.index(current_anchor_id)
                    logger.debug(f"Found {current_anchor_id} at index {current_index}")
                    if current_index + 1 < len(nodes):
                        next_anchor = nodes[current_index + 1]
                        logger.info(f"Next anchor: {current_anchor_id} -> {next_anchor}")
                        return next_anchor
                    else:
                        logger.info(f"Reached end of storyline at {current_anchor_id}")
                        return None
                except ValueError:
                    # Current anchor not found in this storyline
                    logger.debug(f"Anchor {current_anchor_id} not found in nodes list")
                    continue
        
        logger.warning(f"No next anchor found for {current_anchor_id} in storyline {protagonist}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting next anchor: {e}")
        return None


def parse_anchor_id(anchor_id: str) -> tuple[int, int]:
    """Parse anchor ID like 'a1_1' into (chapter_id, anchor_index)."""
    try:
        parts = anchor_id.split('_')
        if len(parts) == 2 and parts[0].startswith('a'):
            chapter_id = int(parts[0][1:])
            anchor_index = int(parts[1]) - 1  # Convert to 0-based index
            return chapter_id, anchor_index
    except (ValueError, IndexError):
        pass
    
    raise ValueError(f"Invalid anchor ID format: {anchor_id}")


def get_chunk_id_from_anchor(anchor_id: str) -> str:
    """Convert anchor ID like 'a1_1' to chunk ID like 'ch1_1'."""
    try:
        storylines = get_storylines_data()
        nodes_detail = storylines.get("nodes_detail", {})
        
        if anchor_id in nodes_detail:
            return nodes_detail[anchor_id].get("text_chunk_id", f"ch{anchor_id[1:]}")
        
        # Fallback: convert a1_1 to ch1_1
        return f"ch{anchor_id[1:]}"
        
    except Exception as e:
        logger.error(f"Error getting chunk ID for anchor {anchor_id}: {e}")
        return f"ch{anchor_id[1:]}"


def get_anchor_info(anchor_id: str) -> Dict[str, Any]:
    """Get detailed anchor information including brief and type with character resolution."""
    try:
        storylines = get_storylines_data()
        characters = get_characters_data()
        nodes_detail = storylines.get("nodes_detail", {})
        merged_characters = characters.get("merged_characters", {})
        
        if anchor_id in nodes_detail:
            anchor_detail = nodes_detail[anchor_id]
            
            # Resolve character IDs to character names
            character_ids = anchor_detail.get("characters", [])
            resolved_characters = []
            for char_id in character_ids:
                if char_id in merged_characters:
                    char_data = merged_characters[char_id]
                    resolved_characters.append({
                        "id": char_id,
                        "name": char_data.get("canonical_name", "Unknown"),
                        "aliases": char_data.get("all_aliases", [])
                    })
                else:
                    # Handle unknown character IDs
                    resolved_characters.append({
                        "id": char_id,
                        "name": f"Unknown_{char_id}",
                        "aliases": []
                    })
            
            return {
                "anchor_id": anchor_id,
                "brief": anchor_detail.get("brief", ""),
                "type": anchor_detail.get("type", ""),
                "characters": resolved_characters,
                "character_ids": character_ids,  # Keep original IDs for backward compatibility
                "impact_score": anchor_detail.get("impact_score", 0),
                "text_chunk_id": anchor_detail.get("text_chunk_id", f"ch{anchor_id[1:]}")
            }
        
        # Fallback for unknown anchors
        return {
            "anchor_id": anchor_id,
            "brief": "",
            "type": "unknown",
            "characters": [],
            "character_ids": [],
            "impact_score": 0,
            "text_chunk_id": f"ch{anchor_id[1:]}"
        }
        
    except Exception as e:
        logger.error(f"Error getting anchor info for {anchor_id}: {e}")
        return {
            "anchor_id": anchor_id,
            "brief": "",
            "type": "unknown",
            "characters": [],
            "character_ids": [],
            "impact_score": 0,
            "text_chunk_id": f"ch{anchor_id[1:]}"
        }


# === Main Game API Endpoints ===

@router.post(
    "/start",
    response_model=GameStartResponse,
    summary="Start a new game session",
    description="""
    Start a new game session with initial story generation.
    
    This endpoint:
    1. Creates a new session in LLM service
    2. Gets the first anchor context from Anchor service
    3. Generates initial story script
    4. Returns the first script sequence for frontend rendering
    
    This implements the complete game startup flow described in CLAUDE.md.
    """
)
async def start_game(
    request: GameStartRequest,
    anchor_service: AnchorService = Depends(get_anchor_service),
    llm_service: LLMService = Depends(get_llm_service)
) -> GameStartResponse:
    """
    Start a new game session.
    
    Args:
        request: Game start request
        anchor_service: Anchor service instance
        llm_service: LLM service instance
        
    Returns:
        GameStartResponse with initial script and state
    """
    try:
        logger.info(f"Starting new game session: {request.session_id}")
        
        # 1. Create session in LLM service
        snapshot = await llm_service.create_session(request.session_id, request.protagonist)
        
        # 2. Get initial anchor from storyline data
        storylines = get_storylines_data()
        storyline_protagonist = convert_protagonist_id(request.protagonist)
        
        # Find the first anchor from the storyline
        initial_anchor_id = None
        for storyline in storylines.get("storylines", []):
            if storyline.get("protagonist") == storyline_protagonist:
                nodes = storyline.get("nodes", [])
                if nodes:
                    initial_anchor_id = nodes[0]  # Use first anchor in storyline
                    break
        
        if not initial_anchor_id:
            # Fallback to linear construction
            initial_anchor_id = f"a{request.chapter_id}_{request.anchor_index + 1}"
            logger.warning(f"No storyline found for {request.protagonist}, using fallback anchor: {initial_anchor_id}")
        
        logger.info(f"Starting game with initial anchor: {initial_anchor_id}")
        initial_anchor_info = get_anchor_info(initial_anchor_id)
        initial_chunk_id = initial_anchor_info["text_chunk_id"]
        # Parse the actual chapter ID from the anchor
        try:
            actual_chapter_id, _ = parse_anchor_id(initial_anchor_id)
        except ValueError:
            actual_chapter_id = request.chapter_id
            
        initial_anchor = Anchor(
            node_id=initial_anchor_id,
            chapter_id=actual_chapter_id,
            chunk_id=initial_chunk_id
        )
        
        # 3. Build context from anchor service
        context_response = anchor_service.build_anchor_context(
            current_anchor=initial_anchor,
            previous_anchor=None,
            include_tail=False,
            is_last_anchor_in_chapter=False
        )
        
        # 3.5. Extract specific anchor chunk text for ANCHOR_TEXT area
        anchor_chunk_text = anchor_service.repo.get_chunk_text(initial_chunk_id)
        initial_anchor_info["anchor_text"] = anchor_chunk_text
        logger.info(f"Extracted anchor text for {initial_anchor_id}: {len(anchor_chunk_text)} characters")
        
        # 4. Generate initial script with LLM service
        generate_request = GenerateRequest(
            session_id=request.session_id,
            context=context_response.context,
            player_choice="", # Empty for game start
            anchor_id=initial_anchor_id,
            anchor_info=initial_anchor_info,
            options={}
        )
        
        generation_result = await llm_service.generate_story_script(generate_request)
        
        # 5. Convert script units to frontend format
        script_data = []
        for unit in generation_result.script:
            script_data.append({
                "type": unit.type.value,
                "content": unit.content,
                "speaker": unit.speaker,
                "choice_id": unit.choice_id,
                "default_reply": unit.default_reply,
                "metadata": unit.metadata
            })
        
        # 6. Build response
        response = GameStartResponse(
            session_id=request.session_id,
            script=script_data,
            context=context_response.context,
            current_anchor={
                "node_id": initial_anchor.node_id,
                "chapter_id": initial_anchor.chapter_id,
                "chunk_id": initial_anchor.chunk_id
            },
            game_state={
                "deviation": generation_result.globals.deviation,
                "affinity": generation_result.globals.affinity,
                "flags": generation_result.globals.flags,
                "variables": generation_result.globals.variables
            },
            turn_number=generation_result.turn_number
        )
        
        logger.info(f"Successfully started game session: {request.session_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to start game session {request.session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to start game", "error": str(e)}
        )


@router.post(
    "/turn",
    response_model=GameTurnResponse,
    summary="Process a complete game turn",
    description="""
    Process a complete game turn: player input → context building → LLM generation → response.
    
    This is the core endpoint implementing the full interaction loop from CLAUDE.md:
    1. Build context from current anchor position (Anchor Service)
    2. Include player choice and session history
    3. Generate story script with state changes (LLM Service)
    4. Return structured response for frontend rendering
    
    Supports:
    - Cross-chapter anchor handling
    - Context tail inclusion for chapter transitions
    - Deviation control and auto-convergence
    - State persistence (events.jsonl + snapshot.json)
    """
)
async def process_turn(
    request: GameTurnRequest,
    anchor_service: AnchorService = Depends(get_anchor_service),
    llm_service: LLMService = Depends(get_llm_service)
) -> GameTurnResponse:
    """
    Process a complete game turn.
    
    Args:
        request: Game turn request with player choice and anchor info
        anchor_service: Anchor service instance
        llm_service: LLM service instance
        
    Returns:
        GameTurnResponse with generated script and updated state
    """
    try:
        logger.info(f"Processing turn for session {request.session_id}, anchor {request.chapter_id}_{request.anchor_index}")
        
        # 1. Determine current anchor we're progressing FROM
        logger.debug(f"🔍 TURN REQUEST DEBUG:")
        logger.debug(f"  - request.current_anchor_id: {request.current_anchor_id}")
        logger.debug(f"  - request.chapter_id: {request.chapter_id}")
        logger.debug(f"  - request.anchor_index: {request.anchor_index}")
        
        if request.current_anchor_id:
            # Use the provided current anchor ID from storyline progression
            current_anchor_id = request.current_anchor_id
            logger.info(f"✅ Using storyline-based anchor: {current_anchor_id}")
        else:
            # Fallback to linear construction for backward compatibility
            current_anchor_id = f"a{request.chapter_id}_{request.anchor_index + 1}"
            logger.warning(f"⚠️  Using linear fallback anchor: {current_anchor_id} (this may not exist in storyline!)")
        
        logger.info(f"Current anchor: {current_anchor_id}")
        
        # 2. Find the next anchor using storyline relationships
        next_anchor_id = get_next_anchor_index(current_anchor_id)
        logger.info(f"Next anchor from storyline: {next_anchor_id}")
        
        # 3. Use next anchor as target (where we're progressing TO)
        if next_anchor_id:
            target_anchor_id = next_anchor_id
            target_anchor_info = get_anchor_info(target_anchor_id)
            target_chunk_id = target_anchor_info["text_chunk_id"]
        else:
            # No next anchor found - this could be end of storyline or missing anchor
            logger.warning(f"No next anchor found for {current_anchor_id}. Using current anchor as target.")
            target_anchor_id = current_anchor_id
            target_anchor_info = get_anchor_info(target_anchor_id)
            target_chunk_id = target_anchor_info["text_chunk_id"]
        
        # 3.5. Extract specific anchor chunk text for ANCHOR_TEXT area
        target_anchor_chunk_text = anchor_service.repo.get_chunk_text(target_chunk_id)
        target_anchor_info["anchor_text"] = target_anchor_chunk_text
        logger.info(f"Extracted anchor text for {target_anchor_id}: {len(target_anchor_chunk_text)} characters")
        
        # Build anchor for context generation
        target_anchor = Anchor(
            node_id=target_anchor_id,
            chapter_id=request.chapter_id,
            chunk_id=target_chunk_id
        )
        
        # Determine response anchor info (where we've progressed TO)
        response_anchor_id = target_anchor_id
        response_chapter_id = request.chapter_id
        response_anchor_index = request.anchor_index
        
        try:
            response_chapter_id, response_anchor_index = parse_anchor_id(target_anchor_id)
            logger.info(f"Response anchor: {target_anchor_id} -> chapter {response_chapter_id}, index {response_anchor_index}")
        except ValueError as e:
            logger.error(f"Failed to parse target anchor ID {target_anchor_id}: {e}")
            # Keep current values as fallback
        
        # Find the anchor after target for future progression  
        future_anchor_id = get_next_anchor_index(target_anchor_id) if target_anchor_id != current_anchor_id else None
        
        # 3. Build previous anchor using storyline-based current anchor
        previous_anchor = None
        if request.current_anchor_id:
            # Use current anchor as previous anchor for context building
            # This ensures proper storyline progression instead of linear indexing
            current_anchor_info = get_anchor_info(request.current_anchor_id)
            current_chunk_id = current_anchor_info["text_chunk_id"]
            previous_anchor = Anchor(
                node_id=request.current_anchor_id,
                chapter_id=request.chapter_id,
                chunk_id=current_chunk_id
            )
            logger.info(f"🔗 ANCHOR CONTEXT: Using {request.current_anchor_id} (chunk: {current_chunk_id}) as previous anchor for context building")
        
        # 4. Build context using Anchor Service
        context_response = anchor_service.build_anchor_context(
            current_anchor=target_anchor,
            previous_anchor=previous_anchor,
            include_tail=request.include_tail,
            is_last_anchor_in_chapter=request.is_last_anchor_in_chapter
        )
        
        # 4.0. Debug logging for context building results
        logger.info(f"📖 CONTEXT RESULT: Built context for {target_anchor_id} with {len(context_response.context)} characters")
        if context_response.context_stats:
            stats = context_response.context_stats
            logger.info(f"📊 CONTEXT STATS: chunks={stats.get('chunks_included', 0)}, "
                       f"start_chunk={stats.get('start_chunk_id')}, end_chunk={stats.get('end_chunk_id')}")
            if context_response.context:
                preview = context_response.context[:100].replace('\n', ' ')
                logger.info(f"🔍 CONTEXT PREVIEW: '{preview}...'")
        else:
            logger.warning(f"⚠️  No context stats available for {target_anchor_id}")
        
        # 4.1. Fallback for empty context - provide story continuation prompt
        if not context_response.context or len(context_response.context.strip()) == 0:
            logger.warning(f"Empty context for anchor {target_anchor_id}. Providing fallback content.")
            fallback_context = f"""### 故事延续
            
玩家选择了: {request.player_choice}

请基于当前游戏状态和玩家选择，创造一个合理的故事片段。
保持角色一致性，推进剧情发展，并在适当位置提供新的玩家选择机会。

当前情境: 需要继续故事发展..."""
            
            # Create a mock context response for fallback
            from .anchor_service.models import AnchorContextResponse
            context_response = AnchorContextResponse(
                context=fallback_context,
                current_anchor=target_anchor,
                context_stats={
                    "total_length": len(fallback_context),
                    "has_prefix": False,
                    "has_tail": False,
                    "chunks_included": 0,
                    "is_fallback": True,
                    "original_anchor_id": target_anchor_id
                }
            )
        
        # 5. Generate script using LLM Service
        generate_request = GenerateRequest(
            session_id=request.session_id,
            context=context_response.context,
            player_choice=request.player_choice,
            anchor_id=target_anchor_id,
            anchor_info=target_anchor_info,
            options={}
        )
        
        generation_result = await llm_service.generate_story_script(generate_request)
        
        # 6. Convert script units to frontend format
        script_data = []
        for unit in generation_result.script:
            script_data.append({
                "type": unit.type.value,
                "content": unit.content,
                "speaker": unit.speaker,
                "choice_id": unit.choice_id,
                "default_reply": unit.default_reply,
                "metadata": unit.metadata
            })
        
        # 7. Build response with next anchor info
        response = GameTurnResponse(
            session_id=request.session_id,
            script=script_data,
            updated_state={
                "deviation": generation_result.globals.deviation,
                "affinity": generation_result.globals.affinity,
                "flags": generation_result.globals.flags,
                "variables": generation_result.globals.variables
            },
            turn_number=generation_result.turn_number,
            context_used=context_response.context,
            anchor_info={
                "chapter_id": response_chapter_id,
                "anchor_index": response_anchor_index,
                "chunk_id": target_chunk_id,
                "current_anchor_id": target_anchor_id,
                "next_anchor_id": future_anchor_id,
                "previous_anchor_id": current_anchor_id,
                "context_stats": context_response.context_stats
            },
            generation_metadata=generation_result.metadata
        )
        
        logger.info(f"Successfully processed turn for session {request.session_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to process turn for session {request.session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to process turn", "error": str(e)}
        )


@router.get(
    "/sessions/{session_id}/status",
    summary="Get game session status",
    description="Get current status and state of a game session."
)
async def get_session_status(
    session_id: str,
    llm_service: LLMService = Depends(get_llm_service)
) -> Dict[str, Any]:
    """
    Get session status and current state.
    
    Args:
        session_id: Session identifier
        llm_service: LLM service instance
        
    Returns:
        Session status information
    """
    try:
        # Get session info from LLM service
        session_info = await llm_service.get_session_info(session_id)
        
        if session_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Session not found", "session_id": session_id}
            )
        
        return {
            "session_id": session_id,
            "status": session_info.status,
            "protagonist": session_info.protagonist,
            "created_at": session_info.created_at.isoformat(),
            "last_active": session_info.last_active.isoformat(),
            "turn_count": session_info.turn_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status for {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get session status", "error": str(e)}
        )


@router.post(
    "/characters/batch",
    response_model=BatchCharacterResponse,
    summary="Batch query characters for game",
    description="Query multiple characters by their IDs. Useful for loading character info when rendering scripts."
)
async def batch_query_game_characters(
    request: BatchCharacterRequest,
    dict_service: DictService = Depends(get_dict_service)
) -> BatchCharacterResponse:
    """
    Batch query characters for the game interface.
    
    This is a convenience endpoint that proxies to the dict service,
    making it easier for the frontend to get character information
    in the game context.
    
    Args:
        request: Batch character query request
        dict_service: Dictionary service instance
        
    Returns:
        BatchCharacterResponse with character data
    """
    try:
        result = await dict_service.batch_query_characters(
            character_ids=request.character_ids,
            include_relationships=request.include_relationships
        )
        return BatchCharacterResponse(**result)
    except Exception as e:
        logger.error(f"Failed to batch query characters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to query characters", "error": str(e)}
        )


@router.get(
    "/health",
    summary="Game service health check",
    description="Check health of both Anchor and LLM services."
)
async def health_check(
    anchor_service: AnchorService = Depends(get_anchor_service),
    llm_service: LLMService = Depends(get_llm_service)
) -> Dict[str, Any]:
    """
    Health check for the complete game service.
    
    Returns:
        Health status of all components
    """
    try:
        # Check LLM service health
        llm_health = await llm_service.health_check()
        
        # Check anchor service (basic check)
        anchor_health = {
            "status": "healthy",
            "service": "anchor_service",
            "data_available": True
        }
        
        # Try to get first chunk to verify data access
        try:
            first_chunk = anchor_service.get_first_chunk()
            anchor_health["first_chunk_available"] = True
        except Exception as e:
            anchor_health["status"] = "degraded"
            anchor_health["first_chunk_available"] = False
            anchor_health["error"] = str(e)
        
        # Overall health
        overall_healthy = (
            llm_health.get("status") == "healthy" and
            anchor_health.get("status") == "healthy"
        )
        
        return {
            "status": "healthy" if overall_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "llm_service": llm_health,
                "anchor_service": anchor_health
            },
            "version": "1.0.0",
            "description": "WhatIf AI Galgame - Complete Game Service"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "components": {},
            "version": "1.0.0"
        }