"""
Tests for the user service
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.services.user_service import UserService
from app.database.repositories.user_repository import UserRepository
from app.components.event_system import EventSystem
from app.models.domain.user import User

@pytest.fixture
def mock_repository():
    """Create a mock user repository"""
    return MagicMock(spec=UserRepository)

@pytest.fixture
def mock_event_system():
    """Create a mock event system"""
    return MagicMock(spec=EventSystem)

@pytest.fixture
def user_service(mock_repository, mock_event_system):
    """Create a user service with mock dependencies"""
    mock_db = MagicMock()
    return UserService(mock_db, mock_repository, mock_event_system)

@pytest.fixture
def test_user():
    """Create a test user"""
    now = datetime.now(timezone.utc)
    return User(
        id="test-id",
        email="test@example.com",
        name="Test User",
        created_at=now,
        updated_at=now,
        last_login_at=None,
        roles=[],
        metadata={},
        password_hash="test-hash"
    )

def test_get_user(user_service, mock_repository, test_user):
    """Test getting a user by ID"""
    # Configure mock repository
    mock_repository.get_by_id.return_value = test_user
    
    # Call the service
    user = user_service.get_user("test-id")
    
    # Verify result
    assert user == test_user
    mock_repository.get_by_id.assert_called_once_with("test-id")

def test_get_user_by_email(user_service, mock_repository, test_user):
    """Test getting a user by email"""
    # Configure mock repository
    mock_repository.get_by_email.return_value = test_user
    
    # Call the service
    user = user_service.get_user_by_email("test@example.com")
    
    # Verify result
    assert user == test_user
    mock_repository.get_by_email.assert_called_once_with("test@example.com")

def test_create_user(user_service, mock_repository, mock_event_system, test_user):
    """Test creating a user"""
    # Configure mock repository
    mock_repository.create.return_value = test_user
    
    # Call the service
    user = user_service.create_user(
        email="test@example.com",
        name="Test User",
        password_hash="test-hash"
    )
    
    # Verify result
    assert user == test_user
    mock_repository.create.assert_called_once_with(
        email="test@example.com",
        name="Test User",
        password_hash="test-hash"
    )
    
    # Verify event published
    mock_event_system.publish.assert_called_once()
    event_data = mock_event_system.publish.call_args[1]
    assert event_data["event_type"] == "user.created"
    assert event_data["data"]["user_id"] == test_user.id

def test_update_last_login(user_service, mock_repository, mock_event_system, test_user):
    """Test updating user's last login time"""
    # Create a user with login time
    user_with_login = test_user.model_copy(deep=True)
    user_with_login.last_login_at = datetime.now(timezone.utc)
    
    # Configure mock repository
    mock_repository.update_last_login.return_value = user_with_login
    
    # Call the service
    user = user_service.update_last_login("test-id")
    
    # Verify result
    assert user == user_with_login
    mock_repository.update_last_login.assert_called_once_with("test-id")
    
    # Verify event published
    mock_event_system.publish.assert_called_once()
    event_data = mock_event_system.publish.call_args[1]
    assert event_data["event_type"] == "user.login"
    assert event_data["data"]["user_id"] == test_user.id