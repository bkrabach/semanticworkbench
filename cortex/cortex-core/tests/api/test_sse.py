"""
Test suite for the SSE (Server-Sent Events) API endpoints
"""

import pytest
import json
import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from jose import jwt

from app.main import app
from app.config import settings
from app.api.auth import get_current_user
from app.database.connection import get_db
from app.components.sse import get_sse_service, SSEService


@pytest.fixture
def valid_token():
    """Create a valid JWT token for testing"""
    user_id = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc).timestamp() + 3600,  # 1 hour expiry
    }
    token = jwt.encode(payload, settings.security.jwt_secret, algorithm="HS256")
    return token, user_id


# Mock response for SSE testing
class MockSSEResponse:
    """A mock response for SSE endpoints that won't cause hanging"""
    def __init__(self):
        self.status_code = 200
        self.headers = {"content-type": "text/event-stream", "Cache-Control": "no-cache", "Connection": "keep-alive"}
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


# Define mock objects
@pytest.fixture
def mock_sse_service():
    """Mock SSE service"""
    # Create mock user info
    mock_user_info = {"id": "test-user-id", "roles": ["user"]}
    
    # Create mock service
    mock_service = MagicMock(spec=SSEService)
    mock_service.authenticate_token = AsyncMock(return_value=mock_user_info)
    mock_service.verify_resource_access = AsyncMock(return_value=True)
    
    # Mock connection manager within the service
    mock_service.connection_manager = MagicMock()
    mock_service.connection_manager.register_connection = AsyncMock(
        return_value=(asyncio.Queue(), "test-connection-id")
    )
    mock_service.connection_manager.remove_connection = AsyncMock()
    mock_service.connection_manager.generate_sse_events = MagicMock(
        return_value=["event: connect\ndata: {\"connected\": true}\n\n"]
    )
    mock_service.connection_manager.get_stats = MagicMock(
        return_value={
            "global": 1,
            "channels": {"user": {}, "workspace": {}, "conversation": {}},
            "total": 1
        }
    )
    
    return mock_service


def test_events_endpoint_no_token():
    """Test events endpoint without a token"""
    client = TestClient(app)
    response = client.get("/v1/global")  # Updated path
    assert response.status_code == 422  # Validation error for missing required query parameter
    assert "token" in response.text.lower()  # Token field should be mentioned in the error


@pytest.mark.asyncio
async def test_events_handler():
    """Test the events handler function directly"""
    # Create test data
    token = "test-token"
    channel_type = "user"  # Changed from global to user since global has special handling now
    resource_id = "test-user-id"
    request = MagicMock()
    
    # Create mocks
    mock_service = AsyncMock()
    mock_service.authenticate_token.return_value = {"id": "test-user-id", "roles": ["user"]}
    mock_service.verify_resource_access.return_value = True
    
    mock_service.connection_manager = AsyncMock()
    mock_service.connection_manager.register_connection.return_value = (asyncio.Queue(), "test-connection-id")
    mock_service.connection_manager.generate_sse_events.return_value = ["event: connect\ndata: {\"connected\": true}\n\n"]
    
    mock_db = MagicMock()
    
    # Import the function to test
    from app.api.sse import events
    
    # Call the function directly
    response = await events(
        channel_type=channel_type,
        resource_id=resource_id,
        request=request,
        token=token,
        sse_service=mock_service,
        db=mock_db
    )
    
    # Verify the response
    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["Connection"] == "keep-alive"
    
    # Verify the service was called correctly
    mock_service.authenticate_token.assert_awaited_once_with(token)
    
    # Verify the connection manager was called correctly - with the actual channel type and resource ID
    mock_service.connection_manager.register_connection.assert_awaited_once_with(
        channel_type, resource_id, "test-user-id"
    )


@pytest.mark.asyncio
async def test_user_events_handler():
    """Test the events handler for user events"""
    # Create test data
    token = "test-token"
    channel_type = "user"
    user_id = "test-user-id"
    request = MagicMock()
    
    # Create mocks
    mock_service = AsyncMock()
    mock_service.authenticate_token.return_value = {"id": "test-user-id", "roles": ["user"]}
    mock_service.verify_resource_access.return_value = True
    
    mock_service.connection_manager = AsyncMock()
    mock_service.connection_manager.register_connection.return_value = (asyncio.Queue(), "test-connection-id")
    mock_service.connection_manager.generate_sse_events.return_value = ["event: connect\ndata: {\"connected\": true}\n\n"]
    
    mock_db = MagicMock()
    
    # Import the function to test
    from app.api.sse import events
    
    # Call the function directly
    response = await events(
        channel_type=channel_type,
        resource_id=user_id,
        request=request,
        token=token,
        sse_service=mock_service,
        db=mock_db
    )
    
    # Verify the response
    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/event-stream"
    
    # Verify the service was called correctly
    mock_service.authenticate_token.assert_awaited_once_with(token)
    mock_service.verify_resource_access.assert_awaited_once_with(
        mock_service.authenticate_token.return_value, "user", user_id, mock_db
    )
    
    # Verify the connection manager was called correctly
    mock_service.connection_manager.register_connection.assert_awaited_once_with(
        "user", user_id, "test-user-id"
    )


