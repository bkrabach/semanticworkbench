"""
Cognition Service - Configuration

Defines settings for the Cognition Service including server configuration,
LLM provider settings, and other operational parameters.
"""

import os

from pydantic import BaseModel


class Settings(BaseModel):
    """Configuration settings for the Cognition Service."""

    # Server settings
    port: int = int(os.getenv("COGNITION_SERVICE_PORT", "5000"))
    host: str = os.getenv("COGNITION_SERVICE_HOST", "0.0.0.0")

    # LLM provider settings
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")  # or "openai", etc.
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # LLM configuration
    model_name: str = os.getenv("LLM_MODEL_NAME", "claude-3-sonnet-20240229")  # or "gpt-4", etc.
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))

    # System prompt
    system_prompt: str = os.getenv(
        "SYSTEM_PROMPT", "You are Cortex, a helpful AI assistant. Provide concise, accurate answers."
    )

    # Memory service connection (optional)
    memory_service_url: str = os.getenv("MEMORY_SERVICE_URL", "http://localhost:5001/sse")

    # Feature flags
    enable_memory_integration: bool = os.getenv("ENABLE_MEMORY", "false").lower() == "true"
    enable_tool_use: bool = os.getenv("ENABLE_TOOL_USE", "false").lower() == "true"


# Create a global settings instance
settings = Settings()
