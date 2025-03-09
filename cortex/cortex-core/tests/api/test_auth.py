"""
Test suite for the authentication API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from jose import jwt
from sqlalchemy.orm import Session

from app.main import app
from app.api.auth import get_current_user
from app.components.tokens import TokenData, generate_jwt_token
from app.components.security_manager import SecurityManager
from app.database.models import User, ApiKey, Workspace
from app.database.connection import get_db
from app.database.repositories.user_repository import UserRepository, get_user_repository
from app.services.user_service import UserService
from app.models.domain.user import User as UserDomain
from app.components.event_system import EventSystem


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


def test_login_success(client_with_db_override, mock_db, test_user):
    """Test successful login with password"""
    # Create a domain model version of the test user
    domain_user = UserDomain(
        id=test_user.id,
        email=test_user.email,
        name=test_user.name,
        created_at=test_user.created_at_utc,
        updated_at=test_user.updated_at_utc,
        last_login_at=None,
        roles=[]
    )
    
    # Set up mocked repository and service
    mock_user_repo = MagicMock(spec=UserRepository)
    mock_user_repo.get_by_email.return_value = domain_user
    mock_user_repo.update_last_login.return_value = domain_user
    
    mock_event_system = MagicMock(spec=EventSystem)
    
    mock_user_service = UserService(mock_db, mock_user_repo, mock_event_system)
    
    # Configure mock workspace repository
    mock_workspace_repo = MagicMock()
    mock_workspace_repo.get_user_workspaces.return_value = [MagicMock()]
    
    # Set up dependency overrides
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo
    
    with patch("app.api.auth.get_user_service_with_events", return_value=mock_user_service), \
         patch("app.api.auth.get_workspace_repository", return_value=mock_workspace_repo):
        
        # Make login request using the client with DB override
        response = client_with_db_override.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "password"
            }
        )

    # Remove overrides
    app.dependency_overrides.pop(get_user_repository, None)

    # Verify the response
    assert response.status_code == 200
    data = response.json()

    assert data["access_token"] is not None
    assert data["token_type"] == "bearer"
    assert data["user"]["id"] == test_user.id
    assert data["user"]["email"] == test_user.email


def test_login_invalid_password(client_with_db_override, mock_db, test_user):
    """Test login with invalid password"""
    # Create a domain model version of the test user
    domain_user = UserDomain(
        id=test_user.id,
        email=test_user.email,
        name=test_user.name,
        created_at=test_user.created_at_utc,
        updated_at=test_user.updated_at_utc,
        last_login_at=None,
        roles=[],
        password_hash=test_user.password_hash
    )
    
    # Set up mocked repository and service
    mock_user_repo = MagicMock(spec=UserRepository)
    mock_user_repo.get_by_email.return_value = domain_user
    
    mock_event_system = MagicMock(spec=EventSystem)
    
    mock_user_service = UserService(mock_db, mock_user_repo, mock_event_system)
    
    # Configure mock workspace repository
    mock_workspace_repo = MagicMock()
    
    # Set up dependency overrides
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo
    
    with patch("app.api.auth.get_user_service_with_events", return_value=mock_user_service), \
         patch("app.api.auth.get_workspace_repository", return_value=mock_workspace_repo):
        
        # Make login request with wrong password
        response = client_with_db_override.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrong-password"
            }
        )

    # Remove overrides
    app.dependency_overrides.pop(get_user_repository, None)

    # Verify the response
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid email or password"


def test_login_user_not_found(client_with_db_override, mock_db):
    """Test login with non-existent user"""
    # Set up mocked repository and service
    mock_user_repo = MagicMock(spec=UserRepository)
    mock_user_repo.get_by_email.return_value = None
    
    mock_event_system = MagicMock(spec=EventSystem)
    
    mock_user_service = UserService(mock_db, mock_user_repo, mock_event_system)
    
    # Configure mock workspace repository
    mock_workspace_repo = MagicMock()
    
    # Set up dependency overrides
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo
    
    with patch("app.api.auth.get_user_service_with_events", return_value=mock_user_service), \
         patch("app.api.auth.get_workspace_repository", return_value=mock_workspace_repo):
        
        # Make login request
        response = client_with_db_override.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password"
            }
        )

    # Remove overrides
    app.dependency_overrides.pop(get_user_repository, None)

    # Verify the response
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid email or password"


def test_login_missing_password(client_with_db_override, mock_db, test_user):
    """Test login with missing password"""
    # Make login request without password using client with DB override
    response = client_with_db_override.post(
        "/auth/login",
        json={
            "email": "test@example.com"
        }
    )

    # Verify the response
    assert response.status_code == 422  # Validation error


def test_login_auto_create_test_user(client_with_db_override, mock_db):
    """Test creating a test user automatically during login (localhost only)"""
    # Create a new test user as domain model
    new_domain_user = UserDomain(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_login_at=None,
        roles=[]
    )
    
    # Set up mocked repository and service
    mock_user_repo = MagicMock(spec=UserRepository)
    mock_user_repo.get_by_email.return_value = None  # User doesn't exist
    mock_user_repo.create.return_value = new_domain_user
    mock_user_repo.update_last_login.return_value = new_domain_user
    
    mock_event_system = MagicMock(spec=EventSystem)
    
    mock_user_service = UserService(mock_db, mock_user_repo, mock_event_system)
    
    # Configure mock workspace repository
    mock_workspace_repo = MagicMock()
    mock_workspace_repo.get_user_workspaces.return_value = []
    mock_workspace_repo.create_workspace.return_value = MagicMock()
    
    # Patch settings to indicate we're on localhost
    test_settings = MagicMock()
    test_settings.server.host = "localhost"
    test_settings.security.token_expiry_seconds = 3600
    test_settings.security.jwt_secret = "test-secret"
    
    # Set up dependency overrides
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo
    
    # Patch settings and service dependencies
    with patch("app.api.auth.settings", test_settings), \
         patch("app.components.tokens.settings", test_settings), \
         patch("app.api.auth.get_user_service_with_events", return_value=mock_user_service), \
         patch("app.api.auth.get_workspace_repository", return_value=mock_workspace_repo):
        
        # Make login request with test credentials
        response = client_with_db_override.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "password"
            }
        )

    # Remove overrides
    app.dependency_overrides.pop(get_user_repository, None)

    # Verify the response
    assert response.status_code == 200
    data = response.json()

    assert data["access_token"] is not None
    assert data["token_type"] == "bearer"
    assert data["user"]["id"] == new_domain_user.id
    assert data["user"]["email"] == new_domain_user.email
    
    # Verify service calls
    mock_user_service.create_user.assert_called_once()
    mock_workspace_repo.create_workspace.assert_called_once()


# No longer applicable with the updated login endpoint


@pytest.mark.asyncio
async def test_get_current_user_valid_token(mock_db, test_user, test_token):
    """Test getting current user with valid token"""
    # Create a domain model version of the test user
    domain_user = UserDomain(
        id=test_user.id,
        email=test_user.email,
        name=test_user.name,
        created_at=test_user.created_at_utc,
        updated_at=test_user.updated_at_utc,
        last_login_at=None,
        roles=[]
    )
    
    # Set up mocked user service
    mock_user_service = MagicMock(spec=UserService)
    mock_user_service.get_user.return_value = domain_user
    
    try:
        # Call the function with our valid token
        user = await get_current_user(token=test_token, user_service=mock_user_service)
        
        # Verify the result
        assert user.id == test_user.id
        assert user.email == test_user.email
        
        # Verify service was called correctly
        mock_user_service.get_user.assert_called_once_with(test_user.id)
        
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


def test_generate_api_key(client_with_auth_override, mock_db, test_user):
    """Test generating an API key"""
    # Create a mock security manager
    mock_security_manager = MagicMock(spec=SecurityManager)
    mock_security_manager.encrypt.return_value = "encrypted-key"
    mock_security_manager.stringify_json.return_value = '["*"]'

    # Patch just the security manager, auth and DB already patched in fixture
    with patch("app.api.auth.security_manager", mock_security_manager):

        # Make the API key generation request (no need for token in header, auth is mocked)
        response = client_with_auth_override.post(
            "/auth/key/generate",
            json={"scopes": ["*"], "expiry_days": 30}
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
        assert added_api_key.user_id == test_user.id


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