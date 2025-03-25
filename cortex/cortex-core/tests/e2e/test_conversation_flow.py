"""
End-to-end tests for conversation flows.
"""

import uuid
from typing import Any, Dict

import pytest
from app.main import app
from app.utils.auth import create_access_token
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Create authentication headers with test token."""
    user_id = f"e2e-user-{uuid.uuid4()}"
    token = create_access_token({
        "sub": f"{user_id}@example.com",
        "oid": user_id,
        "name": "E2E Test User",
        "email": f"{user_id}@example.com",
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_workspace(client: TestClient, auth_headers: Dict[str, str]) -> Dict[str, Any]:
    """Create a test workspace."""
    response = client.post(
        "/v1/workspace",
        json={
            "name": f"E2E Test Workspace {uuid.uuid4()}",
            "description": "Workspace for E2E testing",
            "metadata": {"e2e_test": True},
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    workspace: Dict[str, Any] = response.json()["workspace"]
    return workspace


@pytest.fixture
def test_conversation(
    client: TestClient, auth_headers: Dict[str, str], test_workspace: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a test conversation."""
    response = client.post(
        "/v1/conversation",
        json={
            "workspace_id": test_workspace["id"],
            "topic": f"E2E Test Conversation {uuid.uuid4()}",
            "metadata": {"e2e_test": True},
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    conversation: Dict[str, Any] = response.json()["conversation"]
    return conversation


def test_create_workspace_and_conversation(client: TestClient, auth_headers: Dict[str, str]) -> None:
    """Test creating a workspace and conversation."""
    # Create workspace
    workspace_response = client.post(
        "/v1/workspace",
        json={
            "name": f"Flow Test Workspace {uuid.uuid4()}",
            "description": "Workspace for flow testing",
            "metadata": {"flow_test": True},
        },
        headers=auth_headers,
    )
    assert workspace_response.status_code == 201
    workspace = workspace_response.json()["workspace"]
    assert workspace["name"].startswith("Flow Test Workspace")

    # Create conversation
    conversation_response = client.post(
        "/v1/conversation",
        json={
            "workspace_id": workspace["id"],
            "topic": f"Flow Test Conversation {uuid.uuid4()}",
            "metadata": {"flow_test": True},
        },
        headers=auth_headers,
    )
    assert conversation_response.status_code == 201
    conversation = conversation_response.json()["conversation"]
    assert conversation["topic"].startswith("Flow Test Conversation")
    assert conversation["workspace_id"] == workspace["id"]

    # Verify conversation in workspace
    conversations_response = client.get(f"/v1/conversation?workspace_id={workspace['id']}", headers=auth_headers)
    assert conversations_response.status_code == 200
    conversations = conversations_response.json()["conversations"]
    assert any(c["id"] == conversation["id"] for c in conversations)


def test_send_and_receive_message(
    client: TestClient, auth_headers: Dict[str, str], test_conversation: Dict[str, Any]
) -> None:
    """Test sending a message and getting a response."""
    # Send a message
    input_response = client.post(
        f"/v1/conversation/{test_conversation['id']}/messages",
        json={
            "content": "Hello, this is a test message",
            "metadata": {"test": True},
        },
        headers=auth_headers,
    )
    assert input_response.status_code == 200
    assert input_response.json()["status"] == "received"

    # Give some time for processing (since we're testing against the same process)
    # In a real world scenario, we would use SSE to get the response
    # For E2E test purposes, we'll just wait a bit and then check the conversation detail
    import time

    time.sleep(2)

    # Get conversation detail to see the messages
    conversation_detail_response = client.get(f"/v1/conversation/{test_conversation['id']}", headers=auth_headers)
    assert conversation_detail_response.status_code == 200
    conversation_detail = conversation_detail_response.json()["conversation"]

    # Verify messages
    assert "messages" in conversation_detail
    messages = conversation_detail["messages"]
    assert len(messages) >= 2  # At least user message and assistant response

    # Find user message by content
    user_message = next((m for m in messages if m["content"] == "Hello, this is a test message"), None)
    assert user_message is not None, "User message not found in messages"

    # Find assistant response - just find a message that's not from user
    # Since the assistant is the only other sender, any message not matching user's will be from assistant
    assistant_message = next(
        (m for m in messages if m["content"] != "Hello, this is a test message" and m["content"] is not None), None
    )
    assert assistant_message is not None, "Assistant message not found in messages"


def test_complex_conversation_flow(
    client: TestClient, auth_headers: Dict[str, str], test_conversation: Dict[str, Any]
) -> None:
    """Test a more complex conversation flow with multiple messages."""
    # Send several messages
    test_messages = [
        "Hello, I need help with testing",
        "Can you tell me about the application?",
        "How do I create a workspace?",
        "How do I send a message to a conversation?",
    ]

    for message in test_messages:
        response = client.post(
            f"/v1/conversation/{test_conversation['id']}/messages",
            json={"content": message, "metadata": {"test": True}},
            headers=auth_headers,
        )
        assert response.status_code == 200
        # Give time for processing
        import time

        time.sleep(2)

    # Get conversation detail
    conversation_detail_response = client.get(f"/v1/conversation/{test_conversation['id']}", headers=auth_headers)
    assert conversation_detail_response.status_code == 200
    conversation_detail = conversation_detail_response.json()["conversation"]

    # Verify all messages are there
    messages = conversation_detail["messages"]
    for test_message in test_messages:
        found = any(m["content"] == test_message for m in messages)
        assert found, f"Message '{test_message}' not found in conversation"

    # Verify we have responses (at least as many as user messages)
    # Count messages that aren't one of the test messages - these should be assistant messages
    assistant_messages = [m for m in messages if m["content"] not in test_messages]
    assert len(assistant_messages) >= len(test_messages), "Not enough assistant responses"


def test_update_conversation(
    client: TestClient, auth_headers: Dict[str, str], test_conversation: Dict[str, Any]
) -> None:
    """Test updating a conversation."""
    # Update the conversation
    new_topic = f"Updated Topic {uuid.uuid4()}"
    update_response = client.put(
        f"/v1/conversation/{test_conversation['id']}",
        json={"topic": new_topic, "metadata": {**test_conversation["metadata"], "updated": True}},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    updated_conversation = update_response.json()["conversation"]
    assert updated_conversation["topic"] == new_topic
    assert updated_conversation["metadata"]["updated"] is True

    # Verify the update
    get_response = client.get(f"/v1/conversation/{test_conversation['id']}", headers=auth_headers)
    assert get_response.status_code == 200
    retrieved_conversation = get_response.json()["conversation"]
    assert retrieved_conversation["topic"] == new_topic
    assert retrieved_conversation["metadata"]["updated"] is True


def test_invalid_requests(client: TestClient, auth_headers: Dict[str, str], test_workspace: Dict[str, Any]) -> None:
    """Test handling of invalid requests."""
    # Try to create a conversation with missing workspace_id
    response = client.post("/v1/conversation", json={"topic": "Invalid Conversation"}, headers=auth_headers)
    assert response.status_code == 422  # Validation error

    # Try to send a message with missing content
    random_id = str(uuid.uuid4())
    response = client.post(f"/v1/conversation/{random_id}/messages", json={}, headers=auth_headers)
    assert response.status_code == 422  # Validation error

    # Try to access a non-existent conversation
    response = client.get(f"/v1/conversation/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404  # Not found

    # Try to send a message to a non-existent conversation
    non_existent_id = str(uuid.uuid4())
    response = client.post(
        f"/v1/conversation/{non_existent_id}/messages", json={"content": "Message to nowhere"}, headers=auth_headers
    )
    assert response.status_code == 404  # Not found


def test_unauthorized_access(client: TestClient, test_conversation: Dict[str, Any]) -> None:
    """Test unauthorized access attempts."""
    # Try to access without auth header
    response = client.get("/v1/workspace")
    assert response.status_code == 401

    # Try with invalid token
    response = client.get("/v1/workspace", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401

    # Try to create a workspace without auth
    response = client.post("/v1/workspace", json={"name": "Unauthorized Workspace", "description": "Should fail"})
    assert response.status_code == 401

    # Try to send a message without auth
    response = client.post(
        f"/v1/conversation/{test_conversation['id']}/messages", json={"content": "Unauthorized message"}
    )
    assert response.status_code == 401
