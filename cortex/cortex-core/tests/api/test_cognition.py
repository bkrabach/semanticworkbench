"""
Tests for the Cognition API endpoints.
"""

import pytest
from unittest.mock import patch, AsyncMock

from app.api.cognition import router
from fastapi.testclient import TestClient
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture
def user_context():
    """Create a mock user context."""
    return {
        "user_id": "test-user-id", 
        "name": "Test User", 
        "email": "test@example.com"
    }


@pytest.fixture
def auth_headers(test_token):
    """Create mock authentication headers."""
    return {"Authorization": f"Bearer {test_token}"}


@patch("app.api.cognition.get_current_user")
@patch("app.api.cognition.get_context")
async def test_get_user_context(mock_get_context, mock_get_current_user, user_context, auth_headers):
    """Test getting user context API endpoint."""
    # Mock get_current_user
    mock_get_current_user.return_value = user_context
    
    # Mock get_context with mock response
    mock_get_context_response = {
        "context": [
            {"id": "msg1", "content": "Test message 1", "timestamp": "2023-01-01T00:00:00Z"},
            {"id": "msg2", "content": "Test message 2", "timestamp": "2023-01-02T00:00:00Z"}
        ],
        "user_id": user_context["user_id"],
        "query": "test",
        "count": 2
    }
    mock_get_context.return_value = mock_get_context_response
    
    # Call API endpoint
    response = client.post(
        "/cognition/context",
        json={"query": "test", "limit": 5},
        headers=auth_headers
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["count"] == 2
    assert len(data["data"]["context"]) == 2
    assert data["data"]["user_id"] == user_context["user_id"]
    
    # Verify function was called with correct parameters
    mock_get_context.assert_awaited_once_with(
        user_id=user_context["user_id"],
        query="test",
        limit=5
    )


@patch("app.api.cognition.get_current_user")
@patch("app.api.cognition.analyze_conversation")
async def test_analyze_user_conversation(mock_analyze_conversation, mock_get_current_user, user_context, auth_headers):
    """Test analyzing a conversation API endpoint."""
    # Mock get_current_user
    mock_get_current_user.return_value = user_context
    
    # Mock analyze_conversation with mock response
    mock_analyze_response = {
        "type": "summary",
        "results": {
            "message_count": 10,
            "participants": 2,
            "duration_seconds": 3600
        },
        "conversation_id": "conv123"
    }
    mock_analyze_conversation.return_value = mock_analyze_response
    
    # Call API endpoint
    response = client.post(
        "/cognition/analyze",
        json={"conversation_id": "conv123", "analysis_type": "summary"},
        headers=auth_headers
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["type"] == "summary"
    assert data["data"]["conversation_id"] == "conv123"
    assert data["data"]["results"]["message_count"] == 10
    
    # Verify function was called with correct parameters
    mock_analyze_conversation.assert_awaited_once_with(
        user_id=user_context["user_id"],
        conversation_id="conv123",
        analysis_type="summary"
    )


@patch("app.api.cognition.get_current_user")
@patch("app.api.cognition.search_history")
async def test_search_user_history(mock_search_history, mock_get_current_user, user_context, auth_headers):
    """Test searching user history API endpoint."""
    # Mock get_current_user
    mock_get_current_user.return_value = user_context
    
    # Mock search_history with mock response
    mock_search_response = {
        "results": [
            {"id": "msg1", "content": "Test message 1", "timestamp": "2023-01-01T00:00:00Z"},
            {"id": "msg2", "content": "Test message 2", "timestamp": "2023-01-02T00:00:00Z"}
        ],
        "count": 2,
        "query": "test"
    }
    mock_search_history.return_value = mock_search_response
    
    # Call API endpoint
    response = client.post(
        "/cognition/search",
        json={"query": "test", "limit": 5, "include_conversations": True},
        headers=auth_headers
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["count"] == 2
    assert len(data["data"]["results"]) == 2
    assert data["data"]["query"] == "test"
    
    # Verify function was called with correct parameters
    mock_search_history.assert_awaited_once_with(
        user_id=user_context["user_id"],
        query="test",
        limit=5,
        include_conversations=True
    )