"""
Base LLM Provider Interface

Defines the abstract interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..models import TurnEvent


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


@dataclass
class LLMProviderConfig:
    """Configuration for an LLM provider."""
    provider: LLMProvider
    model_name: str
    api_key: Optional[str] = None
    temperature: float = 0.8
    max_tokens: Optional[int] = None
    top_p: float = 0.95
    top_k: Optional[int] = 40
    thinking_budget: Optional[int] = 1024  # Gemini 2.5 Flash thinking token limit
    extra_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All LLM providers must implement this interface to ensure compatibility
    with the rest of the system.
    """
    
    def __init__(self, config: LLMProviderConfig):
        """
        Initialize the provider with configuration.
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self.provider = config.provider
        self.model_name = config.model_name
        self._validate_config()
        self._initialize()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider-specific configuration."""
        pass
    
    @abstractmethod
    def _initialize(self) -> None:
        """Initialize provider-specific resources."""
        pass
    
    @abstractmethod
    async def generate_structured_script(
        self,
        prompt: str,
        context: str,
        current_state: Dict[str, Any],
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
        anchor_info: Optional[Dict[str, Any]] = None,
        session_id: str = None,
        user_event: Optional[TurnEvent] = None,
        assistant_event: Optional[TurnEvent] = None,
        memory_context: str = ""
    ) -> Dict[str, Any]:
        """
        Generate structured story script using the LLM.
        
        Args:
            prompt: Player's choice/input
            context: Story context
            current_state: Current game state
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            anchor_info: Anchor information
            session_id: Session identifier
            user_event: User turn event
            assistant_event: Assistant turn event
            memory_context: Memory/history context
            
        Returns:
            Dictionary with generated script and metadata
        """
        pass
    
    @abstractmethod
    async def generate_summary(
        self,
        text: str,
        max_length: int = 500
    ) -> str:
        """
        Generate a summary of the given text.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            
        Returns:
            Summary text
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health status of the provider.
        
        Returns:
            Dictionary with health status information
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dictionary with model information
        """
        pass
    
    def update_temperature(self, temperature: float) -> None:
        """
        Update the temperature setting.
        
        Args:
            temperature: New temperature value
        """
        self.config.temperature = max(0.0, min(2.0, temperature))
    
    def _create_fallback_response(self, prompt: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a standardized fallback response when generation fails.
        
        Args:
            prompt: Original prompt
            current_state: Current game state
            
        Returns:
            Fallback response dictionary
        """
        return {
            "script_units": [
                {
                    "type": "narration",
                    "content": "系统正在处理您的请求，请稍候...",
                    "metadata": {"fallback": True}
                },
                {
                    "type": "interaction",
                    "content": "请选择下一步行动：",
                    "choice_id": "fallback_choice",
                    "default_reply": "继续",
                    "metadata": {"fallback": True}
                }
            ],
            "required_counts": {
                "narration": 1,
                "dialogue": 0,
                "interaction": 1
            },
            "deviation_delta": 0.0,
            "new_deviation": current_state.get('deviation', 0),
            "deviation_reasoning": "系统处理中",
            "affinity_changes": {},
            "flags_updates": {},
            "variables_updates": {},
            "metadata": {
                "error": "Generation failed",
                "fallback": True,
                "provider": self.provider.value,
                "model": self.model_name
            }
        }