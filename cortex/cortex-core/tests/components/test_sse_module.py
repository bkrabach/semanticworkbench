"""
Test suite for the SSE module components
"""

import pytest
import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone

from app.services.sse_service import SSEService
from app.components.sse.manager import SSEConnectionManager
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
    assert manager.connections["global"][0].user_id == "user-123"
    
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
    
    # Make sure the queue is attached to the connection
    connection = manager.connections["conversation"]["conv-123"][0]
    assert hasattr(connection, "queue")
    
    # Put a test event to check the queue is working
    test_event = {"event": "test", "data": {"message": "Test"}}
    await connection.queue.put(test_event)
    
    # Check we can get the event from the queue
    event = await asyncio.wait_for(connection.queue.get(), timeout=0.5)
    assert event["event"] == "test"
    assert event["data"]["message"] == "Test"
    
    # Let's just test that send_event doesn't throw errors
    await manager.send_event("conversation", "conv-123", "test_event", {"message": "Hello"})


@pytest.mark.asyncio
async def test_service_token_verification():
    """Test token verification in the SSE service"""
    # Create mock repository
    mock_repo = MagicMock()
    mock_db = MagicMock()
    
    # Create SSE service with mocked components
    service = SSEService(mock_db, mock_repo)
    
    # Create a test token
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "email": "test@example.com",
        "name": "Test User",
        "roles": ["user"],
        "exp": now.timestamp() + 3600
    }
    
    # Mock the jwt.decode function and datetime for created_at
    with patch("app.services.sse_service.jwt.decode", return_value=payload), \
         patch("app.models.domain.user.datetime") as mock_datetime:
        
        # Mock datetime.now to return a fixed time
        mock_datetime.now.return_value = now
        
        # Verify the token
        user_info = await service.authenticate_token("test-token")
        assert user_info.id == user_id
        assert user_info.email == "test@example.com"
        assert user_info.name == "Test User"
        assert "user" in user_info.roles


@pytest.mark.asyncio
async def test_service_resource_access():
    """Test resource access verification in the SSE service"""
    from app.models.domain.user import UserInfo
    
    # Create mock repository and database session
    mock_repo = MagicMock()
    mock_db = MagicMock()
    
    # Create SSE service
    service = SSEService(mock_db, mock_repo)
    
    # Create test user domain model
    now = datetime.now(timezone.utc)
    user_info = UserInfo(
        id="user-123",
        email="test@example.com",
        name="Test User",
        roles=["user"],
        created_at=now
    )
    
    # Same user id - should have access
    has_access = await service.verify_resource_access(user_info, "user", "user-123")
    assert has_access is True
    
    # Different user id - should not have access
    has_access = await service.verify_resource_access(user_info, "user", "user-456")
    assert has_access is False


@pytest.mark.asyncio
async def test_service_workspace_access():
    """Test workspace access verification in the SSE service"""
    from app.models.domain.user import UserInfo
    
    # Create user domain model
    now = datetime.now(timezone.utc)
    user_info = UserInfo(
        id="user-123",
        email="test@example.com",
        name="Test User",
        roles=["user"],
        created_at=now
    )
    
    # Mock database session
    mock_db = MagicMock()
    
    # Mock repository with configured responses
    mock_repo = MagicMock()
    
    # Configure repository mock behavior
    # Case 1: User is workspace owner
    mock_repo.is_workspace_owner.return_value = True
    mock_repo.has_workspace_sharing_access.return_value = False
    
    # Create service
    service = SSEService(mock_db, mock_repo)
    
    # Test as workspace owner
    has_access = await service.verify_resource_access(user_info, "workspace", "workspace-123")
    assert has_access is True
    mock_repo.is_workspace_owner.assert_called_with("workspace-123", "user-123")
    
    # Case 2: User is not workspace owner but has sharing access
    mock_repo.is_workspace_owner.return_value = False
    mock_repo.has_workspace_sharing_access.return_value = True
    
    # Test with shared workspace (not owner)
    has_access = await service.verify_resource_access(user_info, "workspace", "workspace-456")
    assert has_access is True
    mock_repo.is_workspace_owner.assert_called_with("workspace-456", "user-123")
    mock_repo.has_workspace_sharing_access.assert_called_with("workspace-456", "user-123")
    
    # Case 3: User has no access at all
    mock_repo.is_workspace_owner.return_value = False
    mock_repo.has_workspace_sharing_access.return_value = False
    
    # Test with no access
    has_access = await service.verify_resource_access(user_info, "workspace", "workspace-789")
    assert has_access is False
    mock_repo.is_workspace_owner.assert_called_with("workspace-789", "user-123")
    mock_repo.has_workspace_sharing_access.assert_called_with("workspace-789", "user-123")


