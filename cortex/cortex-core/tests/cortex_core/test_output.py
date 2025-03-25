import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.api.output import event_generator
from app.core.event_bus import EventBus
from app.main import app
from app.utils.auth import create_access_token


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


@pytest.mark.asyncio
async def test_event_generator_timeout_sends_keepalive():
    """Test that event_generator sends keep-alive ping on timeout."""
    # Setup
    user_id = "test-user"
    
    # Mock request
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock()
    # First check says connected, second check will say disconnected to end the loop
    mock_request.is_disconnected.side_effect = [False, True]
    
    # Mock event_bus
    mock_event_bus = MagicMock(spec=EventBus)
    mock_queue = asyncio.Queue()
    # We'll intentionally not put anything in the queue to trigger timeout
    mock_event_bus.subscribe.return_value = mock_queue
    mock_request.app.state.event_bus = mock_event_bus
    
    # Start event generator
    event_gen = event_generator(mock_request, user_id)
    
    # First yield should be a ping (keep-alive) after timeout
    event_text = await event_gen.__anext__()
    assert event_text == ": ping\n\n"
    
    # Generator should stop on next iteration since is_disconnected will return True
    with pytest.raises(StopAsyncIteration):
        await event_gen.__anext__()


@pytest.mark.asyncio
async def test_event_generator_handles_multiple_events():
    """Test that event_generator correctly handles multiple events."""
    # Setup
    user_id = "test-user"
    conversation_id = "test-conversation"
    
    # Mock request
    mock_request = MagicMock()
    # Stay connected for 3 iterations then disconnect
    mock_request.is_disconnected = AsyncMock()
    mock_request.is_disconnected.side_effect = [False, False, False, True]
    
    # Mock event_bus with queue
    mock_event_bus = MagicMock(spec=EventBus)
    mock_queue = asyncio.Queue()
    mock_event_bus.subscribe.return_value = mock_queue
    mock_request.app.state.event_bus = mock_event_bus
    
    # Start event generator
    event_gen = event_generator(mock_request, user_id, conversation_id)
    
    # Put multiple events in the queue
    events = [
        {
            "type": "output",
            "user_id": user_id,
            "conversation_id": conversation_id,
            "content": "Message 1"
        },
        {
            "type": "output",
            "user_id": user_id,
            "conversation_id": conversation_id,
            "content": "Message 2"
        },
        {
            "type": "output",
            "user_id": user_id,
            "conversation_id": conversation_id,
            "content": "Message 3"
        }
    ]
    
    for event in events:
        await mock_queue.put(event)
    
    # Collect the events from the generator
    received_events = []
    try:
        for _ in range(len(events)):
            event_text = await event_gen.__anext__()
            received_events.append(event_text)
    except StopAsyncIteration:
        pass
    
    # Verify we got all the events
    assert len(received_events) == len(events)
    
    # Verify each event was formatted correctly
    for i, event in enumerate(events):
        expected_format = f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
        assert received_events[i] == expected_format
    
    # We can't check call_count for a real asyncio.Queue, so we'll skip this assertion


def test_stream_output_endpoint_authentication():
    """Test that the stream output endpoint requires authentication."""
    # No auth header
    client = TestClient(app)
    response = client.get("/output/stream")
    assert response.status_code == 401

    # Invalid token
    client = TestClient(app)
    response = client.get(
        "/output/stream", 
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


def test_stream_output_endpoint_initiates_event_stream():
    """Test that the stream output endpoint starts an SSE event stream with authentication."""
    # Create a patch for event_generator that returns a simple generator
    async def mock_event_generator(*args, **kwargs):
        yield "data: test\n\n"
        
    # Create a valid token
    token_data = {"sub": "test-user", "id": "test-user", "name": "Test User"}
    token = create_access_token(token_data)
    
    with patch("app.api.output.event_generator", return_value=mock_event_generator()):
        # Make the request with a valid token
        with TestClient(app) as client:
            response = client.get("/output/stream", headers={"Authorization": f"Bearer {token}"})
            
            # Verify the response code
            assert response.status_code == 200
            # Verify the content type (FastAPI adds charset=utf-8)
            assert response.headers["content-type"].startswith("text/event-stream")
            # Verify streaming response headers are set
            assert response.headers.get("cache-control") == "no-cache"
            assert response.headers.get("connection") == "keep-alive"