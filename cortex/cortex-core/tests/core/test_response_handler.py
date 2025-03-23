"""
Tests for the response handler module.
"""

import json
import os
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.core.exceptions import ToolExecutionException
from app.core.response_handler import ResponseHandler, register_tool

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
    # Create a test queue
    test_queue = asyncio.Queue()
    # Create test conversation ID
    conversation_id = "test-conversation"

    # Mock get_output_queue to return our test queue
    # Also create a mock message to provide ID for the response
    mock_message = Mock()
    mock_message.id = "test-message-id"
    
    # Create a mock message repository
    mock_repo = Mock()
    mock_repo.list_by_conversation = AsyncMock(return_value=[mock_message])
    
    # Create a mock UnitOfWork context manager
    mock_uow = Mock()
    mock_uow.repositories = Mock()
    mock_uow.repositories.get_message_repository.return_value = mock_repo
    
    mock_uow_context = AsyncMock()
    mock_uow_context.__aenter__.return_value = mock_uow
    
    with patch('app.core.response_handler.get_output_queue', return_value=test_queue), \
         patch('app.core.response_handler.UnitOfWork.for_transaction', return_value=mock_uow_context):

        # Stream a response
        message = "This is a test response"
        await response_handler._stream_response(conversation_id, message)

        # Calculate expected number of chunks (50 chars per chunk)
        expected_chunks = (len(message) + 49) // 50  # Ceiling division

        # Read from the queue and verify the response chunks
        chunks = []
        for _ in range(expected_chunks + 1):  # +1 for the [DONE] event
            event_json = await asyncio.wait_for(test_queue.get(), timeout=1.0)
            event = json.loads(event_json)
            chunks.append(event)

        # Verify chunk events
        chunk_events = chunks[:-1]  # All except last (done) event
        done_event = chunks[-1]  # Last event is done
        
        # Verify all chunk events
        for event in chunk_events:
            assert event["type"] == "response_chunk"
            assert event["conversation_id"] == conversation_id
            assert event["message_id"] == "test-message-id"
            assert "data" in event
            assert event["is_final"] is False

        # Verify done event
        assert done_event["type"] == "response_complete"
        assert done_event["conversation_id"] == conversation_id
        assert done_event["message_id"] == "test-message-id"
        assert done_event["is_final"] is True

        # Reconstruct the message from chunks
        reconstructed = ""
        for chunk in chunk_events:
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
    
    # Create test message objects
    user_message = Mock()
    user_message.id = "user-message-id"
    
    assistant_message = Mock()
    assistant_message.id = "assistant-message-id"

    # Mock the methods we don't want to test here
    handler._store_message = AsyncMock(side_effect=[user_message, assistant_message])
    handler._get_conversation_history = AsyncMock(return_value=[])
    handler._stream_response = AsyncMock()
    handler._execute_tool = AsyncMock(return_value="Tool result")

    # Mock output queue
    mock_queue = AsyncMock()
    
    # Set up the LLM adapter to use mock
    with patch("app.core.llm_adapter.llm_adapter.generate") as mock_generate, \
         patch("app.core.response_handler.get_output_queue", return_value=mock_queue):
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
