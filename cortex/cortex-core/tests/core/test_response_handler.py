"""
Tests for the response handler module.
"""

import json
import os
from unittest.mock import AsyncMock, patch

import pytest
from app.core.exceptions import ToolExecutionException
from app.core.response_handler import ResponseHandler, get_output_queue, register_tool

# Ensure tests use the mock LLM
os.environ["USE_MOCK_LLM"] = "true"


# Sample test tool
# Use a function name that doesn't start with 'test_' to avoid pytest collection
# Also explicitly tell pytest not to collect this function
@pytest.mark.skip(reason="This is a tool function, not a test")
@register_tool("test_tool")
async def sample_tool_for_testing(param1: str, param2: int = 0):
    """Tool for testing purposes."""
    return {"result": f"{param1}-{param2}"}


@pytest.fixture
def response_handler():
    """Create a ResponseHandler instance for testing."""
    return ResponseHandler()


@pytest.mark.asyncio
async def test_execute_tool_success(response_handler):
    """Test successfully executing a tool."""
    # Execute the test tool
    result = await response_handler._execute_tool("test_tool", {"param1": "test", "param2": 42}, "user123")

    # Verify the result
    assert result == {"result": "test-42"}


@pytest.mark.asyncio
async def test_execute_tool_not_found(response_handler):
    """Test executing a non-existent tool."""
    with pytest.raises(ToolExecutionException) as exc_info:
        await response_handler._execute_tool("nonexistent_tool", {"param": "value"}, "user123")

    assert "Tool not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stream_response(response_handler):
    """Test streaming a response to a queue."""
    # Get a queue for a test conversation
    conversation_id = "test-conversation"
    queue = get_output_queue(conversation_id)

    # Stream a response
    message = "This is a test response"
    await response_handler._stream_response(conversation_id, message)

    # Read from the queue and verify the response chunks
    chunks = []
    done = False

    while not done:
        try:
            event_json = await queue.get()
            event = json.loads(event_json)
            chunks.append(event)

            if event.get("is_final") is True:
                done = True
        except Exception:  # Queue might be empty
            break

    # Verify we got some chunks and a final message
    assert len(chunks) > 0
    assert chunks[-1]["type"] == "response_complete"
    assert chunks[-1]["is_final"] is True

    # Reconstruct the message from chunks
    reconstructed = ""
    for chunk in chunks[:-1]:  # Skip the final [DONE] event
        if "data" in chunk:
            reconstructed += chunk["data"]

    # Verify the reconstructed message matches the original
    assert reconstructed == message


@pytest.mark.asyncio
async def test_handle_message_mock():
    """Test handling a message with mock LLM."""
    # Create a handler with mocked dependencies
    handler = ResponseHandler()

    # Mock the methods we don't want to test here
    handler._store_message = AsyncMock()
    handler._get_conversation_history = AsyncMock(return_value=[])
    handler._stream_response = AsyncMock()

    # Set up the LLM adapter to use mock
    with (
        patch("app.core.llm_adapter.llm_adapter.use_mock", True),
        patch("app.core.mock_llm.mock_llm.generate_mock_response") as mock_generate,
    ):
        # Set up the mock to return a simple response
        mock_generate.return_value = {"content": "This is a mock response"}

        # Call handle_message
        await handler.handle_message(user_id="test-user", conversation_id="test-conv", message_content="Hello, world!")

        # Verify _store_message was called twice (once for user message, once for response)
        assert handler._store_message.call_count == 2

        # Verify _get_conversation_history was called
        handler._get_conversation_history.assert_called_once()

        # Verify _stream_response was called with the expected response
        handler._stream_response.assert_called_once_with("test-conv", "This is a mock response")


@pytest.mark.asyncio
async def test_handle_message_with_tool():
    """Test handling a message with a tool call."""
    # Create a handler with mocked dependencies
    handler = ResponseHandler()

    # Mock the methods we don't want to test here
    handler._store_message = AsyncMock()
    handler._get_conversation_history = AsyncMock(return_value=[])
    handler._stream_response = AsyncMock()
    handler._execute_tool = AsyncMock(return_value="Tool result")

    # Set up the LLM adapter to use mock
    with patch("app.core.llm_adapter.llm_adapter.generate") as mock_generate:
        # First call returns a tool request, second call returns content
        mock_generate.side_effect = [
            {"tool": "test_tool", "input": {"param": "value"}},
            {"content": "Final response after tool"},
        ]

        # Call handle_message
        await handler.handle_message(
            user_id="test-user", conversation_id="test-conv", message_content="Hello, use a tool!"
        )

        # Verify _execute_tool was called
        handler._execute_tool.assert_called_once_with("test_tool", {"param": "value"}, "test-user")

        # Verify LLM was called twice
        assert mock_generate.call_count == 2

        # Verify _stream_response was called with the expected response
        handler._stream_response.assert_called_once_with("test-conv", "Final response after tool")
