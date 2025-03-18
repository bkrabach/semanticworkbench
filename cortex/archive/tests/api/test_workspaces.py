"""
Tests for the workspaces API endpoints.

These tests verify the functionality of the workspace-related API endpoints
using the domain-driven architecture.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.models.domain.workspace import Workspace
from app.models.domain.user import User
from app.services.workspace_service import WorkspaceService
from app.api.workspaces import get_service
from app.api.auth import get_current_user


# Test fixtures
@pytest.fixture
def mock_workspace_service():
    """Create a mock workspace service"""
    service = MagicMock(spec=WorkspaceService)
    
    # Setup sample workspaces
    sample_workspaces = [
        Workspace(
            id="ws1",
            user_id="user1",
            name="Workspace 1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_active_at=datetime.now(timezone.utc),
            metadata={"description": "Test workspace 1"},
            config={}
        ),
        Workspace(
            id="ws2",
            user_id="user1",
            name="Workspace 2",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_active_at=datetime.now(timezone.utc),
            metadata={"description": "Test workspace 2"},
            config={}
        )
    ]
    
    # Setup method returns for the service mock
    service.get_user_workspaces.return_value = sample_workspaces
    service.get_workspace.return_value = sample_workspaces[0]
    
    # Use AsyncMock for async methods
    service.create_workspace = AsyncMock(return_value=sample_workspaces[0])
    service.update_workspace = AsyncMock(return_value=sample_workspaces[0])
    service.delete_workspace = AsyncMock(return_value=True)
    
    return service


@pytest.fixture
def mock_user():
    """Create a mock user"""
    return User(
        id="user1",
        email="user@example.com",
        name="Test User",
        created_at=datetime.now(timezone.utc),
        password_hash="test_password_hash"
    )


@pytest.fixture
def client_with_overrides(mock_workspace_service, mock_user):
    """Create a test client with dependency overrides"""
    # Override dependencies
    app.dependency_overrides[get_service] = lambda: mock_workspace_service
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    # Create client
    client = TestClient(app)
    
    # Yield client
    yield client
    
    # Clean up overrides
    app.dependency_overrides = {}


# Tests
def test_list_workspaces(client_with_overrides, mock_workspace_service):
    """Test listing workspaces"""
    # Call API
    response = client_with_overrides.get("/workspaces")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "workspaces" in data
    assert len(data["workspaces"]) == 2
    assert data["workspaces"][0]["id"] == "ws1"
    assert data["workspaces"][1]["id"] == "ws2"
    
    # Verify service was called correctly
    mock_workspace_service.get_user_workspaces.assert_called_once_with("user1")


def test_get_workspace(client_with_overrides, mock_workspace_service):
    """Test getting a single workspace"""
    # Call API
    response = client_with_overrides.get("/workspaces/ws1")
    
    # Verify response
    assert response.status_code == 200
    workspace = response.json()
    assert workspace["id"] == "ws1"
    assert workspace["name"] == "Workspace 1"
    
    # Verify service was called correctly
    mock_workspace_service.get_workspace.assert_called_once_with("ws1")


def test_create_workspace(monkeypatch, client_with_overrides, mock_workspace_service):
    """Test creating a workspace"""
    # Mock the SSE service
    mock_sse_service = MagicMock()
    mock_sse_service.connection_manager = MagicMock()
    
    # Mock the get_sse_service function
    monkeypatch.setattr("app.api.workspaces.get_sse_service", lambda: mock_sse_service)
    
    # Call API
    response = client_with_overrides.post(
        "/workspaces",
        json={"name": "New Workspace", "description": "Test description"}
    )
    
    # Verify response
    assert response.status_code == 200
    workspace = response.json()
    assert workspace["id"] == "ws1"  # From our mock
    assert workspace["name"] == "Workspace 1"  # From our mock
    
    # Verify service was called correctly
    mock_workspace_service.create_workspace.assert_called_once_with(
        user_id="user1",
        name="New Workspace",
        description="Test description"
    )


def test_update_workspace(client_with_overrides, mock_workspace_service):
    """Test updating a workspace"""
    # Call API
    response = client_with_overrides.put(
        "/workspaces/ws1",
        json={"name": "Updated Workspace", "metadata": {"description": "Updated description"}}
    )
    
    # Verify response
    assert response.status_code == 200
    workspace = response.json()
    assert workspace["id"] == "ws1"
    
    # Verify service was called correctly
    mock_workspace_service.update_workspace.assert_called_once_with(
        workspace_id="ws1",
        name="Updated Workspace",
        metadata={"description": "Updated description"}
    )


def test_delete_workspace(client_with_overrides, mock_workspace_service):
    """Test deleting a workspace"""
    # Call API
    response = client_with_overrides.delete("/workspaces/ws1")
    
    # Verify response
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    
    # Verify service was called correctly
    mock_workspace_service.delete_workspace.assert_called_once_with("ws1")


def test_workspace_not_found(client_with_overrides, mock_workspace_service):
    """Test workspace not found scenario"""
    # Setup mock
    mock_workspace_service.get_workspace.return_value = None
    
    # Call API
    response = client_with_overrides.get("/workspaces/non-existent")
    
    # Verify response
    assert response.status_code == 404
    assert response.json()["detail"] == "Workspace not found"