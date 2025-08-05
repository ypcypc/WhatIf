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
from .repositories import SessionRepository, EventStreamRepository, SnapshotRepository
from .repositories import UnifiedLLMRepository
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
        self.llm_repo = UnifiedLLMRepository()
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
            
            # 4. Create preliminary events for memory tracking
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
                script=None,  # Will be filled by generation
                deviation_delta=0.0,  # Will be updated
                affinity_changes=None,  # Will be updated
                metadata={
                    "session_id": request.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "model": "o4-mini"  # Updated to use o4-mini
                }
            )
            
            # 5. Get temperature directly from configuration
            current_deviation = snapshot.globals.deviation
            config_temperature = self._get_temperature_from_config(current_deviation)
            
            # Allow manual override from request options
            final_temperature = request.options.get("temperature", config_temperature)
            
            logger.info(f"Using temperature {final_temperature} for deviation {current_deviation}")
            
            # 6. Generate structured script using LLM with memory integration
            try:
                generation_result = await self.llm_repo.generate_structured_script(
                    prompt=request.player_choice,  # Pass only the actual player choice
                    context=request.context,
                    current_state=snapshot.globals,
                    temperature=final_temperature,
                    max_tokens=request.options.get("max_tokens", None),  # Uses llm_settings config
                    anchor_info=request.anchor_info,
                    session_id=request.session_id,
                    user_event=user_event,
                    assistant_event=assistant_event,
                    memory_context=enhanced_prompt  # Pass enhanced context as memory
                )
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                # Create minimal fallback generation result
                generation_result = {
                    "script_units": [
                        {
                            "type": "narration",
                            "content": "系统遇到了技术问题，正在尝试恢复中...",
                            "metadata": {"fallback": True, "error": str(e)}
                        },
                        {
                            "type": "interaction",
                            "content": "请选择继续游戏：",
                            "choice_id": "system_recovery",
                            "default_reply": "继续",
                            "metadata": {"fallback": True}
                        }
                    ],
                    "deviation_delta": 0.0,
                    "new_deviation": snapshot.globals.deviation,
                    "affinity_changes": {},
                    "flags_updates": {},
                    "variables_updates": {},
                    "metadata": {"error": str(e), "fallback": True}
                }
            
            # 7. Update global state based on generation result
            updated_globals = self._update_global_state(
                snapshot.globals, 
                generation_result
            )
            
            # 8. Update assistant event with final data - convert raw dicts to ScriptUnit objects
            script_units = []
            script_units_data = generation_result.get("script_units", [])
            
            if not script_units_data:
                # Create fallback script if no units generated
                logger.warning("No script units generated, creating fallback")
                script_units.append(ScriptUnit(
                    type=ScriptUnitType.NARRATION,
                    content="故事暂时停顿了一下，等待着下一个转折点的到来。",
                    metadata={"fallback": True, "error": "No script units generated"}
                ))
                script_units.append(ScriptUnit(
                    type=ScriptUnitType.INTERACTION,
                    content="请选择你的下一步行动：",
                    choice_id="fallback_choice",
                    default_reply="继续",
                    metadata={"fallback": True}
                ))
            else:
                for unit_data in script_units_data:
                    try:
                        # Handle both dict and ScriptUnit objects
                        if isinstance(unit_data, ScriptUnit):
                            script_units.append(unit_data)
                        elif isinstance(unit_data, dict):
                            script_unit = ScriptUnit(
                                type=ScriptUnitType(unit_data.get("type", "narration")),
                                content=unit_data.get("content", ""),
                                speaker=unit_data.get("speaker"),
                                choice_id=unit_data.get("choice_id"),
                                default_reply=unit_data.get("default_reply"),
                                metadata=unit_data.get("metadata", {})
                            )
                            script_units.append(script_unit)
                        else:
                            # Handle unexpected data types
                            logger.warning(f"Unexpected unit data type: {type(unit_data)}")
                            script_units.append(ScriptUnit(
                                type=ScriptUnitType.NARRATION,
                                content=str(unit_data),
                                metadata={"error": f"Unexpected data type: {type(unit_data)}", "original_data": unit_data}
                            ))
                    except Exception as e:
                        logger.error(f"Failed to create ScriptUnit from data {unit_data}: {e}")
                        # Create fallback script unit
                        content = "处理脚本单元时出现错误。"
                        if isinstance(unit_data, dict):
                            content = str(unit_data.get("content", content))
                        elif hasattr(unit_data, 'content'):
                            content = str(unit_data.content)
                        
                        script_units.append(ScriptUnit(
                            type=ScriptUnitType.NARRATION,
                            content=content,
                            metadata={"error": str(e), "original_data": str(unit_data)[:500]}  # Limit data size
                        ))
            
            assistant_event.script = script_units
            assistant_event.deviation_delta = generation_result.get("deviation_delta", 0.0)
            assistant_event.affinity_changes = generation_result.get("affinity_changes", {})
            assistant_event.metadata.update({
                "usage": generation_result.get("usage", {}),
                "generation_config": generation_result.get("generation_config", {})
            })
            
            # 9. Save turn and update snapshot
            await self.session_repo.save_turn(
                request.session_id,
                user_event,
                assistant_event,
                updated_globals
            )
            
            # 10. Build and return response
            response = GenerateResponse(
                script=script_units,
                globals=updated_globals,
                turn_number=current_turn,
                session_id=request.session_id,
                generated_at=datetime.now(),
                deviation_reasoning=generation_result.get("deviation_reasoning"),
                new_deviation=generation_result.get("new_deviation"),
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
        Build enhanced prompt with complete context, history, and state.
        
        Now includes complete historical text instead of summaries,
        as requested for better context preservation.
        
        Args:
            request: Generation request
            snapshot: Current session snapshot
            turn_number: Current turn number
            
        Returns:
            Enhanced prompt string with complete history
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
        
        # Add complete conversation history (not just summary)
        # Include ALL previous turns with complete text
        if snapshot.recent:
            prompt_parts.append(f"\n历史记录（完整文本）:")
            prompt_parts.append("=" * 50)
            
            # Include all events, not just last 5
            for i, event in enumerate(snapshot.recent):
                if event.role == TurnEventRole.USER:
                    prompt_parts.append(f"\n【第{event.t}轮 - 玩家选择】")
                    prompt_parts.append(f"{event.choice or event.anchor}")
                    
                elif event.role == TurnEventRole.ASSISTANT and event.script:
                    prompt_parts.append(f"\n【第{event.t}轮 - 生成的脚本】")
                    # Include complete script content as pure text without type markers
                    for unit in event.script:
                        if isinstance(unit, ScriptUnit):
                            unit_content = unit.content
                            
                            # Format based on type but without explicit type markers
                            if unit.speaker:
                                # Dialogue: show speaker and content
                                prompt_parts.append(f"{unit.speaker}: {unit_content}")
                            else:
                                # Narration or interaction: just show content
                                prompt_parts.append(unit_content)
                            
                            # For interactions, include the choice info in natural format
                            if unit.type == ScriptUnitType.INTERACTION and unit.default_reply:
                                prompt_parts.append(f"（默认选择：{unit.default_reply}）")
                                
                        elif isinstance(unit, dict):
                            unit_content = unit.get("content", "")
                            speaker = unit.get("speaker", "")
                            unit_type = unit.get("type", "")
                            
                            # Format based on type but without explicit type markers
                            if speaker:
                                # Dialogue: show speaker and content
                                prompt_parts.append(f"{speaker}: {unit_content}")
                            else:
                                # Narration or interaction: just show content
                                prompt_parts.append(unit_content)
                            
                            # For interactions, include the choice info in natural format
                            if unit_type == "interaction" and unit.get("default_reply"):
                                prompt_parts.append(f"（默认选择：{unit.get('default_reply')}）")
            
            prompt_parts.append("=" * 50)
        
        # Add current context from anchor_service (only for subsequent turns)
        if turn_number > 1 and request.context:
            prompt_parts.append(f"\n当前锚点情境:")
            # Include more context for better understanding
            prompt_parts.append(request.context)
        
        # Add generation instructions from config
        from .llm_settings import llm_settings
        
        config = llm_settings.get_generation_config(snapshot.globals.deviation)
        target_counts = llm_settings.get_required_counts(snapshot.globals.deviation, len(request.context))
        
        # Build enhanced prompt section using existing methods
        enhanced_prompt_section = llm_settings.build_game_state_details(
            current_state=snapshot.globals.model_dump(),
            target_counts=target_counts
        )
        
        prompt_parts.append(enhanced_prompt_section)
        
        # NOTE: Player choice is now handled separately in the user message
        # to ensure it gets proper <PLAYER_CHOICE> marking
        
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
        new_state.deviation = max(0.0, min(1.0, new_state.deviation + controlled_delta))
        
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
    
    def _get_temperature_from_config(self, deviation: float) -> float:
        """
        Get temperature directly from configuration - single source of truth.
        
        Args:
            deviation: Current deviation value (0.0 - 1.0 as decimal)
            
        Returns:
            Temperature value from configuration file only
        """
        # Import the settings module
        from .llm_settings import llm_settings
        
        # Get temperature directly from configuration without any overrides
        generation_config = llm_settings.get_generation_config(deviation)
        temperature = generation_config.temperature
        
        # Log the configuration source
        logger.info(f"Using temperature from config: deviation={deviation:.2f} ({deviation*100:.1f}%), "
                   f"config_temp={temperature}")
        
        return temperature
    
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
        - deviation < 0.05 → allow small increases
        - 0.05 ≤ deviation ≤ 0.3 → allow moderate changes
        - > 0.3 → force convergence back to main storyline
        
        Args:
            current_deviation: Current deviation ratio (0-1 scale)
            proposed_delta: Proposed deviation change (0-1 scale)
            
        Returns:
            Controlled deviation delta (0-1 scale)
        """
        if current_deviation < 0.05:
            # Low deviation: allow slight increases, cap at 0.05
            controlled_delta = min(proposed_delta, 0.05)
            
        elif current_deviation <= 0.3:
            # Medium deviation: allow moderate changes, slight bias toward convergence
            if proposed_delta > 0:
                # Reduce large increases
                controlled_delta = min(proposed_delta, 0.10)
            else:
                # Allow full decreases
                controlled_delta = proposed_delta
                
        elif current_deviation <= 0.6:
            # High deviation: strong bias toward convergence
            if proposed_delta > 0:
                # Severely limit increases
                controlled_delta = min(proposed_delta, 0.02)
            else:
                # Encourage decreases
                controlled_delta = max(proposed_delta, -0.15)
                
        else:
            # Very high deviation: force convergence
            if proposed_delta > 0:
                # No increases allowed
                controlled_delta = 0.0
            else:
                # Strong convergence force
                controlled_delta = max(proposed_delta, -0.20)
        
        logger.info(f"Deviation control: {current_deviation:.3f} + {proposed_delta:.3f} → {controlled_delta:.3f}")
        return controlled_delta 