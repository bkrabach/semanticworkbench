"""Tests for the Response Handler component."""

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.backend.cognition_client import CognitionClient
from app.backend.memory_client import MemoryClient
from app.core.event_bus import EventBus
from app.core.response_handler import ResponseHandler, get_pydantic_ai_agent

# Import the async_mock utility from conftest.py
from tests.cortex_core.conftest import async_mock


@pytest.mark.asyncio
async def test_response_handler_init(mock_event_bus, mock_memory_client, mock_cognition_client):
    """Test initializing the response handler with dependencies."""
    # Create handler using fixture mocks
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


@pytest.mark.asyncio
async def test_response_handler_start_stop(mock_event_bus):
    """Test starting and stopping the response handler."""
    # Set up mock queue
    mock_queue = asyncio.Queue()
    mock_event_bus.subscribe.return_value = mock_queue

    # Create task mock
    mock_task = MagicMock()
    mock_task.done.return_value = False
    mock_task.cancel = MagicMock()

    # Create methods with our special async_mock to better support type checking
    memory_close_mock = async_mock()
    cognition_close_mock = async_mock()
    
    # Create a process_events mock that returns our task directly
    async def mock_process_events():
        return mock_task

    # Create the clients with mocked methods
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_memory_client.close = memory_close_mock

    mock_cognition_client = MagicMock(spec=CognitionClient)
    mock_cognition_client.close = cognition_close_mock

    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
    )
    
    # Replace the process_events method with our mock version
    handler.process_events = mock_process_events

    # Start the handler
    await handler.start()

    # Verify handler is running and task was created
    assert handler.running is True
    assert handler.input_queue is mock_queue
    assert handler.task is mock_task
    mock_event_bus.subscribe.assert_called_once_with(event_type="input")
    
    # Test case where handler is already running
    await handler.start()
    # Check that subscribe wasn't called again
    assert mock_event_bus.subscribe.call_count == 1

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
async def test_create_response_handler(mock_event_bus):
    """Test the create_response_handler factory function."""
    # Set up mock objects
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_cognition_client = MagicMock(spec=CognitionClient)
    mock_response_handler = MagicMock(spec=ResponseHandler)

    # Use async_mock from conftest.py for the start and process_events methods
    start_mock = async_mock()
    process_events_mock = async_mock()
    process_events_mock.mock.return_value = asyncio.create_task(asyncio.sleep(0))
    
    mock_response_handler.start = start_mock
    mock_response_handler.process_events = process_events_mock

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
        "metadata": {"test": "metadata"},
    }

    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
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
        user_id="test-user", conversation_id="test-conv", message="Hello, world!"
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


