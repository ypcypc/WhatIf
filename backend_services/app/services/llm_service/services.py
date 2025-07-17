"""
LLM Service Business Logic

Handles LLM generation, session management, and state coordination.
Integrates with anchor_service for context and manages story progression.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import (
    GenerateRequest, GenerateResponse, TurnEvent, ScriptUnit, 
    GlobalState, Snapshot, TurnEventRole, ScriptUnitType, SessionInfo
)
from .repositories import SessionRepository, LLMRepository, EventStreamRepository, SnapshotRepository
from backend_services.app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM service for story generation and session management.
    
    Provides high-level business logic for:
    - Story script generation with context
    - Session state management
    - Event streaming and snapshot persistence
    - Integration with anchor_service
    """
    
    def __init__(self):
        """Initialize service with repositories."""
        self.session_repo = SessionRepository()
        self.llm_repo = LLMRepository()
        self.event_repo = EventStreamRepository()
        self.snapshot_repo = SnapshotRepository()
    
    async def generate_story_script(self, request: GenerateRequest) -> GenerateResponse:
        """
        Generate story script based on context and player choice.
        
        This is the main entry point for story generation, implementing
        the core business flow described in the architecture.
        
        Args:
            request: Generation request with context and player choice
            
        Returns:
            GenerateResponse with script and updated state
        """
        logger.info(f"Generating script for session {request.session_id}")
        
        try:
            # 1. Get or create session snapshot
            snapshot = await self.session_repo.get_or_create_session(
                request.session_id, 
                request.options.get("protagonist", "c_san_shang_wu")
            )
            
            # 2. Get current turn number
            current_turn = await self.event_repo.get_latest_turn(request.session_id) + 1
            
            # 3. Build enhanced prompt with context and history
            enhanced_prompt = await self._build_enhanced_prompt(
                request, snapshot, current_turn
            )
            
            # 4. Generate structured script using LLM
            generation_result = await self.llm_repo.generate_structured_script(
                prompt=enhanced_prompt,
                context=request.context,
                current_state=snapshot.globals,
                temperature=request.options.get("temperature", 0.8),
                max_tokens=request.options.get("max_tokens", 1000),
                anchor_info=request.anchor_info,
                session_id=request.session_id
            )
            
            # 5. Update global state based on generation result
            updated_globals = self._update_global_state(
                snapshot.globals, 
                generation_result
            )
            
            # 6. Create events for this turn
            user_event = TurnEvent(
                t=current_turn,
                role=TurnEventRole.USER,
                anchor=request.anchor_id,
                choice=request.player_choice,
                script=None,
                deviation_delta=0.0,
                affinity_changes=None,
                metadata={
                    "session_id": request.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "context_length": len(request.context)
                }
            )
            
            assistant_event = TurnEvent(
                t=current_turn,
                role=TurnEventRole.ASSISTANT,
                anchor=None,
                choice=None,
                script=generation_result["script_units"],
                deviation_delta=generation_result.get("deviation_delta", 0.0),
                affinity_changes=generation_result.get("affinity_changes", {}),
                metadata={
                    "session_id": request.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "model": "gpt-4o-mini",
                    "usage": generation_result.get("usage", {})
                }
            )
            
            # 7. Save turn and update snapshot
            await self.session_repo.save_turn(
                request.session_id,
                user_event,
                assistant_event,
                updated_globals
            )
            
            # 8. Build and return response
            response = GenerateResponse(
                script=generation_result["script_units"],
                globals=updated_globals,
                turn_number=current_turn,
                session_id=request.session_id,
                generated_at=datetime.now(),
                metadata={
                    "prompt_length": len(enhanced_prompt),
                    "context_length": len(request.context),
                    "generation_time": datetime.now().isoformat(),
                    "usage": generation_result.get("usage", {}),
                    "content_balance": {
                        "required_counts": generation_result.get("required_counts", {}),
                        "target_counts": generation_result.get("target_counts", {}),
                        "generation_config": generation_result.get("generation_config", {})
                    }
                }
            )
            
            logger.info(f"Generated script for session {request.session_id}, turn {current_turn}")
            return response
            
        except Exception as e:
            logger.error(f"Script generation failed for session {request.session_id}: {e}")
            raise
    
    async def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get session information and status.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionInfo if session exists, None otherwise
        """
        try:
            snapshot = await self.snapshot_repo.load_snapshot(session_id)
            if not snapshot:
                return None
            
            latest_turn = await self.event_repo.get_latest_turn(session_id)
            
            return SessionInfo(
                session_id=session_id,
                protagonist=snapshot.protagonist,
                created_at=snapshot.created_at,
                last_active=snapshot.updated_at,
                turn_count=latest_turn,
                status="active"  # Could be enhanced with actual status tracking
            )
            
        except Exception as e:
            logger.error(f"Failed to get session info for {session_id}: {e}")
            return None
    
    async def list_sessions(self, limit: int = 10) -> List[SessionInfo]:
        """
        List recent sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of session information
        """
        # This is a simplified implementation
        # In production, you might want to maintain a session index
        try:
            sessions = []
            # Implementation would iterate through data directory
            # For now, return empty list
            return sessions
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check for the service.
        
        Returns:
            Health status with component details
        """
        logger.info("Performing LLM service health check")
        
        try:
            # Check LLM repository health
            llm_health = await self.llm_repo.health_check()
            
            # Check data directories
            data_directories = {
                "sessions_dir": self.session_repo.event_repo.data_dir.exists(),
                "snapshots_dir": self.session_repo.snapshot_repo.data_dir.exists()
            }
            
            # Overall health status
            overall_healthy = (
                llm_health.get("openai_available", False) and
                all(data_directories.values())
            )
            
            return {
                "status": "healthy" if overall_healthy else "unhealthy",
                "components": {
                    "llm": llm_health,
                    "storage": data_directories,
                    "session_management": {
                        "event_repo": "available",
                        "snapshot_repo": "available"
                    }
                },
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _build_enhanced_prompt(
        self, 
        request: GenerateRequest, 
        snapshot: Snapshot, 
        turn_number: int
    ) -> str:
        """
        Build enhanced prompt with context, history, and state.
        
        Args:
            request: Generation request
            snapshot: Current session snapshot
            turn_number: Current turn number
            
        Returns:
            Enhanced prompt string
        """
        prompt_parts = []
        
        # Add session context
        prompt_parts.append(f"会话ID: {request.session_id}")
        prompt_parts.append(f"回合数: {turn_number}")
        prompt_parts.append(f"主角: {snapshot.protagonist}")
        
        # Add current state
        prompt_parts.append(f"当前状态:")
        prompt_parts.append(f"- 偏差值: {snapshot.globals.deviation}")
        prompt_parts.append(f"- 角色好感度: {snapshot.globals.affinity}")
        prompt_parts.append(f"- 故事标记: {snapshot.globals.flags}")
        prompt_parts.append(f"- 游戏变量: {snapshot.globals.variables}")
        
        # Add conversation history summary
        if snapshot.summary:
            prompt_parts.append(f"历史摘要:")
            prompt_parts.append(snapshot.summary)
        
        # Add recent events context
        if snapshot.recent:
            prompt_parts.append(f"最近事件:")
            for event in snapshot.recent[-5:]:  # Last 5 events
                if event.role == TurnEventRole.USER:
                    prompt_parts.append(f"- 玩家: {event.choice or event.anchor}")
                elif event.role == TurnEventRole.ASSISTANT and event.script:
                    content = " ".join([unit.content for unit in event.script[:2]])  # First 2 script units
                    prompt_parts.append(f"- 系统: {content[:100]}...")  # Truncate to 100 chars
        
        # Add current context from anchor_service
        prompt_parts.append(f"当前情境:")
        prompt_parts.append(request.context)
        
        # Add player choice
        if request.player_choice:
            prompt_parts.append(f"玩家选择: {request.player_choice}")
        
        # Add generation instructions from config
        from .llm_config import llm_config
        
        config = llm_config.get_generation_config(snapshot.globals.deviation)
        target_counts = llm_config.get_required_counts(snapshot.globals.deviation)
        
        enhanced_prompt_section = llm_config.build_enhanced_prompt_section(
            current_state=snapshot.globals.model_dump(),
            target_counts=target_counts,
            config=config
        )
        
        prompt_parts.append(enhanced_prompt_section)
        return "\n".join(prompt_parts)
    
    def _update_global_state(
        self, 
        current_state: GlobalState, 
        generation_result: Dict[str, Any]
    ) -> GlobalState:
        """
        Update global state based on generation result.
        
        Args:
            current_state: Current global state
            generation_result: Result from LLM generation
            
        Returns:
            Updated global state
        """
        # Create new state based on current state
        new_state = GlobalState(
            deviation=current_state.deviation,
            affinity=current_state.affinity.copy(),
            flags=current_state.flags.copy(),
            variables=current_state.variables.copy()
        )
        
        # Apply deviation delta with control logic
        deviation_delta = generation_result.get("deviation_delta", 0.0)
        controlled_delta = self._apply_deviation_control(current_state.deviation, deviation_delta)
        new_state.deviation = max(0.0, min(100.0, new_state.deviation + controlled_delta))
        
        # Apply affinity changes
        affinity_changes = generation_result.get("affinity_changes", {})
        for character, change in affinity_changes.items():
            current_affinity = new_state.affinity.get(character, 0.0)
            new_state.affinity[character] = max(-100.0, min(100.0, current_affinity + change))
        
        # Apply flag updates
        flag_updates = generation_result.get("flags_updates", {})
        for flag, value in flag_updates.items():
            new_state.flags[flag] = value
        
        # Apply variable updates
        variable_updates = generation_result.get("variables_updates", {})
        for var, value in variable_updates.items():
            new_state.variables[var] = value
        
        return new_state
    
    async def create_session(self, session_id: str, protagonist: str) -> Snapshot:
        """
        Create a new session with initial state.
        
        Args:
            session_id: Session identifier
            protagonist: Main character identifier
            
        Returns:
            Initial session snapshot
        """
        try:
            return await self.session_repo.get_or_create_session(session_id, protagonist)
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            raise
    
    async def get_session_events(self, session_id: str, from_turn: int = 0) -> List[TurnEvent]:
        """
        Get events for a session.
        
        Args:
            session_id: Session identifier
            from_turn: Starting turn number
            
        Returns:
            List of events
        """
        try:
            return await self.event_repo.read_events(session_id, from_turn)
        except Exception as e:
            logger.error(f"Failed to get events for session {session_id}: {e}")
            return []
    
    def _apply_deviation_control(self, current_deviation: float, proposed_delta: float) -> float:
        """
        Apply deviation control logic to limit deviation increases and encourage convergence.
        
        Based on CLAUDE.md specifications:
        - deviation < 5% → allow small increases
        - 5% ≤ deviation ≤ 30% → allow moderate changes
        - > 30% → force convergence back to main storyline
        
        Args:
            current_deviation: Current deviation percentage (0-100)
            proposed_delta: Proposed deviation change
            
        Returns:
            Controlled deviation delta
        """
        # Convert to 0-1 scale for calculations
        deviation_ratio = current_deviation / 100.0
        
        if deviation_ratio < 0.05:
            # Low deviation: allow slight increases, cap at 5%
            controlled_delta = min(proposed_delta, 5.0)
            
        elif deviation_ratio <= 0.3:
            # Medium deviation: allow moderate changes, slight bias toward convergence
            if proposed_delta > 0:
                # Reduce large increases
                controlled_delta = min(proposed_delta, 10.0)
            else:
                # Allow full decreases
                controlled_delta = proposed_delta
                
        elif deviation_ratio <= 0.6:
            # High deviation: strong bias toward convergence
            if proposed_delta > 0:
                # Severely limit increases
                controlled_delta = min(proposed_delta, 2.0)
            else:
                # Encourage decreases
                controlled_delta = max(proposed_delta, -15.0)
                
        else:
            # Very high deviation: force convergence
            if proposed_delta > 0:
                # No increases allowed
                controlled_delta = 0.0
            else:
                # Strong convergence force
                controlled_delta = max(proposed_delta, -20.0)
        
        logger.info(f"Deviation control: {current_deviation:.1f}% + {proposed_delta:.1f} → {controlled_delta:.1f}")
        return controlled_delta 