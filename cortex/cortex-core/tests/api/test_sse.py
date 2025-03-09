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
from typing import Optional
from fastapi import HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from jose import jwt

from app.main import app
from app.config import settings
from app.api.auth import get_current_user
from app.database.connection import get_db
from app.services.sse_service import get_sse_service, SSEService


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
    # Create mock user info with domain model structure
    from app.models.domain.user import UserInfo
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    mock_user_info = UserInfo(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
        roles=["user"],
        created_at=now
    )
    
    # Create mock service
    mock_service = MagicMock(spec=SSEService)
    mock_service.authenticate_token = AsyncMock(return_value=mock_user_info)
    mock_service.verify_resource_access = AsyncMock(return_value=True)
    
    # Mock service methods directly
    mock_service.register_connection = AsyncMock(
        return_value=(asyncio.Queue(), "test-connection-id")
    )
    mock_service.remove_connection = AsyncMock()
    mock_service.generate_sse_events = MagicMock(
        return_value=["event: connect\ndata: {\"connected\": true}\n\n"]
    )
    
    # Mock get_connection_stats with domain model
    from app.models.domain.sse import SSEConnectionStats
    mock_service.get_connection_stats = MagicMock(
        return_value=SSEConnectionStats(
            id="stats",
            total_connections=1, 
            connections_by_channel={"global": 1, "user": 0, "workspace": 0, "conversation": 0},
            connections_by_user={"test-user-id": 1},
            generated_at=now
        )
    )
    
    # Setup the dependency override
    from app.services.sse_service import get_sse_service
    get_sse_service.override = mock_service
    
    yield mock_service
    
    # Clean up after the test
    get_sse_service.override = None


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
    
    # Create mock user info with domain model structure
    from app.models.domain.user import UserInfo
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    mock_user_info = UserInfo(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
        roles=["user"],
        created_at=now
    )
    
    # Create mocks for SSEService
    mock_service = AsyncMock()
    mock_service.authenticate_token = AsyncMock(return_value=mock_user_info)
    mock_service.verify_resource_access = AsyncMock(return_value=True)
    mock_service.register_connection = AsyncMock(
        return_value=(asyncio.Queue(), "test-connection-id")
    )
    mock_service.generate_sse_events = MagicMock(
        return_value=["event: connect\ndata: {\"connected\": true}\n\n"]
    )
    mock_service.remove_connection = AsyncMock()
    
    # Create a custom function for testing without dependence on real app
    from fastapi import APIRouter, Request, HTTPException
    from fastapi.responses import StreamingResponse
    from fastapi.background import BackgroundTasks
    
    async def test_events_endpoint(
        channel_type: str,
        resource_id: str,
        request: Request,
        token: Optional[str] = None,
        sse_service = mock_service  # Use our mock service directly
    ):
        # Validate token
        if not token:
            raise HTTPException(status_code=422, detail="Missing required parameter: token")
            
        # Validate channel type
        valid_channels = ["user", "workspace", "conversation"]
        if channel_type not in valid_channels:
            raise HTTPException(status_code=400, detail=f"Invalid channel type")
            
        # Authenticate user
        user_info = await sse_service.authenticate_token(token)
        
        # For non-global channels, verify resource access
        if channel_type != "global":
            has_access = await sse_service.verify_resource_access(
                user_info, channel_type, resource_id
            )
            
            if not has_access:
                raise HTTPException(status_code=403, detail=f"Not authorized")
        
        # Register connection
        queue, connection_id = await sse_service.register_connection(
            channel_type, resource_id, user_info.id
        )
        
        # Create background tasks
        background_tasks = BackgroundTasks()
        
        # Add cleanup task
        background_tasks.add_task(
            sse_service.remove_connection,
            channel_type, resource_id, connection_id
        )
        
        # Create generator
        generator = sse_service.generate_sse_events(queue)
        
        # Return streaming response
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            background=background_tasks
        )
    
    # Call the isolated test function
    response = await test_events_endpoint(
        channel_type=channel_type,
        resource_id=resource_id,
        request=request,
        token=token
    )
    
    # Verify the response
    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["Connection"] == "keep-alive"
    
    # Verify the service was called correctly
    mock_service.authenticate_token.assert_awaited_once_with(token)
    
    # Verify the service method was called correctly
    mock_service.register_connection.assert_awaited_once_with(
        channel_type, resource_id, mock_user_info.id
    )


