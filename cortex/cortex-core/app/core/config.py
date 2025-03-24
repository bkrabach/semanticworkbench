"""
Configuration module for Cortex Core.

Loads configuration from environment variables with sensible defaults.
This module follows the "Ruthless Simplicity" principle with minimal abstractions.
"""

import os
from typing import Dict, Any, Optional
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Server settings
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# Authentication settings
USE_AUTH0 = os.getenv("USE_AUTH0", "false").lower() == "true"
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "your-auth0-domain.auth0.com")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "https://api.example.com")
DEV_SECRET = os.getenv("DEV_SECRET", "development_secret_key_do_not_use_in_production")

# Service URLs
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://localhost:5001/sse")
COGNITION_SERVICE_URL = os.getenv("COGNITION_SERVICE_URL", "http://localhost:5000/sse")

# LLM configuration
LLM_MODEL = os.getenv("CORTEX_LLM_MODEL", "claude-3-sonnet-20240229")
LLM_TEMPERATURE = float(os.getenv("CORTEX_LLM_TEMPERATURE", "0.0"))
LLM_STREAMING = os.getenv("CORTEX_LLM_STREAMING", "false").lower() == "true"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# CORS configuration
ALLOWED_CORS_ORIGINS_STR = os.getenv("ALLOWED_CORS_ORIGINS", "*")
if ALLOWED_CORS_ORIGINS_STR == "*":
    ALLOWED_CORS_ORIGINS = ["*"]
else:
    ALLOWED_CORS_ORIGINS = [origin.strip() for origin in ALLOWED_CORS_ORIGINS_STR.split(",")]


def get_settings() -> Dict[str, Any]:
    """
    Return all configuration settings as a dictionary.
    Useful for debugging or serialization.
    
    Returns:
        A dictionary containing all configuration settings.
    """
    return {
        "server": {
            "host": SERVER_HOST,
            "port": SERVER_PORT,
            "debug": DEBUG,
            "environment": ENVIRONMENT,
            "version": APP_VERSION
        },
        "auth": {
            "use_auth0": USE_AUTH0,
            "auth0_domain": AUTH0_DOMAIN,
            "auth0_audience": AUTH0_AUDIENCE
        },
        "services": {
            "memory_url": MEMORY_SERVICE_URL,
            "cognition_url": COGNITION_SERVICE_URL
        },
        "llm": {
            "model": LLM_MODEL,
            "temperature": LLM_TEMPERATURE,
            "streaming": LLM_STREAMING
        },
        "logging": {
            "level": LOG_LEVEL
        },
        "cors": {
            "allowed_origins": ALLOWED_CORS_ORIGINS
        }
    }


def validate_config() -> Optional[str]:
    """
    Validate critical configuration values and return error message if invalid.
    
    Returns:
        None if configuration is valid, or error message string if invalid.
    """
    errors = []
    
    # Check auth configuration
    if USE_AUTH0:
        if AUTH0_DOMAIN == "your-auth0-domain.auth0.com":
            errors.append("AUTH0_DOMAIN is not configured but USE_AUTH0=true")
        if AUTH0_AUDIENCE == "https://api.example.com":
            errors.append("AUTH0_AUDIENCE is not configured but USE_AUTH0=true")
    
    # Check service URLs
    if not MEMORY_SERVICE_URL:
        errors.append("MEMORY_SERVICE_URL is required")
    if not COGNITION_SERVICE_URL:
        errors.append("COGNITION_SERVICE_URL is required")
    
    # Check LLM configuration
    if not LLM_MODEL:
        errors.append("LLM_MODEL is required")
    try:
        float(LLM_TEMPERATURE)
    except ValueError:
        errors.append(f"LLM_TEMPERATURE must be a float, got {LLM_TEMPERATURE}")
    
    # Return None if no errors, otherwise join error messages
    if not errors:
        logger.info("Configuration validation passed")
        return None
    
    error_message = "Configuration validation failed: " + "; ".join(errors)
    logger.error(error_message)
    return error_message


# Log the configuration on module import
logger.debug(f"Loaded configuration for environment: {ENVIRONMENT}")