"""
Tests for the Cognition Service FastMCP server.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from cognition_service.main import mcp, generate_reply, evaluate_context_tool, health
from cognition_service.config import settings


@pytest.fixture
def mock_logic_functions():
    """Fixture for mocking the logic functions."""
    with patch("cognition_service.main.generate_ai_response") as mock_generate, \
         patch("cognition_service.main.evaluate_context") as mock_evaluate:
        
        mock_generate.return_value = "Mock response from generate_ai_response"
        mock_evaluate.return_value = "Mock response from evaluate_context"
        
        yield {
            "generate_ai_response": mock_generate,
            "evaluate_context": mock_evaluate
        }


@pytest.mark.asyncio
async def test_generate_reply_success(mock_logic_functions):
    """Test the generate_reply MCP tool with successful logic."""
    # Call the MCP tool
    result = await generate_reply(
        user_id="test-user",
        conversation_id="test-convo",
        content="Hello, how are you?"
    )
    
    # Verify result
    assert result == "Mock response from generate_ai_response"
    
    # Verify logic function was called
    mock_logic_functions["generate_ai_response"].assert_called_once()
    
    # Verify the correct arguments were passed (regardless of position vs keyword)
    args, kwargs = mock_logic_functions["generate_ai_response"].call_args
    if args:  # If called with positional args
        assert "test-user" in args
        assert "test-convo" in args
        assert "Hello, how are you?" in args
    else:  # If called with keyword args
        assert kwargs.get("user_id") == "test-user"
        assert kwargs.get("conversation_id") == "test-convo"
        assert kwargs.get("content") == "Hello, how are you?"


@pytest.mark.asyncio
async def test_generate_reply_error(mock_logic_functions):
    """Test the generate_reply MCP tool when logic function raises an exception."""
    # Make the logic function raise an exception
    mock_logic_functions["generate_ai_response"].side_effect = Exception("Test error")
    
    # Call the MCP tool
    result = await generate_reply(
        user_id="test-user",
        conversation_id="test-convo",
        content="Hello, how are you?"
    )
    
    # Verify result contains error message
    assert "apologize" in result.lower()
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_evaluate_context_tool_success(mock_logic_functions):
    """Test the evaluate_context_tool MCP tool with successful logic."""
    # Call the MCP tool
    result = await evaluate_context_tool(
        user_id="test-user",
        conversation_id="test-convo",
        message="Hello, evaluate this",
        memory_snippets=[{"content": "Previous interaction"}],
        expert_insights=[{"source": "Expert", "content": "Insight"}]
    )
    
    # Verify result
    assert isinstance(result, dict)
    assert result["message"] == "Mock response from evaluate_context"
    
    # Verify logic function was called with correct args
    mock_logic_functions["evaluate_context"].assert_called_once_with(
        user_id="test-user",
        conversation_id="test-convo",
        message="Hello, evaluate this",
        memory_snippets=[{"content": "Previous interaction"}],
        expert_insights=[{"source": "Expert", "content": "Insight"}]
    )


@pytest.mark.asyncio
async def test_evaluate_context_tool_default_values(mock_logic_functions):
    """Test the evaluate_context_tool MCP tool with default values for optional params."""
    # Call the MCP tool without optional params
    result = await evaluate_context_tool(
        user_id="test-user",
        conversation_id="test-convo",
        message="Hello, evaluate this"
    )
    
    # Verify result
    assert isinstance(result, dict)
    assert result["message"] == "Mock response from evaluate_context"
    
    # Verify logic function was called with empty lists for optional params
    mock_logic_functions["evaluate_context"].assert_called_once_with(
        user_id="test-user",
        conversation_id="test-convo",
        message="Hello, evaluate this",
        memory_snippets=[],
        expert_insights=[]
    )


@pytest.mark.asyncio
async def test_evaluate_context_tool_error(mock_logic_functions):
    """Test the evaluate_context_tool MCP tool when logic function raises an exception."""
    # Make the logic function raise an exception
    mock_logic_functions["evaluate_context"].side_effect = Exception("Test error")
    
    # Call the MCP tool
    result = await evaluate_context_tool(
        user_id="test-user",
        conversation_id="test-convo",
        message="Hello, evaluate this"
    )
    
    # Verify result contains error message
    assert isinstance(result, dict)
    assert "apologize" in result["message"].lower()
    assert "error" in result["message"].lower()


@pytest.mark.asyncio
async def test_health():
    """Test the health check endpoint."""
    # Call the health endpoint
    result = await health()
    
    # Verify result
    assert isinstance(result, dict)
    assert result["status"] == "healthy"
    assert result["service"] == "cognition"
    assert "version" in result
    assert result["provider"] == settings.llm_provider
    assert result["model"] == settings.model_name


def test_mcp_instance():
    """Test that the MCP server instance is properly configured."""
    assert mcp.name == "CognitionService"
    assert hasattr(mcp, "tool")
    assert hasattr(mcp, "settings")
    assert hasattr(mcp, "run")