@pytest.mark.asyncio
async def test_handle_input_event_missing_fields():
    """Test handling an input event with missing required fields."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_event_bus.publish = AsyncMock()

    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_memory_client.ensure_connected = AsyncMock()
    mock_memory_client.store_message = AsyncMock()

    mock_cognition_client = MagicMock(spec=CognitionClient)
    mock_cognition_client.evaluate_context = AsyncMock(return_value="Test response")

    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
    )

    # Test events with missing fields
    incomplete_events = [
        {},  # Empty event
        {"user_id": "test-user"},  # Missing conversation_id and content
        {"conversation_id": "test-conv"},  # Missing user_id and content
        {"content": "Hello"},  # Missing user_id and conversation_id
        {"user_id": "test-user", "conversation_id": "test-conv"},  # Missing content
    ]

    # Process each incomplete event
    for event in incomplete_events:
        # Handle the event
        await handler.handle_input_event(event)

        # Verify no methods were called
        mock_memory_client.ensure_connected.assert_not_called()
        mock_memory_client.store_message.assert_not_called()
        mock_cognition_client.evaluate_context.assert_not_called()
        mock_event_bus.publish.assert_not_called()

        # Reset mocks for the next event
        mock_memory_client.ensure_connected.reset_mock()
        mock_memory_client.store_message.reset_mock()
        mock_cognition_client.evaluate_context.reset_mock()
        mock_event_bus.publish.reset_mock()


@pytest.mark.asyncio
async def test_handle_input_event_memory_exception():
    """Test handling an exception during memory storage."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_event_bus.publish = AsyncMock()

    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_memory_client.ensure_connected = AsyncMock()
    mock_memory_client.store_message = AsyncMock(side_effect=ConnectionError("Memory service unavailable"))

    mock_cognition_client = MagicMock(spec=CognitionClient)
    mock_cognition_client.evaluate_context = AsyncMock(return_value="Test response")

    # Create test event
    test_event: Dict[str, Any] = {"user_id": "test-user", "conversation_id": "test-conv", "content": "Hello, world!"}

    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
    )

    # Handle the event (should catch the exception)
    await handler.handle_input_event(test_event)

    # Verify memory client was attempted
    mock_memory_client.ensure_connected.assert_called_once()
    mock_memory_client.store_message.assert_called_once()

    # Verify cognition client was not called (due to memory error)
    mock_cognition_client.evaluate_context.assert_not_called()

    # Verify error event was published
    mock_event_bus.publish.assert_called_once()
    call_args = mock_event_bus.publish.call_args
    assert call_args[0][0] == "error"  # First arg is event type
    assert call_args[0][1]["user_id"] == "test-user"
    assert call_args[0][1]["conversation_id"] == "test-conv"
    assert "Error processing your message" in call_args[0][1]["content"]
    assert "Memory service unavailable" in call_args[0][1]["content"]
    assert call_args[0][1]["role"] == "system"


@pytest.mark.asyncio
async def test_handle_input_event_cognition_exception():
    """Test handling an exception during cognition service call."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_event_bus.publish = AsyncMock()

    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_memory_client.ensure_connected = AsyncMock()
    mock_memory_client.store_message = AsyncMock()

    mock_cognition_client = MagicMock(spec=CognitionClient)
    mock_cognition_client.evaluate_context = AsyncMock(side_effect=RuntimeError("Cognition service error"))

    # Create test event
    test_event: Dict[str, Any] = {"user_id": "test-user", "conversation_id": "test-conv", "content": "Hello, world!"}

    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
    )

    # Handle the event (should catch the exception)
    await handler.handle_input_event(test_event)

    # Verify memory client was called once (for user message)
    mock_memory_client.ensure_connected.assert_called_once()
    assert mock_memory_client.store_message.call_count == 1

    # Verify cognition client was attempted
    mock_cognition_client.evaluate_context.assert_called_once()

    # Verify error event was published
    mock_event_bus.publish.assert_called_once()
    call_args = mock_event_bus.publish.call_args
    assert call_args[0][0] == "error"  # First arg is event type
    assert call_args[0][1]["user_id"] == "test-user"
    assert call_args[0][1]["conversation_id"] == "test-conv"
    assert "Error processing your message" in call_args[0][1]["content"]
    assert "Cognition service error" in call_args[0][1]["content"]
    assert call_args[0][1]["role"] == "system"


@pytest.mark.asyncio
async def test_process_events_cancelled():
    """Test that process_events handles cancellation properly."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_queue = MagicMock(spec=asyncio.Queue)
    mock_event_bus.subscribe.return_value = mock_queue

    # Make queue.get raise CancelledError to simulate task cancellation
    mock_queue.get = AsyncMock(side_effect=asyncio.CancelledError())

    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_cognition_client = MagicMock(spec=CognitionClient)

    # Create a test task
    async def mock_process_task():
        try:
            await mock_queue.get()  # This will raise CancelledError
        except asyncio.CancelledError:
            # Just let it propagate to test cancellation handling
            raise
            
    mock_task = asyncio.create_task(mock_process_task())
    
    # Create a mock process_events that returns our task
    async def mock_process_events():
        return mock_task
        
    # Create handler with the mocked process_events
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
    )
    handler.process_events = mock_process_events
    handler.handle_input_event = AsyncMock()  # Add a mock to check it's not called

    # Start the handler
    await handler.start()

    # Verify handler is running and task was created
    assert handler.running is True
    assert handler.task is mock_task

    # Give task a chance to run
    await asyncio.sleep(0.1)
    
    # Stop the handler
    await handler.stop()

    # Verify queue.get was called
    mock_queue.get.assert_called()
    
    # Verify task was cancelled
    assert handler.running is False

    # No other methods should have been called due to cancellation
    mock_queue.task_done.assert_not_called()
    handler.handle_input_event.assert_not_called()
    
    # Test the case where task is already done
    # Create handler again
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
    )
    
    # Create a done task mock
    done_mock_task = MagicMock()
    done_mock_task.done.return_value = True
    done_mock_task.cancel = MagicMock()
    
    handler.task = done_mock_task
    handler.input_queue = mock_queue
    handler.running = True
    
    # Stop the handler
    await handler.stop()
    
    # Task cancel should not be called since task was already done
    done_mock_task.cancel.assert_not_called()


