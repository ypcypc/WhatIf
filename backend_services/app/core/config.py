"""
Application configuration settings.

Manages environment variables and application settings.
"""

import os
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings


def load_openai_api_key() -> Optional[str]:
    """Load OpenAI API key from file if not in environment."""
    # First check environment variable
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key
    
    # Then check file
    key_file_path = Path(__file__).parent.parent / "services" / "llm_service" / "OPENAI_APIKEY"
    if key_file_path.exists():
        try:
            with open(key_file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            pass
    
    return None


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "WhatIf AI Galgame Backend"
    debug: bool = False
    
    # API Configuration
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    database_url: str = "sqlite:///./data/game.db"
    chroma_persist_dir: str = "./data/chroma"
    
    # LLM API Keys - auto-load OpenAI key
    openai_api_key: Optional[str] = load_openai_api_key()
    dashscope_api_key: Optional[str] = None
    doubao_api_key: Optional[str] = None
    
    # File paths
    data_dir: str = "./data"
    novels_dir: str = "./data/novels"
    dictionaries_dir: str = "./data/dictionaries"
    anchors_dir: str = "./data/anchors"
    indexes_dir: str = "./data/indexes"
    
    # CORS
    allow_origins: list = [
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173"   # Vite dev server
    ]
    allow_credentials: bool = True
    allow_methods: list = ["*"]
    allow_headers: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 