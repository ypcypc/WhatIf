"""
Application configuration settings.

Unified configuration management with support for JSON config file.
"""

import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic_settings import BaseSettings


def load_unified_config() -> Dict[str, Any]:
    """Load unified configuration from JSON file."""
    # Look for config file in project root
    config_paths = [
        Path(__file__).parent.parent.parent.parent / "llm_config.json",  # Project root
        Path(__file__).parent.parent / "llm_config.json",  # Backend services root
        Path("llm_config.json"),  # Current directory
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config
            except Exception as e:
                # Failed to load config file, continue to next path
                continue
    
    # Return empty config if no file found
    return {}


def load_api_key(key_name: str) -> Optional[str]:
    """Load API key from multiple sources with priority."""
    # 1. Environment variable (highest priority)
    env_key = os.getenv(key_name.upper())
    if env_key:
        return env_key
    
    # 2. Unified config file
    config = load_unified_config()
    api_keys = config.get("api_keys", {})
    config_key = api_keys.get(key_name.lower())
    if config_key:
        return config_key
    
    # 3. Legacy fallback for OpenAI
    if key_name.lower() == "openai_api_key":
        key_file_path = Path(__file__).parent.parent / "services" / "llm_service" / "OPENAI_APIKEY"
        if key_file_path.exists():
            try:
                with open(key_file_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                pass
    
    return None


class Settings(BaseSettings):
    """Application settings loaded from unified configuration."""
    
    def __init__(self, **kwargs):
        """Initialize settings from unified config."""
        super().__init__(**kwargs)
        
        # Load unified config after base initialization
        unified_config = load_unified_config()
        
        # Extract sections
        app_config = unified_config.get("application", {})
        data_config = unified_config.get("data_paths", {})
        cors_config = app_config.get("cors", {})
        
        # Set default values from unified config
        self._app_name = app_config.get("app_name", "WhatIf AI Galgame Backend")
        self._debug = app_config.get("debug", False)
        self._api_prefix = app_config.get("api_prefix", "/api/v1")
        self._host = app_config.get("host", "0.0.0.0")
        self._port = app_config.get("port", 8000)
        
        # Database and paths
        self._database_url = data_config.get("database_url", "sqlite:///./data/game.db")
        self._data_dir = data_config.get("data_dir", "./data")
        self._novels_dir = data_config.get("novels_dir", "./data/novels")
        self._dictionaries_dir = data_config.get("dictionaries_dir", "./data/dictionaries")
        self._anchors_dir = data_config.get("anchors_dir", "./data/anchors")
        self._indexes_dir = data_config.get("indexes_dir", "./data/indexes")
        
        # CORS settings
        self._allow_origins = cors_config.get("origins", [
            "http://localhost:3000", "http://127.0.0.1:3000",
            "http://localhost:5173", "http://127.0.0.1:5173"
        ])
        self._allow_credentials = cors_config.get("credentials", True)
        self._allow_methods = cors_config.get("methods", ["*"])
        self._allow_headers = cors_config.get("headers", ["*"])
    
    # Application properties
    @property
    def app_name(self) -> str:
        return self._app_name
    
    @property
    def debug(self) -> bool:
        return self._debug
    
    @property
    def api_prefix(self) -> str:
        return self._api_prefix
    
    @property
    def host(self) -> str:
        return self._host
    
    @property
    def port(self) -> int:
        return self._port
    
    # Database and paths
    @property
    def database_url(self) -> str:
        return self._database_url
    
    @property
    def data_dir(self) -> str:
        return self._data_dir
    
    @property
    def novels_dir(self) -> str:
        return self._novels_dir
    
    @property
    def dictionaries_dir(self) -> str:
        return self._dictionaries_dir
    
    @property
    def anchors_dir(self) -> str:
        return self._anchors_dir
    
    @property
    def indexes_dir(self) -> str:
        return self._indexes_dir
    
    # CORS properties
    @property
    def allow_origins(self) -> list:
        return self._allow_origins
    
    @property
    def allow_credentials(self) -> bool:
        return self._allow_credentials
    
    @property
    def allow_methods(self) -> list:
        return self._allow_methods
    
    @property
    def allow_headers(self) -> list:
        return self._allow_headers
    
    # API Keys - loaded from unified config or environment
    @property
    def openai_api_key(self) -> Optional[str]:
        return load_api_key("openai_api_key")
    
    @property
    def anthropic_api_key(self) -> Optional[str]:
        return load_api_key("anthropic_api_key")
    
    @property
    def google_api_key(self) -> Optional[str]:
        return load_api_key("google_api_key")
    
    # LLM Configuration from unified config
    @property
    def llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration from unified config file."""
        config = load_unified_config()
        return config.get("llm_provider", {})
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 