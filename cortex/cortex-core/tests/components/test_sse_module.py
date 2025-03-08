"""
Test suite for the SSE module components
"""

import pytest
import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone

from app.components.sse import SSEService, get_sse_service
from app.components.sse.manager import SSEConnectionManager
from app.components.sse.auth import SSEAuthService
from app.components.sse.events import SSEEventSubscriber


@pytest.fixture
def mock_event_system():
    """Mock event system for testing"""
    mock_system = AsyncMock()
    mock_system.subscribe = AsyncMock(return_value="subscription-id")
    mock_system.unsubscribe = AsyncMock()
    return mock_system


@pytest.mark.asyncio
async def test_connection_manager_register():
    """Test connection registration in the manager"""
    manager = SSEConnectionManager()
    
    # Test registering a global connection
    queue, conn_id = await manager.register_connection("global", "global", "user-123")
    assert isinstance(queue, asyncio.Queue)
    assert isinstance(conn_id, str)
    assert len(manager.connections["global"]) == 1
    assert manager.connections["global"][0]["user_id"] == "user-123"
    
    # Test registering a user connection
    queue, conn_id = await manager.register_connection("user", "user-123", "user-123")
    assert "user-123" in manager.connections["user"]
    assert len(manager.connections["user"]["user-123"]) == 1
    
    # Test registering a workspace connection
    queue, conn_id = await manager.register_connection("workspace", "workspace-123", "user-123")
    assert "workspace-123" in manager.connections["workspace"]
    assert len(manager.connections["workspace"]["workspace-123"]) == 1
    
    # Test registering a conversation connection
    queue, conn_id = await manager.register_connection("conversation", "conv-123", "user-123") 
    assert "conv-123" in manager.connections["conversation"]
    assert len(manager.connections["conversation"]["conv-123"]) == 1


@pytest.mark.asyncio
async def test_connection_manager_remove():
    """Test connection removal in the manager"""
    manager = SSEConnectionManager()
    
    # Register connections
    _, global_id = await manager.register_connection("global", "global", "user-123")
    _, user_id = await manager.register_connection("user", "user-123", "user-123")
    _, workspace_id = await manager.register_connection("workspace", "workspace-123", "user-123")
    _, conv_id = await manager.register_connection("conversation", "conv-123", "user-123")
    
    # Remove global connection
    await manager.remove_connection("global", "global", global_id)
    assert len(manager.connections["global"]) == 0
    
    # Remove user connection
    await manager.remove_connection("user", "user-123", user_id)
    assert "user-123" not in manager.connections["user"]
    
    # Remove workspace connection
    await manager.remove_connection("workspace", "workspace-123", workspace_id)
    assert "workspace-123" not in manager.connections["workspace"]
    
    # Remove conversation connection
    await manager.remove_connection("conversation", "conv-123", conv_id)
    assert "conv-123" not in manager.connections["conversation"]


@pytest.mark.asyncio
async def test_connection_manager_send_event():
    """Test sending events to connections"""
    manager = SSEConnectionManager()
    
    # Register a test connection
    queue, _ = await manager.register_connection("conversation", "conv-123", "user-123")
    
    # Send an event
    await manager.send_event("conversation", "conv-123", "test_event", {"message": "Hello"})
    
    # Check that the event was added to the queue
    event = queue.get_nowait()
    assert event["event"] == "test_event"
    assert event["data"]["message"] == "Hello"


@pytest.mark.asyncio
async def test_auth_service_token_verification():
    """Test token verification in the auth service"""
    service = SSEAuthService()
    
    # Create a test token
    user_id = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "roles": ["user"],
        "exp": datetime.now(timezone.utc).timestamp() + 3600
    }
    
    # Mock the jwt.decode function
    with patch("app.components.sse.auth.jwt.decode", return_value=payload):
        # Verify the token
        user_info = await service.authenticate_token("test-token")
        assert user_info["id"] == user_id
        assert "user" in user_info["roles"]


@pytest.mark.asyncio
async def test_auth_service_resource_access():
    """Test resource access verification in the auth service"""
    service = SSEAuthService()
    
    # Test user access - can only access own resources
    user_info = {"id": "user-123", "roles": ["user"]}
    
    # Same user id - should have access
    has_access = await service.verify_resource_access(user_info, "user", "user-123", None)
    assert has_access is True
    
    # Different user id - should not have access
    has_access = await service.verify_resource_access(user_info, "user", "user-456", None)
    assert has_access is False
    
    # Test workspace access with database
    mock_db = MagicMock()
    mock_db.execute().fetchone.return_value = ["workspace-123"]  # Return a result
    
    # Should have access
    has_access = await service.verify_resource_access(user_info, "workspace", "workspace-123", mock_db)
    assert has_access is True
    
    # Test with no result
    mock_db.execute().fetchone.return_value = None
    has_access = await service.verify_resource_access(user_info, "workspace", "workspace-456", mock_db)
    assert has_access is False


@pytest.mark.asyncio
async def test_event_subscriber_event_handling(mock_event_system):
    """Test event handling in the subscriber"""
    # Create dependencies
    manager = SSEConnectionManager()
    
    # Create the subscriber
    subscriber = SSEEventSubscriber(mock_event_system, manager)
    
    # Initialize subscriptions
    await subscriber.initialize()
    
    # Verify subscriptions were created
    assert mock_event_system.subscribe.call_count == 4  # 4 event patterns
    
    # Test conversation event handling
    queue, _ = await manager.register_connection("conversation", "conv-123", "user-123")
    
    # Create a test event
    event_payload = MagicMock()
    event_payload.data = {"conversation_id": "conv-123", "message": "Hello"}
    
    # Handle the event
    await subscriber._handle_conversation_event("message_received", event_payload)
    
    # Check the event was added to the queue
    event = queue.get_nowait()
    assert event["event"] == "message_received"
    assert event["data"]["conversation_id"] == "conv-123"
    
    # Test cleanup
    await subscriber.cleanup()
    assert mock_event_system.unsubscribe.call_count == 4  # 4 subscriptions


@pytest.mark.asyncio
async def test_sse_service_initialization(mock_event_system):
    """Test the SSE service initialization"""
    with patch("app.components.sse.get_event_system", return_value=mock_event_system):
        # Create the service
        service = SSEService()
        
        # Initialize
        await service.initialize()
        
        # Verify initialization
        assert hasattr(service, "connection_manager")
        assert hasattr(service, "auth_service")
        assert hasattr(service, "event_subscriber")
        
        # Clean up
        await service.cleanup()


@pytest.mark.asyncio
async def test_get_sse_service_singleton():
    """Test that get_sse_service returns a singleton instance"""
    # Get the service twice
    service1 = get_sse_service()
    service2 = get_sse_service()
    
    # Should be the same instance
    assert service1 is service2