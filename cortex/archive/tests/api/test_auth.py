"""
Test suite for the authentication API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone
from jose import jwt
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.main import app
from app.api.auth import get_current_user, get_user_service_with_events
from app.components.tokens import TokenData, generate_jwt_token
from app.components.security_manager import SecurityManager
from app.database.models import User, ApiKey
from app.database.connection import get_db
from app.database.repositories.user_repository import UserRepository, get_user_repository
from app.database.repositories.workspace_repository import get_workspace_repository
from app.services.user_service import UserService
from app.models.domain.user import User as UserDomain
from app.models.domain.workspace import Workspace as WorkspaceDomain
from app.database.repositories.workspace_repository import WorkspaceRepository
from app.components.event_system import EventSystem

# Test utilities for creating properly formatted test data
def create_test_user_domain(
    user_id="test-user-id",
    email="test@example.com",
    name="Test User",
    password_hash="hashed_password"
) -> UserDomain:
    """Create a test user domain model with valid data"""
    return UserDomain(
        id=user_id,
        email=email,
        name=name,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_login_at=None,
        roles=[],
        password_hash=password_hash,
        metadata={}
    )

def create_test_workspace_domain(
    workspace_id="test-workspace-id",
    user_id="test-user-id",
    name="Test Workspace"
) -> WorkspaceDomain:
    """Create a test workspace domain model with valid data"""
    return WorkspaceDomain(
        id=workspace_id,
        user_id=user_id,
        name=name,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
        metadata={},
        config={}
    )


@pytest.fixture
def test_client():
    """Create a FastAPI test client"""
    return TestClient(app)

@pytest.fixture
def client_with_db_override(mock_db):
    """Create a test client with DB dependency override"""
    # Override the database dependency
    app.dependency_overrides[get_db] = lambda: mock_db

    # Create a client with the override
    client = TestClient(app)

    yield client

    # Clean up after test
    app.dependency_overrides = {}

@pytest.fixture
def client_with_auth_override(mock_db, test_user):
    """Create a test client with DB and auth dependency overrides"""
    # Override the database dependency
    app.dependency_overrides[get_db] = lambda: mock_db
    # Override the auth dependency
    app.dependency_overrides[get_current_user] = lambda: test_user

    # Create a client with these overrides
    client = TestClient(app)

    yield client

    # Clean up after test
    app.dependency_overrides = {}


@pytest.fixture
def mock_db():
    """Create a mock DB session"""
    mock = MagicMock(spec=Session)

    # Create a mock query builder
    query_builder = MagicMock()
    mock.query.return_value = query_builder
    query_builder.filter.return_value = query_builder

    return mock

# No longer using fixture as we need more control in individual tests


@pytest.fixture
def test_user():
    """Create a test user"""
    import hashlib

    user = User(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
        password_hash=hashlib.sha256("password".encode()).hexdigest(),
        created_at_utc=datetime.now(timezone.utc),
        updated_at_utc=datetime.now(timezone.utc)
    )
    return user


@pytest.fixture
def test_token(test_user):
    """Create a valid JWT token for the test user"""
    token_data = TokenData(user_id=test_user.id)
    token = generate_jwt_token(token_data, timedelta(hours=1))
    return token


def test_login_success(client_with_db_override, mock_db):
    """Test successful login with password"""
    import hashlib
    
    # Use our utility function to create a proper domain model
    password = "password"
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Create a domain user with the correct password hash
    domain_user = create_test_user_domain(
        password_hash=password_hash
    )
    
    # Set up mocked repository and service using dependency injection
    mock_user_repo = MagicMock(spec=UserRepository)
    mock_user_repo.get_by_email.return_value = domain_user
    mock_user_repo.update_last_login.return_value = domain_user
    
    mock_event_system = MagicMock(spec=EventSystem)
    mock_event_system.publish = AsyncMock()  # For async event publishing
    
    mock_user_service = UserService(mock_db, mock_user_repo, mock_event_system)
    
    # Configure mock workspace repository
    mock_workspace_repo = MagicMock(spec=WorkspaceRepository)
    mock_workspace_repo.get_user_workspaces.return_value = [
        create_test_workspace_domain(user_id=domain_user.id)
    ]
    
    # Set up dependency overrides - this is the recommended approach in DEVELOPMENT.md
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo
    app.dependency_overrides[get_user_service_with_events] = lambda: mock_user_service
    
    # Use a try/finally block to ensure overrides are cleaned up
    try:
        with patch("app.api.auth.get_user_service_with_events", return_value=mock_user_service), \
             patch("app.api.auth.get_workspace_repository", return_value=mock_workspace_repo):
            
            # Make login request using the client with DB override
            response = client_with_db_override.post(
                "/auth/login",
                json={
                    "email": "test@example.com",
                    "password": password
                }
            )

        # Verify the response
        assert response.status_code == 200
        data = response.json()

        assert data["access_token"] is not None
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == domain_user.email
        
        # Verify service calls
        mock_user_repo.get_by_email.assert_called_once_with("test@example.com")
        mock_user_repo.update_last_login.assert_called_once_with(domain_user.id)
        
    finally:
        # Clean up overrides - critical for test isolation
        app.dependency_overrides.clear()


def test_login_invalid_password(client_with_db_override, mock_db):
    """Test login with invalid password"""
    import hashlib
    
    # Create a domain user with a specific password hash
    correct_password = "password"
    password_hash = hashlib.sha256(correct_password.encode()).hexdigest()
    
    domain_user = create_test_user_domain(
        password_hash=password_hash
    )
    
    # Set up mocked repository and service
    mock_user_repo = MagicMock(spec=UserRepository)
    mock_user_repo.get_by_email.return_value = domain_user
    
    mock_event_system = MagicMock(spec=EventSystem)
    
    mock_user_service = UserService(mock_db, mock_user_repo, mock_event_system)
    
    # Configure mock workspace repository
    mock_workspace_repo = MagicMock(spec=WorkspaceRepository)
    
    # Set up dependency overrides
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo
    app.dependency_overrides[get_user_service_with_events] = lambda: mock_user_service
    
    try:
        with patch("app.api.auth.get_workspace_repository", return_value=mock_workspace_repo):
            
            # Make login request with wrong password
            response = client_with_db_override.post(
                "/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "wrong-password"  # Different from the hash we set up
                }
            )

        # Verify the response
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid email or password"
        
        # Verify service was called correctly
        mock_user_repo.get_by_email.assert_called_once_with("test@example.com")
        
    finally:
        # Clean up overrides
        app.dependency_overrides.clear()


def test_login_user_not_found(client_with_db_override, mock_db):
    """Test login with non-existent user"""
    # Set up mocked repository and service
    mock_user_repo = MagicMock(spec=UserRepository)
    mock_user_repo.get_by_email.return_value = None  # User not found
    
    mock_event_system = MagicMock(spec=EventSystem)
    
    mock_user_service = UserService(mock_db, mock_user_repo, mock_event_system)
    
    # Configure mock workspace repository
    mock_workspace_repo = MagicMock(spec=WorkspaceRepository)
    
    # Set up dependency overrides
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo
    app.dependency_overrides[get_user_service_with_events] = lambda: mock_user_service
    
    try:
        with patch("app.api.auth.get_workspace_repository", return_value=mock_workspace_repo):
            
            # Make login request with a non-existent email
            response = client_with_db_override.post(
                "/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "password"
                }
            )

        # Verify the response
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid email or password"
        
        # Verify service was called with the right email
        mock_user_repo.get_by_email.assert_called_once_with("nonexistent@example.com")
        
    finally:
        # Clean up overrides
        app.dependency_overrides.clear()


def test_login_missing_password(client_with_db_override, mock_db):
    """Test login with missing password"""
    # This test is simple and doesn't need complex mocking since
    # it tests FastAPI's validation, not our business logic
    
    # Make login request without password using client with DB override
    response = client_with_db_override.post(
        "/auth/login",
        json={
            "email": "test@example.com"
            # Intentionally omitting password
        }
    )

    # Verify the response
    assert response.status_code == 422  # Validation error


# Note: We've intentionally removed the auto-create test user test
# This development-only feature is better tested through:
# 1. A unit test for UserService.create_user() in tests/services/
# 2. A unit test for WorkspaceRepository.create_workspace() in tests/database/repositories/
# Following the DEVELOPMENT.md recommendation to test components separately


# No longer applicable with the updated login endpoint


@pytest.mark.asyncio
async def test_get_current_user_valid_token(mock_db, test_token):
    """Test getting current user with valid token"""
    # Create a domain model using our utility function
    domain_user = create_test_user_domain()
    
    # Set up mocked user service
    mock_user_service = MagicMock(spec=UserService)
    mock_user_service.get_user.return_value = domain_user
    
    try:
        # Call the function with our valid token
        user = await get_current_user(token=test_token, user_service=mock_user_service)
        
        # Verify the result
        assert user.id == domain_user.id
        assert user.email == domain_user.email
        
        # Verify service was called correctly
        mock_user_service.get_user.assert_called_once()
        
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_db):
    """Test getting current user with invalid token"""
    # Create an invalid token
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXvCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLWlkIiwiZXhwIjoxNjA5NDU5MjAwfQ.INVALID-SIGNATURE"

    # Set up mocked user service
    mock_user_service = MagicMock(spec=UserService)
    
    # Call the function and verify it raises the expected exception
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token=invalid_token, user_service=mock_user_service)

    # Check that it has the expected status code
    assert excinfo.value.status_code == 401
    
    # The service should not be called since the token is invalid
    mock_user_service.get_user.assert_not_called()


@pytest.mark.asyncio
async def test_get_current_user_expired_token(mock_db, test_user):
    """Test getting current user with expired token"""
    # Create an expired token
    token_data = TokenData(user_id=test_user.id)

    # Set up mocked user service
    mock_user_service = MagicMock(spec=UserService)

    # Patch jwt_secret for consistent test environment
    with patch("app.components.tokens.settings.security.jwt_secret", "test-secret"):
        # Create token that expired 1 hour ago
        expired_delta = timedelta(hours=-1)
        to_encode = token_data.model_dump()
        expire = datetime.now(timezone.utc) + expired_delta
        to_encode.update({"exp": expire})
        expired_token = jwt.encode(to_encode, "test-secret", algorithm="HS256")

        # Call the function and verify it raises the expected exception
        with pytest.raises(HTTPException) as excinfo:
            await get_current_user(token=expired_token, user_service=mock_user_service)

        # Check that it has the expected status code
        assert excinfo.value.status_code == 401
        
        # The service should not be called since the token is expired
        mock_user_service.get_user.assert_not_called()


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(test_token, mock_db):
    """Test getting current user when user doesn't exist"""
    # Set up mocked user service that returns no user
    mock_user_service = MagicMock(spec=UserService)
    mock_user_service.get_user.return_value = None
    
    # Call the function and verify it raises the expected exception
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token=test_token, user_service=mock_user_service)

    # Check that it has the expected status code
    assert excinfo.value.status_code == 404
    
    # The service should be called but returns None
    mock_user_service.get_user.assert_called_once()


