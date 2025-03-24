"""
Unit tests for the LLM adapter module.
"""

import os
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.llm_adapter import LLMAdapter


@pytest.fixture
def mock_env_openai() -> Generator[None, None, None]:
    """Set environment variables for OpenAI provider."""
    original = os.environ.copy()
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["USE_MOCK_LLM"] = "false"
    os.environ["OPENAI_API_KEY"] = "test-key"  # Ensure we have a key for validation
    yield
    os.environ.clear()
    os.environ.update(original)


@pytest.fixture
def mock_env_mock_llm() -> Generator[None, None, None]:
    """Set environment variables for mock LLM."""
    original = os.environ.copy()
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["USE_MOCK_LLM"] = "true"
    yield
    os.environ.clear()
    os.environ.update(original)


@pytest.mark.asyncio
async def test_llm_adapter_initialization_mock() -> None:
    """Test LLM adapter initialization with mock LLM."""
    with patch.dict("os.environ", {"USE_MOCK_LLM": "true"}):
        adapter = LLMAdapter()
        assert adapter.use_mock is True


@pytest.mark.asyncio
async def test_llm_adapter_initialization_openai() -> None:
    """Test LLM adapter initialization with OpenAI provider."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai", "USE_MOCK_LLM": "false", "OPENAI_API_KEY": "test-key"}):
        adapter = LLMAdapter()
        assert adapter.use_mock is False
        assert adapter.provider == "openai"
        assert adapter.model_name == os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")


@pytest.mark.asyncio
async def test_mock_llm_generation() -> None:
    """Test generation with development mode mock LLM."""
    with patch.dict("os.environ", {"USE_MOCK_LLM": "true"}):
        adapter = LLMAdapter()
        messages = [{"role": "user", "content": "Hello"}]
        
        response = await adapter.generate(messages)

        # Simple fixed response for development mode
        assert "content" in response
        assert "development mode" in response["content"].lower()


@pytest.mark.asyncio
async def test_openai_generation() -> None:
    """Test OpenAI generation with mocked response."""
    with patch.dict("os.environ", {
        "LLM_PROVIDER": "openai", 
        "USE_MOCK_LLM": "false", 
        "OPENAI_API_KEY": "test-key"
    }):
        # Create a mock OpenAI client and response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "OpenAI response"
        mock_response.choices[0].message.tool_calls = None
        
        # Mock the AsyncOpenAI client
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Patch the OpenAI client creation
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            adapter = LLMAdapter()
            messages = [{"role": "user", "content": "Hello"}]
            response = await adapter.generate(messages)
            
            assert response == {"content": "OpenAI response"}
            mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_generation_with_tool_call() -> None:
    """Test generation with tool call in response."""
    with patch.dict("os.environ", {
        "LLM_PROVIDER": "openai", 
        "USE_MOCK_LLM": "false", 
        "OPENAI_API_KEY": "test-key"
    }):
        # Create a mock OpenAI response with tool call
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call-123"
        mock_tool_call.function = MagicMock()
        mock_tool_call.function.name = "test_tool"
        mock_tool_call.function.arguments = '{"param1": "value1", "param2": 42}'
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = ""
        mock_response.choices[0].message.tool_calls = [mock_tool_call]
        
        # Mock the AsyncOpenAI client
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Patch the OpenAI client creation
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            adapter = LLMAdapter()
            messages = [{"role": "user", "content": "Use a tool"}]
            response = await adapter.generate(messages)
            
            # Check that tool name and arguments dictionary are returned
            assert response == {"tool": "test_tool", "input": {"param1": "value1", "param2": 42}}
            mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_generation_with_anthropic_model() -> None:
    """Test generation with Anthropic provider."""
    with patch.dict("os.environ", {
        "LLM_PROVIDER": "anthropic", 
        "USE_MOCK_LLM": "false", 
        "ANTHROPIC_API_KEY": "test-key"
    }):
        # Create a mock Anthropic response
        mock_content_block = MagicMock()
        mock_content_block.text = "Anthropic response"
        
        mock_response = MagicMock()
        mock_response.content = [mock_content_block]
        
        # Mock the AsyncAnthropic client
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        # Patch the Anthropic client creation
        with patch("anthropic.AsyncAnthropic", return_value=mock_client):
            adapter = LLMAdapter()
            messages = [{"role": "user", "content": "Hello"}]
            response = await adapter.generate(messages)
            
            assert response == {"content": "Anthropic response"}
            mock_client.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling() -> None:
    """Test error handling during generation."""
    with patch.dict("os.environ", {
        "LLM_PROVIDER": "openai", 
        "USE_MOCK_LLM": "false", 
        "OPENAI_API_KEY": "test-key"
    }):
        # Mock the OpenAI client to raise an exception
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
        
        # Patch the OpenAI client creation
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            adapter = LLMAdapter()
            messages = [{"role": "user", "content": "Hello"}]
            
            # The adapter should handle exceptions gracefully
            response = await adapter.generate(messages)
            
            # Should return None on error
            assert response is None
            mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_adapter_initialization_failure_fallback() -> None:
    """Test adapter initialization failure with fallback to development mode."""
    # First, save the original environment
    original_env = os.environ.copy()
    # Set environment variables
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["USE_MOCK_LLM"] = "false"
    # Remove OPENAI_API_KEY if present
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    try:
        # Patch the validation method to raise an exception
        with patch.object(LLMAdapter, "_validate_provider_config", side_effect=Exception("Missing API key")):
            adapter = LLMAdapter()
            
            # Should fall back to development mode
            assert adapter.use_mock is True
            
            # Test that it uses development mode response generation
            messages = [{"role": "user", "content": "Hello"}]
            response = await adapter.generate(messages)
            
            # Verify it has a content field with development mode message
            assert "content" in response
            assert "development mode" in response["content"].lower()
    finally:
        # Restore the original environment
        os.environ.clear()
        os.environ.update(original_env)


@pytest.mark.asyncio
async def test_validate_provider_config() -> None:
    """Test provider configuration validation."""
    # Test OpenAI validation
    original_env = os.environ.copy()
    try:
        # Set environment and remove keys we want to test
        os.environ["LLM_PROVIDER"] = "openai"
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        adapter = LLMAdapter()
        with pytest.raises(ValueError) as exc_info:
            adapter._validate_provider_config()
        assert "OPENAI_API_KEY environment variable is required" in str(exc_info.value)
        
        # Test Azure OpenAI validation
        os.environ.clear()
        os.environ.update(original_env)
        os.environ["LLM_PROVIDER"] = "azure_openai"
        os.environ["AZURE_OPENAI_KEY"] = "key"
        if "AZURE_OPENAI_BASE_URL" in os.environ:
            del os.environ["AZURE_OPENAI_BASE_URL"]
        
        adapter = LLMAdapter()
        with pytest.raises(ValueError) as exc_info:
            adapter._validate_provider_config()
        assert "AZURE_OPENAI_KEY and AZURE_OPENAI_BASE_URL environment variables are required" in str(exc_info.value)
        
        # Test Anthropic validation
        os.environ.clear()
        os.environ.update(original_env)
        os.environ["LLM_PROVIDER"] = "anthropic"
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        adapter = LLMAdapter()
        with pytest.raises(ValueError) as exc_info:
            adapter._validate_provider_config()
        assert "ANTHROPIC_API_KEY environment variable is required" in str(exc_info.value)
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)