import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.api.output import event_generator
from app.core.event_bus import EventBus


@pytest.mark.asyncio
async def test_event_generator_filters_by_user_id():
    """Test that event_generator correctly subscribes with user_id filter."""
    # Setup
    user_id = "test-user"
    conversation_id = "test-conversation"
    
    # Mock request
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=False)
    
    # Mock event_bus
    mock_event_bus = MagicMock(spec=EventBus)
    mock_queue = asyncio.Queue()
    
    # Return our mock queue when subscribe is called
    mock_event_bus.subscribe.return_value = mock_queue
    
    # Set up mock app.state.event_bus
    mock_request.app.state.event_bus = mock_event_bus
    
    # Start event generator as async task
    event_gen = event_generator(mock_request, user_id, conversation_id)
    
    # Get first event (or timeout)
    # We expect a ping if we don't put anything in the queue
    gen_task = asyncio.create_task(event_gen.__anext__())
    
    # Wait a bit to ensure subscribe was called
    await asyncio.sleep(0.1)
    
    # Verify subscribe was called with correct parameters
    mock_event_bus.subscribe.assert_called_once_with(
        event_type=None,
        conversation_id=conversation_id,
        user_id=user_id
    )
    
    # Simulate event from event bus
    event_data = {
        "type": "test_event",
        "user_id": user_id,
        "conversation_id": conversation_id,
        "data": {"message": "test"}
    }
    await mock_queue.put(event_data)
    
    # Get the event from generator
    event_text = await asyncio.wait_for(gen_task, timeout=1.0)
    
    # Verify the event was formatted correctly and passed through
    expected_format = f"event: test_event\ndata: {json.dumps(event_data)}\n\n"
    assert event_text == expected_format
    
    # Cleanup: force disconnection
    mock_request.is_disconnected.return_value = True
    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_event_generator_user_id_parameter():
    """Test that event_generator correctly passes user_id to subscribe."""
    # Setup
    user_id = "another-test-user"
    
    # Mock request that disconnects immediately to end the loop
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=True)
    
    # Mock event_bus
    mock_event_bus = MagicMock(spec=EventBus)
    mock_queue = asyncio.Queue()
    
    # Return our mock queue when subscribe is called
    mock_event_bus.subscribe.return_value = mock_queue
    
    # Set up mock app.state.event_bus
    mock_request.app.state.event_bus = mock_event_bus
    
    # Create and immediately close event generator (due to disconnected request)
    gen = event_generator(mock_request, user_id)
    try:
        # This will start the generator but immediately end due to disconnected request
        await gen.__anext__()
    except StopAsyncIteration:
        # This is expected since request is disconnected immediately
        pass
    
    # Verify subscribe was called with correct user_id parameter
    mock_event_bus.subscribe.assert_called_once()
    call_args = mock_event_bus.subscribe.call_args[1]  # Get kwargs
    assert call_args.get('user_id') == user_id