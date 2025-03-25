import pytest
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.utils.auth import create_access_token
from fastapi.testclient import TestClient
from app.core.event_bus import EventBus

# Create a client and add event_bus to app.state for testing
client = TestClient(app)

# Add event_bus to app.state
mock_event_bus = MagicMock(spec=EventBus)
mock_event_bus.publish = AsyncMock()
app.state.event_bus = mock_event_bus


def get_test_token():
    """Create a test token for authenticated requests."""
    # Create a token with a valid user
    token_data = {"sub": "test-user", "id": "user-123", "name": "Test User", "email": "test@example.com"}
    return create_access_token(token_data)


def test_system_status_endpoint():
    """Test that the system status endpoint returns correctly when authenticated."""
    # Get a valid token
    token = get_test_token()

    # Make the request with authorization
    response = client.get("/management/system/status", headers={"Authorization": f"Bearer {token}"})

    # Check the response
    assert response.status_code == 200
    data = response.json()

    # Verify the structure
    assert "active_users" in data
    assert "active_conversations" in data
    assert "uptime_seconds" in data
    assert "service_status" in data
    assert "memory_usage" in data


def test_system_status_unauthorized():
    """Test that the system status endpoint requires authentication."""
    # Make request without a token
    response = client.get("/management/system/status")
    assert response.status_code == 401


def test_publish_system_event():
    """Test that the publish event endpoint works correctly."""
    # Create a fresh mock for this specific test
    test_mock_event_bus = MagicMock(spec=EventBus)
    test_mock_event_bus.publish = AsyncMock()
    
    # Save original event_bus
    original_event_bus = app.state.event_bus
    
    try:
        # Replace app.state.event_bus with our test-specific mock
        app.state.event_bus = test_mock_event_bus
        
        # Get a valid token
        token = get_test_token()

        # Test data
        event_data = {"event_type": "system.notification", "payload": {"message": "Test notification"}}

        # Make the request
        response = client.post("/management/events/publish", json=event_data, headers={"Authorization": f"Bearer {token}"})

        # Check response
        assert response.status_code == 200
        assert response.json()["status"] == "published"
        
        # Verify event bus was called with correct parameters
        test_mock_event_bus.publish.assert_awaited_once()
        call_args = test_mock_event_bus.publish.await_args
        assert call_args[0][0] == "system.notification"  # First arg is event_type
        assert "user_id" in call_args[0][1]  # Second arg is event_payload
        assert call_args[0][1]["data"] == {"message": "Test notification"}
    finally:
        # Restore original event_bus
        app.state.event_bus = original_event_bus


def test_publish_invalid_event_type():
    """Test that the publish event endpoint validates event types."""
    # Get a valid token
    token = get_test_token()

    # Invalid event type
    event_data = {"event_type": "invalid.event.type", "payload": {"message": "Test"}}

    # Make the request
    response = client.post("/management/events/publish", json=event_data, headers={"Authorization": f"Bearer {token}"})

    # Should be rejected with 400
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]
