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
import hashlib
import time
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
from typing import cast

from .models import TurnEvent, Snapshot, ScriptUnit, GlobalState, TurnEventRole, ScriptUnitType
from .llm_settings import llm_settings, DeviationLevel, GenerationConfig
from .memory_manager import ModernMemoryManager, ContextWindow
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
                sleep_time = max(0, self.time_window - (now.timestamp() - self.requests[0]))
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
                        
                        # Convert script dictionaries to ScriptUnit objects
                        if event_data.get('script') and isinstance(event_data['script'], list):
                            script_units = []
                            for unit_data in event_data['script']:
                                if isinstance(unit_data, dict):
                                    try:
                                        script_unit = ScriptUnit(
                                            type=ScriptUnitType(unit_data.get("type", "narration")),
                                            content=unit_data.get("content", ""),
                                            speaker=unit_data.get("speaker"),
                                            choice_id=unit_data.get("choice_id"),
                                            default_reply=unit_data.get("default_reply"),
                                            metadata=unit_data.get("metadata", {})
                                        )
                                        script_units.append(script_unit)
                                    except (KeyError, ValueError) as e:
                                        logger.warning(f"Invalid script unit data in stored event: {unit_data}, error: {e}")
                                        continue
                                elif isinstance(unit_data, ScriptUnit):
                                    script_units.append(unit_data)
                            event_data['script'] = script_units
                        
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
                        turn_number = event_data.get('t', 0)
                        return int(turn_number) if isinstance(turn_number, (int, float)) else 0
                
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


