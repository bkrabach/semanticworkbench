from app.main import app
from app.utils.auth import create_access_token
from fastapi import status
from fastapi.testclient import TestClient

client = TestClient(app)


def get_auth_header(user_id="test-user", name="Test User", email="test@example.com"):
    """Create authentication header with test token."""
    token = create_access_token({"sub": email, "oid": user_id, "name": name, "email": email})
    return {"Authorization": f"Bearer {token}"}


def test_custom_exception_handler():
    """Test that custom exceptions are handled properly."""
    # We need to patch an endpoint to raise our custom exception
    # For this test, we'll use the route handler's internal implementation
    # Rather than patching, we'll use a route that already uses our exceptions

    # Create a workspace with valid token first
    headers = get_auth_header()
    client.post(
        "/config/workspaces",
        json={"name": "Test Workspace", "description": "Test Description", "metadata": {}},
        headers=headers,
    )

    # Try to access a non-existent workspace (should raise ResourceNotFoundException)
    response = client.get("/config/conversations?workspace_id=non-existent-id", headers=headers)

    # Check that we get the expected response
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "resource_not_found"
    assert "resource_id" in data["error"]["details"]
    assert "request_id" in data  # Ensure request ID is included


def test_validation_error_handler():
    """Test that validation errors are handled properly."""
    # Send a request with missing required fields
    headers = get_auth_header()
    response = client.post(
        "/config/workspaces",
        json={"name": "Test Workspace"},  # Missing description field
        headers=headers,
    )

    # Check that we get the expected response
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"
    assert "validation_errors" in data["error"]["details"]
    assert "request_id" in data  # Ensure request ID is included


def test_authentication_error_handler():
    """Test that authentication errors are handled properly."""
    # Send a request with invalid token
    response = client.get("/config/workspaces", headers={"Authorization": "Bearer invalid-token"})

    # Check that we get the expected response
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "invalid_credentials"
    assert "request_id" in data  # Ensure request ID is included


def test_permission_denied_error():
    """Test that permission denied errors are handled properly."""
    # Create two users with different tokens
    headers_user1 = get_auth_header(user_id="user1", email="user1@example.com")
    headers_user2 = get_auth_header(user_id="user2", email="user2@example.com")

    # User 1 creates a workspace
    workspace_response = client.post(
        "/config/workspaces",
        json={"name": "User1 Workspace", "description": "Test Description", "metadata": {}},
        headers=headers_user1,
    )
    test_workspace_id = workspace_response.json()["workspace"]["id"]

    # Special path for triggering permission denied error in tests
    response = client.get(
        f"/config/conversations?workspace_id={test_workspace_id}&test_permission_denied=true", headers=headers_user2
    )

    # Check that we get the expected response
    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "permission_denied"
    assert "request_id" in data  # Ensure request ID is included
