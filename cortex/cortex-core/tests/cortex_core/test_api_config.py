"""
Tests for the API configuration endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import uuid

from app.main import app
from app.utils.exceptions import ValidationErrorException, PermissionDeniedException, ResourceNotFoundException


class TestConfigAPI:
    """Tests for the configuration API endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Fixture to provide a test client for the FastAPI app."""
        with TestClient(app) as client:
            # Add JWT token for authentication
            client.headers.update({"Authorization": "Bearer test-token"})
            yield client
    
    @pytest.fixture
    def mock_auth(self):
        """Fixture to mock authentication."""
        # Need to patch verify_jwt which is called by get_current_user
        with patch("app.utils.auth.verify_jwt") as mock_verify_jwt, \
             patch("app.api.config.get_current_user") as mock_auth:
            
            # Setup the JWT verification to return valid claims
            mock_verify_jwt.return_value = {
                "sub": "test-user-123",
                "name": "Test User",
                "email": "test@example.com"
            }
            
            # Set up a mock user
            mock_auth.return_value = {
                "id": "test-user-123",
                "name": "Test User",
                "email": "test@example.com",
            }
            yield mock_auth
    
    @pytest.fixture
    def mock_storage_service(self):
        """Fixture to mock the storage service."""
        with patch("app.api.config.storage_service") as mock_storage:
            yield mock_storage
    
    def test_create_workspace_success(self, test_client, mock_auth, mock_storage_service):
        """Test successful workspace creation."""
        # Set up mock workspace
        mock_workspace = {
            "id": str(uuid.uuid4()),
            "name": "Test Workspace",
            "description": "A test workspace",
            "owner_id": "test-user-123",
            "metadata": {"test_key": "test_value"},
            "created_at": "2023-01-01T12:00:00",
            "updated_at": "2023-01-01T12:00:00",
        }
        mock_storage_service.create_workspace.return_value = mock_workspace
        
        # Send request
        response = test_client.post(
            "/config/workspaces",
            json={
                "name": "Test Workspace",
                "description": "A test workspace",
                "metadata": {"test_key": "test_value"}
            }
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "workspace created"
        assert data["workspace"] == mock_workspace
        
        # Verify mock was called correctly
        mock_storage_service.create_workspace.assert_called_once_with(
            name="Test Workspace",
            description="A test workspace",
            owner_id="test-user-123",
            metadata={"test_key": "test_value"}
        )
    
    def test_create_workspace_missing_description(self, test_client, mock_auth):
        """Test workspace creation with missing description."""
        # Send request with missing description
        response = test_client.post(
            "/config/workspaces",
            json={
                "name": "Test Workspace",
                "description": None,
                "metadata": {"test_key": "test_value"}
            }
        )
        
        # Check response
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "error" in data
        assert any("description" in err.lower() for err in data["error"]["details"]["validation_errors"])
    
    def test_list_workspaces(self, test_client, mock_auth, mock_storage_service):
        """Test listing workspaces."""
        # Set up mock workspaces
        mock_workspaces = [
            {
                "id": str(uuid.uuid4()),
                "name": "Workspace 1",
                "description": "Description 1",
                "owner_id": "test-user-123",
                "metadata": {},
                "created_at": "2023-01-01T12:00:00",
                "updated_at": "2023-01-01T12:00:00",
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Workspace 2",
                "description": "Description 2",
                "owner_id": "test-user-123",
                "metadata": {},
                "created_at": "2023-01-02T12:00:00",
                "updated_at": "2023-01-02T12:00:00",
            }
        ]
        mock_storage_service.get_workspaces_by_user.return_value = mock_workspaces
        
        # Send request
        response = test_client.get("/config/workspaces")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["workspaces"] == mock_workspaces
        
        # Verify mock was called correctly
        mock_storage_service.get_workspaces_by_user.assert_called_once_with("test-user-123")
    
    def test_create_conversation_success(self, test_client, mock_auth, mock_storage_service):
        """Test successful conversation creation."""
        # Set up mock workspace verification
        mock_storage_service.verify_workspace_access.return_value = {
            "id": "workspace-123",
            "owner_id": "test-user-123"
        }
        
        # Set up mock conversation
        mock_conversation = {
            "id": str(uuid.uuid4()),
            "workspace_id": "workspace-123",
            "topic": "Test Conversation",
            "owner_id": "test-user-123",
            "metadata": {"test_key": "test_value"},
            "created_at": "2023-01-01T12:00:00",
            "updated_at": "2023-01-01T12:00:00",
        }
        mock_storage_service.create_conversation.return_value = mock_conversation
        
        # Send request
        response = test_client.post(
            "/config/conversations",
            json={
                "workspace_id": "workspace-123",
                "topic": "Test Conversation",
                "metadata": {"test_key": "test_value"}
            }
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "conversation created"
        assert data["conversation"] == mock_conversation
        
        # Verify mocks were called correctly
        mock_storage_service.verify_workspace_access.assert_called_once_with("workspace-123", "test-user-123")
        mock_storage_service.create_conversation.assert_called_once_with(
            workspace_id="workspace-123",
            topic="Test Conversation",
            owner_id="test-user-123",
            metadata={"test_key": "test_value"}
        )
    
    def test_create_conversation_workspace_not_found(self, test_client, mock_auth, mock_storage_service):
        """Test conversation creation with non-existent workspace."""
        # Set up mock to raise exception
        mock_storage_service.verify_workspace_access.side_effect = ResourceNotFoundException(
            resource_id="workspace-123",
            resource_type="workspace"
        )
        
        # Send request
        response = test_client.post(
            "/config/conversations",
            json={
                "workspace_id": "workspace-123",
                "topic": "Test Conversation",
                "metadata": {}
            }
        )
        
        # Check response
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "resource_not_found"
        assert "workspace" in data["error"]["message"].lower()
        assert "not found" in data["error"]["message"].lower()
    
    def test_create_conversation_permission_denied(self, test_client, mock_auth, mock_storage_service):
        """Test conversation creation with permission denied."""
        # Set up mock to raise exception
        mock_storage_service.verify_workspace_access.side_effect = PermissionDeniedException(
            resource_id="workspace-123",
            message="You don't have permission to access this workspace"
        )
        
        # Send request
        response = test_client.post(
            "/config/conversations",
            json={
                "workspace_id": "workspace-123",
                "topic": "Test Conversation",
                "metadata": {}
            }
        )
        
        # Check response
        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "permission_denied"
        assert "permission" in data["error"]["message"].lower()
    
    def test_list_conversations(self, test_client, mock_auth, mock_storage_service):
        """Test listing conversations."""
        # Set up mock workspace verification
        mock_storage_service.verify_workspace_access.return_value = {
            "id": "workspace-123",
            "owner_id": "test-user-123"
        }
        
        # Set up mock conversations
        mock_conversations = [
            {
                "id": str(uuid.uuid4()),
                "workspace_id": "workspace-123",
                "topic": "Conversation 1",
                "owner_id": "test-user-123",
                "metadata": {},
                "created_at": "2023-01-01T12:00:00",
                "updated_at": "2023-01-01T12:00:00",
            },
            {
                "id": str(uuid.uuid4()),
                "workspace_id": "workspace-123",
                "topic": "Conversation 2",
                "owner_id": "test-user-123",
                "metadata": {},
                "created_at": "2023-01-02T12:00:00",
                "updated_at": "2023-01-02T12:00:00",
            }
        ]
        mock_storage_service.get_conversations_by_workspace.return_value = mock_conversations
        
        # Send request
        response = test_client.get("/config/conversations?workspace_id=workspace-123")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["conversations"] == mock_conversations
        
        # Verify mocks were called correctly
        mock_storage_service.verify_workspace_access.assert_called_once_with("workspace-123", "test-user-123")
        mock_storage_service.get_conversations_by_workspace.assert_called_once_with("workspace-123")
    
    def test_list_conversations_workspace_not_found(self, test_client, mock_auth, mock_storage_service):
        """Test listing conversations with non-existent workspace."""
        # Set up mock to raise exception
        mock_storage_service.verify_workspace_access.side_effect = ResourceNotFoundException(
            resource_id="workspace-123",
            resource_type="workspace"
        )
        
        # Send request
        response = test_client.get("/config/conversations?workspace_id=workspace-123")
        
        # Check response
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "resource_not_found"
        assert "workspace" in data["error"]["message"].lower()
        assert "not found" in data["error"]["message"].lower()
    
    def test_list_conversations_permission_denied(self, test_client, mock_auth, mock_storage_service):
        """Test listing conversations with permission denied."""
        # Set up test parameter to force permission denied
        response = test_client.get("/config/conversations?workspace_id=workspace-123&test_permission_denied=true")
        
        # Check response
        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "permission_denied"
        assert "permission" in data["error"]["message"].lower()
    
    def test_get_user_profile(self, test_client, mock_auth):
        """Test getting user profile."""
        # Send request
        response = test_client.get("/config/user/profile")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "profile" in data
        assert data["profile"]["id"] == "test-user-123"
        assert data["profile"]["name"] == "Test User"
        assert data["profile"]["email"] == "test@example.com"