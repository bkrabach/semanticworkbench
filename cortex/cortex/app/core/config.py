import os
from functools import lru_cache
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseSettings, Field, validator

class Settings(BaseSettings):
    """Application settings."""
    
    # Application info
    APP_NAME: str = "Cortex Core"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Cortex Core PoC Implementation"
    
    # Environment
    DEBUG: bool = Field(default=False)
    ENV: str = Field(default="development")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./cortex.db")
    
    # LLM configuration
    DEFAULT_LLM_MODEL: str = Field(default="gpt-4o")
    FALLBACK_LLM_MODEL: str = Field(default="gpt-3.5-turbo")
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    
    # Memory configuration
    MAX_CONVERSATION_MEMORY: int = Field(default=100)
    
    # Authentication
    AUTH_SECRET_KEY: str = Field(default="CHANGE_THIS_TO_A_RANDOM_SECRET_IN_PRODUCTION")
    TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    DEMO_MODE: bool = Field(default=False)
    
    # CORS settings
    CORS_ORIGINS: List[str] = Field(default=["*"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    
    # Default system prompt
    DEFAULT_SYSTEM_PROMPT: str = Field(
        default="""You are Claude, an AI assistant created by Anthropic. 
You're helpful, harmless, and honest. 
You strive to respond to users with thoughtful, factual, and concise responses.
"""
    )
    
    # SSE settings
    SSE_HEARTBEAT_INTERVAL: int = Field(default=15)  # seconds
    SSE_CONNECTION_TIMEOUT: int = Field(default=300)  # seconds
    
    # Server settings
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    # API endpoints
    API_PREFIX: str = Field(default="/api")
    
    # MCP settings
    DEFAULT_MCP_SERVERS: List[Dict[str, str]] = Field(default=[])
    
    # Demo user settings
    DEMO_USER_ID: str = Field(default="00000000-0000-0000-0000-000000000000")
    DEMO_USER_NAME: str = Field(default="Demo User")
    
    # Tool execution settings
    TOOL_EXECUTION_TIMEOUT: int = Field(default=30)  # seconds
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO")
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True
    
    @validator("DEFAULT_MCP_SERVERS", pre=True)
    def parse_mcp_servers(cls, v):
        """Parse MCP servers from environment variable."""
        if isinstance(v, str):
            try:
                return [
                    {"name": server.split(":")[0], "url": server.split(":")[1]} 
                    for server in v.split(",") if ":" in server
                ]
            except Exception:
                return []
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            return "INFO"
        return v.upper()

@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings.
    
    Uses lru_cache to avoid loading .env file multiple times.
    
    Returns:
        Settings: Application settings
    """
    return Settings()

def setup_logging():
    """Set up logging configuration."""
    import logging
    import sys
    
    settings = get_settings()
    
    # Configure logging
    log_level = getattr(logging, settings.LOG_LEVEL)
    
    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Create formatters
    if settings.ENV == "development":
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    else:
        formatter = logging.Formatter(
            '{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
        )
    
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    if settings.ENV == "development":
        # Set lower level for our app loggers
        logging.getLogger("app").setLevel(log_level)
        
        # Set higher level for noisy libraries
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured with level {settings.LOG_LEVEL}")