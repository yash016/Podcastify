"""
Application configuration using Pydantic settings.
Loads from environment variables and .env file.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # API Keys
    gemini_api_key: str
    groq_api_key: str
    tavily_api_key: Optional[str] = None

    # Database
    database_url: str = "postgresql://podcastify:podcastify_dev_password@localhost:5432/podcastify"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None

    # Application
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # TTS Service
    chatterbox_url: str = "http://localhost:8001"
    huggingface_api_key: Optional[str] = None

    # Maya1 TTS Configuration
    maya1_provider: str = "huggingface_api"  # "huggingface_api" or "local"
    maya1_model: str = "maya-research/maya1"

    # Model Configuration
    llm_provider: str = "gemini"  # "gemini" or "groq"
    gemini_model: str = "gemini-2.0-flash-exp"
    groq_model: str = "llama-3.1-8b-instant"  # Cheapest: $0.05/$0.08 per M tokens

    # Limits
    max_sources_per_section: int = 5
    max_episode_duration_min: int = 20

    # Storage
    audio_storage_path: str = "./data/audio"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env that aren't defined


# Global settings instance
settings = Settings()
