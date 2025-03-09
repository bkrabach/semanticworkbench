"""
Tests for the workspace service
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone

from app.services.workspace_service import WorkspaceService
from app.database.repositories.workspace_repository import WorkspaceRepository
from app.components.event_system import EventSystem
from app.models.domain.workspace import Workspace

@pytest.fixture
def mock_repository():
    """Create a mock workspace repository"""
    return MagicMock(spec=WorkspaceRepository)

@pytest.fixture
def mock_event_system():
    """Create a mock event system"""
    mock = MagicMock(spec=EventSystem)
    # Mock the async publish method
    mock.publish = AsyncMock()
    return mock

@pytest.fixture
def workspace_service(mock_repository, mock_event_system):
    """Create a workspace service with mock dependencies"""
    mock_db = MagicMock()
    return WorkspaceService(mock_db, mock_repository, mock_event_system)

@pytest.fixture
def test_workspace():
    """Create a test workspace"""
    now = datetime.now(timezone.utc)
    return Workspace(
        id="test-workspace-id",
        user_id="test-user-id",
        name="Test Workspace",
        created_at=now,
        updated_at=now,
        last_active_at=now,
        metadata={"description": "Test workspace description"},
        config={}
    )

def test_get_workspace(workspace_service, mock_repository, test_workspace):
    """Test getting a workspace by ID"""
    # Configure mock repository
    mock_repository.get_by_id.return_value = test_workspace
    
    # Call the service
    workspace = workspace_service.get_workspace("test-workspace-id")
    
    # Verify result
    assert workspace == test_workspace
    mock_repository.get_by_id.assert_called_once_with("test-workspace-id")

def test_get_user_workspaces(workspace_service, mock_repository, test_workspace):
    """Test getting all workspaces for a user"""
    # Configure mock repository
    mock_repository.get_user_workspaces.return_value = [test_workspace]
    
    # Call the service
    workspaces = workspace_service.get_user_workspaces("test-user-id")
    
    # Verify result
    assert len(workspaces) == 1
    assert workspaces[0] == test_workspace
    mock_repository.get_user_workspaces.assert_called_once_with("test-user-id", None)

@pytest.mark.asyncio
async def test_create_workspace(workspace_service, mock_repository, mock_event_system, test_workspace):
    """Test creating a workspace"""
    # Configure mock repository
    mock_repository.create_workspace.return_value = test_workspace
    
    # Call the service
    workspace = await workspace_service.create_workspace(
        user_id="test-user-id",
        name="Test Workspace",
        description="Test workspace description"
    )
    
    # Verify result
    assert workspace == test_workspace
    mock_repository.create_workspace.assert_called_once_with(
        user_id="test-user-id",
        name="Test Workspace",
        description="Test workspace description"
    )
    
    # Verify event published
    mock_event_system.publish.assert_called_once()
    event_data = mock_event_system.publish.call_args[1]
    assert event_data["event_type"] == "workspace.created"
    assert event_data["data"]["workspace_id"] == test_workspace.id

@pytest.mark.asyncio
async def test_update_workspace(workspace_service, mock_repository, mock_event_system, test_workspace):
    """Test updating a workspace"""
    # Configure mock repository
    mock_repository.update_workspace.return_value = test_workspace
    
    # Call the service
    workspace = await workspace_service.update_workspace(
        workspace_id="test-workspace-id",
        name="Updated Workspace",
        metadata={"description": "Updated description"}
    )
    
    # Verify result
    assert workspace == test_workspace
    mock_repository.update_workspace.assert_called_once_with(
        workspace_id="test-workspace-id",
        name="Updated Workspace",
        metadata={"description": "Updated description"}
    )
    
    # Verify event published
    mock_event_system.publish.assert_called_once()
    event_data = mock_event_system.publish.call_args[1]
    assert event_data["event_type"] == "workspace.updated"
    assert event_data["data"]["workspace_id"] == test_workspace.id

@pytest.mark.asyncio
async def test_delete_workspace(workspace_service, mock_repository, mock_event_system, test_workspace):
    """Test deleting a workspace"""
    # Configure mock repository
    mock_repository.get_by_id.return_value = test_workspace
    mock_repository.delete_workspace.return_value = True
    
    # Call the service
    result = await workspace_service.delete_workspace("test-workspace-id")
    
    # Verify result
    assert result is True
    mock_repository.delete_workspace.assert_called_once_with("test-workspace-id")
    
    # Verify event published
    mock_event_system.publish.assert_called_once()
    event_data = mock_event_system.publish.call_args[1]
    assert event_data["event_type"] == "workspace.deleted"
    assert event_data["data"]["workspace_id"] == test_workspace.id