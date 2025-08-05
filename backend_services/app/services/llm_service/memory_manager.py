"""
Modern LangGraph-based Memory Management for Interactive Stories

This module implements sophisticated context management using LangGraph patterns:
1. Short-term memory: Thread-scoped conversation history
2. Long-term memory: Cross-session persistent story state
3. Semantic memory: Character relationships and story facts
4. Episodic memory: Key story events and player choices

Based on LangGraph 2025 best practices and migration from deprecated LangChain memory classes.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
from collections import defaultdict

# LangChain modern imports (LangGraph style)
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from .models import TurnEvent, ScriptUnit, GlobalState, TurnEventRole

logger = logging.getLogger(__name__)


@dataclass
class StoryMemory:
    """Individual story memory unit"""
    memory_id: str
    memory_type: str  # "semantic", "episodic", "procedural"
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    importance: float  # 0.0-1.0 importance score
    namespace: str  # session_id or "global"
    

@dataclass
class ContextWindow:
    """Current context window for LLM generation"""
    current_text: str
    recent_events: List[TurnEvent]
    relevant_memories: List[StoryMemory]
    character_state: Dict[str, Any]
    story_flags: Dict[str, Any]
    

class ModernMemoryManager:
    """
    Modern LangGraph-style memory management for interactive stories.
    
    Implements the 2025 LangGraph pattern for:
    - Thread-scoped short-term memory (conversation history)
    - Cross-thread long-term memory (character relationships, story facts)
    - Semantic search and retrieval
    - Automated memory extraction and summarization
    """
    
    def __init__(self, 
                 data_dir: str = "data/memory",
                 embeddings_model: str = "text-embedding-3-small",
                 max_short_term_events: int = 20,
                 max_context_tokens: int = 4000):
        """
        Initialize modern memory manager.
        
        Args:
            data_dir: Directory for persistent memory storage
            embeddings_model: OpenAI embeddings model for semantic search
            max_short_term_events: Maximum events in short-term memory
            max_context_tokens: Maximum tokens in context window
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Memory configuration
        self.max_short_term_events = max_short_term_events
        self.max_context_tokens = max_context_tokens
        
        # Initialize embeddings for semantic search (optional - requires OpenAI API key)
        try:
            self.embeddings = OpenAIEmbeddings(model=embeddings_model)
            logger.info(f"Initialized embeddings with model: {embeddings_model}")
        except Exception as e:
            logger.info(f"Embeddings not available (OpenAI API key not configured): {e}")
            self.embeddings = None
        
        # Memory stores (namespace -> memories)
        self.short_term_memory: Dict[str, List[TurnEvent]] = defaultdict(list)
        self.long_term_memory: Dict[str, List[StoryMemory]] = defaultdict(list)
        
        # Vector store for semantic search
        self.vector_store = None
        
        # Memory extraction LLM
        self.memory_llm = None
        self._init_memory_llm()
        
        # Load existing memories
        self._load_persistent_memories()
    
    def _init_memory_llm(self):
        """Initialize LLM for memory extraction and summarization (optional - requires OpenAI API key)."""
        try:
            self.memory_llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=8192
            )
            logger.info("Initialized memory extraction LLM")
        except Exception as e:
            logger.info(f"Memory LLM not available (OpenAI API key not configured): {e}")
    
    async def add_interaction(self, 
                            session_id: str, 
                            user_event: TurnEvent, 
                            assistant_event: TurnEvent,
                            context: str) -> None:
        """
        Add a new interaction to memory (LangGraph-style hot path).
        
        Args:
            session_id: Thread identifier for short-term memory
            user_event: User's action/choice
            assistant_event: Assistant's response
            context: Current story context
        """
        # Add to short-term memory (thread-scoped)
        self.short_term_memory[session_id].extend([user_event, assistant_event])
        
        # Trim short-term memory if too long
        if len(self.short_term_memory[session_id]) > self.max_short_term_events:
            # Move oldest events to long-term memory before removing
            old_events = self.short_term_memory[session_id][:5]  # Move 5 oldest
            await self._extract_long_term_memories(session_id, old_events, context)
            self.short_term_memory[session_id] = self.short_term_memory[session_id][5:]
        
        # Extract meaningful memories in background
        asyncio.create_task(self._extract_memories_background(
            session_id, user_event, assistant_event, context
        ))
        
        logger.debug(f"Added interaction to memory for session {session_id}")
    
    async def get_context_window(self, 
                                session_id: str, 
                                current_text: str,
                                player_choice: str = "") -> ContextWindow:
        """
        Build optimized context window for LLM generation.
        
        Args:
            session_id: Session identifier
            current_text: Current story text to continue from
            player_choice: Player's current choice/action
            
        Returns:
            ContextWindow with relevant context for generation
        """
        # Get recent short-term memory
        recent_events = self.short_term_memory.get(session_id, [])[-10:]  # Last 10 events
        
        # Semantic search for relevant long-term memories
        relevant_memories = await self._search_relevant_memories(
            session_id, current_text, player_choice
        )
        
        # Extract current character state and story flags
        character_state, story_flags = self._extract_current_state(recent_events)
        
        return ContextWindow(
            current_text=current_text,
            recent_events=recent_events,
            relevant_memories=relevant_memories,
            character_state=character_state,
            story_flags=story_flags
        )
    
    async def _search_relevant_memories(self, 
                                      session_id: str, 
                                      current_text: str, 
                                      player_choice: str,
                                      max_memories: int = 5) -> List[StoryMemory]:
        """
        Semantic search for relevant memories.
        
        Args:
            session_id: Session identifier
            current_text: Current story context
            player_choice: Player's choice
            max_memories: Maximum memories to return
            
        Returns:
            List of relevant memories
        """
        if not self.embeddings or not self.vector_store:
            return []
        
        try:
            # Combine search query
            search_query = f"{current_text} {player_choice}".strip()
            
            # Search for relevant memories
            docs = self.vector_store.similarity_search(
                search_query, 
                k=max_memories,
                filter={"namespace": session_id}  # Session-specific memories
            )
            
            # Convert documents back to StoryMemory objects
            memories = []
            for doc in docs:
                memory_data = json.loads(doc.page_content)
                memory = StoryMemory(**memory_data)
                memories.append(memory)
            
            logger.debug(f"Found {len(memories)} relevant memories for session {session_id}")
            return memories
            
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []
    
    def _extract_current_state(self, events: List[TurnEvent]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract current character state and story flags from recent events.
        
        Args:
            events: Recent turn events
            
        Returns:
            Tuple of (character_state, story_flags)
        """
        character_state = {"affinity": {}, "stats": {}}
        story_flags = {}
        
        for event in events:
            if event.affinity_changes:
                for char, change in event.affinity_changes.items():
                    character_state["affinity"][char] = character_state["affinity"].get(char, 0) + change
            
            # Extract flags from metadata
            if event.metadata and "flags" in event.metadata:
                story_flags.update(event.metadata["flags"])
        
        return character_state, story_flags
    
    async def _extract_memories_background(self, 
                                         session_id: str, 
                                         user_event: TurnEvent, 
                                         assistant_event: TurnEvent,
                                         context: str) -> None:
        """
        Background memory extraction (LangGraph background pattern).
        
        Args:
            session_id: Session identifier
            user_event: User's action
            assistant_event: Assistant's response
            context: Story context
        """
        if not self.memory_llm:
            return
        
        try:
            # Extract different types of memories
            memories = await self._extract_interaction_memories(
                session_id, user_event, assistant_event, context
            )
            
            # Store extracted memories
            for memory in memories:
                await self._store_long_term_memory(memory)
            
            logger.debug(f"Extracted {len(memories)} memories in background")
            
        except Exception as e:
            logger.error(f"Background memory extraction failed: {e}")
    
    async def _extract_interaction_memories(self, 
                                          session_id: str, 
                                          user_event: TurnEvent, 
                                          assistant_event: TurnEvent,
                                          context: str) -> List[StoryMemory]:
        """
        Extract structured memories from interaction using LLM.
        
        Args:
            session_id: Session identifier
            user_event: User's action
            assistant_event: Assistant's response
            context: Story context
            
        Returns:
            List of extracted memories
        """
        if not self.memory_llm:
            return []
        
        # Build extraction prompt
        # Handle script units with explicit type checking to avoid join errors
        story_response_parts = []
        if assistant_event.script:
            logger.debug(f"Processing {len(assistant_event.script)} script units for memory extraction")
            for i, unit in enumerate(assistant_event.script):
                if isinstance(unit, ScriptUnit):
                    story_response_parts.append(unit.content)
                    logger.debug(f"Unit {i}: ScriptUnit with content length {len(unit.content)}")
                elif isinstance(unit, dict):
                    content = unit.get('content', '')
                    story_response_parts.append(content)
                    logger.debug(f"Unit {i}: dict with content length {len(content)}")
                else:
                    content = str(unit)
                    story_response_parts.append(content)
                    logger.warning(f"Unit {i}: unexpected type {type(unit)}, converted to string: {content[:50]}...")
        story_response_text = ' '.join(story_response_parts)
        
        interaction_text = f"""
User Choice: {user_event.choice or user_event.anchor}
Story Response: {story_response_text}
Context: {context[:500]}...
"""
        
        extraction_prompt = f"""
Analyze this story interaction and extract important memories:

{interaction_text}

Extract 3 types of memories:
1. SEMANTIC: Facts about characters, locations, abilities, relationships
2. EPISODIC: Important events, choices made, consequences
3. PROCEDURAL: Rules learned, game mechanics, story patterns

Format each memory as:
TYPE: content
IMPORTANCE: 0.0-1.0 (how important this is for future story generation)

Only extract memories that would be useful for future story generation.
Focus on lasting character development, story progression, and world-building.
"""
        
        try:
            response = await self.memory_llm.ainvoke([
                SystemMessage(content="You are a memory extraction expert for interactive stories."),
                HumanMessage(content=extraction_prompt)
            ])
            
            # Parse response and create memory objects
            memories = self._parse_memory_extraction(session_id, response.content)
            return memories
            
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")
            return []
    
    def _parse_memory_extraction(self, session_id: str, extraction_text: str) -> List[StoryMemory]:
        """
        Parse LLM memory extraction response into StoryMemory objects.
        
        Args:
            session_id: Session identifier
            extraction_text: LLM response text
            
        Returns:
            List of parsed memories
        """
        memories = []
        lines = extraction_text.strip().split('\n')
        
        current_memory = None
        current_importance = 0.5
        
        for line in lines:
            line = line.strip()
            if line.startswith(('SEMANTIC:', 'EPISODIC:', 'PROCEDURAL:')):
                if current_memory:
                    # Save previous memory
                    memory = StoryMemory(
                        memory_id=f"{session_id}_{datetime.now().timestamp()}",
                        memory_type=current_memory["type"],
                        content=current_memory["content"],
                        metadata={"extracted_from": "interaction"},
                        timestamp=datetime.now(),
                        importance=current_importance,
                        namespace=session_id
                    )
                    memories.append(memory)
                
                # Start new memory
                parts = line.split(':', 1)
                memory_type = parts[0].lower()
                content = parts[1].strip() if len(parts) > 1 else ""
                current_memory = {"type": memory_type, "content": content}
                current_importance = 0.5  # Default
                
            elif line.startswith('IMPORTANCE:'):
                try:
                    importance_str = line.split(':', 1)[1].strip()
                    current_importance = float(importance_str)
                except (ValueError, IndexError):
                    current_importance = 0.5
        
        # Save last memory
        if current_memory:
            memory = StoryMemory(
                memory_id=f"{session_id}_{datetime.now().timestamp()}",
                memory_type=current_memory["type"],
                content=current_memory["content"],
                metadata={"extracted_from": "interaction"},
                timestamp=datetime.now(),
                importance=current_importance,
                namespace=session_id
            )
            memories.append(memory)
        
        return memories
    
    async def _store_long_term_memory(self, memory: StoryMemory) -> None:
        """
        Store memory in long-term storage with vector indexing.
        
        Args:
            memory: Memory to store
        """
        # Add to in-memory store
        self.long_term_memory[memory.namespace].append(memory)
        
        # Add to vector store for semantic search
        if self.embeddings:
            try:
                # Create document for vector store
                doc = Document(
                    page_content=json.dumps(asdict(memory)),
                    metadata={
                        "memory_id": memory.memory_id,
                        "memory_type": memory.memory_type,
                        "namespace": memory.namespace,
                        "importance": memory.importance,
                        "timestamp": memory.timestamp.isoformat()
                    }
                )
                
                # Initialize or update vector store
                if self.vector_store is None:
                    self.vector_store = FAISS.from_documents([doc], self.embeddings)
                else:
                    self.vector_store.add_documents([doc])
                
                logger.debug(f"Stored memory {memory.memory_id} in vector store")
                
            except Exception as e:
                logger.error(f"Failed to store memory in vector store: {e}")
        
        # Persist to disk
        await self._persist_memory(memory)
    
    async def _persist_memory(self, memory: StoryMemory) -> None:
        """
        Persist memory to disk storage.
        
        Args:
            memory: Memory to persist
        """
        try:
            memory_file = self.data_dir / f"{memory.namespace}_memories.jsonl"
            
            # Append memory to JSONL file
            with open(memory_file, 'a', encoding='utf-8') as f:
                memory_json = json.dumps(asdict(memory), default=str, ensure_ascii=False)
                f.write(memory_json + '\n')
            
            logger.debug(f"Persisted memory {memory.memory_id} to disk")
            
        except Exception as e:
            logger.error(f"Failed to persist memory: {e}")
    
    def _load_persistent_memories(self) -> None:
        """Load existing memories from disk storage."""
        try:
            memory_files = list(self.data_dir.glob("*_memories.jsonl"))
            
            for memory_file in memory_files:
                namespace = memory_file.stem.replace("_memories", "")
                
                with open(memory_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            memory_data = json.loads(line)
                            # Convert timestamp string back to datetime
                            if isinstance(memory_data['timestamp'], str):
                                memory_data['timestamp'] = datetime.fromisoformat(memory_data['timestamp'])
                            
                            memory = StoryMemory(**memory_data)
                            self.long_term_memory[namespace].append(memory)
            
            logger.info(f"Loaded memories from {len(memory_files)} files")
            
        except Exception as e:
            logger.error(f"Failed to load persistent memories: {e}")
    
    async def _extract_long_term_memories(self, 
                                        session_id: str, 
                                        events: List[TurnEvent], 
                                        context: str) -> None:
        """
        Extract and summarize memories from multiple events.
        
        Args:
            session_id: Session identifier
            events: Events to process
            context: Story context
        """
        if not self.memory_llm or not events:
            return
        
        try:
            # Summarize multiple events
            events_text = []
            for event in events:
                if event.role == TurnEventRole.USER:
                    events_text.append(f"Player: {event.choice or event.anchor}")
                elif event.role == TurnEventRole.ASSISTANT and event.script:
                    # Handle both ScriptUnit objects and raw dictionaries from storage
                    script_contents = []
                    for unit in event.script[:2]:  # First 2 units
                        if isinstance(unit, ScriptUnit):
                            script_contents.append(unit.content)
                        elif isinstance(unit, dict):
                            script_contents.append(unit.get("content", ""))
                        else:
                            script_contents.append(str(unit))
                    content = ' '.join(script_contents)
                    events_text.append(f"Story: {content}")
            
            summary_prompt = f"""
Summarize the key story developments from these interactions:

{chr(10).join(events_text)}

Context: {context[:300]}...

Create a concise summary focusing on:
1. Character development and relationships
2. Important story events and consequences  
3. World-building and lore discoveries
4. Player choices that affected the story

Make it useful for future story generation.
"""
            
            response = await self.memory_llm.ainvoke([
                SystemMessage(content="You are a story summarization expert."),
                HumanMessage(content=summary_prompt)
            ])
            
            # Create summary memory
            summary_memory = StoryMemory(
                memory_id=f"{session_id}_summary_{datetime.now().timestamp()}",
                memory_type="episodic",
                content=response.content,
                metadata={"events_count": len(events), "summary": True},
                timestamp=datetime.now(),
                importance=0.7,  # Summaries are important
                namespace=session_id
            )
            
            await self._store_long_term_memory(summary_memory)
            logger.debug(f"Created summary memory for {len(events)} events")
            
        except Exception as e:
            logger.error(f"Failed to extract long-term memories: {e}")
    
    def build_memory_context(self, context_window: ContextWindow) -> str:
        """
        Build memory context string for LLM prompt.
        
        Args:
            context_window: Current context window
            
        Returns:
            Formatted memory context string
        """
        context_parts = []
        
        # Add relevant long-term memories
        if context_window.relevant_memories:
            context_parts.append("## 相关记忆 (Reference Only)")
            for memory in context_window.relevant_memories[:3]:  # Top 3 memories
                context_parts.append(f"- {memory.content}")
        
        # Add character state
        if context_window.character_state:
            context_parts.append("## 角色状态")
            if context_window.character_state.get("affinity"):
                context_parts.append(f"好感度: {context_window.character_state['affinity']}")
        
        # Add recent events summary
        if context_window.recent_events:
            context_parts.append("## 最近选择")
            recent_choices = []
            for event in context_window.recent_events[-3:]:  # Last 3 events
                if event.role == TurnEventRole.USER:
                    recent_choices.append(event.choice or event.anchor)
            if recent_choices:
                context_parts.append(f"玩家最近选择: {', '.join(recent_choices)}")
        
        return "\n".join(context_parts)
    
    async def cleanup_old_memories(self, days_to_keep: int = 30) -> None:
        """
        Clean up old, low-importance memories.
        
        Args:
            days_to_keep: Number of days to keep memories
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for namespace in list(self.long_term_memory.keys()):
            memories = self.long_term_memory[namespace]
            
            # Keep important memories and recent memories
            filtered_memories = [
                memory for memory in memories
                if memory.timestamp > cutoff_date or memory.importance > 0.8
            ]
            
            removed_count = len(memories) - len(filtered_memories)
            self.long_term_memory[namespace] = filtered_memories
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old memories from {namespace}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        total_short_term = sum(len(events) for events in self.short_term_memory.values())
        total_long_term = sum(len(memories) for memories in self.long_term_memory.values())
        
        return {
            "short_term_sessions": len(self.short_term_memory),
            "total_short_term_events": total_short_term,
            "long_term_namespaces": len(self.long_term_memory),
            "total_long_term_memories": total_long_term,
            "vector_store_initialized": self.vector_store is not None,
            "embeddings_available": self.embeddings is not None,
            "memory_llm_available": self.memory_llm is not None
        }