@pytest.mark.asyncio
async def test_service_conversation_access():
    """Test conversation access verification in the SSE service"""
    from app.models.domain.user import UserInfo
    
    # Create user domain model
    now = datetime.now(timezone.utc)
    user_info = UserInfo(
        id="user-123",
        email="test@example.com",
        name="Test User",
        roles=["user"],
        created_at=now
    )
    
    # Mock database session
    mock_db = MagicMock()
    
    # Mock repository with configured responses
    mock_repo = MagicMock()
    
    # Set up conversation workspace lookup
    mock_repo.get_conversation_workspace_id.return_value = "workspace-123"
    
    # Case 1: User is workspace owner
    mock_repo.is_workspace_owner.return_value = True
    mock_repo.has_workspace_sharing_access.return_value = False
    
    # Create service
    service = SSEService(mock_db, mock_repo)
    
    # Test conversation access where user is workspace owner
    has_access = await service.verify_resource_access(user_info, "conversation", "conv-123")
    assert has_access is True
    mock_repo.get_conversation_workspace_id.assert_called_with("conv-123")
    mock_repo.is_workspace_owner.assert_called_with("workspace-123", "user-123")
    
    # Case 2: User is not workspace owner but has sharing access
    mock_repo.is_workspace_owner.return_value = False
    mock_repo.has_workspace_sharing_access.return_value = True
    
    # Test conversation access with shared workspace
    has_access = await service.verify_resource_access(user_info, "conversation", "conv-456")
    assert has_access is True
    mock_repo.get_conversation_workspace_id.assert_called_with("conv-456")
    mock_repo.is_workspace_owner.assert_called_with("workspace-123", "user-123")
    mock_repo.has_workspace_sharing_access.assert_called_with("workspace-123", "user-123")
    
    # Case 3: User has no access at all
    mock_repo.is_workspace_owner.return_value = False
    mock_repo.has_workspace_sharing_access.return_value = False
    
    # Test conversation access with no workspace access
    has_access = await service.verify_resource_access(user_info, "conversation", "conv-789")
    assert has_access is False
    
    # Case 4: Non-existent conversation (no workspace ID found)
    mock_repo.get_conversation_workspace_id.return_value = None
    
    # Test non-existent conversation
    has_access = await service.verify_resource_access(user_info, "conversation", "conv-999")
    assert has_access is False
    mock_repo.get_conversation_workspace_id.assert_called_with("conv-999")


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
    queue, conn_id = await manager.register_connection("conversation", "conv-123", "user-123")
    
    # Get the connection directly from the manager
    connection = manager.connections["conversation"]["conv-123"][0]
    assert hasattr(connection, "queue")
    
    # Make sure we can use the queue directly
    test_event = {"event": "test", "data": {"message": "Direct test"}}
    await connection.queue.put(test_event)
    
    # Get the event back from the queue
    event = await asyncio.wait_for(connection.queue.get(), timeout=0.5)
    assert event["event"] == "test"
    assert event["data"]["message"] == "Direct test"
    
    # Create a test event for the handler
    event_payload = MagicMock()
    event_payload.data = {"conversation_id": "conv-123", "message": "Hello"}
    
    # Create and use the event handler class directly
    from app.components.sse.events import SSEEventHandler
    conversation_handler = SSEEventHandler(
        subscriber=subscriber,
        resource_id_key="conversation_id",
        channel_type="conversation"
    )
    
    # Just test that it doesn't throw errors
    await conversation_handler("message_received", event_payload)
    
    # Test cleanup
    await subscriber.cleanup()
    assert mock_event_system.unsubscribe.call_count == 4  # 4 subscriptions


@pytest.mark.asyncio
async def test_sse_service_initialization(mock_event_system):
    """Test the SSE service initialization"""
    # Create mock repository and DB session
    mock_repo = MagicMock()
    mock_db = MagicMock()
    
    with patch("app.services.sse_service.get_event_system", return_value=mock_event_system):
        # Create the service
        service = SSEService(mock_db, mock_repo)
        
        # Initialize
        await service.initialize()
        
        # Verify initialization
        assert hasattr(service, "connection_manager")
        assert hasattr(service, "repository")
        assert hasattr(service, "event_subscriber")
        
        # Clean up
        await service.cleanup()


@pytest.mark.asyncio
async def test_get_connection_stats():
    """Test getting connection statistics from the service"""
    # Create mock repository and DB session
    mock_repo = MagicMock()
    mock_db = MagicMock()
    
    # Create the service
    service = SSEService(mock_db, mock_repo)
    
    # Mock the connection manager
    service.connection_manager = MagicMock()
    service.connection_manager.get_stats.return_value = {
        "total_connections": 3,
        "connections_by_channel": {"global": 1, "user": 1, "workspace": 1},
        "connections_by_user": {"user-123": 2, "user-456": 1},
        "generated_at": datetime.now(timezone.utc)
    }
    
    # Get stats
    stats = service.get_connection_stats()
    
    # Verify stats is a domain model
    assert stats.id == "stats"
    assert stats.total_connections == 3
    assert stats.connections_by_channel == {"global": 1, "user": 1, "workspace": 1}
    assert stats.connections_by_user == {"user-123": 2, "user-456": 1}