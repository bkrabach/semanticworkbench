"""Tests for the Response Handler component."""

import asyncio
from typing import Any, Dict, Protocol, TypeVar, cast
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from app.backend.cognition_client import CognitionClient
from app.backend.memory_client import MemoryClient
from app.core.event_bus import EventBus
from app.core.response_handler import ResponseHandler


@pytest.mark.asyncio
async def test_response_handler_init():
    """Test initializing the response handler with dependencies."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_cognition_client = MagicMock(spec=CognitionClient)

    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
    )

    # Verify handler has correct attributes
    assert handler.event_bus is mock_event_bus
    assert handler.memory_client is mock_memory_client
    assert handler.cognition_client is mock_cognition_client
    assert handler.running is False
    assert handler.input_queue is None
    assert handler.task is None


# Define a protocol for our async mock functions
T = TypeVar("T")


class AsyncMockFunction(Protocol):
    """Protocol for async mock functions with Mock attributes."""

    mock: Mock

    async def __call__(self, *args: Any, **kwargs: Any) -> Any: ...
    def assert_called(self) -> None: ...
    def assert_called_once(self) -> None: ...
    def assert_called_with(self, *args: Any, **kwargs: Any) -> None: ...
    def assert_called_once_with(self, *args: Any, **kwargs: Any) -> None: ...
    def reset_mock(self) -> None: ...


def async_mock() -> AsyncMockFunction:
    """Create an async mock function that works with type checking."""
    mock = Mock()

    async def async_mock_function(*args: Any, **kwargs: Any) -> Any:
        return mock(*args, **kwargs)

    # Copy attributes from the mock to the function
    async_mock_function.mock = mock  # type: ignore
    async_mock_function.assert_called = mock.assert_called  # type: ignore
    async_mock_function.assert_called_once = mock.assert_called_once  # type: ignore
    async_mock_function.assert_called_with = mock.assert_called_with  # type: ignore
    async_mock_function.assert_called_once_with = mock.assert_called_once_with  # type: ignore
    async_mock_function.call_count = mock.call_count  # type: ignore
    async_mock_function.reset_mock = mock.reset_mock  # type: ignore

    return cast(AsyncMockFunction, async_mock_function)


@pytest.mark.asyncio
async def test_response_handler_start_stop():
    """Test starting and stopping the response handler."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_queue = asyncio.Queue()
    mock_event_bus.subscribe.return_value = mock_queue
    
    # Create task mock
    mock_task = MagicMock()
    mock_task.done.return_value = False
    mock_task.cancel = MagicMock()

    # Create methods with our special async_mock to better support type checking
    memory_close_mock = async_mock()
    cognition_close_mock = async_mock()

    # Create the clients with mocked methods
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_memory_client.close = memory_close_mock

    mock_cognition_client = MagicMock(spec=CognitionClient)
    mock_cognition_client.close = cognition_close_mock

    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
    )

    # Mock the asyncio.create_task function
    with patch("asyncio.create_task", return_value=mock_task):
        # Start the handler
        await handler.start()

        # Verify handler is running and task was created
        assert handler.running is True
        assert handler.input_queue is mock_queue
        assert handler.task is mock_task
        mock_event_bus.subscribe.assert_called_once_with(event_type="input")

        # Stop the handler
        await handler.stop()

        # Verify handler is stopped and task was cancelled
        assert handler.running is False
        mock_task.cancel.assert_called_once()
        mock_event_bus.unsubscribe.assert_called_once_with(mock_queue)
        
        # Verify clients were closed
        memory_close_mock.mock.assert_called_once()
        cognition_close_mock.mock.assert_called_once()


@pytest.mark.asyncio
async def test_create_response_handler():
    """Test the create_response_handler factory function."""
    # Mock dependencies
    mock_event_bus = MagicMock(spec=EventBus)
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_cognition_client = MagicMock(spec=CognitionClient)
    mock_response_handler = MagicMock(spec=ResponseHandler)

    # Create mock start method
    start_mock = async_mock()
    mock_response_handler.start = start_mock

    # Set up patches for factory function dependencies
    with (
        patch("app.core.response_handler.MemoryClient", return_value=mock_memory_client),
        patch("app.core.response_handler.CognitionClient", return_value=mock_cognition_client),
        patch("app.core.response_handler.ResponseHandler", return_value=mock_response_handler),
    ):
        # Call the factory function
        from app.core.response_handler import create_response_handler

        handler = await create_response_handler(
            event_bus=mock_event_bus, memory_url="http://test-memory", cognition_url="http://test-cognition"
        )

        # Verify mock response handler was returned
        assert handler is mock_response_handler

        # Check start method was called
        start_mock.mock.assert_called_once()


@pytest.mark.asyncio
async def test_handle_input_event():
    """Test handling an input event."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_event_bus.publish = AsyncMock()
    
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_memory_client.ensure_connected = AsyncMock()
    mock_memory_client.store_message = AsyncMock()
    
    mock_cognition_client = MagicMock(spec=CognitionClient)
    mock_cognition_client.evaluate_context = AsyncMock(return_value="Test response")
    
    # Create test event
    test_event: Dict[str, Any] = {
        "user_id": "test-user",
        "conversation_id": "test-conv",
        "content": "Hello, world!",
        "metadata": {"test": "metadata"}
    }
    
    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, 
        memory_client=mock_memory_client, 
        cognition_client=mock_cognition_client
    )
    
    # Handle the event
    await handler.handle_input_event(test_event)
    
    # Verify memory client interactions
    mock_memory_client.ensure_connected.assert_called_once()
    assert mock_memory_client.store_message.call_count == 2  # Once for user, once for assistant
    
    # Verify first store_message call (user message)
    user_call = mock_memory_client.store_message.call_args_list[0]
    assert user_call.kwargs["user_id"] == "test-user"
    assert user_call.kwargs["conversation_id"] == "test-conv"
    assert user_call.kwargs["content"] == "Hello, world!"
    assert user_call.kwargs["role"] == "user"
    assert user_call.kwargs["metadata"] == {"test": "metadata"}
    
    # Verify cognition client was called
    mock_cognition_client.evaluate_context.assert_called_once_with(
        user_id="test-user",
        conversation_id="test-conv",
        message="Hello, world!"
    )
    
    # Verify second store_message call (assistant response)
    assistant_call = mock_memory_client.store_message.call_args_list[1]
    assert assistant_call.kwargs["user_id"] == "test-user"
    assert assistant_call.kwargs["conversation_id"] == "test-conv"
    assert assistant_call.kwargs["content"] == "Test response"
    assert assistant_call.kwargs["role"] == "assistant"
    
    # Verify event was published
    mock_event_bus.publish.assert_called_once()
    call_args = mock_event_bus.publish.call_args
    assert call_args[0][0] == "output"  # First arg is event type
    assert call_args[0][1]["user_id"] == "test-user"
    assert call_args[0][1]["conversation_id"] == "test-conv"
    assert call_args[0][1]["content"] == "Test response"
    assert call_args[0][1]["role"] == "assistant"
