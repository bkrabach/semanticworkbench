"""
Tests for the response handler module.
"""

import json
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.core.exceptions import ToolExecutionException
from app.core.response_handler import ResponseHandler, register_tool


# Sample test tool
# Use a function name that doesn't start with 'test_' to avoid pytest collection
# Also explicitly tell pytest not to collect this function
@pytest.mark.skip(reason="This is a tool function, not a test")
@register_tool("test_tool")
async def sample_tool_for_testing(param1: str, param2: int = 0, user_id: str = "") -> dict:
    """Tool for testing purposes."""
    return {"result": f"{param1}-{param2}"}


@pytest.fixture
def response_handler() -> ResponseHandler:
    """Create a ResponseHandler instance for testing."""
    return ResponseHandler()


@pytest.mark.asyncio
async def test_execute_tool_success(response_handler: ResponseHandler) -> None:
    """Test successfully executing a tool."""
    # Execute the test tool
    result = await response_handler._execute_tool("test_tool", {"param1": "test", "param2": 42}, "user123")

    # Verify the result
    assert result == {"result": "test-42"}


@pytest.mark.asyncio
async def test_execute_tool_not_found(response_handler: ResponseHandler) -> None:
    """Test executing a non-existent tool."""
    with pytest.raises(ToolExecutionException) as exc_info:
        await response_handler._execute_tool("nonexistent_tool", {"param": "value"}, "user123")

    assert "Tool not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stream_response(response_handler: ResponseHandler) -> None:
    """Test streaming a response to a queue."""
    # Create a test queue
    test_queue: asyncio.Queue = asyncio.Queue()
    # Create test conversation ID
    conversation_id = "test-conversation"

    # Mock get_output_queue to return our test queue
    # Also create a mock message to provide ID for the response
    mock_message: Mock = Mock()
    mock_message.id = "test-message-id"
    
    # Create a mock message repository
    mock_repo: Mock = Mock()
    mock_repo.list_by_conversation = AsyncMock(return_value=[mock_message])
    
    # Create a mock UnitOfWork context manager
    mock_uow: Mock = Mock()
    mock_uow.repositories = Mock()
    mock_uow.repositories.get_message_repository.return_value = mock_repo
    
    mock_uow_context: AsyncMock = AsyncMock()
    mock_uow_context.__aenter__.return_value = mock_uow
    
    with patch('app.core.response_handler.get_output_queue', return_value=test_queue), \
         patch('app.core.response_handler.UnitOfWork.for_transaction', return_value=mock_uow_context):

        # Stream a response
        message: str = "This is a test response"
        await response_handler._stream_response(conversation_id, message)

        # Calculate expected number of chunks (50 chars per chunk)
        expected_chunks: int = (len(message) + 49) // 50  # Ceiling division

        # Read from the queue and verify the response chunks
        chunks: list[dict] = []
        for _ in range(expected_chunks + 1):  # +1 for the [DONE] event
            event_json = await asyncio.wait_for(test_queue.get(), timeout=1.0)
            event = json.loads(event_json)
            chunks.append(event)

        # Verify chunk events
        chunk_events: list[dict] = chunks[:-1]  # All except last (done) event
        done_event: dict = chunks[-1]  # Last event is done
        
        # Verify all chunk events
        for event in chunk_events:
            assert event["type"] == "message"
            assert event["message_type"] == "chunk"
            assert event["data"]["conversation_id"] == conversation_id
            assert event["data"]["message_id"] == "test-message-id"
            assert "content" in event["data"]
            assert "sender" in event["data"]
            assert event["data"]["sender"]["id"] == "cortex-core"
            assert event["data"]["sender"]["name"] == "Cortex"
            assert event["data"]["sender"]["role"] == "assistant"
            assert "metadata" in event

        # Verify done event
        assert done_event["type"] == "message"
        assert done_event["message_type"] == "complete"
        assert done_event["data"]["conversation_id"] == conversation_id
        assert done_event["data"]["message_id"] == "test-message-id"
        assert "sender" in done_event["data"]
        assert done_event["data"]["sender"]["id"] == "cortex-core"
        assert done_event["data"]["sender"]["name"] == "Cortex"
        assert done_event["data"]["sender"]["role"] == "assistant"
        assert "metadata" in done_event

        # Reconstruct the message from chunks
        reconstructed: str = ""
        for chunk in chunk_events:
            reconstructed += chunk["data"]["content"]

        # Verify the reconstructed message matches the original
        assert reconstructed == message