@pytest.mark.asyncio
async def test_events_handler_unauthorized():
    """Test the events handler when unauthorized"""
    # Create test data
    token = "test-token"
    channel_type = "workspace"
    resource_id = "test-workspace-id"
    request = MagicMock()
    
    # Create mocks
    mock_service = AsyncMock()
    mock_service.authenticate_token.return_value = {"id": "test-user-id", "roles": ["user"]}
    mock_service.verify_resource_access.return_value = False  # Deny access
    
    mock_db = MagicMock()
    
    # Import the function to test
    from app.api.sse import events
    
    # Test with unauthorized access - should raise HTTPException
    with pytest.raises(HTTPException) as excinfo:
        await events(
            channel_type=channel_type,
            resource_id=resource_id,
            request=request,
            token=token,
            sse_service=mock_service,
            db=mock_db
        )
    
    # Verify the exception
    assert excinfo.value.status_code == 403
    assert "not authorized" in excinfo.value.detail.lower()
    
    # Verify the service was called correctly
    mock_service.authenticate_token.assert_awaited_once_with(token)
    mock_service.verify_resource_access.assert_awaited_once_with(
        mock_service.authenticate_token.return_value, channel_type, resource_id, mock_db
    )


@pytest.mark.asyncio
async def test_conversation_events_handler():
    """Test the events handler for conversation events"""
    # Create test data
    token = "test-token"
    channel_type = "conversation"
    conversation_id = "test-conversation-id"
    request = MagicMock()
    
    # Create mocks
    mock_service = AsyncMock()
    mock_service.authenticate_token.return_value = {"id": "test-user-id", "roles": ["user"]}
    mock_service.verify_resource_access.return_value = True
    
    mock_service.connection_manager = AsyncMock()
    mock_service.connection_manager.register_connection.return_value = (asyncio.Queue(), "test-connection-id")
    mock_service.connection_manager.generate_sse_events.return_value = ["event: connect\ndata: {\"connected\": true}\n\n"]
    
    mock_db = MagicMock()
    
    # Import the function to test
    from app.api.sse import events
    
    # Mock the publisher import and background tasks
    with patch("app.components.conversation_channels.get_conversation_publisher") as mock_publisher, \
         patch("app.api.sse.BackgroundTasks", return_value=MagicMock(spec=BackgroundTasks)) as mock_bg_tasks:
        
        # Call the function directly
        response = await events(
            channel_type=channel_type,
            resource_id=conversation_id,
            request=request,
            token=token,
            sse_service=mock_service,
            db=mock_db
        )
        
        # Verify the response
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"
        
        # Verify the service was called correctly
        mock_service.authenticate_token.assert_awaited_once_with(token)
        mock_service.verify_resource_access.assert_awaited_once_with(
            mock_service.authenticate_token.return_value, channel_type, conversation_id, mock_db
        )
        
        # Verify the connection manager was called correctly
        mock_service.connection_manager.register_connection.assert_awaited_once_with(
            channel_type, conversation_id, "test-user-id"
        )
        
        # Verify conversation publisher was added to background tasks
        mock_bg_tasks.return_value.add_task.assert_called()


@pytest.mark.asyncio
async def test_connection_stats_endpoint():
    """Test the connection stats endpoint"""
    # Create mock service
    mock_service = MagicMock()
    mock_service.connection_manager = MagicMock()
    mock_service.connection_manager.get_stats.return_value = {
        "global": 1,
        "channels": {"user": {}, "workspace": {}, "conversation": {}},
        "total": 1
    }
    
    # Import the function to test
    from app.api.sse import connection_stats
    
    # Call the function directly
    result = await connection_stats(sse_service=mock_service)
    
    # Verify the result
    assert result == mock_service.connection_manager.get_stats.return_value
    
    # Verify the service was called correctly
    mock_service.connection_manager.get_stats.assert_called_once()


def test_events_endpoint_invalid_channel():
    """Test events endpoint with an invalid channel type"""
    client = TestClient(app)
    
    # Override dependency
    app.dependency_overrides[get_sse_service] = lambda: AsyncMock(spec=SSEService)
    app.dependency_overrides[get_db] = lambda: MagicMock()
    
    try:
        response = client.get("/v1/invalid/123?token=test-token")  # Updated path
        assert response.status_code == 400
        assert "invalid channel type" in response.json()["detail"].lower()
    finally:
        # Clean up
        app.dependency_overrides = {}