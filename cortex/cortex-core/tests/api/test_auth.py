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
    # Configure mock database to return our test user
    query_builder = mock_db.query.return_value.filter.return_value
    query_builder.first.return_value = test_user

    # Make login request using the client with DB override
    response = client_with_db_override.post(
        "/auth/login",
        json={
            "type": "password",
            "identifier": "test@example.com",
            "secret": "password"
        }
    )

    # Verify the response
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["user_id"] == test_user.id
    assert data["token"] is not None
    assert data["expires_at_utc"] is not None
    assert data["error"] is None


def test_login_invalid_password(client_with_db_override, mock_db, test_user):
    """Test login with invalid password"""
    # Configure mock database to return our test user
    query_builder = mock_db.query.return_value.filter.return_value
    query_builder.first.return_value = test_user

    # Make login request with wrong password using client with DB override
    response = client_with_db_override.post(
        "/auth/login",
        json={
            "type": "password",
            "identifier": "test@example.com",
            "secret": "wrong-password"
        }
    )

    # Verify the response
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is False
    assert data["error"] == "Invalid email or password"
    assert data["token"] is None


def test_login_user_not_found(client_with_db_override, mock_db):
    """Test login with non-existent user"""
    # Configure mock database to return None (user not found)
    query_builder = mock_db.query.return_value.filter.return_value
    query_builder.first.return_value = None

    # Make login request using client with DB override
    response = client_with_db_override.post(
        "/auth/login",
        json={
            "type": "password",
            "identifier": "nonexistent@example.com",
            "secret": "password"
        }
    )

    # Verify the response
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is False
    assert data["error"] == "Invalid email or password"
    assert data["token"] is None


def test_login_missing_password(client_with_db_override, mock_db, test_user):
    """Test login with missing password"""
    # Configure mock database to return our test user
    query_builder = mock_db.query.return_value.filter.return_value
    query_builder.first.return_value = test_user

    # Make login request without password using client with DB override
    response = client_with_db_override.post(
        "/auth/login",
        json={
            "type": "password",
            "identifier": "test@example.com"
        }
    )

    # Verify the response
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is False
    assert data["error"] == "Password is required"
    assert data["token"] is None


def test_login_auto_create_test_user(client_with_db_override, mock_db):
    """Test creating a test user automatically during login (localhost only)"""
    # Configure mock to indicate the user doesn't exist
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # Configure count for workspace check to return 0
    workspace_query = MagicMock()
    mock_db.query.side_effect = lambda model: (
        workspace_query if model == Workspace else mock_db.query.return_value
    )
    workspace_query.filter.return_value.count.return_value = 0

    # Patch settings to indicate we're on localhost
    test_settings = MagicMock()
    test_settings.server.host = "localhost"
    test_settings.security.token_expiry_seconds = 3600
    test_settings.security.jwt_secret = "test-secret"

    # Patch only the settings, DB is already patched in the fixture
    with patch("app.api.auth.settings", test_settings), \
         patch("app.components.tokens.settings", test_settings):

        # Make login request with test credentials
        response = client_with_db_override.post(
            "/auth/login",
            json={
                "type": "password",
                "identifier": "test@example.com",
                "secret": "password"
            }
        )

        # Verify the response
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["user_id"] is not None
        assert data["token"] is not None

        # Verify the test user was created in the mock DB
        assert mock_db.add.call_count == 3  # User and 2 workspaces were added
        assert mock_db.commit.call_count >= 2  # At least 2 commits were made


def test_login_unsupported_type(client_with_db_override):
    """Test login with unsupported authentication type"""
    # Make login request with unsupported type
    response = client_with_db_override.post(
        "/auth/login",
        json={
            "type": "unsupported",
            "identifier": "test@example.com",
            "secret": "password"
        }
    )

    # Verify the response
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is False
    assert "Unsupported authentication type" in data["error"]


@pytest.mark.asyncio
async def test_get_current_user_valid_token(mock_db, test_user, test_token):
    """Test getting current user with valid token"""
    # Configure mock to return the test user
    mock_db.query.return_value.filter.return_value.first.return_value = test_user

    # Call the function with our valid token
    try:
        user = await get_current_user(token=test_token, db=mock_db)
        assert user.id == test_user.id
        assert user.email == test_user.email
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_db):
    """Test getting current user with invalid token"""
    # Create an invalid token
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXvCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLWlkIiwiZXhwIjoxNjA5NDU5MjAwfQ.INVALID-SIGNATURE"

    # Call the function and verify it raises the expected exception
    with pytest.raises(Exception) as excinfo:
        await get_current_user(token=invalid_token, db=mock_db)

    # Check that it has the expected status code
    assert "401" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_current_user_expired_token(mock_db, test_user):
    """Test getting current user with expired token"""
    # Create an expired token
    token_data = TokenData(user_id=test_user.id)

    # Patch jwt_secret for consistent test environment
    with patch("app.components.tokens.settings.security.jwt_secret", "test-secret"):
        # Create token that expired 1 hour ago
        expired_delta = timedelta(hours=-1)
        to_encode = token_data.model_dump()
        expire = datetime.now(timezone.utc) + expired_delta
        to_encode.update({"exp": expire})
        expired_token = jwt.encode(to_encode, "test-secret", algorithm="HS256")

        # Call the function and verify it raises the expected exception
        with pytest.raises(Exception) as excinfo:
            await get_current_user(token=expired_token, db=mock_db)

        # Check that it has the expected status code
        assert "401" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(mock_db, test_token):
    """Test getting current user when user doesn't exist"""
    # Configure mock to indicate the user doesn't exist
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # Call the function and verify it raises the expected exception
    with pytest.raises(Exception) as excinfo:
        await get_current_user(token=test_token, db=mock_db)

    # Check that it has the expected status code
    assert "404" in str(excinfo.value)


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