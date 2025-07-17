"""
LLM Service Data Access Layer

Handles:
- Event stream storage (JSONL format)
- Snapshot storage (JSON format)
- LangChain integration for summarization
- OpenAI API interactions
- Automatic memory management with summarization
"""

import json
import os
import logging
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from pathlib import Path
from datetime import datetime
import aiofiles
from openai import AsyncOpenAI
from openai import OpenAIError

# 修复1：更新LangChain导入路径到0.3兼容版本（2025年优化）
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

# 修复verbose导入警告
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="langchain")

import tenacity
from typing import List, cast, Any

from .models import TurnEvent, Snapshot, ScriptUnit, GlobalState, TurnEventRole, ScriptUnitType
from .llm_config import llm_config, DeviationLevel, GenerationConfig
from backend_services.app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """简单的速率限制器"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """获取一个请求令牌"""
        async with self.lock:
            now = datetime.now()
            # 清理过期的请求记录
            cutoff = now.timestamp() - self.time_window
            self.requests = [req for req in self.requests if req > cutoff]
            
            # 检查是否超过限制
            if len(self.requests) >= self.max_requests:
                sleep_time = self.time_window - (now.timestamp() - self.requests[0])
                if sleep_time > 0:
                    logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()
            
            # 记录新请求
            self.requests.append(now.timestamp())
            return True


class EventStreamRepository:
    """
    Repository for event stream storage using JSONL format.
    
    Handles:
    - Appending events to session JSONL files
    - Reading event history
    - Event persistence and recovery
    """
    
    def __init__(self, data_dir: str = "data/sessions"):
        """Initialize event stream repository."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_event_file_path(self, session_id: str) -> Path:
        """Get JSONL file path for session events."""
        return self.data_dir / f"{session_id}.jsonl"
    
    async def append_event(self, session_id: str, event: TurnEvent) -> None:
        """
        Append event to session JSONL file.
        
        Args:
            session_id: Session identifier
            event: Event to append
        """
        file_path = self._get_event_file_path(session_id)
        
        try:
            async with aiofiles.open(file_path, 'a', encoding='utf-8') as f:
                await f.write(json.dumps(event.model_dump(), ensure_ascii=False) + '\n')
            logger.debug(f"Appended event to {session_id}: turn {event.t}")
        except Exception as e:
            logger.error(f"Failed to append event to {session_id}: {e}")
            raise
    
    async def read_events(self, session_id: str, from_turn: int = 0) -> List[TurnEvent]:
        """
        Read events from session JSONL file.
        
        Args:
            session_id: Session identifier
            from_turn: Starting turn number (inclusive)
            
        Returns:
            List of events from the specified turn
        """
        file_path = self._get_event_file_path(session_id)
        
        if not file_path.exists():
            return []
        
        events = []
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                lines = await f.readlines()
                for line in lines:
                    if line.strip():
                        event_data = json.loads(line)
                        event = TurnEvent(**event_data)
                        if event.t >= from_turn:
                            events.append(event)
            
            logger.debug(f"Read {len(events)} events from {session_id}")
            return events
        except Exception as e:
            logger.error(f"Failed to read events from {session_id}: {e}")
            raise
    
    async def get_latest_turn(self, session_id: str) -> int:
        """
        Get the latest turn number for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Latest turn number, or 0 if no events
        """
        file_path = self._get_event_file_path(session_id)
        
        if not file_path.exists():
            return 0
        
        try:
            # Optimized: read from end of file to get last line
            async with aiofiles.open(file_path, 'rb') as f:
                # Seek to end
                await f.seek(0, os.SEEK_END)
                file_size = await f.tell()
                
                if file_size == 0:
                    return 0
                
                # Read backwards to find last complete line
                buffer_size = min(8192, file_size)  # Read last 8KB or entire file
                await f.seek(file_size - buffer_size)
                
                # Read and decode
                buffer = await f.read()
                content = buffer.decode('utf-8')
                
                # Find last complete line
                lines = content.split('\n')
                for line in reversed(lines):
                    if line.strip():
                        event_data = json.loads(line)
                        return event_data.get('t', 0)
                
                return 0
        except Exception as e:
            logger.error(f"Failed to get latest turn for {session_id}: {e}")
            return 0


