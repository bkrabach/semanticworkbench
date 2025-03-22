import asyncio

import pytest
from app.core.event_bus import EventBus


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    """Test event bus publish and subscribe functionality."""
    bus = EventBus()
    queue = asyncio.Queue()

    # Subscribe to events
    bus.subscribe(queue)

    # Test event
    test_event = {"type": "test", "data": {"message": "hello"}, "user_id": "test-user"}

    # Publish event
    await bus.publish(test_event)

    # Get event from queue
    received_event = await asyncio.wait_for(queue.get(), timeout=1.0)

    # Verify event
    assert received_event == test_event

    # Unsubscribe
    bus.unsubscribe(queue)

    # Publish another event
    await bus.publish({"type": "test2", "data": {"message": "world"}, "user_id": "test-user"})

    # Verify queue is empty (no more events after unsubscribe)
    assert queue.empty()