@pytest.mark.asyncio
async def test_handle_message_mock_streaming() -> None:
    """Test handling a message with mocked dependencies and streaming enabled."""
    # Create a handler with mocked dependencies
    handler = ResponseHandler()

    # Mock the methods we don't want to test here
    user_message: Mock = Mock()
    user_message.id = "user-message-id"
    
    store_message_mock: AsyncMock = AsyncMock(return_value=user_message)
    get_history_mock: AsyncMock = AsyncMock(return_value=[])
    get_context_mock: AsyncMock = AsyncMock(return_value=[])
    prepare_messages_mock: AsyncMock = AsyncMock(return_value=[{"role": "user", "content": "Hello, world!"}])
    process_llm_mock: AsyncMock = AsyncMock(return_value="This is a mock response")
    handle_final_response_mock: AsyncMock = AsyncMock()
    
    with patch.object(handler, '_store_message', new=store_message_mock), \
         patch.object(handler, '_get_conversation_history', new=get_history_mock), \
         patch.object(handler, '_get_cognition_context', new=get_context_mock), \
         patch.object(handler, '_prepare_messages_with_context', new=prepare_messages_mock), \
         patch.object(handler, '_process_llm_conversation', new=process_llm_mock), \
         patch.object(handler, '_handle_final_response', new=handle_final_response_mock), \
         patch('app.core.response_handler.llm_adapter'):

        # Call handle_message with streaming enabled (default)
        await handler.handle_message(
            user_id="test-user", 
            conversation_id="test-conv", 
            message_content="Hello, world!"
        )

        # Verify _store_message was called for user message
        store_message_mock.assert_called_once_with(
            conversation_id="test-conv", 
            sender_id="test-user", 
            content="Hello, world!", 
            role="user", 
            metadata=None
        )

        # Verify _get_cognition_context was called
        get_context_mock.assert_called_once_with("test-user", "Hello, world!")

        # Verify _prepare_messages_with_context was called
        prepare_messages_mock.assert_called_once_with([], "Hello, world!", [])

        # Verify _process_llm_conversation was called
        process_llm_mock.assert_called_once_with("test-user", "test-conv", [{"role": "user", "content": "Hello, world!"}], "user-message-id")

        # Verify _handle_final_response was called with streaming=True (default)
        handle_final_response_mock.assert_called_once_with(
            "test-conv", "This is a mock response", True, "user-message-id"
        )


@pytest.mark.asyncio
async def test_handle_message_mock_non_streaming() -> None:
    """Test handling a message with mocked dependencies and streaming disabled."""
    # Create a handler with mocked dependencies
    handler = ResponseHandler()

    # Mock the methods we don't want to test here
    user_message: Mock = Mock()
    user_message.id = "user-message-id"
    
    store_message_mock: AsyncMock = AsyncMock(return_value=user_message)
    get_history_mock: AsyncMock = AsyncMock(return_value=[])
    get_context_mock: AsyncMock = AsyncMock(return_value=[])
    prepare_messages_mock: AsyncMock = AsyncMock(return_value=[{"role": "user", "content": "Hello, world!"}])
    process_llm_mock: AsyncMock = AsyncMock(return_value="This is a mock response")
    handle_final_response_mock: AsyncMock = AsyncMock()
    
    with patch.object(handler, '_store_message', new=store_message_mock), \
         patch.object(handler, '_get_conversation_history', new=get_history_mock), \
         patch.object(handler, '_get_cognition_context', new=get_context_mock), \
         patch.object(handler, '_prepare_messages_with_context', new=prepare_messages_mock), \
         patch.object(handler, '_process_llm_conversation', new=process_llm_mock), \
         patch.object(handler, '_handle_final_response', new=handle_final_response_mock), \
         patch('app.core.response_handler.llm_adapter'):

        # Call handle_message with streaming disabled
        await handler.handle_message(
            user_id="test-user", 
            conversation_id="test-conv", 
            message_content="Hello, world!",
            streaming=False
        )

        # Verify _store_message was called for user message
        store_message_mock.assert_called_once_with(
            conversation_id="test-conv", 
            sender_id="test-user", 
            content="Hello, world!", 
            role="user", 
            metadata=None
        )

        # Verify _get_cognition_context was called
        get_context_mock.assert_called_once_with("test-user", "Hello, world!")

        # Verify _prepare_messages_with_context was called
        prepare_messages_mock.assert_called_once_with([], "Hello, world!", [])

        # Verify _process_llm_conversation was called
        process_llm_mock.assert_called_once_with("test-user", "test-conv", [{"role": "user", "content": "Hello, world!"}], "user-message-id")

        # Verify _handle_final_response was called with streaming=False
        handle_final_response_mock.assert_called_once_with(
            "test-conv", "This is a mock response", False, "user-message-id"
        )


