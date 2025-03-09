"""
Test suite for the monitoring API endpoints
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.main import app
from app.components.event_system import EventSystem


@pytest.fixture
def test_client():
    """Create a FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def client_with_event_system_override(mock_event_system):
    """Create a test client with event system dependency override"""
    # Import get_event_system to override it
    from app.api.monitoring import get_event_system
    
    # Override the get_event_system dependency
    app.dependency_overrides[get_event_system] = lambda: mock_event_system
    
    # Create a client with the override
    client = TestClient(app)
    
    yield client
    
    # Clean up after test
    app.dependency_overrides = {}


@pytest.fixture
def mock_event_system():
    """Create a mock event system with predefined stats"""
    mock_system = AsyncMock(spec=EventSystem)
    
    # Configure the mock to return predefined stats
    async def mock_get_stats():
        return {
            "events_published": 100,
            "events_delivered": 95,
            "subscriber_count": 5,
            "event_types": {
                "test.event": 50,
                "other.event": 30,
                "system.event": 20
            },
            "errors": 2,
            "uptime_seconds": 3600,
            "events_per_second": 0.028
        }
    
    mock_system.get_stats.side_effect = mock_get_stats
    return mock_system


def test_get_event_stats(client_with_event_system_override, mock_event_system):
    """Test the event stats endpoint with a dependency override"""
    # Make the request using client with event system override
    response = client_with_event_system_override.get("/monitoring/events/stats")
    
    # Verify the response
    assert response.status_code == 200
    data = response.json()
    
    # Check that we have the expected keys in the response
    assert "events_published" in data
    assert "events_delivered" in data
    assert "subscriber_count" in data
    assert "event_types" in data
    assert "errors" in data
    assert "uptime_seconds" in data
    assert "events_per_second" in data


@pytest.mark.asyncio
async def test_event_system_stats_real():
    """Test the event system stats with the real implementation"""
    # Create a real EventSystem instance
    event_system = EventSystem()
    
    # Define a simple subscriber
    async def test_subscriber(event_type, payload):
        # Just a dummy subscriber that does nothing
        pass
    
    # Another subscriber that will raise an exception
    async def error_subscriber(event_type, payload):
        raise Exception("Test error")
    
    # Subscribe to events
    await event_system.subscribe("test.*", test_subscriber)
    await event_system.subscribe("error.*", error_subscriber)
    await event_system.subscribe("another.*", test_subscriber)
    
    # Publish some events
    await event_system.publish("test.event1", {"data": "value1"}, "test_source")
    await event_system.publish("test.event2", {"data": "value2"}, "test_source")
    await event_system.publish("another.event", {"data": "value3"}, "test_source")
    
    # Publish an event that will cause an error
    await event_system.publish("error.event", {"data": "error_data"}, "test_source")
    
    # Get stats
    stats = await event_system.get_stats()
    
    # Verify stats
    assert stats["events_published"] == 4
    assert stats["events_delivered"] == 3  # One failed due to error
    assert stats["subscriber_count"] == 3
    assert len(stats["event_types"]) == 4  # Four different event types
    assert "test.event1" in stats["event_types"]
    assert "test.event2" in stats["event_types"]
    assert "another.event" in stats["event_types"]
    assert "error.event" in stats["event_types"]
    assert stats["errors"] == 1
    assert "uptime_seconds" in stats
    assert "events_per_second" in stats


@pytest.mark.asyncio
async def test_monitoring_api_with_real_event_system():
    """Test the monitoring API with a real event system"""
    # Create a real EventSystem instance
    event_system = EventSystem()
    
    # Generate some activity
    async def test_subscriber(event_type, payload):
        pass
    
    # Subscribe and publish some events
    await event_system.subscribe("api.test.*", test_subscriber)
    for i in range(5):
        await event_system.publish(f"api.test.event{i}", {"index": i}, "test_source")
    
    # Set up dependency override for this test
    from app.api.monitoring import get_event_system
    app.dependency_overrides[get_event_system] = lambda: event_system
    
    try:
        # Create a test client
        client = TestClient(app)
        
        # Make the request
        response = client.get("/monitoring/events/stats")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check that stats reflect our activity
        # With proper dependency override, the stats should include our events
        assert "events_published" in data
        assert "events_delivered" in data 
        assert "subscriber_count" in data
        assert "event_types" in data
        assert "errors" in data
        assert "uptime_seconds" in data
        assert "events_per_second" in data
        
        # Now we can more confidently check the actual values
        assert data["events_published"] == 5
        assert data["subscriber_count"] == 1
    finally:
        # Clean up dependency override
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_stats_update_over_time():
    """Test that stats update correctly over time"""
    # Create an event system
    event_system = EventSystem()
    
    # Initial stats
    initial_stats = await event_system.get_stats()
    initial_time = initial_stats["uptime_seconds"]
    
    # Wait a short time
    await asyncio.sleep(0.1)
    
    # Get updated stats
    updated_stats = await event_system.get_stats()
    updated_time = updated_stats["uptime_seconds"]
    
    # Verify time has advanced
    assert updated_time > initial_time
    
    # Now publish some events
    pre_publish_stats = await event_system.get_stats()
    pre_count = pre_publish_stats["events_published"]
    
    # Define a subscriber
    async def test_subscriber(event_type, payload):
        pass
    
    # Subscribe and publish
    subscription_id = await event_system.subscribe("stats.test.*", test_subscriber)
    await event_system.publish("stats.test.event1", {"test": 1}, "test_source")
    await event_system.publish("stats.test.event2", {"test": 2}, "test_source")
    
    # Get post-publish stats
    post_publish_stats = await event_system.get_stats()
    
    # Verify counts increased
    assert post_publish_stats["events_published"] == pre_count + 2
    assert post_publish_stats["subscriber_count"] == 1
    assert "stats.test.event1" in post_publish_stats["event_types"]
    assert "stats.test.event2" in post_publish_stats["event_types"]
    
    # Unsubscribe
    await event_system.unsubscribe(subscription_id)
    
    # Check subscriber count decreased
    final_stats = await event_system.get_stats()
    assert final_stats["subscriber_count"] == 0