class SnapshotRepository:
    """
    Repository for snapshot storage using JSON format.
    
    Handles:
    - Snapshot creation and updates
    - Snapshot retrieval and caching
    - Snapshot size management
    """
    
    def __init__(self, data_dir: str = "data/sessions"):
        """Initialize snapshot repository."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_snapshot_file_path(self, session_id: str) -> Path:
        """Get JSON file path for session snapshot."""
        return self.data_dir / f"{session_id}_snapshot.json"
    
    async def save_snapshot(self, snapshot: Snapshot) -> None:
        """
        Save snapshot to JSON file.
        
        Args:
            snapshot: Snapshot to save
        """
        file_path = self._get_snapshot_file_path(snapshot.session_id)
        
        try:
            # Update timestamp
            snapshot.updated_at = datetime.now()
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                json_content = snapshot.model_dump_json(indent=2)
                await f.write(json_content)
            
            logger.debug(f"Saved snapshot for {snapshot.session_id}")
        except Exception as e:
            logger.error(f"Failed to save snapshot for {snapshot.session_id}: {e}")
            raise
    
    async def load_snapshot(self, session_id: str) -> Optional[Snapshot]:
        """
        Load snapshot from JSON file.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Snapshot if exists, None otherwise
        """
        file_path = self._get_snapshot_file_path(session_id)
        
        if not file_path.exists():
            return None
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                data = await f.read()
                snapshot_data = json.loads(data)
                return Snapshot(**snapshot_data)
        except Exception as e:
            logger.error(f"Failed to load snapshot for {session_id}: {e}")
            return None
    
    async def get_snapshot_size(self, session_id: str) -> int:
        """
        Get snapshot file size in bytes.
        
        Args:
            session_id: Session identifier
            
        Returns:
            File size in bytes, or 0 if not exists
        """
        file_path = self._get_snapshot_file_path(session_id)
        
        if not file_path.exists():
            return 0
        
        try:
            return file_path.stat().st_size
        except Exception as e:
            logger.error(f"Failed to get snapshot size for {session_id}: {e}")
            return 0
    
    async def create_initial_snapshot(self, session_id: str, protagonist: str) -> Snapshot:
        """
        Create initial snapshot for a new session.
        
        Args:
            session_id: Session identifier
            protagonist: Main character identifier
            
        Returns:
            Initial snapshot
        """
        snapshot = Snapshot(
            session_id=session_id,
            protagonist=protagonist,
            globals=GlobalState(deviation=0.0),
            summary=None,
            recent=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version=1
        )
        
        await self.save_snapshot(snapshot)
        return snapshot


class LLMRepository:
    """
    Repository for LLM API interactions and chain management.
    
    Handles:
    - OpenAI API calls with structured outputs
    - LangChain chain configuration
    - Memory management and summarization
    """
    
    def __init__(self):
        """Initialize LLM repository."""
        self.openai_client = None
        self.langchain_llm = None
        self.rate_limiter = RateLimiter(max_requests=30, time_window=60)  # 每分钟30个请求
        
        # Content balance tracking
        self._last_generation_stats = {}  # session_id -> {narration_count, dialogue_count}
        
        self._init_clients()
    
    def _init_clients(self):
        """Initialize OpenAI and LangChain clients."""
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured")
            return
        
        try:
            # Initialize OpenAI client
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            
            # Initialize LangChain ChatOpenAI (2025年优化：依赖环境变量)
            self.langchain_llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.3
            )
            
            logger.info("Initialized OpenAI and LangChain clients")
        except Exception as e:
            logger.error(f"Failed to initialize LLM clients: {e}")
    
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
        retry=tenacity.retry_if_exception_type((OpenAIError, json.JSONDecodeError)),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING)
    )
    async def generate_structured_script(
        self,
        prompt: str,
        context: str,
        current_state: GlobalState,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        anchor_info: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate structured script using OpenAI with improved content balance control.
        
        Implements the enhanced prompt strategy to reduce narrator overuse and
        improve dialogue-to-narration ratios based on deviation levels.
        
        Args:
            prompt: User action/choice
            context: Context from anchor_service
            current_state: Current global state
            temperature: Base sampling temperature (will be adjusted based on content balance)
            max_tokens: Maximum tokens
            anchor_info: Optional anchor information for choice event generation
            session_id: Session ID for tracking generation stats
            
        Returns:
            Structured generation result with balanced content
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        # 应用速率限制
        await self.rate_limiter.acquire()
        
        try:
            # Get generation configuration based on deviation level
            deviation = current_state.deviation
            config = llm_config.get_generation_config(deviation)
            target_counts = llm_config.get_required_counts(deviation)
            
            # Use config values as defaults
            final_temperature = temperature if temperature is not None else config.temperature
            final_max_tokens = max_tokens if max_tokens is not None else config.max_tokens
            
            # Check if temperature adjustment is needed based on last generation
            if session_id and session_id in self._last_generation_stats:
                last_stats = self._last_generation_stats[session_id]
                should_adjust, adjusted_temp = llm_config.should_adjust_temperature(
                    deviation,
                    last_stats.get('narration_count', 0),
                    last_stats.get('dialogue_count', 0)
                )
                if should_adjust:
                    final_temperature = adjusted_temp
                    logger.info(f"Adjusted temperature to {adjusted_temp} for better content balance")
            # Get tools and messages from config
            tools = self._build_tools_from_config(deviation)
            system_message = self._build_system_message_from_config(
                current_state, context, target_counts, config
            )
            
            # Build user message from config
            user_message = self._build_user_message_from_config(
                context, prompt, anchor_info, current_state, target_counts, config
            )
            
            # Make API call with optimized parameters
            response = await self._make_openai_request(
                system_message, user_message, tools, final_temperature, final_max_tokens
            )
            
            # 更安全的响应解析
            if not response.choices or not response.choices[0].message.tool_calls:
                logger.error("No tool calls returned from OpenAI API")
                return {
                    "error": True,
                    "error_type": "no_tool_calls",
                    "error_message": "No tool calls returned from OpenAI API",
                    "retry": True
                }
            
            tool_call = response.choices[0].message.tool_calls[0]
            
            try:
                result = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool call arguments: {e}")
                return {
                    "error": True,
                    "error_type": "json_parse_error",
                    "error_message": f"Failed to parse tool call arguments: {e}",
                    "retry": True
                }
            
            # Convert to ScriptUnit objects
            script_units = []
            for unit_data in result.get("script_units", []):
                try:
                    unit_type = ScriptUnitType(unit_data["type"])
                    script_units.append(ScriptUnit(
                        type=unit_type,
                        content=unit_data["content"],
                        speaker=unit_data.get("speaker"),
                        choice_id=unit_data.get("choice_id"),
                        default_reply=unit_data.get("default_reply"),
                        metadata=unit_data.get("metadata", {})
                    ))
                except (KeyError, ValueError) as e:
                    logger.error(f"Invalid script unit data: {unit_data}, error: {e}")
                    continue
            
            # Get usage info
            usage_info = {}
            if response.usage:
                usage_info = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            
            # Track content balance statistics for next generation
            if session_id:
                narration_count = sum(1 for unit in script_units if unit.type == ScriptUnitType.NARRATION)
                dialogue_count = sum(1 for unit in script_units if unit.type in [ScriptUnitType.DIALOGUE])
                
                self._last_generation_stats[session_id] = {
                    'narration_count': narration_count,
                    'dialogue_count': dialogue_count,
                    'total_count': len(script_units)
                }
                
                logger.info(f"Content balance for {session_id}: {narration_count} narration, {dialogue_count} dialogue")
            
            # Validate and fix script structure
            script_units = self._ensure_valid_script_structure(script_units, session_id)
            
            # Validate content counts match targets
            actual_counts = result.get("required_counts", {})
            if not actual_counts:
                # Calculate actual counts if not provided
                actual_counts = {
                    "narration": sum(1 for unit in script_units if unit.type == ScriptUnitType.NARRATION),
                    "dialogue": sum(1 for unit in script_units if unit.type == ScriptUnitType.DIALOGUE),
                    "interaction": sum(1 for unit in script_units if unit.type == ScriptUnitType.INTERACTION)
                }
            
            return {
                "script_units": script_units,
                "required_counts": actual_counts,
                "target_counts": target_counts,
                "deviation_delta": result.get("deviation_delta", 0.0),
                "affinity_changes": result.get("affinity_changes", {}),
                "flags_updates": result.get("flags_updates", {}),
                "variables_updates": result.get("variables_updates", {}),
                "usage": usage_info,
                "generation_config": {
                    "temperature": final_temperature,
                    "original_temperature": temperature,
                    "deviation_level": llm_config.get_deviation_level(deviation).value,
                    "dialogue_ratio_target": config.dialogue_ratio_target
                }
            }
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            # Return fallback response from config
            if session_id:
                fallback = llm_config.get_fallback_response(session_id, str(e))
                return fallback
            return {
                "error": True,
                "error_type": "openai_error",
                "error_message": str(e),
                "retry": True
            }
        except Exception as e:
            logger.error(f"Failed to generate structured script: {e}")
            # Return fallback response from config
            if session_id:
                fallback = llm_config.get_fallback_response(session_id, str(e))
                return fallback
            raise
    
    async def summarize_events(self, events: List[TurnEvent]) -> str:
        """
        使用新的LangChain API进行事件摘要
        
        Args:
            events: List of events to summarize
            
        Returns:
            Summarized conversation history
        """
        if not self.langchain_llm:
            raise ValueError("LangChain LLM not initialized")
        
        try:
            # 将事件转换为文本内容
            conversation_parts = []
            for event in events:
                if event.role == TurnEventRole.USER:
                    user_content = f"玩家选择: {event.choice or event.anchor}"
                    conversation_parts.append(f"用户: {user_content}")
                elif event.role == TurnEventRole.ASSISTANT and event.script:
                    assistant_content = "\n".join([unit.content for unit in event.script])
                    conversation_parts.append(f"助手: {assistant_content}")
            
            # 组合所有对话内容
            full_text = "\n".join(conversation_parts)
            
            # 如果文本为空，返回空摘要
            if not full_text.strip():
                return ""
            
            # 使用配置文件的摘要模板
            summary_prompt = PromptTemplate(
                input_variables=["text"],
                template=llm_config.get_summarization_prompt()
            )
            
            # 使用LCEL替代deprecated LLMChain
            chain = summary_prompt | self.langchain_llm | StrOutputParser()
            
            # 如果文本太长，进行分块处理
            if len(full_text) > 8000:  # 大约4000 tokens
                # 分块摘要
                chunks = self._split_text_into_chunks(full_text, 4000)
                summaries = []
                
                for chunk in chunks:
                    try:
                        # 使用LCEL chain.ainvoke方法
                        summary = await chain.ainvoke({"text": chunk})
                        summaries.append(summary)
                    except Exception as e:
                        logger.error(f"Failed to summarize chunk: {e}")
                        continue
                
                # 合并摘要
                combined_summary = " ".join(summaries)
                
                # 对合并后的摘要再次摘要
                if len(combined_summary) > 2000:
                    final_summary = await chain.ainvoke({"text": combined_summary})
                    return final_summary
                else:
                    return combined_summary
            else:
                # 直接摘要
                summary = await chain.ainvoke({"text": full_text})
                return summary
            
        except Exception as e:
            logger.error(f"Failed to summarize events: {e}")
            # 返回一个基本的摘要
            return f"对话摘要生成失败，共处理了 {len(events)} 个事件。"
    
    
    def _split_text_into_chunks(self, text: str, max_length: int) -> List[str]:
        """
        将文本分割成块
        
        Args:
            text: 要分割的文本
            max_length: 每块的最大长度
            
        Returns:
            分割后的文本块列表
        """
        chunks = []
        sentences = text.split('\n')
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk += sentence + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + "\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _build_tools_from_config(self, deviation: float) -> List[Dict[str, Any]]:
        """Build tools array from config."""
        function_schema = llm_config.get_function_schema_with_counts(deviation)
        return [
            {
                "type": "function",
                "function": function_schema
            }
        ]
    
    def _build_system_message_from_config(
        self, 
        current_state: GlobalState, 
        context: str, 
        target_counts: Dict[str, int], 
        config: GenerationConfig
    ) -> str:
        """Build system message from config."""
        # Build enhanced system prompt using config
        system_message = llm_config.build_system_prompt(
            deviation=current_state.deviation,
            current_state=current_state.model_dump(),
            context_length=len(context)
        )
        
        # Add game state details from config
        system_message += llm_config.build_game_state_details(
            current_state.model_dump(),
            target_counts
        )
        
        return system_message
    
    def _build_user_message_from_config(
        self,
        context: str,
        prompt: str,
        anchor_info: Optional[Dict[str, Any]],
        current_state: GlobalState,
        target_counts: Dict[str, int],
        config: GenerationConfig
    ) -> str:
        """Build user message from config."""
        return llm_config.build_user_message(
            context=context,
            prompt=prompt,
            anchor_info=anchor_info,
            current_state=current_state.model_dump(),
            target_counts=target_counts,
            config=config
        )
    
    def _ensure_valid_script_structure(self, script_units: List[ScriptUnit], session_id: Optional[str]) -> List[ScriptUnit]:
        """Ensure script has valid structure with interaction unit at the end."""
        if not script_units:
            logger.error(f"Empty script units for session {session_id}")
            # Return fallback script
            return [
                ScriptUnit(
                    type=ScriptUnitType.NARRATION,
                    content="故事继续展开...",
                    metadata={"fallback": True}
                ),
                ScriptUnit(
                    type=ScriptUnitType.INTERACTION,
                    content="你想要如何继续？",
                    choice_id="fallback_choice",
                    default_reply="继续",
                    metadata={"fallback": True}
                )
            ]
        
        # Check if last unit is interaction
        has_interaction = any(unit.type == ScriptUnitType.INTERACTION for unit in script_units)
        last_is_interaction = script_units[-1].type == ScriptUnitType.INTERACTION
        
        if not has_interaction or not last_is_interaction:
            logger.warning(f"Script missing proper interaction unit for session {session_id}, adding fallback")
            
            # Remove any existing interaction units that are not at the end
            script_units = [unit for unit in script_units if unit.type != ScriptUnitType.INTERACTION]
            
            # Add fallback interaction unit
            script_units.append(ScriptUnit(
                type=ScriptUnitType.INTERACTION,
                content="请选择你的下一步行动：",
                choice_id="continue_story",
                default_reply="继续",
                metadata={"fallback_added": True}
            ))
        
        return script_units
    
    async def _make_openai_request(
        self,
        system_message: str,
        user_message: str,
        tools: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int
    ):
        """Make OpenAI API request with standardized parameters."""
        return await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            tools=cast(Any, tools),
            tool_choice={"type": "function", "function": {"name": tools[0]["function"]["name"]}},
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check LLM service health.
        
        Returns:
            Health status information
        """
        status = {
            "openai_available": self.openai_client is not None,
            "langchain_available": self.langchain_llm is not None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Test OpenAI API
        if self.openai_client:
            try:
                # 使用更安全的健康检查
                models = await self.openai_client.models.list()
                status["openai_status"] = "healthy"
                status["available_models"] = len(models.data) if models.data else 0
            except Exception as e:
                status["openai_status"] = f"error: {str(e)[:100]}"
        
        return status


class SessionRepository:
    """
    High-level repository for session management.
    
    Coordinates event stream, snapshot, and LLM repositories.
    Handles automatic summarization and memory management.
    """
    
    def __init__(self):
        """Initialize session repository."""
        self.event_repo = EventStreamRepository()
        self.snapshot_repo = SnapshotRepository()
        self.llm_repo = LLMRepository()
        
        # Configuration
        self.max_recent_events = 50
        self.max_snapshot_size = 32 * 1024  # 32KB
        self.summarization_batch_size = 30
    
    async def get_or_create_session(self, session_id: str, protagonist: str) -> Snapshot:
        """
        Get existing session or create new one.
        
        Args:
            session_id: Session identifier
            protagonist: Main character identifier
            
        Returns:
            Session snapshot
        """
        # Try to load existing snapshot
        snapshot = await self.snapshot_repo.load_snapshot(session_id)
        
        if snapshot is None:
            # Create new session
            snapshot = await self.snapshot_repo.create_initial_snapshot(session_id, protagonist)
            logger.info(f"Created new session: {session_id}")
        
        return snapshot
    
    async def save_turn(
        self,
        session_id: str,
        user_event: TurnEvent,
        assistant_event: TurnEvent,
        updated_globals: GlobalState
    ) -> Snapshot:
        """
        Save a complete turn (user action + assistant response).
        
        Args:
            session_id: Session identifier
            user_event: User action event
            assistant_event: Assistant response event
            updated_globals: Updated global state
            
        Returns:
            Updated snapshot
        """
        # Append events to stream
        await self.event_repo.append_event(session_id, user_event)
        await self.event_repo.append_event(session_id, assistant_event)
        
        # Load current snapshot
        snapshot = await self.snapshot_repo.load_snapshot(session_id)
        if not snapshot:
            raise ValueError(f"Snapshot not found for session: {session_id}")
        
        # Update snapshot
        snapshot.recent.extend([user_event, assistant_event])
        snapshot.globals = updated_globals
        snapshot.updated_at = datetime.now()
        
        # Check if summarization is needed
        await self._check_and_summarize(snapshot)
        
        # Save updated snapshot
        await self.snapshot_repo.save_snapshot(snapshot)
        
        return snapshot
    
    async def _check_and_summarize(self, snapshot: Snapshot) -> None:
        """
        Check if summarization is needed and perform it.
        
        Args:
            snapshot: Current snapshot
        """
        needs_summarization = False
        
        # Check number of recent events
        if len(snapshot.recent) > self.max_recent_events:
            needs_summarization = True
            logger.info(f"Summarization needed: {len(snapshot.recent)} recent events")
        
        # Check snapshot size (fixed byte calculation)
        snapshot_json = snapshot.model_dump_json()
        snapshot_size = len(snapshot_json.encode('utf-8'))
        if snapshot_size > self.max_snapshot_size:
            needs_summarization = True
            logger.info(f"Summarization needed: snapshot size {snapshot_size} bytes")
        
        if needs_summarization:
            await self._perform_summarization(snapshot)
    
    async def _perform_summarization(self, snapshot: Snapshot) -> None:
        """
        改进摘要逻辑，避免无限循环
        
        Args:
            snapshot: Snapshot to summarize
        """
        try:
            # 检查是否有足够的事件需要摘要
            if not snapshot.recent or len(snapshot.recent) < 2:
                logger.debug("No sufficient recent events to summarize")
                return
            
            # 安全的批量大小计算
            batch_size = min(
                self.summarization_batch_size, 
                len(snapshot.recent) - 1,  # 保留至少一个事件
                max(1, len(snapshot.recent) // 2)  # 至少处理一半
            )
            
            if batch_size <= 0:
                logger.debug("Batch size too small, skipping summarization")
                return
            
            # 获取要摘要的事件
            events_to_summarize = snapshot.recent[:batch_size]
            
            # 生成摘要
            new_summary = await self.llm_repo.summarize_events(events_to_summarize)
            
            # 组合摘要
            if snapshot.summary:
                # 如果现有摘要太长，也进行压缩
                if len(snapshot.summary) > 2000:
                    # 对现有摘要进行压缩
                    compressed_summary = snapshot.summary[:1500] + "...[摘要被压缩]"
                    snapshot.summary = f"{compressed_summary}\n\n{new_summary}"
                else:
                    snapshot.summary = f"{snapshot.summary}\n\n{new_summary}"
            else:
                snapshot.summary = new_summary
            
            # 更新recent列表
            snapshot.recent = snapshot.recent[batch_size:]
            
            logger.info(f"Summarized {len(events_to_summarize)} events for {snapshot.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to perform summarization: {e}")
            # 摘要失败时的备用方案：直接移除最老的事件
            if len(snapshot.recent) > self.max_recent_events:
                remove_count = len(snapshot.recent) - self.max_recent_events
                snapshot.recent = snapshot.recent[remove_count:]
                logger.info(f"Removed {remove_count} old events due to summarization failure")