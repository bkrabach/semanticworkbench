"""
Tests for the response handler module.
"""

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.core.exceptions import ToolExecutionException
from app.core.response_handler import ResponseHandler, register_tool


# Sample test tool for both basic and enhanced tests
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
async def test_send_event(response_handler: ResponseHandler) -> None:
    """Test sending an event through the SSE queue."""
    # Create a test queue
    test_queue: asyncio.Queue[str] = asyncio.Queue()
    # Create test conversation ID
    conversation_id = "test-conversation"
    # Create test message ID
    message_id = "test-message-id"

    # Mock get_output_queue to return our test queue
    with patch("app.core.response_handler.get_output_queue", return_value=test_queue):
        # Test sender info
        sender = {"id": "test-sender", "name": "Test Sender", "role": "test"}

        # Send an event
        await response_handler._send_event(
            conversation_id=conversation_id,
            event_type="test_event",
            message_id=message_id,
            content="Test content",
            sender=sender,
            metadata={"test_key": "test_value"},
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
async def test_stream_response(response_handler: ResponseHandler) -> None:
    """Test streaming a response to a queue."""
    # Create a test queue
    test_queue: asyncio.Queue[str] = asyncio.Queue()
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

    with (
        patch("app.core.response_handler.get_output_queue", return_value=test_queue),
        patch("app.core.response_handler.UnitOfWork.for_transaction", return_value=mock_uow_context),
    ):
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
        reconstructed = ""
        for chunk in chunk_events:
            reconstructed += chunk["data"]["content"]

        # Verify the reconstructed message matches the original
        assert reconstructed == message


@pytest.mark.asyncio
async def test_handle_tool_execution(response_handler: ResponseHandler) -> None:
    """Test handling tool execution with events."""
    # Create a test queue
    test_queue: asyncio.Queue[str] = asyncio.Queue()
    # Create test conversation ID
    conversation_id = "test-conversation"
    # Create test tool details
    tool_name = "test_tool"
    tool_args = {"param1": "test"}
    user_id = "test-user"

    # Mock the dependencies
    with (
        patch("app.core.response_handler.get_output_queue", return_value=test_queue),
        patch.object(response_handler, "_execute_tool", return_value="Tool result"),
    ):
        # Execute the tool
        result = await response_handler._handle_tool_execution(
            conversation_id=conversation_id, tool_name=tool_name, tool_args=tool_args, user_id=user_id
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
async def test_handle_message_mock_streaming() -> None:
    """Test handling a message with mocked dependencies and streaming enabled."""
    # Create a handler with mocked dependencies
    handler = ResponseHandler()

    # Mock the methods we don't want to test here
    user_message = Mock()
    user_message.id = "user-message-id"

    store_message_mock = AsyncMock(return_value=user_message)
    get_history_mock = AsyncMock(return_value=[])
    get_context_mock = AsyncMock(return_value=[])
    prepare_messages_mock = AsyncMock(return_value=[{"role": "user", "content": "Hello, world!"}])
    process_llm_mock = AsyncMock(return_value="This is a mock response")
    handle_final_response_mock = AsyncMock()

    with (
        patch.object(handler, "_store_message", new=store_message_mock),
        patch.object(handler, "_get_conversation_history", new=get_history_mock),
        patch.object(handler, "_get_cognition_context", new=get_context_mock),
        patch.object(handler, "_prepare_messages_with_context", new=prepare_messages_mock),
        patch.object(handler, "_process_llm_conversation", new=process_llm_mock),
        patch.object(handler, "_handle_final_response", new=handle_final_response_mock),
        patch("app.core.response_handler.llm_adapter"),
    ):
        # Call handle_message with streaming enabled (default)
        await handler.handle_message(user_id="test-user", conversation_id="test-conv", message_content="Hello, world!")

        # Verify _store_message was called for user message
        store_message_mock.assert_called_once_with(
            conversation_id="test-conv", sender_id="test-user", content="Hello, world!", role="user", metadata=None
        )

        # Verify _get_cognition_context was called
        get_context_mock.assert_called_once_with("test-user", "Hello, world!")

        # Verify _prepare_messages_with_context was called
        prepare_messages_mock.assert_called_once_with([], "Hello, world!", [])

        # Verify _process_llm_conversation was called
        process_llm_mock.assert_called_once_with(
            "test-user", "test-conv", [{"role": "user", "content": "Hello, world!"}], "user-message-id"
        )

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
    user_message = Mock()
    user_message.id = "user-message-id"

    store_message_mock = AsyncMock(return_value=user_message)
    get_history_mock = AsyncMock(return_value=[])
    get_context_mock = AsyncMock(return_value=[])
    prepare_messages_mock = AsyncMock(return_value=[{"role": "user", "content": "Hello, world!"}])
    process_llm_mock = AsyncMock(return_value="This is a mock response")
    handle_final_response_mock = AsyncMock()

    with (
        patch.object(handler, "_store_message", new=store_message_mock),
        patch.object(handler, "_get_conversation_history", new=get_history_mock),
        patch.object(handler, "_get_cognition_context", new=get_context_mock),
        patch.object(handler, "_prepare_messages_with_context", new=prepare_messages_mock),
        patch.object(handler, "_process_llm_conversation", new=process_llm_mock),
        patch.object(handler, "_handle_final_response", new=handle_final_response_mock),
        patch("app.core.response_handler.llm_adapter"),
    ):
        # Call handle_message with streaming disabled
        await handler.handle_message(
            user_id="test-user", conversation_id="test-conv", message_content="Hello, world!", streaming=False
        )

        # Verify _handle_final_response was called with streaming=False
        handle_final_response_mock.assert_called_once_with(
            "test-conv", "This is a mock response", False, "user-message-id"
        )


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
    store_message_mock = AsyncMock(side_effect=[user_message, assistant_message])
    get_history_mock = AsyncMock(return_value=[])
    get_context_mock = AsyncMock(return_value=[])
    prepare_messages_mock = AsyncMock(return_value=[{"role": "user", "content": "Hello, use a tool!"}])
    # We don't need to mock handle_tool_execution for this test
    handle_final_response_mock = AsyncMock()

    with (
        patch.object(handler, "_store_message", new=store_message_mock),
        patch.object(handler, "_get_conversation_history", new=get_history_mock),
        patch.object(handler, "_get_cognition_context", new=get_context_mock),
        patch.object(handler, "_prepare_messages_with_context", new=prepare_messages_mock),
        patch.object(handler, "_process_llm_conversation", return_value="Final response after tool"),
        patch.object(handler, "_handle_final_response", new=handle_final_response_mock),
        patch("app.core.response_handler.llm_adapter"),
    ):
        # Call handle_message
        await handler.handle_message(
            user_id="test-user", conversation_id="test-conv", message_content="Hello, use a tool!"
        )

        # Verify _handle_final_response was called with the expected response
        handle_final_response_mock.assert_called_once_with(
            "test-conv", "Final response after tool", True, "user-message-id"
        )


# Enhanced tests for additional methods and edge cases


@pytest.mark.asyncio
async def test_get_conversation_history_empty() -> None:
    """Test getting an empty conversation history."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Mock UnitOfWork and message repository
    mock_message_repo = AsyncMock()
    mock_message_repo.list_by_conversation = AsyncMock(return_value=[])

    mock_uow = Mock()
    mock_uow.repositories = Mock()
    mock_uow.repositories.get_message_repository.return_value = mock_message_repo

    mock_uow_context = AsyncMock()
    mock_uow_context.__aenter__.return_value = mock_uow

    # Call the method with mocked dependencies
    with patch("app.core.response_handler.UnitOfWork.for_transaction", return_value=mock_uow_context):
        result = await handler._get_conversation_history("test-conversation")

    # Verify the result
    assert result == []
    mock_message_repo.list_by_conversation.assert_called_once_with("test-conversation", limit=10)


@pytest.mark.asyncio
async def test_get_conversation_history_with_messages() -> None:
    """Test getting conversation history with messages."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Create mock messages
    mock_message1 = Mock()
    mock_message1.content = "Hello"
    mock_message1.metadata = {"role": "user"}

    mock_message2 = Mock()
    mock_message2.content = "Hi there!"
    mock_message2.metadata = {"role": "assistant"}

    # Mock UnitOfWork and message repository
    mock_message_repo = AsyncMock()
    mock_message_repo.list_by_conversation = AsyncMock(return_value=[mock_message1, mock_message2])

    mock_uow = Mock()
    mock_uow.repositories = Mock()
    mock_uow.repositories.get_message_repository.return_value = mock_message_repo

    mock_uow_context = AsyncMock()
    mock_uow_context.__aenter__.return_value = mock_uow

    # Call the method with mocked dependencies
    with patch("app.core.response_handler.UnitOfWork.for_transaction", return_value=mock_uow_context):
        result = await handler._get_conversation_history("test-conversation")

    # Verify the result
    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "Hello"
    assert result[1]["role"] == "assistant"
    assert result[1]["content"] == "Hi there!"


@pytest.mark.asyncio
async def test_get_cognition_context_empty() -> None:
    """Test getting empty cognition context when no tools are available."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Mock the tool registry to return None
    with (
        patch("app.core.response_handler.tool_registry.get", return_value=None),
        patch("app.core.response_handler.get_mcp_client", side_effect=Exception("MCP not available")),
    ):
        result = await handler._get_cognition_context("test-user", "Hello")

    # Verify the result
    assert result == []


@pytest.mark.asyncio
async def test_get_cognition_context_with_local_tool() -> None:
    """Test getting cognition context with a local tool."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Mock context result
    mock_context = {"context": [{"content": "Test context"}]}
    mock_tool = AsyncMock(return_value=mock_context)

    # Mock the tool registry to return our mock tool
    with patch("app.core.response_handler.tool_registry.get", return_value=mock_tool):
        result = await handler._get_cognition_context("test-user", "Hello")

    # Verify the result
    assert len(result) == 1
    assert result[0]["content"] == "Test context"

    # Verify tool was called with correct arguments
    mock_tool.assert_called_once_with(user_id="test-user", query="Hello", limit=5)


@pytest.mark.asyncio
async def test_get_cognition_context_with_mcp_client() -> None:
    """Test getting cognition context with MCP client."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Mock context result
    mock_context = {"context": [{"content": "Test MCP context"}]}

    # Mock MCP client
    mock_mcp_client = AsyncMock()
    mock_mcp_client.call_tool = AsyncMock(return_value=mock_context)

    # Mock the dependencies
    with (
        patch("app.core.response_handler.tool_registry.get", return_value=None),
        patch("app.core.response_handler.get_mcp_client", return_value=mock_mcp_client),
    ):
        result = await handler._get_cognition_context("test-user", "Hello")

    # Verify the result
    assert len(result) == 1
    assert result[0]["content"] == "Test MCP context"

    # Verify MCP client was called with correct arguments
    mock_mcp_client.call_tool.assert_called_once_with(
        service_name="cognition",
        tool_name="get_context",
        input_data={"user_id": "test-user", "query": "Hello", "limit": 5},
    )


@pytest.mark.asyncio
async def test_prepare_messages_with_context_simple_message() -> None:
    """Test preparing messages with just a simple message."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Set a custom system prompt for testing
    handler.system_prompt = ""

    # Prepare test data
    history: List[Dict[str, str]] = []
    message_content = "Hello, world!"
    context_items: List[Dict[str, Any]] = []

    # Call the method
    result = await handler._prepare_messages_with_context(history, message_content, context_items)

    # Verify the result
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "Hello, world!"


@pytest.mark.asyncio
async def test_prepare_messages_with_context_with_system_prompt() -> None:
    """Test preparing messages with a system prompt."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Set a custom system prompt for testing
    handler.system_prompt = "You are a helpful assistant."

    # Prepare test data
    history: List[Dict[str, str]] = []
    message_content = "Hello, world!"
    context_items: List[Dict[str, Any]] = []

    # Call the method
    result = await handler._prepare_messages_with_context(history, message_content, context_items)

    # Verify the result
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[0]["content"] == "You are a helpful assistant."
    assert result[1]["role"] == "user"
    assert result[1]["content"] == "Hello, world!"


@pytest.mark.asyncio
async def test_prepare_messages_with_context_with_context_items() -> None:
    """Test preparing messages with context items but no system prompt."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Set an empty system prompt for testing
    handler.system_prompt = ""

    # Prepare test data
    history: List[Dict[str, str]] = []
    message_content = "Tell me about apples."
    context_items: List[Dict[str, Any]] = [{"content": "Apples are fruits."}, {"content": "Apples are red or green."}]

    # Call the method
    result = await handler._prepare_messages_with_context(history, message_content, context_items)

    # Verify the result
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert "Apples are fruits" in result[0]["content"]
    assert "Apples are red or green" in result[0]["content"]
    assert result[1]["role"] == "user"
    assert result[1]["content"] == "Tell me about apples."


@pytest.mark.asyncio
async def test_process_llm_conversation_single_response() -> None:
    """Test processing an LLM conversation with a single response (no tools)."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Mock LLM response
    mock_llm_result = {"content": "This is a test response"}

    # Mock the dependencies
    with patch("app.core.response_handler.llm_adapter.generate", AsyncMock(return_value=mock_llm_result)):
        result = await handler._process_llm_conversation(
            user_id="test-user",
            conversation_id="test-conversation",
            messages=[{"role": "user", "content": "Hello"}],
            user_message_id="test-message-id",
        )

    # Verify the result
    assert result == "This is a test response"


@pytest.mark.asyncio
async def test_process_llm_conversation_with_tool() -> None:
    """Test processing an LLM conversation with tool execution."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Mock LLM responses - first requesting a tool, then giving final answer
    mock_llm_results = [{"tool": "test_tool", "input": {"param": "value"}}, {"content": "Final answer after tool"}]

    # Mock llm_adapter.generate to return different results on each call
    generate_mock = AsyncMock(side_effect=mock_llm_results)

    # Mock handle_tool_execution to return a tool result
    tool_execution_mock = AsyncMock(return_value="Tool result")

    # Mock the dependencies
    with (
        patch("app.core.response_handler.llm_adapter.generate", generate_mock),
        patch.object(handler, "_handle_tool_execution", tool_execution_mock),
    ):
        result = await handler._process_llm_conversation(
            user_id="test-user",
            conversation_id="test-conversation",
            messages=[{"role": "user", "content": "Hello, use a tool"}],
            user_message_id="test-message-id",
        )

    # Verify the result
    assert result == "Final answer after tool"

    # Verify tool execution was called
    tool_execution_mock.assert_called_once()

    # Verify generate was called twice with the right messages
    assert generate_mock.call_count == 2


@pytest.mark.asyncio
async def test_process_llm_conversation_with_failed_tool() -> None:
    """Test processing an LLM conversation with a failed tool execution."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Mock LLM response requesting a tool
    mock_llm_result = {"tool": "test_tool", "input": {"param": "value"}}

    # Mock the dependencies
    with (
        patch("app.core.response_handler.llm_adapter.generate", AsyncMock(return_value=mock_llm_result)),
        patch.object(handler, "_handle_tool_execution", AsyncMock(return_value=None)),
    ):
        result = await handler._process_llm_conversation(
            user_id="test-user",
            conversation_id="test-conversation",
            messages=[{"role": "user", "content": "Hello, use a tool"}],
            user_message_id="test-message-id",
        )

    # Verify that we get an apologetic response
    assert result is not None
    assert "I apologize" in result
    assert "test_tool" in result


@pytest.mark.asyncio
async def test_handle_error() -> None:
    """Test handling an error during processing."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Test data
    conversation_id = "test-conversation"
    error = Exception("Test error")
    test_queue: asyncio.Queue[str] = asyncio.Queue()

    # Mock the queue and event_bus
    with (
        patch("app.core.response_handler.get_output_queue", return_value=test_queue),
        patch("app.core.response_handler.event_bus.publish", new_callable=AsyncMock) as mock_publish,
    ):
        # Call the method
        await handler._handle_error(conversation_id, error)

        # Check that error event was sent to output queue
        event_json = await asyncio.wait_for(test_queue.get(), timeout=1.0)
        event = json.loads(event_json)

        # Verify event structure
        assert event["message_type"] == "error"
        assert "Test error" in event["data"]["content"]
        assert event["data"]["sender"]["role"] == "system"

        # Verify event bus was called
        mock_publish.assert_called_once()
        event_bus_event = mock_publish.call_args[0][0]
        assert event_bus_event["message_type"] == "error"
        assert "Test error" in event_bus_event["data"]["content"]


@pytest.mark.asyncio
async def test_handle_message_with_error() -> None:
    """Test handling a message when an error occurs."""
    # Create a ResponseHandler instance
    handler = ResponseHandler()

    # Mock data
    user_id = "test-user"
    conversation_id = "test-conversation"
    message_content = "Test message"

    # Mock to raise an exception
    with (
        patch.object(handler, "_store_message", side_effect=Exception("Test error")),
        patch.object(handler, "_handle_error", new_callable=AsyncMock) as mock_handle_error,
    ):
        # Call the method
        await handler.handle_message(user_id=user_id, conversation_id=conversation_id, message_content=message_content)

        # Verify error was handled
        mock_handle_error.assert_called_once()
        # Check the exception passed to _handle_error
        exception = mock_handle_error.call_args[0][1]
        assert str(exception) == "Test error"
