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
    os.environ["OPENAI_API_KEY"] = "test-key"  # Ensure we have a key for validation
    yield
    os.environ.clear()
    os.environ.update(original)


@pytest.mark.asyncio
async def test_llm_adapter_initialization() -> None:
    """Test LLM adapter initialization with OpenAI provider."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}):
        adapter = LLMAdapter()
        assert adapter.provider == "openai"
        assert adapter.model_name == os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")


@pytest.mark.asyncio
async def test_simple_mocked_generation() -> None:
    """Test generation with a mocked adapter."""
    # Create an adapter instance
    adapter = LLMAdapter()

    # Mock the adapter's _generate_openai method
    with patch.object(adapter, "_generate_openai", new_callable=AsyncMock) as mock_generate:
        # Set up the mock to return a simple response
        mock_generate.return_value = {"content": "This is a test response"}

        # Call generate with a test message
        messages = [{"role": "user", "content": "Hello"}]
        response = await adapter.generate(messages)

        # Verify the response
        assert response == {"content": "This is a test response"}
        mock_generate.assert_called_once()


@pytest.mark.asyncio
async def test_openai_generation() -> None:
    """Test OpenAI generation with mocked response."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}):
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
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}):
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
    with patch.dict("os.environ", {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test-key"}):
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
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}):
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
async def test_adapter_initialization_failure() -> None:
    """Test adapter initialization failure."""
    # First, save the original environment
    original_env = os.environ.copy()
    # Set environment variables
    os.environ["LLM_PROVIDER"] = "openai"
    # Remove OPENAI_API_KEY if present
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]

    try:
        # Attempting to initialize the adapter should raise a ValueError
        with pytest.raises(ValueError) as exc_info:
            _adapter = LLMAdapter()  # Variable intentionally unused

        # Verify the error message
        assert "OPENAI_API_KEY environment variable is required" in str(exc_info.value)
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

        with pytest.raises(ValueError) as exc_info:
            _adapter = LLMAdapter()  # Variable intentionally unused
        assert "OPENAI_API_KEY environment variable is required" in str(exc_info.value)

        # Test Azure OpenAI validation
        os.environ.clear()
        os.environ.update(original_env)
        os.environ["LLM_PROVIDER"] = "azure_openai"
        os.environ["AZURE_OPENAI_KEY"] = "key"
        if "AZURE_OPENAI_BASE_URL" in os.environ:
            del os.environ["AZURE_OPENAI_BASE_URL"]

        with pytest.raises(ValueError) as exc_info:
            _adapter = LLMAdapter()  # Variable intentionally unused
        assert "AZURE_OPENAI_KEY and AZURE_OPENAI_BASE_URL environment variables are required" in str(exc_info.value)

        # Test Anthropic validation
        os.environ.clear()
        os.environ.update(original_env)
        os.environ["LLM_PROVIDER"] = "anthropic"
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        with pytest.raises(ValueError) as exc_info:
            _adapter = LLMAdapter()  # Variable intentionally unused
        assert "ANTHROPIC_API_KEY environment variable is required" in str(exc_info.value)
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)