@pytest.mark.asyncio
async def test_process_events_timeout():
    """Test that process_events handles Queue.get timeout gracefully."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_queue = MagicMock(spec=asyncio.Queue)
    mock_event_bus.subscribe.return_value = mock_queue

    # Make queue.get raise TimeoutError to simulate timeout
    mock_queue.get = AsyncMock(side_effect=asyncio.TimeoutError())

    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_cognition_client = MagicMock(spec=CognitionClient)

    # Create handler and mock handle_input_event
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
    )
    handler.handle_input_event = AsyncMock()

    # Start the handler
    await handler.start()

    # Let the process_events task run
    # Wait a short time to ensure the task has a chance to execute
    await asyncio.sleep(0.1)

    # Stop the handler
    await handler.stop()

    # Verify queue.get was called
    mock_queue.get.assert_called()

    # handle_input_event should not be called since queue.get timed out
    handler.handle_input_event.assert_not_called()


@pytest.mark.asyncio
async def test_process_events_input_queue_not_initialized():
    """Test that process_events handles the case where input_queue is not initialized."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_cognition_client = MagicMock(spec=CognitionClient)

    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, memory_client=mock_memory_client, cognition_client=mock_cognition_client
    )
    
    # Call process_events directly with no input queue set
    task = await handler.process_events()
    
    # Let the task run for a brief moment
    await asyncio.sleep(0.1)
    
    # Cancel the task to avoid warnings about unawaited tasks
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # The task should have been created but returned immediately due to no queue
    assert task is not None


@pytest.mark.asyncio
async def test_process_events_exception_handling():
    """Test that process_events handles general exceptions gracefully."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_queue = asyncio.Queue()
    mock_event_bus.subscribe.return_value = mock_queue
    
    # Create a handler with a handle_input_event that raises an exception
    handler = ResponseHandler(
        event_bus=mock_event_bus, 
        memory_client=MagicMock(spec=MemoryClient),
        cognition_client=MagicMock(spec=CognitionClient)
    )
    
    # Add a mock to handle_input_event that raises an exception
    handler.handle_input_event = AsyncMock(side_effect=RuntimeError("Test exception"))
    
    # Start the handler
    await handler.start()
    
    # Add a test event to the queue
    await mock_queue.put({"test": "event"})
    
    # Give the task time to process
    await asyncio.sleep(0.2)
    
    # The task should still be running despite the exception
    assert handler.running is True
    assert handler.task is not None  # Verify task is not None
    assert not handler.task.done()  # Then check its done status
    
    # Now add another event to make sure it continues processing
    await mock_queue.put({"test": "event2"})
    
    # Give the task time to process
    await asyncio.sleep(0.2)
    
    # Verify handle_input_event was called twice (both events were processed)
    assert handler.handle_input_event.call_count == 2
    
    # Clean up
    await handler.stop()


@pytest.mark.asyncio
async def test_stop_with_magicmock_task():
    """Test stop method when task is a MagicMock."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_memory_client.close = AsyncMock()
    mock_cognition_client = MagicMock(spec=CognitionClient)
    mock_cognition_client.close = AsyncMock()
    
    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, 
        memory_client=mock_memory_client,
        cognition_client=mock_cognition_client
    )
    
    # Setup with a MagicMock task
    mock_task = MagicMock()
    mock_task.done.return_value = False
    mock_task.cancel = MagicMock()
    
    handler.task = mock_task
    handler.input_queue = asyncio.Queue()
    handler.running = True
    
    # Stop the handler
    await handler.stop()
    
    # Verify task was cancelled
    mock_task.cancel.assert_called_once()
    
    # Verify running was set to False
    assert handler.running is False
    
    # Verify clients were closed
    mock_memory_client.close.assert_called_once()
    mock_cognition_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_pydantic_ai_agent():
    """Test the cached pydantic-ai agent singleton function."""
    # Patch the Agent class
    with patch("app.core.response_handler.Agent") as mock_agent_class:
        # Create a mock agent instance
        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        # First call should create a new agent
        agent1 = get_pydantic_ai_agent()

        # Verify Agent constructor was called
        mock_agent_class.assert_called_once()

        # Second call should return the cached agent
        mock_agent_class.reset_mock()  # Reset the mock to check it's not called again
        agent2 = get_pydantic_ai_agent()

        # Verify Agent constructor was not called again
        mock_agent_class.assert_not_called()

        # Both calls should return the same instance
        assert agent1 is agent2


