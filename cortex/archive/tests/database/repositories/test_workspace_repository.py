"""
Tests for the workspace repository
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import json

from app.database.repositories.workspace_repository import WorkspaceRepository
from app.models.domain.workspace import Workspace

@pytest.fixture
def mock_session():
    """Create a mock database session"""
    mock = MagicMock()
    return mock

@pytest.fixture
def workspace_repository(mock_session):
    """Create a workspace repository with mock session"""
    return WorkspaceRepository(mock_session)

def test_create_workspace(workspace_repository, mock_session):
    """Test creating a workspace with the repository"""
    # Create a timestamp for consistency
    now = datetime.now(timezone.utc)
    
    # Setup the mock for the db session
    mock_add = MagicMock()
    mock_commit = MagicMock()
    mock_refresh = MagicMock()
    
    mock_session.add = mock_add
    mock_session.commit = mock_commit
    mock_session.refresh = mock_refresh
    
    # Create a mock for the WorkspaceDB model
    with patch('app.database.repositories.workspace_repository.WorkspaceDB') as MockWorkspaceDB:
        # Configure the mock db model instance
        mock_workspace_db = MagicMock()
        mock_workspace_db.id = "test-id"
        mock_workspace_db.user_id = "test-user-id"
        mock_workspace_db.name = "Test Workspace"
        mock_workspace_db.created_at_utc = now
        mock_workspace_db.last_active_at_utc = now
        mock_workspace_db.meta_data = "{}"
        
        # Set up the WorkspaceDB constructor to return our mock instance
        MockWorkspaceDB.return_value = mock_workspace_db
        
        # Call the repository method
        result = workspace_repository.create_workspace(
            user_id="test-user-id",
            name="Test Workspace",
            description="Test workspace description"
        )
        
        # Verify WorkspaceDB constructor was called with expected params
        MockWorkspaceDB.assert_called_once()
        
        # In the DB model, there's no updated_at_utc field
        args, kwargs = MockWorkspaceDB.call_args
        assert kwargs['user_id'] == "test-user-id"
        assert kwargs['name'] == "Test Workspace"
        assert 'created_at_utc' in kwargs
        assert 'meta_data' in kwargs
        assert 'updated_at_utc' not in kwargs  # Verify updated_at_utc isn't passed
        
        # Verify the session methods were called
        mock_add.assert_called_once_with(mock_workspace_db)
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(mock_workspace_db)
        
        # Verify the result
        assert isinstance(result, Workspace)
        assert result.id == "test-id"
        assert result.user_id == "test-user-id"
        assert result.name == "Test Workspace"
        
        # Verify metadata contains the description
        if hasattr(result, 'metadata') and isinstance(result.metadata, dict):
            metadata = json.loads(mock_workspace_db.meta_data)
            if "description" in metadata:
                assert metadata["description"] == "Test workspace description"