"""
OpenAI Provider Implementation

Provides integration with OpenAI models (GPT-4, GPT-4o-mini, etc.)
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from openai import AsyncOpenAI
from openai import OpenAIError
import tenacity

from .base import BaseLLMProvider, LLMProviderConfig, LLMProvider
from ..models import TurnEvent
from ..llm_settings import llm_settings
from backend_services.app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider implementation."""
    
    def _validate_config(self) -> None:
        """Validate OpenAI-specific configuration."""
        if not self.config.api_key:
            # Try to get from settings or environment
            self.config.api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.config.api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY.")
        
        # Validate model name
        valid_models = ["gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini", "o4-mini"]
        if self.config.model_name not in valid_models:
            logger.warning(f"Unknown OpenAI model: {self.config.model_name}")
    
    def _initialize(self) -> None:
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=self.config.api_key)
        logger.info(f"Initialized OpenAI provider with model: {self.config.model_name}")
    
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
        retry=tenacity.retry_if_exception_type(OpenAIError),
        before_sleep=lambda retry_state: logger.warning(
            f"OpenAI API call failed, retrying (attempt {retry_state.attempt_number})..."
        )
    )
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
        """Generate structured story script using OpenAI."""
        try:
            # Get system prompt and user message from settings
            system_prompt = llm_settings.get_system_prompt(
                current_state.get('deviation', 0),
                current_state,
                len(context),
                session_id
            )
            
            # Get target counts for content generation
            target_counts = llm_settings.get_required_counts(
                current_state.get('deviation', 0),
                len(context)
            )
            
            # Get generation config
            config = llm_settings.get_generation_config(current_state.get('deviation', 0))
            
            # Build user message
            user_message = llm_settings.get_user_message(
                context=context,
                memory_context=memory_context,
                prompt=prompt,
                anchor_info=anchor_info,
                current_state=current_state,
                target_counts=target_counts,
                config=config,
                session_id=session_id
            )
            
            # Get function schema from settings
            function_schema = llm_settings.get_function_schema_with_counts(
                current_state.get('deviation', 0),
                len(context)
            )
            
            # Build messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Log the generation request
            logger.info(f"Generating script for session {session_id} with {self.config.model_name}")
            logger.debug(f"Temperature: {temperature}, Deviation: {current_state.get('deviation', 0)}")
            
            # Generate response
            start_time = datetime.now()
            
            if self.config.model_name in ["o4-mini"]:
                # o4-mini uses fixed temperature of 1.0
                response = await self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=messages,
                    temperature=1.0,  # o4-mini fixed temperature
                    max_completion_tokens=max_tokens or self.config.max_tokens or 50000,
                    response_format={"type": "json_object"},
                )
            else:
                # Other models support function calling
                response = await self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=messages,
                    functions=[function_schema],
                    function_call={"name": "generate_story_script"},
                    temperature=temperature,
                    max_tokens=max_tokens or self.config.max_tokens,
                    top_p=self.config.top_p,
                )
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # Extract result based on model type
            if self.config.model_name in ["o4-mini"]:
                # Parse JSON response directly
                response_text = response.choices[0].message.content
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse o4-mini response: {e}")
                    result = self._create_fallback_response(prompt, current_state)
            else:
                # Extract from function call
                function_call = response.choices[0].message.function_call
                if function_call and function_call.arguments:
                    try:
                        result = json.loads(function_call.arguments)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse function arguments: {e}")
                        result = self._create_fallback_response(prompt, current_state)
                else:
                    logger.error("No function call in response")
                    result = self._create_fallback_response(prompt, current_state)
            
            # Add metadata
            result['metadata'] = result.get('metadata', {})
            result['metadata'].update({
                'model': self.config.model_name,
                'temperature': temperature,
                'generation_time': generation_time,
                'session_id': session_id,
                'provider': 'openai',
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                    'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                    'total_tokens': response.usage.total_tokens if response.usage else 0
                }
            })
            
            logger.info(f"Successfully generated script with {len(result.get('script_units', []))} units")
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return self._create_fallback_response(prompt, current_state)
    
    async def generate_summary(self, text: str, max_length: int = 500) -> str:
        """Generate a summary using OpenAI."""
        try:
            prompt = llm_settings.get_summarization_prompt().format(text=text)
            
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的文本总结助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Low temperature for summaries
                max_tokens=max_length
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI summarization failed: {e}")
            return f"[总结失败] {text[:max_length]}..."
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI API health status."""
        try:
            # Try a simple completion
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": "Say 'OK' if you're working."}],
                max_tokens=10
            )
            
            return {
                "openai_available": True,
                "model": self.config.model_name,
                "provider": "openai",
                "status": "healthy",
                "response": response.choices[0].message.content
            }
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return {
                "openai_available": False,
                "model": self.config.model_name,
                "provider": "openai",
                "status": "unhealthy",
                "error": str(e)
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "provider": "openai",
            "model": self.config.model_name,
            "temperature_range": (0.0, 2.0),
            "supports_functions": self.config.model_name not in ["o4-mini"],
            "max_tokens": self.config.max_tokens,
            "features": {
                "structured_output": True,
                "function_calling": self.config.model_name not in ["o4-mini"],
                "json_mode": self.config.model_name in ["o4-mini"],
                "vision": self.config.model_name in ["gpt-4o", "gpt-4o-mini"]
            }
        }