"""
Tests for the user repository
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import json

from app.database.repositories.user_repository import UserRepository
from app.models.domain.user import User

@pytest.fixture
def mock_session():
    """Create a mock database session"""
    mock = MagicMock()
    return mock

@pytest.fixture
def user_repository(mock_session):
    """Create a user repository with mock session"""
    return UserRepository(mock_session)

def test_create_user(user_repository, mock_session):
    """Test creating a user with the repository"""
    # Create a timestamp for consistency
    now = datetime.now(timezone.utc)
    
    # Setup the mock for the db session
    mock_add = MagicMock()
    mock_commit = MagicMock()
    mock_refresh = MagicMock()
    
    mock_session.add = mock_add
    mock_session.commit = mock_commit
    mock_session.refresh = mock_refresh
    
    # Create a mock for the UserDB model
    with patch('app.database.repositories.user_repository.UserDB') as MockUserDB:
        # Configure the mock db model instance
        mock_user_db = MagicMock()
        mock_user_db.id = "test-id"
        mock_user_db.email = "test@example.com"
        mock_user_db.name = "Test User"
        mock_user_db.password_hash = "test-hash"
        mock_user_db.created_at_utc = now
        mock_user_db.updated_at_utc = now
        mock_user_db.last_login_at_utc = None
        mock_user_db.roles = "[]"
        
        # Set up the UserDB constructor to return our mock instance
        MockUserDB.return_value = mock_user_db
        
        # Call the repository method
        result = user_repository.create(
            email="test@example.com",
            name="Test User",
            password_hash="test-hash"
        )
        
        # Verify UserDB constructor was called with expected params
        MockUserDB.assert_called_once()
        
        # In the DB model, there's no meta_data field and roles is a relationship
        args, kwargs = MockUserDB.call_args
        assert kwargs['email'] == "test@example.com"
        assert kwargs['name'] == "Test User"
        assert kwargs['password_hash'] == "test-hash"
        assert 'roles' not in kwargs  # roles is a relationship that should not be set directly
        assert 'meta_data' not in kwargs  # Make sure meta_data isn't being passed
        
        # Verify the session methods were called
        mock_add.assert_called_once_with(mock_user_db)
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(mock_user_db)
        
        # Verify the result
        assert isinstance(result, User)
        assert result.id == "test-id"
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        assert result.password_hash == "test-hash"
        assert result.metadata == {}  # Metadata should be empty dict