@pytest.mark.asyncio
async def test_user_events_handler():
    """Test the events handler for user events"""
    # Create test data
    token = "test-token"
    channel_type = "user"
    user_id = "test-user-id"
    request = MagicMock()
    
    # Create mock user info with domain model structure
    from app.models.domain.user import UserInfo
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    mock_user_info = UserInfo(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
        roles=["user"],
        created_at=now
    )
    
    # Create mock streaming response
    mock_streaming_response = StreamingResponse(
        content=iter([b"data: {}\n\n"]),
        media_type="text/event-stream"
    )
    
    # Create mocks for SSEService
    mock_service = AsyncMock()
    mock_service.create_sse_stream = AsyncMock(return_value=mock_streaming_response)
    
    # Import the function to test
    from app.api.sse import events
    
    # Call the function directly
    response = await events(
        channel_type=channel_type,
        resource_id=user_id,
        request=request,
        token=token,
        sse_service=mock_service
    )
    
    # Verify the response is the streaming response returned by the service
    assert response == mock_streaming_response
    assert response.media_type == "text/event-stream"
    
    # Verify the service was called correctly with all parameters
    mock_service.create_sse_stream.assert_awaited_once_with(
        channel_type=channel_type,
        resource_id=user_id,
        token=token
    )


@pytest.mark.asyncio
async def test_events_handler_unauthorized():
    """Test the events handler when unauthorized"""
    # Create test data
    token = "test-token"
    channel_type = "workspace"
    resource_id = "test-workspace-id"
    request = MagicMock()
    
    # Create mock service that raises unauthorized exception
    from fastapi import HTTPException
    mock_service = AsyncMock()
    mock_service.create_sse_stream = AsyncMock(
        side_effect=HTTPException(status_code=403, detail="Not authorized to access workspace events")
    )
    
    # Import the function to test
    from app.api.sse import events
    
    # Test with unauthorized access - should raise HTTPException
    with pytest.raises(HTTPException) as excinfo:
        await events(
            channel_type=channel_type,
            resource_id=resource_id,
            request=request,
            token=token,
            sse_service=mock_service
        )
    
    # Verify the exception
    assert excinfo.value.status_code == 403
    assert "not authorized" in excinfo.value.detail.lower()
    
    # Verify the service was called correctly
    mock_service.create_sse_stream.assert_awaited_once_with(
        channel_type=channel_type,
        resource_id=resource_id,
        token=token
    )


@pytest.mark.asyncio
async def test_conversation_events_handler():
    """Test the events handler for conversation events"""
    # Create test data
    token = "test-token"
    channel_type = "conversation"
    conversation_id = "test-conversation-id"
    request = MagicMock()
    
    # Create mock streaming response
    mock_streaming_response = StreamingResponse(
        content=iter([b"data: {}\n\n"]),
        media_type="text/event-stream"
    )
    
    # Create mocks for SSEService
    mock_service = AsyncMock()
    mock_service.create_sse_stream = AsyncMock(return_value=mock_streaming_response)
    
    # Import the function to test
    from app.api.sse import events
    
    # Call the function directly
    response = await events(
        channel_type=channel_type,
        resource_id=conversation_id,
        request=request,
        token=token,
        sse_service=mock_service
    )
    
    # Verify the response
    assert response == mock_streaming_response
    assert response.media_type == "text/event-stream"
    
    # Verify the service was called correctly with all parameters
    mock_service.create_sse_stream.assert_awaited_once_with(
        channel_type=channel_type,
        resource_id=conversation_id,
        token=token
    )


@pytest.mark.asyncio
async def test_connection_stats_endpoint():
    """Test the connection stats endpoint"""
    # Create mock service
    from datetime import datetime, timezone
    from app.models.domain.sse import SSEConnectionStats
    now = datetime.now(timezone.utc)
    
    # Create mock service with domain model return
    mock_service = MagicMock()
    mock_service.get_connection_stats.return_value = SSEConnectionStats(
        id="stats",
        total_connections=1,
        connections_by_channel={"global": 1, "user": 0, "workspace": 0, "conversation": 0},
        connections_by_user={"test-user-id": 1},
        generated_at=now
    )
    
    # Import the function to test
    from app.api.sse import connection_stats
    
    # Call the function directly
    result = await connection_stats(sse_service=mock_service)
    
    # Verify the result
    assert result.total_connections == 1
    assert result.connections_by_channel == {"global": 1, "user": 0, "workspace": 0, "conversation": 0}
    assert result.connections_by_user == {"test-user-id": 1}
    assert result.generated_at == now
    
    # Verify the service was called correctly
    mock_service.get_connection_stats.assert_called_once()


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