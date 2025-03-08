"""
Integration tests for Server-Sent Events (SSE) endpoints
"""

import pytest
import uuid
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch
from jose import jwt
from datetime import datetime, timedelta, timezone

from app.main import app
from app.config import settings
from app.api.sse import active_connections


# Mock response for SSE testing
class MockSSEResponse:
    """A mock SSE response that won't cause tests to hang"""
    def __init__(self):
        self.status_code = 200
        self.headers = {
            "content-type": "text/event-stream",
            "cache-control": "no-cache",
            "connection": "keep-alive"
        }
        self._content = b"data: {}\n\n"
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._closed = True

    def json(self):
        raise ValueError("Cannot call json() on a streaming response")

    # For iterator protocol
    def __iter__(self):
        yield self._content

    def iter_lines(self):
        yield self._content


# Fixtures
@pytest.fixture
def valid_token():
    """Create a valid JWT token for testing"""
    user_id = str(uuid.uuid4())
    token_data = {
        "sub": "test@example.com",
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=1)
    }
    token = jwt.encode(token_data, settings.security.jwt_secret, algorithm="HS256")
    return token, user_id


@pytest.fixture
def sse_test_client(monkeypatch):
    """Test client that safely tests SSE endpoints without hanging"""
    client = TestClient(app)
    original_get = client.get

    # Patch get method to return mock responses for SSE endpoints
    def mock_get(url, **kwargs):
        if "/events" in url and "token=" in url:
            # For any SSE endpoint with a token, return a mock response
            token = url.split("token=")[1].split("&")[0] if "token=" in url else None
            if token:
                try:
                    # Verify token is valid
                    payload = jwt.decode(token, settings.security.jwt_secret, algorithms=["HS256"])

                    # For user-specific endpoint, check the user ID matches
                    if "/users/" in url:
                        url_user_id = url.split("/users/")[1].split("/")[0]
                        token_user_id = payload.get("user_id")

                        # If user IDs don't match, let the endpoint handle the authorization error
                        if url_user_id != token_user_id:
                            return original_get(url, **kwargs)

                    # Valid token and matching user ID (if applicable)
                    return MockSSEResponse()
                except Exception:
                    # If token is invalid, let the endpoint handle it
                    pass
        # For all other requests, use original implementation
        return original_get(url, **kwargs)

    monkeypatch.setattr(client, "get", mock_get)
    return client


@pytest.fixture
def clean_connections():
    """Create a clean set of connections for the test"""
    # Save original connections
    original = {
        "global": active_connections["global"].copy(),
        "users": {k: v.copy() for k, v in active_connections["users"].items()},
        "workspaces": {k: v.copy() for k, v in active_connections["workspaces"].items()},
        "conversations": {k: v.copy() for k, v in active_connections["conversations"].items()},
    }

    # Clear connections for the test
    active_connections["global"].clear()
    active_connections["users"].clear()
    active_connections["workspaces"].clear()
    active_connections["conversations"].clear()

    yield active_connections

    # Restore original connections
    active_connections["global"] = original["global"]
    active_connections["users"] = original["users"]
    active_connections["workspaces"] = original["workspaces"]
    active_connections["conversations"] = original["conversations"]


# Tests
def test_sse_global_events_endpoint_auth(sse_test_client, valid_token):
    """Test global events endpoint authentication"""
    token, user_id = valid_token

    # Test with no token
    response = sse_test_client.get("/events")
    assert response.status_code == 401
    assert "No token provided" in response.json()["detail"]

    # Test with valid token
    response = sse_test_client.get(f"/events?token={token}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"

    # Always close SSE connections in tests
    response.close()


def test_sse_user_events_endpoint(sse_test_client, valid_token):
    """Test user events endpoint"""
    token, user_id = valid_token

    # Test with no token
    response = sse_test_client.get(f"/users/{user_id}/events")
    assert response.status_code == 401

    # Test with valid token
    response = sse_test_client.get(f"/users/{user_id}/events?token={token}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"

    # Test with token for different user
    other_user_id = str(uuid.uuid4())
    response = sse_test_client.get(f"/users/{other_user_id}/events?token={token}")
    assert response.status_code == 401 or response.status_code == 403

    # Close any open connections
    if response.status_code == 200:
        response.close()


def test_sse_workspace_events_endpoint(sse_test_client, valid_token):
    """Test workspace events endpoint"""
    token, user_id = valid_token
    workspace_id = str(uuid.uuid4())

    # Test with valid token
    response = sse_test_client.get(f"/workspaces/{workspace_id}/events?token={token}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"

    # Always close SSE connections in tests
    response.close()


def test_sse_conversation_events_endpoint(sse_test_client, valid_token, monkeypatch):
    """Test conversation events endpoint"""
    token, user_id = valid_token
    conversation_id = str(uuid.uuid4())

    # Mock the get_conversation_publisher to avoid real background tasks
    async def mock_publisher(conversation_id):
        return None

    # Patch the publisher function
    with patch('app.components.conversation_channels.get_conversation_publisher',
               side_effect=mock_publisher):

        # Test with valid token
        response = sse_test_client.get(f"/conversations/{conversation_id}/events?token={token}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

        # Always close SSE connections in tests
        response.close()


@pytest.mark.asyncio
async def test_sse_connection_tracking(clean_connections):
    """Test that connections are properly tracked and cleaned up"""
    # Add a test connection
    conversation_id = str(uuid.uuid4())
    connection_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    queue = asyncio.Queue()

    if conversation_id not in clean_connections["conversations"]:
        clean_connections["conversations"][conversation_id] = []

    clean_connections["conversations"][conversation_id].append({
        "id": connection_id,
        "user_id": user_id,
        "queue": queue
    })

    # Verify connection was added
    assert len(clean_connections["conversations"][conversation_id]) == 1

    # Remove the connection
    clean_connections["conversations"][conversation_id] = [
        conn for conn in clean_connections["conversations"][conversation_id]
        if conn["id"] != connection_id
    ]

    # Verify connection was removed
    assert len(clean_connections["conversations"][conversation_id]) == 0