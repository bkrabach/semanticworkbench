"""
Tests for the core configuration module.
"""
import os
from unittest.mock import patch

from app.core.config import (
    # get_settings imported in the test
    validate_config,
    SERVER_HOST,
    SERVER_PORT,
    DEBUG,
    ENVIRONMENT,
    APP_VERSION,
    USE_AUTH0,
    AUTH0_DOMAIN,
    AUTH0_AUDIENCE,
    DEV_SECRET,
    MEMORY_SERVICE_URL,
    COGNITION_SERVICE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_STREAMING,
    LOG_LEVEL,
)


class TestConfig:
    """Tests for the configuration module."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        assert SERVER_HOST == "0.0.0.0"
        assert SERVER_PORT == 8000
        assert DEBUG is False
        assert ENVIRONMENT == "development"
        assert APP_VERSION == "1.0.0"
        assert USE_AUTH0 is False
        assert AUTH0_DOMAIN == "your-auth0-domain.auth0.com"
        assert AUTH0_AUDIENCE == "https://api.example.com"
        assert DEV_SECRET == "development_secret_key_do_not_use_in_production"
        assert MEMORY_SERVICE_URL == "http://localhost:5001/sse"
        assert COGNITION_SERVICE_URL == "http://localhost:5000/sse"
        assert LLM_MODEL == "claude-3-sonnet-20240229"
        assert LLM_TEMPERATURE == 0.0
        assert LLM_STREAMING is False
        assert LOG_LEVEL == "INFO"
    
    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        test_env = {
            "SERVER_HOST": "127.0.0.1",
            "SERVER_PORT": "9000",
            "DEBUG": "true",
            "ENVIRONMENT": "test",
            "APP_VERSION": "2.0.0",
            "USE_AUTH0": "true",
            "AUTH0_DOMAIN": "test-domain.auth0.com",
            "AUTH0_AUDIENCE": "test-audience",
            "DEV_SECRET": "test-secret",
            "MEMORY_SERVICE_URL": "http://test-memory/sse",
            "COGNITION_SERVICE_URL": "http://test-cognition/sse",
            "CORTEX_LLM_MODEL": "test-model",
            "CORTEX_LLM_TEMPERATURE": "0.5",
            "CORTEX_LLM_STREAMING": "true",
            "LOG_LEVEL": "DEBUG",
        }
        
        with patch.dict(os.environ, test_env):
            # Re-import to refresh values
            import importlib
            import app.core.config
            importlib.reload(app.core.config)
            from app.core.config import (
                SERVER_HOST,
                SERVER_PORT,
                DEBUG,
                ENVIRONMENT,
                APP_VERSION,
                USE_AUTH0,
                AUTH0_DOMAIN,
                AUTH0_AUDIENCE,
                DEV_SECRET,
                MEMORY_SERVICE_URL,
                COGNITION_SERVICE_URL,
                LLM_MODEL,
                LLM_TEMPERATURE,
                LLM_STREAMING,
                LOG_LEVEL,
            )
            
            # Check that values were overridden
            assert SERVER_HOST == "127.0.0.1"
            assert SERVER_PORT == 9000
            assert DEBUG is True
            assert ENVIRONMENT == "test"
            assert APP_VERSION == "2.0.0"
            assert USE_AUTH0 is True
            assert AUTH0_DOMAIN == "test-domain.auth0.com"
            assert AUTH0_AUDIENCE == "test-audience"
            assert DEV_SECRET == "test-secret"
            assert MEMORY_SERVICE_URL == "http://test-memory/sse"
            assert COGNITION_SERVICE_URL == "http://test-cognition/sse"
            assert LLM_MODEL == "test-model"
            assert LLM_TEMPERATURE == 0.5
            assert LLM_STREAMING is True
            assert LOG_LEVEL == "DEBUG"
    
    def test_get_settings(self):
        """Test the get_settings function."""
        # Get settings directly
        from app.core.config import get_settings, SERVER_HOST, SERVER_PORT
        
        settings = get_settings()
        
        # Check structure
        assert "server" in settings
        assert "auth" in settings
        assert "services" in settings
        assert "llm" in settings
        assert "logging" in settings
        
        # Check that server settings match the actual values
        assert settings["server"]["host"] == SERVER_HOST
        assert settings["server"]["port"] == SERVER_PORT
        
        # Check server settings structure
        assert "debug" in settings["server"]
        assert "environment" in settings["server"]
        assert "version" in settings["server"]
        
        # Check auth settings structure
        assert "use_auth0" in settings["auth"]
        assert "auth0_domain" in settings["auth"]
        assert "auth0_audience" in settings["auth"]
        
        # Check services settings structure
        assert "memory_url" in settings["services"]
        assert "cognition_url" in settings["services"]
        
        # Check llm settings structure
        assert "model" in settings["llm"]
        assert "temperature" in settings["llm"]
        assert "streaming" in settings["llm"]
        
        # Check logging settings structure
        assert "level" in settings["logging"]
    
    def test_validate_config_valid(self):
        """Test config validation with valid values."""
        with patch("app.core.config.USE_AUTH0", False), \
             patch("app.core.config.MEMORY_SERVICE_URL", "http://memory-service"), \
             patch("app.core.config.COGNITION_SERVICE_URL", "http://cognition-service"), \
             patch("app.core.config.LLM_MODEL", "model-name"), \
             patch("app.core.config.LLM_TEMPERATURE", 0.7):
            
            result = validate_config()
            assert result is None  # No errors
    
    def test_validate_config_auth0_missing_config(self):
        """Test config validation with missing Auth0 config."""
        with patch("app.core.config.USE_AUTH0", True), \
             patch("app.core.config.AUTH0_DOMAIN", "your-auth0-domain.auth0.com"), \
             patch("app.core.config.AUTH0_AUDIENCE", "https://api.example.com"):
            
            result = validate_config()
            assert result is not None
            assert "AUTH0_DOMAIN is not configured" in result
            assert "AUTH0_AUDIENCE is not configured" in result
    
    def test_validate_config_missing_urls(self):
        """Test config validation with missing service URLs."""
        with patch("app.core.config.MEMORY_SERVICE_URL", ""), \
             patch("app.core.config.COGNITION_SERVICE_URL", ""):
            
            result = validate_config()
            assert result is not None
            assert "MEMORY_SERVICE_URL is required" in result
            assert "COGNITION_SERVICE_URL is required" in result
    
    def test_validate_config_missing_llm_config(self):
        """Test config validation with missing LLM config."""
        with patch("app.core.config.LLM_MODEL", ""):
            result = validate_config()
            assert result is not None
            assert "LLM_MODEL is required" in result
    
    def test_validate_config_invalid_temperature(self):
        """Test config validation with invalid temperature."""
        with patch("app.core.config.LLM_TEMPERATURE", "not-a-float"):
            result = validate_config()
            assert result is not None
            assert "LLM_TEMPERATURE must be a float" in result
    
    def test_validate_config_multiple_errors(self):
        """Test config validation with multiple errors."""
        with patch("app.core.config.USE_AUTH0", True), \
             patch("app.core.config.AUTH0_DOMAIN", "your-auth0-domain.auth0.com"), \
             patch("app.core.config.MEMORY_SERVICE_URL", ""), \
             patch("app.core.config.LLM_TEMPERATURE", "invalid"):
            
            result = validate_config()
            assert result is not None
            assert "AUTH0_DOMAIN is not configured" in result
            assert "MEMORY_SERVICE_URL is required" in result
            assert "LLM_TEMPERATURE must be a float" in result