@pytest.mark.asyncio
async def test_process_events_outer_exception():
    """Test that process_events handles unexpected exceptions in the outer loop."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_queue = MagicMock(spec=asyncio.Queue)
    
    # Create a special mock for asyncio.Queue.get that raises a different exception
    # each time it's called to force execution through different code paths
    call_count = 0
    
    async def queue_get_with_exceptions():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call - raise a ValueError to trigger the outer exception handler
            raise ValueError("Unexpected error")
        elif call_count == 2:
            # Second call - return a normal event
            return {"test": "event"}
        else:
            # Subsequent calls - just wait (for test cleanup)
            await asyncio.sleep(1000)
    
    mock_queue.get = queue_get_with_exceptions
    mock_queue.task_done = MagicMock()
    mock_event_bus.subscribe.return_value = mock_queue
    
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_cognition_client = MagicMock(spec=CognitionClient)
    
    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, 
        memory_client=mock_memory_client,
        cognition_client=mock_cognition_client
    )
    handler.handle_input_event = AsyncMock()
    
    # Start the handler
    await handler.start()
    
    # Give the task time to process both exceptions
    await asyncio.sleep(0.3)
    
    # The handler should still be running despite the outer exception
    assert handler.running is True
    assert handler.task is not None
    assert not handler.task.done()
    
    # Verify handle_input_event was called once (for the second event)
    assert handler.handle_input_event.call_count == 1
    
    # Cleanup
    await handler.stop()


@pytest.mark.asyncio
async def test_stop_with_real_task_cancelled():
    """Test stopping when task is a real Task and CancelledError is raised."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_memory_client = MagicMock(spec=MemoryClient)
    mock_memory_client.close = AsyncMock()
    mock_cognition_client = MagicMock(spec=CognitionClient)
    mock_cognition_client.close = AsyncMock()
    
    # Create a queue that will block forever
    mock_queue = asyncio.Queue()
    mock_event_bus.subscribe.return_value = mock_queue
    
    # Create handler
    handler = ResponseHandler(
        event_bus=mock_event_bus, 
        memory_client=mock_memory_client,
        cognition_client=mock_cognition_client
    )
    
    # Start the handler (this will create a real task)
    await handler.start()
    
    # Verify task is a real asyncio.Task, not a MagicMock
    assert isinstance(handler.task, asyncio.Task)
    assert not handler.task.done()
    
    # Stop the handler - this will cancel the task and it should handle CancelledError
    await handler.stop()
    
    # Verify the handler state
    assert handler.running is False
    assert handler.task.done()  # Task should be done but not raise an unhandled exception
    
    # Verify clients were closed
    mock_memory_client.close.assert_called_once()
    mock_cognition_client.close.assert_called_once()
