"""
LLM Provider Factory

Factory pattern for creating LLM providers based on configuration.
"""

import os
import logging
from typing import Dict, Any, Optional

from .base import BaseLLMProvider, LLMProvider, LLMProviderConfig
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from backend_services.app.core.config import settings, load_unified_config

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""
    
    # Provider class mapping
    _providers = {
        LLMProvider.OPENAI: OpenAIProvider,
        LLMProvider.GEMINI: GeminiProvider,
    }
    
    @classmethod
    def _get_default_models(cls) -> Dict[LLMProvider, str]:
        """Get default models from unified configuration."""
        try:
            config = load_unified_config()
            llm_provider_config = config.get("llm_provider", {})
            providers = llm_provider_config.get("providers", {})
            
            default_models = {}
            
            # Get OpenAI default model
            openai_config = providers.get("openai", {})
            default_models[LLMProvider.OPENAI] = openai_config.get("default_model", "gpt-4o-mini")
            
            # Get Gemini default model
            gemini_config = providers.get("gemini", {})
            default_models[LLMProvider.GEMINI] = gemini_config.get("default_model", "gemini-2.5-flash")
            
            logger.info(f"Loaded default models from config: {default_models}")
            return default_models
            
        except Exception as e:
            logger.warning(f"Failed to load default models from config: {e}")
            # Fallback to hardcoded defaults
            return {
                LLMProvider.OPENAI: "gpt-4o-mini",
                LLMProvider.GEMINI: "gemini-2.5-flash",  # 修正默认值为Flash
            }
    
    @classmethod
    def create_provider(
        cls,
        provider: str = None,
        model: str = None,
        **kwargs
    ) -> BaseLLMProvider:
        """
        Create an LLM provider instance.
        
        Args:
            provider: Provider name (openai, gemini, etc.)
            model: Model name (optional, uses default if not specified)
            **kwargs: Additional provider-specific configuration
            
        Returns:
            LLM provider instance
        """
        # Get provider from environment or parameter
        if not provider:
            provider = os.getenv("LLM_PROVIDER", "openai")
        
        # Convert string to enum
        try:
            provider_enum = LLMProvider(provider.lower())
        except ValueError:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(LLMProvider)}")
        
        # Get provider class
        provider_class = cls._providers.get(provider_enum)
        if not provider_class:
            raise ValueError(f"Provider {provider} not implemented")
        
        # Get model name
        if not model:
            default_models = cls._get_default_models()
            model = os.getenv("LLM_MODEL") or default_models.get(provider_enum)
        
        # Create configuration
        config = LLMProviderConfig(
            provider=provider_enum,
            model_name=model,
            **kwargs
        )
        
        # Create and return provider instance
        logger.info(f"Creating {provider} provider with model {model}")
        return provider_class(config)
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get information about available providers.
        
        Returns:
            Dictionary of provider information
        """
        providers_info = {}
        default_models = cls._get_default_models()
        
        for provider_enum, provider_class in cls._providers.items():
            providers_info[provider_enum.value] = {
                "name": provider_enum.value,
                "default_model": default_models.get(provider_enum),
                "available": True,
                "class": provider_class.__name__
            }
        
        return providers_info
    
    @classmethod
    def create_from_settings(cls) -> BaseLLMProvider:
        """
        Create a provider based on current application settings.
        
        Returns:
            LLM provider instance configured from settings
        """
        # Check environment variables first
        provider = os.getenv("LLM_PROVIDER")
        model = os.getenv("LLM_MODEL")
        
        # If not set, try to load from unified configuration
        if not provider or not model:
            try:
                config = load_unified_config()
                llm_provider_config = config.get("llm_provider", {})
                
                # Get provider from config
                if not provider:
                    provider = llm_provider_config.get("default_provider", "gemini")
                
                # Get model from config
                if not model:
                    model = llm_provider_config.get("default_model", "gemini-2.5-flash")
                
                logger.info(f"Loaded from unified config: provider={provider}, model={model}")
                
            except Exception as e:
                logger.warning(f"Failed to load from unified config: {e}")
                
                # Fallback: determine based on available API keys
                if not provider:
                    if settings.google_api_key:
                        provider = "gemini"
                        model = model or "gemini-2.5-flash"  # 修正为Flash
                    elif settings.openai_api_key:
                        provider = "openai"
                        model = model or "gpt-4o-mini"
                    else:
                        raise ValueError("No API keys found. Please set GOOGLE_API_KEY or OPENAI_API_KEY")
        
        # 从llm_settings获取thinking_budget配置
        thinking_budget = 1024  # 默认1024 tokens，符合用户要求
        try:
            from ..llm_settings import llm_settings
            # 为Gemini模型添加thinking_budget支持
            if provider == "gemini":
                logger.info(f"Adding thinking_budget={thinking_budget} for Gemini provider")
        except ImportError:
            logger.warning("Could not import llm_settings, using default thinking_budget")
        
        logger.info(f"Creating provider from settings: {provider} with model {model}")
        return cls.create_provider(
            provider=provider, 
            model=model,
            thinking_budget=thinking_budget if provider == "gemini" else None
        )


# Singleton instance
_provider_instance: Optional[BaseLLMProvider] = None


def get_llm_provider(force_recreate: bool = False) -> BaseLLMProvider:
    """
    Get the current LLM provider instance.
    
    This function returns a singleton instance of the LLM provider
    based on current configuration.
    
    Args:
        force_recreate: Force recreation of the provider instance
        
    Returns:
        LLM provider instance
    """
    global _provider_instance
    
    if _provider_instance is None or force_recreate:
        _provider_instance = LLMProviderFactory.create_from_settings()
    
    return _provider_instance


def switch_provider(provider: str, model: str = None) -> BaseLLMProvider:
    """
    Switch to a different LLM provider.
    
    Args:
        provider: Provider name
        model: Model name (optional)
        
    Returns:
        New LLM provider instance
    """
    global _provider_instance
    
    _provider_instance = LLMProviderFactory.create_provider(
        provider=provider,
        model=model
    )
    
    logger.info(f"Switched to {provider} provider with model {_provider_instance.model_name}")
    
    return _provider_instance