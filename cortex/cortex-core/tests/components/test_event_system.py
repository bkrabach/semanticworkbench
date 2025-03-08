"""
Test suite for the enhanced event system
"""

import pytest
import asyncio
from app.components.event_system import EventSystem, EventPayload


@pytest.fixture
def event_system():
    """Create a fresh event system for each test"""
    return EventSystem()


@pytest.mark.asyncio
async def test_publish_subscribe(event_system):
    """Test basic publish/subscribe functionality"""
    # Setup
    received_events = []
    
    async def callback(event_type, payload):
        received_events.append(payload)
    
    # Subscribe to events
    subscription_id = await event_system.subscribe("test.*", callback)
    
    # Publish an event
    await event_system.publish(
        event_type="test.event",
        data={"key": "value"},
        source="test_component"
    )
    
    # Verify
    assert len(received_events) == 1
    assert received_events[0].event_type == "test.event"
    assert received_events[0].data == {"key": "value"}
    assert received_events[0].source == "test_component"
    
    # Unsubscribe
    result = await event_system.unsubscribe(subscription_id)
    assert result is True


@pytest.mark.asyncio
async def test_wildcard_patterns(event_system):
    """Test pattern matching with wildcards"""
    # Setup callbacks for different patterns
    pattern_a_events = []
    pattern_b_events = []
    pattern_all_events = []
    
    async def callback_a(event_type, payload):
        pattern_a_events.append(payload)
    
    async def callback_b(event_type, payload):
        pattern_b_events.append(payload)
    
    async def callback_all(event_type, payload):
        pattern_all_events.append(payload)
    
    # Subscribe to different patterns
    await event_system.subscribe("test.a.*", callback_a)
    await event_system.subscribe("test.b.*", callback_b)
    await event_system.subscribe("*", callback_all)
    
    # Publish events
    await event_system.publish("test.a.1", {"index": 1}, "test")
    await event_system.publish("test.b.1", {"index": 2}, "test")
    await event_system.publish("other.event", {"index": 3}, "test")
    
    # Verify
    assert len(pattern_a_events) == 1
    assert pattern_a_events[0].data["index"] == 1
    
    assert len(pattern_b_events) == 1
    assert pattern_b_events[0].data["index"] == 2
    
    assert len(pattern_all_events) == 3


@pytest.mark.asyncio
async def test_event_stats(event_system):
    """Test event statistics collection"""
    # Setup
    async def callback(event_type, payload):
        pass
    
    # Subscribe to events
    await event_system.subscribe("test.*", callback)
    
    # Publish some events
    await event_system.publish("test.event1", {"key": "value1"}, "test")
    await event_system.publish("test.event2", {"key": "value2"}, "test")
    
    # Get stats
    stats = await event_system.get_stats()
    
    # Verify
    assert stats["events_published"] == 2
    assert stats["events_delivered"] == 2
    assert stats["subscriber_count"] == 1
    assert "test.event1" in stats["event_types"]
    assert "test.event2" in stats["event_types"]
    assert stats["event_types"]["test.event1"] == 1
    assert stats["event_types"]["test.event2"] == 1
    assert "uptime_seconds" in stats
    assert "events_per_second" in stats


@pytest.mark.asyncio
async def test_error_handling(event_system):
    """Test that errors in one subscriber don't affect others"""
    # Setup
    successful_deliveries = []
    
    async def good_callback(event_type, payload):
        successful_deliveries.append(payload)
    
    async def bad_callback(event_type, payload):
        raise Exception("Simulated error")
    
    # Subscribe both callbacks
    await event_system.subscribe("test.*", good_callback)
    await event_system.subscribe("test.*", bad_callback)
    
    # Publish an event
    await event_system.publish("test.event", {"key": "value"}, "test")
    
    # Verify
    assert len(successful_deliveries) == 1  # Good callback still received the event
    
    # Check stats
    stats = await event_system.get_stats()
    assert stats["errors"] == 1  # One error recorded


@pytest.mark.asyncio
async def test_event_tracing(event_system):
    """Test event tracing with trace ID and correlation ID"""
    # Setup
    received_events = []
    
    async def callback(event_type, payload):
        received_events.append(payload)
    
    # Subscribe to events
    await event_system.subscribe("test.*", callback)
    
    # Use explicit trace and correlation IDs
    trace_id = "trace-123"
    correlation_id = "corr-456"
    
    # Publish an event
    await event_system.publish(
        event_type="test.event",
        data={"key": "value"},
        source="test_component",
        trace_id=trace_id,
        correlation_id=correlation_id
    )
    
    # Verify
    assert len(received_events) == 1
    assert received_events[0].trace_id == trace_id
    assert received_events[0].correlation_id == correlation_id
    
    # Publish without explicit trace ID (should generate one)
    await event_system.publish(
        event_type="test.event2",
        data={"key": "value2"},
        source="test_component",
        correlation_id=correlation_id
    )
    
    # Verify
    assert len(received_events) == 2
    assert received_events[1].trace_id is not None  # Auto-generated
    assert received_events[1].trace_id != trace_id  # Different from the explicit one
    assert received_events[1].correlation_id == correlation_id


@pytest.mark.asyncio
async def test_many_subscribers(event_system):
    """Test the event system with a large number of subscribers"""
    # Setup
    received_counts = [0] * 50  # Track calls for 50 different subscribers
    
    # Create many subscribers for the same event
    for i in range(50):
        idx = i  # Capture loop variable
        
        async def callback(event_type, payload, idx=idx):
            received_counts[idx] += 1
        
        await event_system.subscribe("test.event", callback)
    
    # Publish a single event
    await event_system.publish(
        event_type="test.event", 
        data={"key": "value"}, 
        source="test_component"
    )
    
    # Verify all subscribers received the event
    assert all(count == 1 for count in received_counts)
    
    # Check stats
    stats = await event_system.get_stats()
    assert stats["events_published"] == 1
    assert stats["events_delivered"] == 50
    assert stats["subscriber_count"] == 50


