from unittest.mock import patch

from app.main import app
from app.utils.auth import create_access_token
from fastapi.testclient import TestClient

client = TestClient(app)


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


@patch("app.core.event_bus.event_bus.publish")
def test_publish_system_event(mock_publish):
    """Test that the publish event endpoint works correctly."""
    # Configure the mock to return a future
    mock_publish.return_value = None

    # Get a valid token
    token = get_test_token()

    # Test data
    event_data = {"event_type": "system.notification", "payload": {"message": "Test notification"}}

    # Make the request
    response = client.post("/management/events/publish", json=event_data, headers={"Authorization": f"Bearer {token}"})

    # Check response
    assert response.status_code == 200
    assert response.json()["status"] == "published"

    # Verify the event_bus.publish was called
    mock_publish.assert_called_once()


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