@pytest.mark.asyncio
async def test_send_event(response_handler: ResponseHandler) -> None:
    """Test sending an event through the SSE queue."""
    # Create a test queue
    test_queue: asyncio.Queue = asyncio.Queue()
    # Create test conversation ID
    conversation_id: str = "test-conversation"
    # Create test message ID
    message_id: str = "test-message-id"
    
    # Mock get_output_queue to return our test queue
    with patch('app.core.response_handler.get_output_queue', return_value=test_queue):
        # Test sender info
        sender: dict[str, str] = {
            "id": "test-sender",
            "name": "Test Sender",
            "role": "test"
        }
        
        # Send an event
        await response_handler._send_event(
            conversation_id=conversation_id,
            event_type="test_event",
            message_id=message_id,
            content="Test content",
            sender=sender,
            metadata={"test_key": "test_value"}
        )
        
        # Get the event from the queue
        event_json = await asyncio.wait_for(test_queue.get(), timeout=1.0)
        event = json.loads(event_json)
        
        # Verify the event structure
        assert event["type"] == "message"
        assert event["message_type"] == "test_event"
        assert event["data"]["content"] == "Test content"
        assert event["data"]["conversation_id"] == conversation_id
        assert event["data"]["message_id"] == message_id
        assert "timestamp" in event["data"]
        assert event["data"]["sender"] == sender
        assert event["metadata"] == {"test_key": "test_value"}

@pytest.mark.asyncio
async def test_handle_tool_execution(response_handler: ResponseHandler) -> None:
    """Test handling tool execution with events."""
    # Create a test queue
    test_queue: asyncio.Queue = asyncio.Queue()
    # Create test conversation ID
    conversation_id: str = "test-conversation"
    # Create test tool details
    tool_name: str = "test_tool"
    tool_args: dict[str, str] = {"param1": "test"}
    user_id: str = "test-user"
    
    # Mock the dependencies
    with patch('app.core.response_handler.get_output_queue', return_value=test_queue), \
         patch.object(response_handler, '_execute_tool', return_value="Tool result"):
        
        # Execute the tool
        result = await response_handler._handle_tool_execution(
            conversation_id=conversation_id,
            tool_name=tool_name,
            tool_args=tool_args,
            user_id=user_id
        )
        
        # Verify the result
        assert result == "Tool result"
        
        # Get the tool execution event
        tool_event_json = await asyncio.wait_for(test_queue.get(), timeout=1.0)
        tool_event = json.loads(tool_event_json)
        
        # Verify the tool execution event
        assert tool_event["message_type"] == "tool"
        assert f"Executing tool: {tool_name}" in tool_event["data"]["content"]
        assert tool_event["data"]["sender"]["role"] == "tool"
        assert tool_event["metadata"]["tool_name"] == tool_name
        assert tool_event["metadata"]["tool_args"] == tool_args
        
        # Get the tool result event
        result_event_json = await asyncio.wait_for(test_queue.get(), timeout=1.0)
        result_event = json.loads(result_event_json)
        
        # Verify the tool result event
        assert result_event["message_type"] == "tool_result"
        assert result_event["data"]["content"] == "Tool result"
        assert result_event["data"]["sender"]["role"] == "tool"
        assert result_event["metadata"]["tool_name"] == tool_name

@pytest.mark.asyncio
async def test_handle_message_with_tool() -> None:
    """Test handling a message with a tool call."""
    # Create a handler with mocked dependencies
    handler = ResponseHandler()
    
    # Create test message objects
    user_message = Mock()
    user_message.id = "user-message-id"
    
    assistant_message = Mock()
    assistant_message.id = "assistant-message-id"

    # Mock the methods we don't want to test here
    store_message_mock: AsyncMock = AsyncMock(side_effect=[user_message, assistant_message])
    get_history_mock: AsyncMock = AsyncMock(return_value=[])
    get_context_mock: AsyncMock = AsyncMock(return_value=[])
    prepare_messages_mock: AsyncMock = AsyncMock(return_value=[{"role": "user", "content": "Hello, use a tool!"}])
    # We don't need to mock handle_tool_execution for this test
    handle_final_response_mock: AsyncMock = AsyncMock()
    
    with patch.object(handler, '_store_message', new=store_message_mock), \
         patch.object(handler, '_get_conversation_history', new=get_history_mock), \
         patch.object(handler, '_get_cognition_context', new=get_context_mock), \
         patch.object(handler, '_prepare_messages_with_context', new=prepare_messages_mock), \
         patch.object(handler, '_process_llm_conversation', return_value="Final response after tool"), \
         patch.object(handler, '_handle_final_response', new=handle_final_response_mock), \
         patch('app.core.response_handler.llm_adapter'):

        # Call handle_message
        await handler.handle_message(
            user_id="test-user", conversation_id="test-conv", message_content="Hello, use a tool!"
        )

        # Verify _store_message was called for user message
        store_message_mock.assert_called_once_with(
            conversation_id="test-conv", 
            sender_id="test-user", 
            content="Hello, use a tool!", 
            role="user", 
            metadata=None
        )

        # Verify _get_cognition_context was called
        get_context_mock.assert_called_once_with("test-user", "Hello, use a tool!")

        # Verify _prepare_messages_with_context was called
        prepare_messages_mock.assert_called_once_with([], "Hello, use a tool!", [])

        # Verify _handle_final_response was called with the expected response
        handle_final_response_mock.assert_called_once_with(
            "test-conv", "Final response after tool", True, "user-message-id"
        )
