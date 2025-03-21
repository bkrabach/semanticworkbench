# We need pytest for test discovery, even if not directly used
import pytest  # noqa: F401
from fastapi.testclient import TestClient
from app.main import app
from app.utils.auth import create_access_token

client = TestClient(app)

def get_auth_header(user_id="test-user", name="Test User", email="test@example.com"):
    """Create authentication header with test token."""
    token = create_access_token({
        "sub": email,
        "oid": user_id,
        "name": name,
        "email": email
    })
    return {"Authorization": f"Bearer {token}"}

def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "service": "Cortex Core"}

def test_login_endpoint():
    """Test login endpoint."""
    response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_invalid_login():
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login",
        data={"username": "wrong@example.com", "password": "wrong"}
    )
    assert response.status_code == 401

def test_verify_token():
    """Test token verification."""
    headers = get_auth_header()
    response = client.get("/auth/verify", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test-user"

def test_input_endpoint():
    """Test input endpoint."""
    headers = get_auth_header()
    
    # Create a workspace and conversation first
    workspace_response = client.post(
        "/config/workspace",
        json={"name": "Test Workspace", "description": "Test Description", "metadata": {}},
        headers=headers
    )
    workspace_data = workspace_response.json()
    workspace_id = workspace_data["workspace"]["id"]
    
    conversation_response = client.post(
        "/config/conversation",
        json={
            "workspace_id": workspace_id,
            "topic": "Test Conversation",
            "metadata": {}
        },
        headers=headers
    )
    conversation_data = conversation_response.json()
    conversation_id = conversation_data["conversation"]["id"]
    
    # Test input endpoint with required conversation_id
    response = client.post(
        "/input",
        json={"content": "Test message", "conversation_id": conversation_id, "metadata": {}},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["data"]["content"] == "Test message"
    assert data["data"]["conversation_id"] == conversation_id

def test_input_endpoint_missing_conversation_id():
    """Test input endpoint with missing conversation_id."""
    headers = get_auth_header()
    
    # Test input endpoint without the required conversation_id
    response = client.post(
        "/input",
        json={"content": "Test message", "metadata": {}},
        headers=headers
    )
    # Should return a validation error
    assert response.status_code == 422
    data = response.json()
    # Check that the error is about the missing conversation_id
    assert "error" in data
    assert data["error"]["code"] == "validation_error"
    assert "validation_errors" in data["error"]["details"]
    assert any("conversation_id" in str(error) for error in data["error"]["details"]["validation_errors"])

def test_workspace_endpoints():
    """Test workspace creation and listing."""
    headers = get_auth_header()

    # Create workspace
    response = client.post(
        "/config/workspace",
        json={"name": "Test Workspace", "description": "Test Description", "metadata": {}},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "workspace created"
    assert data["workspace"]["name"] == "Test Workspace"
    workspace_id = data["workspace"]["id"]

    # List workspaces
    response = client.get("/config/workspace", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["workspaces"]) > 0
    assert any(w["id"] == workspace_id for w in data["workspaces"])

    # Create conversation
    response = client.post(
        "/config/conversation",
        json={
            "workspace_id": workspace_id,
            "topic": "Test Conversation",
            "metadata": {}
        },
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "conversation created"
    assert data["conversation"]["topic"] == "Test Conversation"
    conversation_id = data["conversation"]["id"]

    # List conversations
    response = client.get(
        f"/config/conversation?workspace_id={workspace_id}",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["conversations"]) > 0
    assert any(c["id"] == conversation_id for c in data["conversations"])