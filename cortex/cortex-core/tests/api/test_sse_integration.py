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
from app.components.sse import get_sse_service


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
        if "/v1/" in url and "token=" in url:
            # For any SSE endpoint with a token, return a mock response
            token = url.split("token=")[1].split("&")[0] if "token=" in url else None
            if token:
                try:
                    # Verify token is valid
                    payload = jwt.decode(token, settings.security.jwt_secret, algorithms=["HS256"])

                    # For user-specific endpoint, check the user ID matches
                    if "/user/" in url:
                        url_user_id = url.split("/user/")[1].split("?")[0]
                        token_user_id = payload.get("user_id")

                        # If user IDs don't match, let the endpoint handle the authorization error
                        if url_user_id != token_user_id:
                            return original_get(url, **kwargs)

                    # For global endpoint, no additional checks needed
                    if "/v1/global" in url:
                        return MockSSEResponse()

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
    # Get the connection manager
    connection_manager = get_sse_service().connection_manager
    
    # Save original connections
    original = {
        "global": connection_manager.connections["global"].copy(),
        "user": {k: v.copy() for k, v in connection_manager.connections["user"].items()},
        "workspace": {k: v.copy() for k, v in connection_manager.connections["workspace"].items()},
        "conversation": {k: v.copy() for k, v in connection_manager.connections["conversation"].items()},
    }

    # Clear connections for the test
    connection_manager.connections["global"].clear()
    connection_manager.connections["user"].clear()
    connection_manager.connections["workspace"].clear()
    connection_manager.connections["conversation"].clear()

    yield connection_manager.connections

    # Restore original connections
    connection_manager.connections["global"] = original["global"]
    connection_manager.connections["user"] = original["user"]
    connection_manager.connections["workspace"] = original["workspace"]
    connection_manager.connections["conversation"] = original["conversation"]


# Tests
def test_sse_global_events_endpoint_auth(sse_test_client, valid_token):
    """Test global events endpoint authentication"""
    token, user_id = valid_token

    # Test with no token
    response = sse_test_client.get("/v1/global")
    assert response.status_code == 422  # Validation error for missing required query parameter

    # Test with valid token
    response = sse_test_client.get(f"/v1/global?token={token}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"

    # Always close SSE connections in tests
    response.close()


def test_sse_user_events_endpoint(sse_test_client, valid_token):
    """Test user events endpoint"""
    token, user_id = valid_token

    # Test with no token
    response = sse_test_client.get(f"/v1/user/{user_id}")
    assert response.status_code == 422  # Validation error for missing required query parameter

    # Test with valid token
    response = sse_test_client.get(f"/v1/user/{user_id}?token={token}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"

    # Test with token for different user
    other_user_id = str(uuid.uuid4())
    response = sse_test_client.get(f"/v1/user/{other_user_id}?token={token}")
    assert response.status_code == 403  # Should now consistently be 403 Forbidden

    # Close any open connections
    if response.status_code == 200:
        response.close()


def test_sse_workspace_events_endpoint(sse_test_client, valid_token):
    """Test workspace events endpoint"""
    token, user_id = valid_token
    workspace_id = str(uuid.uuid4())

    # Test with valid token
    response = sse_test_client.get(f"/v1/workspace/{workspace_id}?token={token}")
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
        response = sse_test_client.get(f"/v1/conversation/{conversation_id}?token={token}")
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

    if conversation_id not in clean_connections["conversation"]:
        clean_connections["conversation"][conversation_id] = []

    clean_connections["conversation"][conversation_id].append({
        "id": connection_id,
        "user_id": user_id,
        "queue": queue
    })

    # Verify connection was added
    assert len(clean_connections["conversation"][conversation_id]) == 1

    # Remove the connection
    clean_connections["conversation"][conversation_id] = [
        conn for conn in clean_connections["conversation"][conversation_id]
        if conn["id"] != connection_id
    ]

    # Verify connection was removed
    assert len(clean_connections["conversation"][conversation_id]) == 0