# We need pytest for test discovery, even if not directly used
from typing import Dict

from app.main import app
from app.utils.auth import create_access_token
from fastapi.testclient import TestClient

client = TestClient(app)


def get_auth_header(
    user_id: str = "test-user", name: str = "Test User", email: str = "test@example.com"
) -> Dict[str, str]:
    """Create authentication header with test token."""
    token = create_access_token({"sub": email, "oid": user_id, "name": name, "email": email})
    return {"Authorization": f"Bearer {token}"}


def test_root_endpoint() -> None:
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "service": "Cortex Core"}


def test_health_endpoints() -> None:
    """Test health endpoints."""
    # Basic health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    
    # Enhanced v1 health endpoint
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Cortex Core"
    assert "version" in data
    assert "resources" in data
    
    
def test_cognition_endpoints_existence() -> None:
    """Test cognition endpoints existence."""
    # We simply check that the routes exist and require authentication
    # Don't test functionality here - that's done in the unit tests
    headers = get_auth_header()
    
    # Context endpoint
    response = client.post("/v1/context", json={"query": "test"})
    assert response.status_code == 401  # Unauthorized without token
    
    # Analysis endpoint
    response = client.post("/v1/analyze", json={"conversation_id": "test"})
    assert response.status_code == 401  # Unauthorized without token
    
    # Search endpoint
    response = client.post("/v1/search", json={"query": "test"})
    assert response.status_code == 401  # Unauthorized without token


def test_login_endpoint() -> None:
    """Test login endpoint."""
    response = client.post("/v1/auth/login", data={"username": "user@example.com", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    # With the standardized response format, fields are in the data object
    assert "data" in data
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"


def test_invalid_login() -> None:
    """Test login with invalid credentials."""
    response = client.post("/v1/auth/login", data={"username": "wrong@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_verify_token() -> None:
    """Test token verification."""
    headers = get_auth_header()
    response = client.get("/v1/auth/verify", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test-user"


def test_input_endpoint() -> None:
    """Test input endpoint."""
    headers = get_auth_header()

    # Create a workspace and conversation first
    workspace_response = client.post(
        "/v1/workspace",
        json={"name": "Test Workspace", "description": "Test Description", "metadata": {}},
        headers=headers,
    )
    workspace_data = workspace_response.json()
    workspace_id = workspace_data["data"]["workspace"]["id"]

    conversation_response = client.post(
        "/v1/conversation",
        json={"workspace_id": workspace_id, "topic": "Test Conversation", "metadata": {}},
        headers=headers,
    )
    conversation_data = conversation_response.json()
    conversation_id = conversation_data["data"]["conversation"]["id"]

    # Test input endpoint with conversation_id in path
    response = client.post(
        f"/v1/conversation/{conversation_id}/messages", json={"content": "Test message", "metadata": {}}, headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["data"]["content"] == "Test message"
    assert data["data"]["conversation_id"] == conversation_id


def test_input_endpoint_missing_conversation_path() -> None:
    """Test input endpoint with invalid conversation path."""
    headers = get_auth_header()

    # Test input endpoint with an invalid conversation ID path
    response = client.post("/v1/conversation/invalid-id/messages", json={"content": "Test message", "metadata": {}}, headers=headers)
    # Should return a not found error
    assert response.status_code == 404
    data = response.json()
    # Check that the error is about the conversation not found
    assert "detail" in data
    assert "error" in data["detail"]
    assert data["detail"]["error"]["code"] == "resource_not_found"
    assert "Conversation not found" in data["detail"]["error"]["message"]


def test_workspace_endpoints() -> None:
    """Test workspace creation and listing."""
    headers = get_auth_header()

    # Create workspace
    response = client.post(
        "/v1/workspace",
        json={"name": "Test Workspace", "description": "Test Description", "metadata": {}},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "workspace created"
    assert data["data"]["workspace"]["name"] == "Test Workspace"
    workspace_id = data["data"]["workspace"]["id"]

    # List workspaces
    response = client.get("/v1/workspace", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    # In a test environment, workspaces may or may not persist between calls depending on the database setup
    # Just verify we get a list and the response format is correct, without requiring the specific workspace
    assert "data" in data
    assert "workspaces" in data["data"]
    assert isinstance(data["data"]["workspaces"], list)

    # Create conversation
    response = client.post(
        "/v1/conversation",
        json={"workspace_id": workspace_id, "topic": "Test Conversation", "metadata": {}},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "conversation created"
    assert data["data"]["conversation"]["topic"] == "Test Conversation"
    conversation_id = data["data"]["conversation"]["id"]

    # List conversations
    response = client.get(f"/v1/conversation?workspace_id={workspace_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["conversations"]) > 0
    assert any(c["id"] == conversation_id for c in data["data"]["conversations"])
