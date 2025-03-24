"""
Tests for the in-memory storage service.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.core.storage_service import StorageService
from app.utils.exceptions import PermissionDeniedException, ResourceNotFoundException


class TestStorageService:
    """Tests for the StorageService class."""
    
    @pytest.fixture
    def storage_service(self):
        """Fixture to provide a fresh StorageService for each test."""
        return StorageService()
    
    @pytest.fixture
    def sample_workspace(self, storage_service):
        """Fixture to provide a sample workspace."""
        return storage_service.create_workspace(
            name="Test Workspace",
            description="A test workspace",
            owner_id="user-123",
            metadata={"test": True}
        )
    
    @pytest.fixture
    def sample_conversation(self, storage_service, sample_workspace):
        """Fixture to provide a sample conversation."""
        return storage_service.create_conversation(
            workspace_id=sample_workspace["id"],
            topic="Test Conversation",
            owner_id="user-123",
            metadata={"test": True}
        )
    
    def test_create_workspace(self, storage_service):
        """Test creating a workspace."""
        workspace = storage_service.create_workspace(
            name="Test Workspace",
            description="A test workspace",
            owner_id="user-123",
            metadata={"test": True}
        )
        
        # Check that the workspace has all the expected fields
        assert isinstance(workspace["id"], str)
        assert workspace["name"] == "Test Workspace"
        assert workspace["description"] == "A test workspace"
        assert workspace["owner_id"] == "user-123"
        assert workspace["metadata"] == {"test": True}
        assert "created_at" in workspace
        assert "updated_at" in workspace
        
        # Check that the workspace is stored in the service
        assert workspace["id"] in storage_service._workspaces
        assert storage_service._workspaces[workspace["id"]] == workspace
    
    def test_create_workspace_defaults(self, storage_service):
        """Test creating a workspace with default values."""
        workspace = storage_service.create_workspace(
            name="Test Workspace",
            description="",
            owner_id="user-123"
        )
        
        # Check default values
        assert workspace["description"] == ""
        assert workspace["metadata"] == {}
    
    def test_get_workspace(self, storage_service, sample_workspace):
        """Test retrieving a workspace by ID."""
        # Get the workspace
        workspace = storage_service.get_workspace(sample_workspace["id"])
        
        # Check that it's the same one we created
        assert workspace == sample_workspace
        
        # Check that a non-existent workspace returns None
        assert storage_service.get_workspace("non-existent-id") is None
    
    def test_get_workspaces_by_user(self, storage_service):
        """Test retrieving workspaces owned by a user."""
        # Create multiple workspaces for different users
        workspace1 = storage_service.create_workspace("Workspace 1", "Description 1", "user-1")
        workspace2 = storage_service.create_workspace("Workspace 2", "Description 2", "user-1")
        workspace3 = storage_service.create_workspace("Workspace 3", "Description 3", "user-2")
        
        # Get workspaces for user-1
        user1_workspaces = storage_service.get_workspaces_by_user("user-1")
        
        # Check that we got the right workspaces
        assert len(user1_workspaces) == 2
        assert workspace1 in user1_workspaces
        assert workspace2 in user1_workspaces
        assert workspace3 not in user1_workspaces
        
        # Get workspaces for user-2
        user2_workspaces = storage_service.get_workspaces_by_user("user-2")
        
        # Check that we got the right workspaces
        assert len(user2_workspaces) == 1
        assert workspace3 in user2_workspaces
        
        # Get workspaces for non-existent user
        assert storage_service.get_workspaces_by_user("non-existent-user") == []
    
    def test_verify_workspace_access_success(self, storage_service, sample_workspace):
        """Test verifying access to a workspace when access is allowed."""
        # Verify access for the owner
        workspace = storage_service.verify_workspace_access(sample_workspace["id"], "user-123")
        
        # Check that we got the right workspace
        assert workspace == sample_workspace
    
    def test_verify_workspace_access_not_found(self, storage_service):
        """Test verifying access to a non-existent workspace."""
        # Verify access for a non-existent workspace
        with pytest.raises(ResourceNotFoundException) as excinfo:
            storage_service.verify_workspace_access("non-existent-id", "user-123")
        
        # Check that the exception was raised
        assert "not found" in str(excinfo.value)
        assert "workspace" in str(excinfo.value).lower()
    
    def test_verify_workspace_access_permission_denied(self, storage_service, sample_workspace):
        """Test verifying access to a workspace when access is denied."""
        # Verify access for a different user
        with pytest.raises(PermissionDeniedException) as excinfo:
            storage_service.verify_workspace_access(sample_workspace["id"], "other-user")
        
        # Check the exception details
        assert "permission" in str(excinfo.value).lower()
        assert "don't have permission" in str(excinfo.value).lower()
    
    def test_create_conversation(self, storage_service, sample_workspace):
        """Test creating a conversation."""
        conversation = storage_service.create_conversation(
            workspace_id=sample_workspace["id"],
            topic="Test Conversation",
            owner_id="user-123",
            metadata={"test": True}
        )
        
        # Check that the conversation has all the expected fields
        assert isinstance(conversation["id"], str)
        assert conversation["workspace_id"] == sample_workspace["id"]
        assert conversation["topic"] == "Test Conversation"
        assert conversation["owner_id"] == "user-123"
        assert conversation["metadata"] == {"test": True}
        assert "created_at" in conversation
        assert "updated_at" in conversation
        
        # Check that the conversation is stored in the service
        assert conversation["id"] in storage_service._conversations
        assert storage_service._conversations[conversation["id"]] == conversation
    
    def test_create_conversation_defaults(self, storage_service, sample_workspace):
        """Test creating a conversation with default values."""
        conversation = storage_service.create_conversation(
            workspace_id=sample_workspace["id"],
            topic="",
            owner_id="user-123"
        )
        
        # Check default values
        assert conversation["topic"] == "New Conversation"
        assert conversation["metadata"] == {}
    
    def test_get_conversation(self, storage_service, sample_conversation):
        """Test retrieving a conversation by ID."""
        # Get the conversation
        conversation = storage_service.get_conversation(sample_conversation["id"])
        
        # Check that it's the same one we created
        assert conversation == sample_conversation
        
        # Check that a non-existent conversation returns None
        assert storage_service.get_conversation("non-existent-id") is None
    
    def test_get_conversations_by_workspace(self, storage_service, sample_workspace):
        """Test retrieving conversations in a workspace."""
        # Create multiple conversations in different workspaces
        workspace2 = storage_service.create_workspace("Workspace 2", "Description 2", "user-123")
        
        conversation1 = storage_service.create_conversation(sample_workspace["id"], "Conversation 1", "user-123")
        conversation2 = storage_service.create_conversation(sample_workspace["id"], "Conversation 2", "user-123")
        conversation3 = storage_service.create_conversation(workspace2["id"], "Conversation 3", "user-123")
        
        # Get conversations for the first workspace
        workspace1_conversations = storage_service.get_conversations_by_workspace(sample_workspace["id"])
        
        # Check that we got the right conversations
        assert len(workspace1_conversations) == 2
        assert conversation1 in workspace1_conversations
        assert conversation2 in workspace1_conversations
        assert conversation3 not in workspace1_conversations
        
        # Get conversations for the second workspace
        workspace2_conversations = storage_service.get_conversations_by_workspace(workspace2["id"])
        
        # Check that we got the right conversations
        assert len(workspace2_conversations) == 1
        assert conversation3 in workspace2_conversations
        
        # Get conversations for non-existent workspace
        assert storage_service.get_conversations_by_workspace("non-existent-id") == []
    
    def test_verify_conversation_access_success(self, storage_service, sample_conversation):
        """Test verifying access to a conversation when access is allowed."""
        # Verify access for the owner
        conversation = storage_service.verify_conversation_access(sample_conversation["id"], "user-123")
        
        # Check that we got the right conversation
        assert conversation == sample_conversation
    
    def test_verify_conversation_access_not_found(self, storage_service):
        """Test verifying access to a non-existent conversation."""
        # Verify access for a non-existent conversation
        with pytest.raises(ResourceNotFoundException) as excinfo:
            storage_service.verify_conversation_access("non-existent-id", "user-123")
        
        # Check that the exception was raised
        assert "not found" in str(excinfo.value)
        assert "conversation" in str(excinfo.value).lower()
    
    def test_verify_conversation_access_permission_denied(self, storage_service, sample_conversation):
        """Test verifying access to a conversation when access is denied."""
        # Verify access for a different user
        with pytest.raises(PermissionDeniedException) as excinfo:
            storage_service.verify_conversation_access(sample_conversation["id"], "other-user")
        
        # Check the exception details
        assert "permission" in str(excinfo.value).lower()
        assert "don't have permission" in str(excinfo.value).lower()
    
    def test_datetime_fields(self, storage_service):
        """Test that datetime fields are properly formatted."""
        with patch("app.core.storage_service.datetime") as mock_datetime:
            # Set a fixed datetime for testing
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            # Create a workspace
            workspace = storage_service.create_workspace("Test", "Description", "user-123")
            
            # Check datetime fields
            assert workspace["created_at"] == mock_now.isoformat()
            assert workspace["updated_at"] == mock_now.isoformat()
            
            # Create a conversation
            mock_now = mock_now + timedelta(minutes=5)  # Advance time
            mock_datetime.now.return_value = mock_now
            
            conversation = storage_service.create_conversation(workspace["id"], "Test", "user-123")
            
            # Check datetime fields
            assert conversation["created_at"] == mock_now.isoformat()
            assert conversation["updated_at"] == mock_now.isoformat()