class UnifiedLLMRepository:
    """
    Unified repository for LLM operations supporting multiple providers.
    
    Handles:
    - Multiple LLM providers (OpenAI, Gemini, etc.)
    - Unified API interface across providers
    - Memory management and summarization
    - Provider switching and configuration
    """
    
    def __init__(self):
        """Initialize unified LLM repository."""
        # Import provider system
        from .providers import get_llm_provider, LLMProviderFactory
        
        # Initialize current provider
        self.provider = get_llm_provider()
        self.provider_factory = LLMProviderFactory
        
        # Legacy OpenAI client for summarization (deprecated)
        self.openai_client = None
        self.langchain_llm = None
        
        # Use rate limiting from settings
        self.rate_limiter = RateLimiter(
            max_requests=llm_settings.rate_limit_requests, 
            time_window=llm_settings.rate_limit_window
        )
        
        # Content balance tracking
        self._last_generation_stats = {}  # session_id -> {narration_count, dialogue_count}
        
        # Request deduplication tracking  
        self._pending_requests = {}  # request_hash -> asyncio.Task
        self._request_cache = {}  # request_hash -> (result, timestamp)
        self._session_locks = {}  # session_id -> asyncio.Lock (prevent concurrent sessions)
        self._cache_timeout = 30  # seconds
        
        # Initialize modern memory manager
        self.memory_manager = ModernMemoryManager()
        
        # Initialize legacy clients for backward compatibility (deprecated - now using unified provider)
        # self._init_legacy_clients()
        
        logger.info(f"Initialized unified repository with {self.provider.provider.value} provider")
    
    def _init_legacy_clients(self):
        """Initialize legacy OpenAI and LangChain clients for backward compatibility."""
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured")
            return
        
        try:
            # Initialize OpenAI client
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            
            # Initialize LangChain ChatOpenAI using settings
            self.langchain_llm = ChatOpenAI(
                model=llm_settings.summarization_model,
                temperature=llm_settings.summarization_temperature,
                max_tokens=llm_settings.summarization_max_tokens
            )
            
            logger.info("Initialized OpenAI and LangChain clients")
        except Exception as e:
            logger.error(f"Failed to initialize LLM clients: {e}")
    
    # Unified Provider Interface Methods
    def switch_provider(self, provider: str, model: str = None) -> None:
        """
        Switch to a different LLM provider.
        
        Args:
            provider: Provider name (openai, gemini, etc.)
            model: Model name (optional)
        """
        from .providers import switch_provider
        self.provider = switch_provider(provider, model)
        logger.info(f"Repository switched to {provider} provider")
    
    def get_current_provider_info(self) -> Dict[str, Any]:
        """
        Get information about the current provider.
        
        Returns:
            Dictionary with provider information
        """
        return {
            "provider": self.provider.provider.value,
            "model": self.provider.model_name,
            "info": self.provider.get_model_info()
        }
    
    async def generate_summary(self, text: str, max_length: int = 500) -> str:
        """
        Generate a summary using the current provider.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            
        Returns:
            Summary text
        """
        return await self.provider.generate_summary(text, max_length)
    
    def _create_request_hash(self, prompt: str, context: str, session_id: str, 
                           deviation: float, temperature: float) -> str:
        """Create a hash for request deduplication."""
        # Use more stable elements for hashing to prevent minor variations
        stable_context = context[:200] if context else ""  # More context for stability
        stable_prompt = prompt[:100] if prompt else ""  # Include player choice in hash
        # Round temperature to avoid floating point precision issues
        stable_temp = round(temperature, 1)
        stable_deviation = round(deviation, 2)
        request_str = f"{session_id}:{stable_context}:{stable_prompt}:{stable_deviation}:{stable_temp}"
        return hashlib.md5(request_str.encode()).hexdigest()
    
    def _cleanup_cache(self):
        """Clean up expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._request_cache.items()
            if current_time - timestamp > self._cache_timeout
        ]
        for key in expired_keys:
            del self._request_cache[key]
    
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
        session_id: Optional[str] = None,
        user_event: Optional[TurnEvent] = None,
        assistant_event: Optional[TurnEvent] = None,
        memory_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate structured script using the current LLM provider.
        
        Uses the unified provider system to support multiple LLM backends
        while maintaining the same interface and content balance control.
        
        Args:
            prompt: User action/choice
            context: Context from anchor_service
            current_state: Current global state
            temperature: Base sampling temperature (will be adjusted based on content balance)
            max_tokens: Maximum tokens
            anchor_info: Optional anchor information for choice event generation
            session_id: Session ID for tracking generation stats
            user_event: User turn event
            assistant_event: Assistant turn event  
            memory_context: Memory/history context
            
        Returns:
            Structured generation result with balanced content
        """
        # Initialize memory_context immediately to prevent UnboundLocalError in exception handlers
        if memory_context is None:
            memory_context = ""
        
        if not self.provider:
            raise ValueError("LLM provider not initialized")
        
        # Clean up expired cache entries
        self._cleanup_cache()
        
        # Get or create session lock to prevent concurrent requests for same session
        session_key = session_id or "unknown"
        if session_key not in self._session_locks:
            self._session_locks[session_key] = asyncio.Lock()
        session_lock = self._session_locks[session_key]
        
        # Use session lock to prevent race conditions
        async with session_lock:
            # Create request hash for deduplication
            request_hash = self._create_request_hash(
                prompt, context, session_key, 
                current_state.deviation, temperature or 0.7
            )
            
            # Check if this exact request is already being processed
            if request_hash in self._pending_requests:
                logger.info(f"🚫 Duplicate request detected, waiting for existing request: {request_hash[:8]}")
                try:
                    return await self._pending_requests[request_hash]
                except asyncio.CancelledError:
                    logger.info(f"Existing request was cancelled, processing new one: {request_hash[:8]}")
            
            # Check cache for recent identical requests (but reduce caching for interaction generation)
            cache_timeout = self._cache_timeout * 0.5 if prompt else self._cache_timeout  # Shorter cache for user interactions
            if request_hash in self._request_cache:
                result, timestamp = self._request_cache[request_hash]
                if time.time() - timestamp < cache_timeout:
                    logger.info(f"🔄 Returning cached result for request: {request_hash[:8]} (timeout: {cache_timeout}s)")
                    return result
            
            # 应用速率限制
            await self.rate_limiter.acquire()
            
            # Create and register the generation task
            async def _perform_generation():
                nonlocal memory_context
                    
                try:
                    # Store player choice for duplicate detection
                    self._last_player_choice = prompt if prompt else ""
                    
                    # Get memory context - use provided context or build from memory manager
                    if not memory_context and session_id:
                        try:
                            context_window = await self.memory_manager.get_context_window(
                                session_id, context, prompt
                            )
                            # Keep memory separate - don't mix with source context
                            memory_context = self.memory_manager.build_memory_context(context_window)
                        except Exception as e:
                            logger.warning(f"Failed to build memory context: {e}")
                            memory_context = ""  # Fallback to empty
                    
                    # Ensure memory_context is always a string
                    memory_context = str(memory_context) if memory_context else ""
                    
                    source_context = context  # This is the actual text to be rewritten
                    
                    # Get generation configuration based on deviation level
                    deviation = current_state.deviation
                    config = llm_settings.get_generation_config(deviation)
                    target_counts = llm_settings.get_required_counts(deviation, len(source_context))
                    
                    # Use config values as defaults
                    final_temperature = temperature if temperature is not None else config.temperature
                    final_max_tokens = max_tokens if max_tokens is not None else config.max_tokens
                    
                    # Check if temperature adjustment is needed based on last generation
                    if session_id and session_id in self._last_generation_stats:
                        last_stats = self._last_generation_stats[session_id]
                        should_adjust, adjusted_temp = llm_settings.should_adjust_temperature(
                            deviation,
                            last_stats.get('narration_count', 0),
                            last_stats.get('dialogue_count', 0)
                        )
                        if should_adjust:
                            final_temperature = adjusted_temp
                            logger.info(f"Adjusted temperature to {adjusted_temp} for better content balance")
                            
                    # Get tools and messages from config
                    tools = self._build_tools_from_config(deviation, len(source_context))
                    system_message = self._build_system_message_from_config(
                        current_state, context, target_counts, config
                    )
                    
                    # Build user message with separated memory and source context
                    user_message = self._build_user_message_from_config(
                        source_context, memory_context, prompt, anchor_info, current_state, target_counts, config
                    )
                    
                    # Generate structured script with provider
                    
                    # Use unified provider for generation
                    result_data = await self.provider.generate_structured_script(
                        prompt=prompt,
                        context=source_context,
                        current_state=current_state.model_dump(),
                        temperature=final_temperature,
                        max_tokens=final_max_tokens,
                        anchor_info=anchor_info,
                        session_id=session_id,
                        user_event=user_event,
                        assistant_event=assistant_event,
                        memory_context=memory_context
                    )
                    
                    # Store interaction in memory manager (if events provided)
                    if session_id and user_event and assistant_event:
                        # Update assistant event with generated script
                        script_units = result_data.get("script_units", [])
                        assistant_event.script = script_units
                        await self.memory_manager.add_interaction(
                            session_id, user_event, assistant_event, context
                        )
                    
                    # Cache the result
                    self._request_cache[request_hash] = (result_data, time.time())
                    return result_data
                    
                except Exception as e:
                    logger.error(f"Failed to generate structured script: {e}")
                    # Return fallback response - create basic fallback
                    if session_id:
                        fallback = self._get_fallback_response(session_id, str(e))
                        return fallback
                    raise
            
            # Register and execute the generation task
            task = asyncio.create_task(_perform_generation())
            self._pending_requests[request_hash] = task
            
            try:
                result = await task
                return result
            finally:
                # Clean up the pending request
                if request_hash in self._pending_requests:
                    del self._pending_requests[request_hash]
    
    async def summarize_events(self, events: List[TurnEvent]) -> str:
        """
        使用新的LangChain API进行事件摘要
        
        Args:
            events: List of events to summarize
            
        Returns:
            Summarized conversation history
        """
        # 使用统一的provider系统进行摘要
        if not self.provider:
            raise ValueError("Provider not initialized")
        
        try:
            # 将事件转换为文本内容
            conversation_parts = []
            for event in events:
                if event.role == TurnEventRole.USER:
                    user_content = f"玩家选择: {event.choice or event.anchor}"
                    conversation_parts.append(f"用户: {user_content}")
                elif event.role == TurnEventRole.ASSISTANT and event.script:
                    # Handle both ScriptUnit objects and raw dictionaries from storage
                    script_contents = []
                    for unit in event.script:
                        if isinstance(unit, ScriptUnit):
                            script_contents.append(unit.content)
                        elif isinstance(unit, dict):
                            script_contents.append(unit.get("content", ""))
                        else:
                            script_contents.append(str(unit))
                    assistant_content = "\n".join(script_contents)
                    conversation_parts.append(f"助手: {assistant_content}")
            
            # 组合所有对话内容
            full_text = "\n".join(conversation_parts)
            
            # 如果文本为空，返回空摘要
            if not full_text.strip():
                return ""
            
            # 使用provider的generate_summary方法
            summary = await self.provider.generate_summary(
                text=full_text,
                max_length=llm_settings.summarization_max_tokens
            )
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
    
    def _build_tools_from_config(self, deviation: float, input_length: int = 0) -> List[Dict[str, Any]]:
        """Build tools array from config."""
        function_schema = llm_settings.get_function_schema_with_counts(deviation, input_length)
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
        # Build enhanced system prompt using version routing
        system_message = llm_settings.get_system_prompt(
            deviation=current_state.deviation,
            current_state=current_state.model_dump(),
            context_length=len(context)
        )
        
        # Add game state details from config
        system_message += llm_settings.build_game_state_details(
            current_state.model_dump(),
            target_counts
        )
        
        return system_message
    
    def _build_user_message_from_config(
        self,
        context: str,
        memory_context: str,
        prompt: str,
        anchor_info: Optional[Dict[str, Any]],
        current_state: GlobalState,
        target_counts: Dict[str, int],
        config: GenerationConfig
    ) -> str:
        """Build user message from config with separated memory and context."""
        return llm_settings.get_user_message(
            context=context,
            memory_context=memory_context,
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
        
        # Check for duplicate/invalid interaction content
        if last_is_interaction and len(script_units) > 0:
            last_unit = script_units[-1]
            # Check if interaction content is too generic or repetitive
            generic_patterns = [
                "你感受到了「捕食者」的力量，接下来你想做什么？",
                "面对眼前的情况，你会如何行动？",
                "你想要探索什么方向？"
            ]
            # Only flag as duplicate if it exactly matches known generic patterns
            if (last_unit.content and any(pattern in last_unit.content for pattern in generic_patterns)):
                logger.warning(f"Detected generic interaction content for session {session_id}: {last_unit.content[:50]}...")
                last_is_interaction = False  # Force fallback generation
        
        if not has_interaction or not last_is_interaction:
            logger.warning(f"Script missing proper interaction unit for session {session_id}, adding fallback")
            
            # Remove any existing interaction units that are not at the end
            script_units = [unit for unit in script_units if unit.type != ScriptUnitType.INTERACTION]
            
            # Add context-aware fallback interaction unit
            import random
            fallback_prompts = [
                "在这个关键时刻，你准备如何行动？",
                "面对当前的局面，你有什么想法？",
                "接下来的选择将影响你的命运，你决定...？",
                "这种情况下，你会选择什么样的应对方式？",
                "你感到内心涌起一种冲动，想要...",
                "现在你需要做出一个重要的决定..."
            ]
            fallback_content = random.choice(fallback_prompts)
            
            script_units.append(ScriptUnit(
                type=ScriptUnitType.INTERACTION,
                content=fallback_content,
                choice_id="continue_story",
                default_reply="继续探索",
                metadata={"fallback_added": True, "timestamp": time.time()}
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
        # Check if using o4-mini model which has different requirements
        if llm_settings.current_model == "o4-mini":
            # o4-mini uses a single user message for reasoning
            # Combine system and user messages for better reasoning
            combined_message = f"# System Instructions\n{system_message}\n\n# User Request\n{user_message}"
            return await self.openai_client.chat.completions.create(
                model=llm_settings.current_model,
                messages=[
                    {"role": "user", "content": combined_message}
                ],
                tools=cast(Any, tools),
                tool_choice={"type": "function", "function": {"name": tools[0]["function"]["name"]}},
                temperature=1.0,  # o4-mini uses fixed temperature
                max_completion_tokens=max_tokens  # o4-mini uses max_completion_tokens instead of max_tokens
            )
        else:
            # Standard OpenAI models
            return await self.openai_client.chat.completions.create(
                model=llm_settings.current_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                tools=cast(Any, tools),
                tool_choice={"type": "function", "function": {"name": tools[0]["function"]["name"]}},
                temperature=temperature,
                max_tokens=max_tokens
            )
    
    def _get_fallback_response(self, session_id: str, error: str) -> Dict[str, Any]:
        """Get fallback response when generation fails."""
        return {
            "script_units": [
                ScriptUnit(
                    type=ScriptUnitType.NARRATION,
                    content="故事暂时停顿了一下，等待着下一个转折点的到来。",
                    metadata={"fallback": True, "error": error}
                ),
                ScriptUnit(
                    type=ScriptUnitType.INTERACTION,
                    content="请选择你的下一步行动：",
                    choice_id="fallback_choice",
                    default_reply="继续",
                    metadata={"fallback": True}
                )
            ],
            "required_counts": {"narration": 1, "dialogue": 0, "interaction": 1},
            "deviation_delta": 0.0,
            "affinity_changes": {},
            "metadata": {
                "fallback": True,
                "error": error,
                "session_id": session_id
            }
        }
    
    def _clean_malformed_json(self, raw_json: str) -> str:
        """
        Attempt to fix common JSON formatting issues.
        
        Args:
            raw_json: Malformed JSON string
            
        Returns:
            Cleaned JSON string
        """
        cleaned = raw_json
        
        # Common fixes for malformed JSON
        try:
            # 1. Fix unescaped quotes in strings (basic approach)
            # This is a simplified fix - a more robust solution would use proper parsing
            import re
            
            # 2. Ensure the JSON ends properly (sometimes gets truncated)
            if not cleaned.rstrip().endswith('}'):
                # Find the last complete object
                brace_count = 0
                last_valid_pos = len(cleaned)
                for i in range(len(cleaned) - 1, -1, -1):
                    if cleaned[i] == '}':
                        brace_count += 1
                    elif cleaned[i] == '{':
                        brace_count -= 1
                        if brace_count == 0:
                            last_valid_pos = i
                            break
                
                # Truncate to last valid position and add closing brace if needed
                if last_valid_pos < len(cleaned):
                    cleaned = cleaned[:last_valid_pos]
                    # Count opening vs closing braces
                    open_braces = cleaned.count('{')
                    close_braces = cleaned.count('}')
                    if open_braces > close_braces:
                        cleaned += '}' * (open_braces - close_braces)
            
            # 3. Fix unterminated strings by adding closing quotes
            # This is a heuristic approach - look for lines that start with quotes but don't end with them
            lines = cleaned.split('\n')
            fixed_lines = []
            for line in lines:
                stripped = line.strip()
                # If line starts with a quote but doesn't end properly, try to fix
                if stripped.startswith('"') and not (stripped.endswith('"') or stripped.endswith('",') or stripped.endswith('"}')):
                    # Find the last quote and see if we need to add one
                    if stripped.count('"') % 2 == 1:  # Odd number of quotes means unterminated
                        # Add closing quote before any trailing comma or brace
                        if stripped.endswith(','):
                            line = line.rstrip(',') + '",'
                        elif stripped.endswith('}'):
                            line = line.rstrip('}') + '"}'
                        else:
                            line = line + '"'
                fixed_lines.append(line)
            
            cleaned = '\n'.join(fixed_lines)
            
            # 4. Remove any trailing comma before closing braces/brackets
            cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
            
            logger.info(f"Applied JSON cleaning heuristics")
            return cleaned
            
        except Exception as e:
            logger.error(f"Error during JSON cleaning: {e}")
            return raw_json
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check unified LLM service health.
        
        Returns:
            Health status information
        """
        # Check current provider health
        provider_health = await self.provider.health_check()
        
        status = {
            "provider": self.provider.provider.value,
            "model": self.provider.model_name,
            "provider_health": provider_health,
            "langchain_available": self.langchain_llm is not None,
            "memory_manager_stats": self.memory_manager.get_memory_stats(),
            "available_providers": self.provider_factory.get_available_providers(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Test legacy OpenAI client if available
        if self.openai_client:
            try:
                models = await self.openai_client.models.list()
                status["legacy_openai_status"] = "healthy"
                status["legacy_openai_models"] = len(models.data) if models.data else 0
            except Exception as e:
                status["legacy_openai_status"] = f"error: {str(e)[:100]}"
        
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
        self.llm_repo = UnifiedLLMRepository()
        
        # Configuration from settings
        self.max_recent_events = llm_settings.max_recent_events
        self.max_snapshot_size = llm_settings.max_snapshot_size
        self.summarization_batch_size = llm_settings.summarization_batch_size
    
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


# Backward compatibility alias
LLMRepository = UnifiedLLMRepository


# Convenience functions for unified repository
def get_unified_repository() -> UnifiedLLMRepository:
    """Get the default unified repository instance."""
    return UnifiedLLMRepository()