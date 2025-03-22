import pytest
from fastapi.testclient import TestClient
from app.main import app
import jwt
import datetime

client = TestClient(app)

def test_login_endpoint_dev_mode():
    """Test the login endpoint in development mode."""
    # Test with valid credentials
    response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
    
    # Test with invalid credentials
    response = client.post(
        "/auth/login",
        data={"username": "wrong@example.com", "password": "wrongpass"}
    )
    assert response.status_code == 401
    assert "message" in response.json()["error"]

def test_verify_endpoint():
    """Test the verify endpoint with a valid token."""
    # First, get a token
    login_response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    # Test the verify endpoint
    response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "authenticated" in response.json()
    assert response.json()["authenticated"] == True
    assert "user" in response.json()
    
    # Test with invalid token
    response = client.get(
        "/auth/verify",
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401

def test_protected_endpoint():
    """Test a protected endpoint (config/user/profile)."""
    # First, get a token
    login_response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    # Test the protected endpoint
    response = client.get(
        "/config/user/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "profile" in response.json()
    
    # Test without token
    response = client.get("/config/user/profile")
    assert response.status_code == 401
    
    # Test with invalid token
    response = client.get(
        "/config/user/profile",
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401

def test_workspace_flow():
    """Test creating and listing workspaces with authentication."""
    # First, get a token
    login_response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    # Create a workspace
    response = client.post(
        "/config/workspace",
        json={"name": "Test Workspace", "description": "Test description"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    workspace_id = response.json()["workspace"]["id"]
    
    # List workspaces
    response = client.get(
        "/config/workspace",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "workspaces" in response.json()
    assert len(response.json()["workspaces"]) > 0
    
    # Create a conversation in the workspace
    response = client.post(
        "/config/conversation",
        json={"workspace_id": workspace_id, "topic": "Test Conversation"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    conversation_id = response.json()["conversation"]["id"]
    
    # List conversations in the workspace
    response = client.get(
        f"/config/conversation?workspace_id={workspace_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "conversations" in response.json()
    assert len(response.json()["conversations"]) > 0

if __name__ == "__main__":
    # Run tests
    test_login_endpoint_dev_mode()
    test_verify_endpoint()
    test_protected_endpoint()
    test_workspace_flow()
    print("All tests passed!")