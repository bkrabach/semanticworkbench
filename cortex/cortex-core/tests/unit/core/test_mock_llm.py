"""
Tests for the mock_llm module.
"""

import pytest
from typing import Dict, List, Any
from unittest.mock import patch

from app.core.mock_llm import MockLLM, MockLLMAgent
from app.models.domain.pydantic_ai import (
    AssistantMessage,
    UserMessage,
    SystemMessage,
    ChatMessage,
    LLMInput,
    LLMOutput,
)


@pytest.fixture
def mock_llm_agent() -> MockLLMAgent:
    """Create a MockLLMAgent instance for testing."""
    return MockLLMAgent()


@pytest.fixture
def mock_llm() -> MockLLM:
    """Create a MockLLM instance for testing."""
    return MockLLM()


@pytest.mark.asyncio
async def test_model_config(mock_llm_agent: MockLLMAgent) -> None:
    """Test the model configuration returned by the agent."""
    config = mock_llm_agent.model_config()
    assert isinstance(config, dict)
    assert config["model"] == "mock-model"
    assert config["temperature"] == 0.0
    assert config["max_tokens"] == 1000


@pytest.mark.asyncio
async def test_agent_run_normal_response(mock_llm_agent: MockLLMAgent) -> None:
    """Test the agent's response to a normal query."""
    with patch("random.random", return_value=0.5):  # Ensure no tool is triggered
        input_data = LLMInput(
            user_message=UserMessage(content="Tell me about testing"),
            system_message=SystemMessage(content="You are a helpful assistant"),
            history=[],
        )
        
        output = await mock_llm_agent.run(input_data)
        
        assert isinstance(output, LLMOutput)
        assert output.response.content is not None
        assert "testing" in output.response.content
        assert output.tool_calls is None


@pytest.mark.asyncio
async def test_agent_run_time_tool(mock_llm_agent: MockLLMAgent) -> None:
    """Test that the agent returns a time tool when prompted."""
    input_data = LLMInput(
        user_message=UserMessage(content="What time is it?"),
        system_message=None,
        history=[],
    )
    
    output = await mock_llm_agent.run(input_data)
    
    assert isinstance(output, LLMOutput)
    assert output.tool_calls is not None
    assert len(output.tool_calls) == 1
    assert output.tool_calls[0].name == "get_current_time"


@pytest.mark.asyncio
async def test_agent_run_user_tool(mock_llm_agent: MockLLMAgent) -> None:
    """Test that the agent returns a user info tool when prompted."""
    # Force the random value to be above 0.3 to skip first tool condition
    # But below 0.3 in the second condition to trigger the user tool
    with patch("random.random", side_effect=[0.4, 0.1]):
        input_data = LLMInput(
            user_message=UserMessage(content="Tell me about the user"),
            system_message=None,
            history=[],
        )
        
        output = await mock_llm_agent.run(input_data)
        
        assert isinstance(output, LLMOutput)
        assert output.tool_calls is not None
        assert len(output.tool_calls) == 1
        assert output.tool_calls[0].name == "get_user_info"
        assert output.tool_calls[0].arguments == {"user_id": "user123"}


@pytest.mark.asyncio
async def test_agent_run_random_tool(mock_llm_agent: MockLLMAgent) -> None:
    """Test the agent's random tool selection behavior."""
    with patch("random.random", return_value=0.1):  # Force tool selection
        input_data = LLMInput(
            user_message=UserMessage(content="Tell me something"),
            system_message=None,
            history=[],
        )
        
        output = await mock_llm_agent.run(input_data)
        
        assert isinstance(output, LLMOutput)
        assert output.tool_calls is not None
        assert len(output.tool_calls) == 1
        assert output.tool_calls[0].name in ["get_current_time", "get_user_info"]


@pytest.mark.asyncio
async def test_mock_llm_generate_normal_response(mock_llm: MockLLM) -> None:
    """Test the MockLLM's response generation."""
    with patch("random.random", return_value=0.5):  # Ensure no tool is triggered
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Tell me about testing"},
        ]
        
        response = await mock_llm.generate_mock_response(messages)
        
        assert isinstance(response, dict)
        assert "content" in response
        assert "testing" in response["content"]
        assert "tool" not in response


@pytest.mark.asyncio
async def test_mock_llm_generate_with_tool(mock_llm: MockLLM) -> None:
    """Test the MockLLM's tool-based response."""
    with patch("random.random", return_value=0.4):  # Use the first tool
        messages = [
            {"role": "user", "content": "Tell me something"},
        ]
        
        response = await mock_llm.generate_mock_response(messages, with_tool=True)
        
        assert isinstance(response, dict)
        assert "tool" in response
        assert response["tool"] == "get_current_time"
        assert "input" in response
        assert isinstance(response["input"], dict)


@pytest.mark.asyncio
async def test_mock_llm_generate_with_alternate_tool(mock_llm: MockLLM) -> None:
    """Test the MockLLM's alternate tool selection."""
    with patch("random.random", return_value=0.6):  # Use the second tool
        messages = [
            {"role": "user", "content": "Tell me something"},
        ]
        
        response = await mock_llm.generate_mock_response(messages, with_tool=True)
        
        assert isinstance(response, dict)
        assert "tool" in response
        assert response["tool"] == "get_user_info"
        assert "input" in response
        assert response["input"]["user_id"] == "user123"


@pytest.mark.asyncio
async def test_mock_llm_handles_empty_messages(mock_llm: MockLLM) -> None:
    """Test the MockLLM's handling of empty message lists."""
    messages: List[Dict[str, str]] = []
    
    response = await mock_llm.generate_mock_response(messages)
    
    assert isinstance(response, dict)
    assert "content" in response or "tool" in response


@pytest.mark.asyncio
async def test_mock_llm_handles_exception(mock_llm: MockLLM) -> None:
    """Test the MockLLM's exception handling."""
    messages = [
        {"role": "user", "content": "Tell me something"},
    ]
    
    # Mock the agent run method to raise an exception
    with patch.object(mock_llm.agent, 'run', side_effect=Exception("Test error")):
        response = await mock_llm.generate_mock_response(messages)
        
        assert isinstance(response, dict)
        assert "content" in response
        assert "I apologize" in response["content"]