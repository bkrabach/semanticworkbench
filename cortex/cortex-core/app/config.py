"""Configuration settings for the Cortex application."""
import os
from typing import Any, Dict, List, Optional, Union

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration settings for the Cortex application."""
    
    # Application settings
    APP_NAME: str = "Cortex Core"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cortex"
    SQL_ECHO: bool = False
    
    # Security settings
    SECRET_KEY: str = "change_this_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # LLM settings
    DEFAULT_LLM_MODEL: str = "openai/gpt-3.5-turbo"
    LLM_TIMEOUT: int = 60
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # SSE settings
    SSE_HEARTBEAT_INTERVAL: int = 15  # seconds
    SSE_RETRY_TIMEOUT: int = 5000  # milliseconds
    
    # MCP settings
    MCP_DEFAULT_TIMEOUT: int = 60  # seconds
    
    # Path settings
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    
    class Config:
        """Configuration for the Settings class."""
        
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()