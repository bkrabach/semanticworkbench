import asyncio

import pytest
from app.core.event_bus import EventBus, EventData


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe() -> None:
    """Test event bus publish and subscribe functionality."""
    bus = EventBus()
    queue: asyncio.Queue[EventData] = asyncio.Queue()

    # Subscribe to events
    queue = bus.subscribe()

    # Test event
    test_event = EventData({"type": "test", "data": {"message": "hello"}, "user_id": "test-user"})

    # Publish event
    await bus.publish_async("test", test_event)

    # Get event from queue
    received_event = await asyncio.wait_for(queue.get(), timeout=1.0)

    # Verify event
    assert received_event == test_event

    # Unsubscribe
    bus.unsubscribe(queue)

    # Publish another event
    test_event2 = EventData({"type": "test2", "data": {"message": "world"}, "user_id": "test-user"})
    await bus.publish_async("test2", test_event2)

    # Verify queue is empty (no more events after unsubscribe)
    assert queue.empty()