@pytest.mark.asyncio
async def test_concurrent_publishing(event_system):
    """Test concurrent publishing of events"""
    # Setup
    event_types = set()
    
    async def callback(event_type, payload):
        event_types.add(event_type)
    
    # Subscribe to all events
    await event_system.subscribe("*", callback)
    
    # Publish multiple events concurrently
    events_to_publish = [
        ("test.event1", {"index": 1}, "source1"),
        ("test.event2", {"index": 2}, "source2"),
        ("test.event3", {"index": 3}, "source3"),
        ("other.event1", {"index": 4}, "source4"),
        ("other.event2", {"index": 5}, "source5")
    ]
    
    tasks = [
        event_system.publish(event_type, data, source)
        for event_type, data, source in events_to_publish
    ]
    
    await asyncio.gather(*tasks)
    
    # Verify all events were received
    assert len(event_types) == 5
    for event_type, _, _ in events_to_publish:
        assert event_type in event_types
    
    # Check stats
    stats = await event_system.get_stats()
    assert stats["events_published"] == 5
    assert stats["events_delivered"] == 5


@pytest.mark.asyncio
async def test_pattern_matching_edge_cases(event_system):
    """Test edge cases in pattern matching"""
    # Setup
    received_events = {
        "exact": [],
        "prefix": [],
        "suffix": [],
        "middle": [],
        "complex": [],
        "all": []
    }
    
    async def callback_exact(event_type, payload):
        received_events["exact"].append(event_type)
    
    async def callback_prefix(event_type, payload):
        received_events["prefix"].append(event_type)
    
    async def callback_suffix(event_type, payload):
        received_events["suffix"].append(event_type)
    
    async def callback_middle(event_type, payload):
        received_events["middle"].append(event_type)
    
    async def callback_complex(event_type, payload):
        received_events["complex"].append(event_type)
    
    async def callback_all(event_type, payload):
        received_events["all"].append(event_type)
    
    # Subscribe with different pattern types
    await event_system.subscribe("test.event", callback_exact)     # Exact match
    await event_system.subscribe("test.*", callback_prefix)        # Prefix match
    await event_system.subscribe("*.event", callback_suffix)       # Suffix match
    await event_system.subscribe("test.*.event", callback_middle)  # Middle wildcard
    await event_system.subscribe("test.*.*.event", callback_complex)  # Multiple wildcards
    await event_system.subscribe("*", callback_all)                # All events
    
    # Publish events
    test_events = [
        "test.event",                  # Should match exact, prefix, suffix, all
        "test.something",              # Should match prefix, all
        "something.event",             # Should match suffix, all
        "test.middle.event",           # Should match middle, all
        "test.part1.part2.event",      # Should match complex, all
        "completely.different.thing"   # Should match only all
    ]
    
    for event in test_events:
        await event_system.publish(event, {"event": event}, "test")
    
    # Verify pattern matching worked correctly
    assert len(received_events["exact"]) == 1
    assert "test.event" in received_events["exact"]
    
    assert len(received_events["prefix"]) == 2
    assert "test.event" in received_events["prefix"]
    assert "test.something" in received_events["prefix"]
    
    assert len(received_events["suffix"]) == 2
    assert "test.event" in received_events["suffix"]
    assert "something.event" in received_events["suffix"]
    
    assert len(received_events["middle"]) == 1
    assert "test.middle.event" in received_events["middle"]
    
    assert len(received_events["complex"]) == 1
    assert "test.part1.part2.event" in received_events["complex"]
    
    assert len(received_events["all"]) == 6  # Should match all events


@pytest.mark.asyncio
async def test_unsubscribe_behavior(event_system):
    """Test unsubscribing behavior in detail"""
    # Setup counters for each callback
    counters = {
        "callback1": 0,
        "callback2": 0,
        "callback3": 0
    }
    
    async def callback1(event_type, payload):
        counters["callback1"] += 1
    
    async def callback2(event_type, payload):
        counters["callback2"] += 1
    
    async def callback3(event_type, payload):
        counters["callback3"] += 1
    
    # Subscribe all callbacks to the same pattern
    sub_id1 = await event_system.subscribe("test.*", callback1)
    sub_id2 = await event_system.subscribe("test.*", callback2)
    sub_id3 = await event_system.subscribe("other.*", callback3)
    
    # Initial event to verify all subscriptions work
    await event_system.publish("test.event", {}, "test")
    await event_system.publish("other.event", {}, "test")
    
    assert counters["callback1"] == 1
    assert counters["callback2"] == 1
    assert counters["callback3"] == 1
    
    # Unsubscribe first callback
    result = await event_system.unsubscribe(sub_id1)
    assert result is True
    
    # Verify the callback was unsubscribed
    await event_system.publish("test.event", {}, "test")
    assert counters["callback1"] == 1  # No change
    assert counters["callback2"] == 2  # Increased
    
    # Try to unsubscribe with invalid ID
    result = await event_system.unsubscribe("invalid-id")
    assert result is False
    
    # Unsubscribe remaining callbacks
    await event_system.unsubscribe(sub_id2)
    await event_system.unsubscribe(sub_id3)
    
    # Verify no callbacks are triggered
    await event_system.publish("test.event", {}, "test")
    await event_system.publish("other.event", {}, "test")
    
    assert counters["callback1"] == 1
    assert counters["callback2"] == 2
    assert counters["callback3"] == 1
    
    # Verify subscriber count in stats
    stats = await event_system.get_stats()
    assert stats["subscriber_count"] == 0