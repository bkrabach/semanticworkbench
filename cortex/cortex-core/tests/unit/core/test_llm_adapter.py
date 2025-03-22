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
        # Create a mock for the CortexLLMAgent
        with patch('app.core.llm_adapter.CortexLLMAgent') as mock_agent_class:
            mock_agent_instance = AsyncMock()
            mock_agent_class.return_value = mock_agent_instance
            
            adapter = LLMAdapter()
            assert adapter.use_mock is False
            assert adapter.provider == 'openai'
            
            # Verify the agent was initialized
            mock_agent_class.assert_called_once()


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
        # Create mock objects for the chain of calls
        mock_output = MagicMock()
        mock_output.tool_calls = None
        mock_output.response = MagicMock()
        mock_output.response.content = "OpenAI response"
        
        # Create a mock agent instance
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_output
        
        # Patch the agent creation
        with patch('app.core.llm_adapter.CortexLLMAgent') as mock_agent_class:
            mock_agent_class.return_value = mock_agent
            
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
        mock_output = MagicMock()
        
        # Mock the tool call structure
        mock_tool_call = MagicMock()
        mock_tool_call.name = "test_tool"
        # Set arguments as a dictionary, not a string
        mock_tool_call.arguments = {"param1": "value1", "param2": 42}
        
        # Set up the response structure
        mock_output.tool_calls = [mock_tool_call]
        mock_output.response = MagicMock()
        mock_output.response.content = ""
        
        mock_agent.run.return_value = mock_output
        
        # Patch the agent creation
        with patch('app.core.llm_adapter.CortexLLMAgent') as mock_agent_class:
            mock_agent_class.return_value = mock_agent
            
            adapter = LLMAdapter()
            messages = [{"role": "user", "content": "Use a tool"}]
            response = await adapter.generate(messages)
            
            # Check that tool name and arguments dictionary are returned
            assert response == {"tool": "test_tool", "input": {"param1": "value1", "param2": 42}}
            mock_agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_generation_with_anthropic_model():
    """Test generation with Anthropic provider."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "anthropic", "USE_MOCK_LLM": "false"}):
        # Create mock objects for the chain of calls
        mock_output = MagicMock()
        mock_output.tool_calls = None
        mock_output.response = MagicMock()
        mock_output.response.content = "Anthropic response"
        
        # Create a mock agent instance
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_output
        
        # Patch the agent creation
        with patch('app.core.llm_adapter.CortexLLMAgent') as mock_agent_class:
            mock_agent_class.return_value = mock_agent
            
            adapter = LLMAdapter()
            messages = [{"role": "user", "content": "Hello"}]
            response = await adapter.generate(messages)
            
            assert response == {"content": "Anthropic response"}
            mock_agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling during generation."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai", "USE_MOCK_LLM": "false"}):
        # Create a mock agent that raises an exception
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = Exception("API error")
        
        # Patch the agent creation
        with patch('app.core.llm_adapter.CortexLLMAgent') as mock_agent_class:
            mock_agent_class.return_value = mock_agent
            
            adapter = LLMAdapter()
            messages = [{"role": "user", "content": "Hello"}]
            
            # The adapter should handle exceptions gracefully
            response = await adapter.generate(messages)
            
            # Should return None on error
            assert response is None
            mock_agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_adapter_initialization_failure_fallback():
    """Test adapter initialization failure with fallback to mock."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "openai", "USE_MOCK_LLM": "false"}):
        # Create a mock for the CortexLLMAgent that raises an exception
        with patch('app.core.llm_adapter.CortexLLMAgent', side_effect=Exception("Init error")):
            adapter = LLMAdapter()
            
            # Should fall back to mock
            assert adapter.use_mock is True
            
            # Test that it uses mock_llm for generation
            with patch("app.core.mock_llm.mock_llm.generate_mock_response") as mock_generate:
                mock_generate.return_value = {"content": "Fallback response"}
                
                messages = [{"role": "user", "content": "Hello"}]
                response = await adapter.generate(messages)
                
                assert response == {"content": "Fallback response"}
                mock_generate.assert_called_once()