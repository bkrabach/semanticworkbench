"""
Unit tests for the LLM adapter module.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.llm_adapter import LLMAdapter


@pytest.fixture
def mock_env_openai():
    """Set environment variables for OpenAI provider."""
    original = os.environ.copy()
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["USE_MOCK_LLM"] = "false"
    yield
    os.environ.clear()
    os.environ.update(original)


@pytest.fixture
def mock_env_mock_llm():
    """Set environment variables for mock LLM."""
    original = os.environ.copy()
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["USE_MOCK_LLM"] = "true"
    yield
    os.environ.clear()
    os.environ.update(original)


@pytest.mark.asyncio
async def test_llm_adapter_initialization_mock():
    """Test LLM adapter initialization with mock LLM."""
    with patch.dict("os.environ", {"USE_MOCK_LLM": "true"}):
        adapter = LLMAdapter()
        assert adapter.use_mock is True


@pytest.mark.asyncio
async def test_llm_adapter_initialization_openai():
    """Test LLM adapter initialization with OpenAI provider."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai", "USE_MOCK_LLM": "false"}):
        # Mock the litellm client
        with patch("app.core.llm_adapter.litellm"):
            adapter = LLMAdapter()
            assert adapter.use_mock is False
            assert adapter.provider == "openai"


@pytest.mark.asyncio
async def test_mock_llm_generation():
    """Test generation with mock LLM."""
    with patch.dict("os.environ", {"USE_MOCK_LLM": "true"}):
        with patch("app.core.mock_llm.mock_llm.generate_mock_response") as mock_generate:
            mock_generate.return_value = {"content": "Mock response"}

            adapter = LLMAdapter()
            messages = [{"role": "user", "content": "Hello"}]
            response = await adapter.generate(messages)

            assert response == {"content": "Mock response"}
            mock_generate.assert_called_once()


@pytest.mark.asyncio
async def test_openai_generation():
    """Test OpenAI generation with mocked response."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai", "USE_MOCK_LLM": "false"}):
        # Create a mock agent
        mock_agent = AsyncMock()
        mock_run_response = MagicMock()
        mock_run_response.response.model_dump.return_value = {"content": "OpenAI response"}
        mock_run_response.tool_calls = None
        mock_agent.run.return_value = mock_run_response

        # Patch the agent creation
        with patch("app.core.llm_adapter.CortexLLMAgent", return_value=mock_agent):
            adapter = LLMAdapter()
            messages = [{"role": "user", "content": "Hello"}]
            response = await adapter.generate(messages)

            assert response == {"content": "OpenAI response"}
            mock_agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_generation_with_tool_call():
    """Test generation with tool call in response."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai", "USE_MOCK_LLM": "false"}):
        # Create a mock agent with tool call
        mock_agent = AsyncMock()
        mock_run_response = MagicMock()
        mock_run_response.response.model_dump.return_value = {"content": None}

        # Create a mock tool call
        mock_tool_call = MagicMock()
        mock_tool_call.name = "test_tool"
        mock_tool_call.arguments = '{"param1": "value1", "param2": 42}'
        mock_run_response.tool_calls = [mock_tool_call]

        mock_agent.run.return_value = mock_run_response

        # Patch the agent creation
        with patch("app.core.llm_adapter.CortexLLMAgent", return_value=mock_agent):
            adapter = LLMAdapter()
            messages = [{"role": "user", "content": "Use a tool"}]
            response = await adapter.generate(messages)

            assert response == {"tool": "test_tool", "input": {"param1": "value1", "param2": 42}}
            mock_agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling during generation."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai", "USE_MOCK_LLM": "false"}):
        # Create a mock agent that raises an exception
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = Exception("API error")

        # Patch the agent creation
        with patch("app.core.llm_adapter.CortexLLMAgent", return_value=mock_agent):
            adapter = LLMAdapter()
            messages = [{"role": "user", "content": "Hello"}]

            # The adapter should handle exceptions gracefully
            response = await adapter.generate(messages)

            # Should return a content with error message
            assert "content" in response
            assert "error" in response["content"].lower()
            mock_agent.run.assert_called_once()
