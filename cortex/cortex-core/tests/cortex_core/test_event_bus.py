import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from app.core.event_bus import EventBus


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe() -> None:
    """Test event bus publish and subscribe functionality."""
    bus = EventBus()
    queue: asyncio.Queue = asyncio.Queue()

    # Subscribe to events
    queue = bus.subscribe()

    # Test event
    test_event = {"message": "hello", "user_id": "test-user"}

    # Publish event
    await bus.publish("test", test_event)

    # Get event from queue
    received_event = await asyncio.wait_for(queue.get(), timeout=1.0)

    # Verify event - type will be added by the event bus
    assert received_event["message"] == test_event["message"]
    assert received_event["user_id"] == test_event["user_id"]
    assert received_event["type"] == "test"

    # Unsubscribe
    bus.unsubscribe(queue)

    # Publish another event
    test_event2 = {"message": "world", "user_id": "test-user"}
    await bus.publish("test2", test_event2)

    # Verify queue is empty (no more events after unsubscribe)
    assert queue.empty()


@pytest.mark.asyncio
async def test_event_bus_filtered_subscription() -> None:
    """Test event bus with filtered subscriptions."""
    bus = EventBus()
    
    # Subscribe with different filters
    queue_event_type = bus.subscribe(event_type="input")
    queue_conversation = bus.subscribe(conversation_id="conv-123")
    queue_user = bus.subscribe(user_id="user-456")
    queue_all_filters = bus.subscribe(
        event_type="input", 
        conversation_id="conv-123", 
        user_id="user-456"
    )
    queue_no_filters = bus.subscribe()
    
    # Create test events
    matching_event = {
        "message": "hello",
        "conversation_id": "conv-123",
        "user_id": "user-456"
    }
    
    non_matching_event = {
        "message": "world",
        "conversation_id": "conv-789",
        "user_id": "user-789"
    }
    
    # Publish events
    await bus.publish("input", matching_event)
    await bus.publish("output", non_matching_event)
    
    # Check queue with event_type filter
    assert not queue_event_type.empty()
    received = await asyncio.wait_for(queue_event_type.get(), timeout=1.0)
    assert received["type"] == "input"
    assert queue_event_type.empty()  # Only the matching event
    
    # Check queue with conversation_id filter
    assert not queue_conversation.empty()
    received = await asyncio.wait_for(queue_conversation.get(), timeout=1.0)
    assert received["conversation_id"] == "conv-123"
    assert queue_conversation.empty()  # Only the matching event
    
    # Check queue with user_id filter
    assert not queue_user.empty()
    received = await asyncio.wait_for(queue_user.get(), timeout=1.0)
    assert received["user_id"] == "user-456"
    assert queue_user.empty()  # Only the matching event
    
    # Check queue with all filters - should only get the first event
    assert not queue_all_filters.empty()
    received = await asyncio.wait_for(queue_all_filters.get(), timeout=1.0)
    assert received["type"] == "input"
    assert received["conversation_id"] == "conv-123"
    assert received["user_id"] == "user-456"
    assert queue_all_filters.empty()
    
    # Queue with no filters should get both events
    assert not queue_no_filters.empty()
    first = await asyncio.wait_for(queue_no_filters.get(), timeout=1.0)
    assert not queue_no_filters.empty()
    second = await asyncio.wait_for(queue_no_filters.get(), timeout=1.0)
    assert {first["type"], second["type"]} == {"input", "output"}
    assert queue_no_filters.empty()


@pytest.mark.asyncio
async def test_event_bus_error_handling() -> None:
    """Test error handling in the event bus."""
    bus = EventBus()
    
    # Create a queue that will raise an exception when put() is called
    mock_queue = MagicMock()
    mock_queue.put = AsyncMock(side_effect=Exception("Test exception"))
    
    # Create subscriptions with the problematic queue
    bus._subscriptions.append({
        "queue": mock_queue,
        "event_type": None,
        "conversation_id": None,
        "user_id": None
    })
    
    # Normal queue for verification
    normal_queue = bus.subscribe()
    
    # Publish an event - this should handle the exception from the problematic queue
    with patch("app.core.event_bus.logger") as mock_logger:
        test_event = {"data": "test"}
        await bus.publish("test", test_event)
        
        # Verify the exception was logged
        mock_logger.error.assert_called_once()
        assert "Test exception" in mock_logger.error.call_args[0][0]
    
    # Verify the normal queue still got the event
    assert not normal_queue.empty()
    received = await asyncio.wait_for(normal_queue.get(), timeout=1.0)
    assert received["data"] == "test"
    assert received["type"] == "test"
    
    # Verify the problematic subscription was removed
    assert len(bus._subscriptions) == 1
    # Verify normal queue is still in subscriptions
    assert any(sub["queue"] is normal_queue for sub in bus._subscriptions)
    # Verify the problematic queue was removed
    assert not any(sub["queue"] is mock_queue for sub in bus._subscriptions)


@pytest.mark.asyncio
async def test_async_publish_error_handling() -> None:
    """Test error handling in the async publish method."""
    bus = EventBus()
    
    # Create a queue that will raise an exception when put() is called
    mock_queue = MagicMock()
    mock_queue.put = AsyncMock(side_effect=Exception("Async test exception"))
    
    # Create a subscription with the problematic queue
    bus._subscriptions.append({
        "queue": mock_queue,
        "event_type": None,
        "conversation_id": None,
        "user_id": None
    })
    
    # Normal queue for verification
    normal_queue = bus.subscribe()
    
    # Publish an event - this should handle the exception from the problematic queue
    with patch("app.core.event_bus.logger") as mock_logger:
        test_event = {"data": "test"}
        await bus.publish("test", test_event)
        
        # Verify the exception was logged
        mock_logger.error.assert_called_once()
        assert "Async test exception" in mock_logger.error.call_args[0][0]
    
    # Verify the normal queue still got the event
    assert not normal_queue.empty()
    received = await asyncio.wait_for(normal_queue.get(), timeout=1.0)
    assert received["data"] == "test"
    assert received["type"] == "test"
    
    # Verify the problematic subscription was removed
    assert len(bus._subscriptions) == 1
    assert bus._subscriptions[0]["queue"] is normal_queue