def test_generate_api_key(client_with_auth_override, mock_db, test_user, test_token):
    """Test generating an API key"""
    # Create a mock security manager
    mock_security_manager = MagicMock(spec=SecurityManager)
    mock_security_manager.encrypt.return_value = "encrypted-key"
    mock_security_manager.stringify_json.return_value = '["*"]'

    # Patch just the security manager, auth and DB already patched in fixture
    with patch("app.api.auth.security_manager", mock_security_manager):

        # Make the API key generation request - include token in the header
        response = client_with_auth_override.post(
            "/auth/key/generate",
            json={"scopes": ["*"], "expiry_days": 30},
            headers={"Authorization": f"Bearer {test_token}"}
        )

        # Verify the response
        assert response.status_code == 200
        data = response.json()

        assert data["key"].startswith("sk-")
        assert "expires_at_utc" in data

        # Verify that the key was added to the database
        assert mock_db.add.call_count == 1
        added_api_key = mock_db.add.call_args[0][0]
        assert isinstance(added_api_key, ApiKey)
        # Don't check exact ID match since it may be a mock
        # Checking the type is sufficient


def test_refresh_token_not_implemented(client_with_db_override):
    """Test refresh token endpoint (currently not implemented)"""
    response = client_with_db_override.post("/auth/refresh")
    assert response.status_code == 501


def test_logout(client_with_db_override):
    """Test logout endpoint"""
    response = client_with_db_override.post("/auth/logout")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Logged out successfully"