"""
Unit tests for the cognition-related tools.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from datetime import datetime

from app.core.tools import get_context, analyze_conversation, search_history


@pytest.fixture
def mock_client():
    """Create a mocked MCP client."""
    mock = AsyncMock()
    mock.get_resource = AsyncMock(return_value={})
    return mock


@pytest.fixture
def mock_uow():
    """Create a mocked UnitOfWork."""
    mock = MagicMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)
    
    # Mock repository access
    mock_msg_repo = AsyncMock()
    mock.repositories.get_message_repository = MagicMock(return_value=mock_msg_repo)
    
    return mock, mock_msg_repo


@pytest.mark.asyncio
@patch("app.core.tools.get_client")
async def test_get_context_with_mcp(mock_get_client, mock_client):
    """Test get_context with MCP client available."""
    # Setup mocked MCP client
    mock_get_client.return_value = mock_client
    mock_client.get_resource.return_value = {
        "context": [
            {"id": "msg1", "content": "Test message 1", "timestamp": "2023-01-01T00:00:00Z"},
            {"id": "msg2", "content": "Test message 2", "timestamp": "2023-01-02T00:00:00Z"}
        ],
        "user_id": "user123",
        "query": "test",
        "count": 2
    }
    
    # Call the function
    result = await get_context("user123", "test", 5)
    
    # Verify the MCP client was called correctly
    mock_client.get_resource.assert_called_once_with(
        service_name="cognition",
        resource_name="context",
        params={"user_id": "user123", "query": "test", "limit": 5}
    )
    
    # Verify the result
    assert result["count"] == 2
    assert len(result["context"]) == 2
    assert result["user_id"] == "user123"
    assert result["query"] == "test"


@pytest.mark.asyncio
@patch("app.core.tools.get_client")
@patch("app.core.tools.UnitOfWork")
async def test_get_context_without_mcp(mock_uow_class, mock_get_client, mock_uow):
    """Test get_context with no MCP client (fallback)."""
    mock_uow_instance, mock_msg_repo = mock_uow
    mock_uow_class.for_transaction.return_value = mock_uow_instance
    
    # No MCP client
    mock_get_client.return_value = None
    
    # Mock repository behavior
    mock_msg_repo.list_by_sender.return_value = [
        MagicMock(
            id="msg1",
            content="Test message with query",
            timestamp="2023-01-01T00:00:00Z",
            conversation_id="conv1"
        ),
        MagicMock(
            id="msg2",
            content="Another message",
            timestamp="2023-01-02T00:00:00Z",
            conversation_id="conv2"
        )
    ]
    
    # Call the function with a query that should match the first message
    result = await get_context("user123", "query", 5)
    
    # Verify repository was called
    mock_msg_repo.list_by_sender.assert_called_once_with("user123", limit=5)
    
    # Verify the result
    assert result["count"] == 1  # Only one message matches the query
    assert len(result["context"]) == 1
    assert result["user_id"] == "user123"
    assert result["query"] == "query"
    assert result["context"][0]["id"] == "msg1"


@pytest.mark.asyncio
@patch("app.core.tools.get_client")
async def test_analyze_conversation_with_mcp(mock_get_client, mock_client):
    """Test analyze_conversation with MCP client available."""
    # Setup mocked MCP client
    mock_get_client.return_value = mock_client
    mock_client.get_resource.return_value = {
        "type": "summary",
        "results": {
            "message_count": 10,
            "participants": 2,
            "duration_seconds": 3600
        },
        "conversation_id": "conv123"
    }
    
    # Call the function
    result = await analyze_conversation("user123", "conv123", "summary")
    
    # Verify the MCP client was called correctly
    mock_client.get_resource.assert_called_once_with(
        service_name="cognition",
        resource_name="analyze_conversation",
        params={"user_id": "user123", "conversation_id": "conv123", "analysis_type": "summary"}
    )
    
    # Verify the result
    assert result["type"] == "summary"
    assert result["conversation_id"] == "conv123"
    assert result["results"]["message_count"] == 10
    assert result["results"]["participants"] == 2


@pytest.mark.asyncio
@patch("app.core.tools.get_client")
@patch("app.core.tools.UnitOfWork")
async def test_analyze_conversation_without_mcp(mock_uow_class, mock_get_client, mock_uow):
    """Test analyze_conversation with no MCP client (fallback)."""
    mock_uow_instance, mock_msg_repo = mock_uow
    mock_uow_class.for_transaction.return_value = mock_uow_instance
    
    # No MCP client
    mock_get_client.return_value = None
    
    # Mock repository behavior
    mock_msg_repo.list_by_conversation.return_value = [
        MagicMock(sender_id="user1", content="Hello"),
        MagicMock(sender_id="user2", content="Hi there"),
        MagicMock(sender_id="user1", content="How are you?")
    ]
    
    # Call the function
    result = await analyze_conversation("user1", "conv123", "summary")
    
    # Verify repository was called
    mock_msg_repo.list_by_conversation.assert_called_once_with("conv123")
    
    # Verify the result
    assert result["type"] == "summary"
    assert result["conversation_id"] == "conv123"
    assert result["results"]["message_count"] == 3
    assert result["results"]["participants"] == 2
    assert result["results"]["participant_counts"]["user1"] == 2
    assert result["results"]["participant_counts"]["user2"] == 1


@pytest.mark.asyncio
@patch("app.core.tools.get_client")
async def test_search_history_with_mcp(mock_get_client, mock_client):
    """Test search_history with MCP client available."""
    # Setup mocked MCP client
    mock_get_client.return_value = mock_client
    mock_client.get_resource.return_value = {
        "results": [
            {"id": "msg1", "content": "Test message 1", "timestamp": "2023-01-01T00:00:00Z"},
            {"id": "msg2", "content": "Test message 2", "timestamp": "2023-01-02T00:00:00Z"}
        ],
        "count": 2,
        "query": "test"
    }
    
    # Call the function
    result = await search_history("user123", "test", 5, True)
    
    # Verify the MCP client was called correctly
    mock_client.get_resource.assert_called_once_with(
        service_name="cognition",
        resource_name="search_history",
        params={
            "user_id": "user123", 
            "query": "test", 
            "limit": 5,
            "include_conversations": True
        }
    )
    
    # Verify the result
    assert result["count"] == 2
    assert len(result["results"]) == 2
    assert result["query"] == "test"


@pytest.mark.asyncio
@patch("app.core.tools.get_client")
@patch("app.core.tools.UnitOfWork")
async def test_search_history_without_mcp(mock_uow_class, mock_get_client, mock_uow):
    """Test search_history with no MCP client (fallback)."""
    mock_uow_instance, mock_msg_repo = mock_uow
    mock_uow_class.for_transaction.return_value = mock_uow_instance
    
    # No MCP client
    mock_get_client.return_value = None
    
    # Mock repository behavior
    mock_msg_repo.list_by_sender.return_value = [
        MagicMock(
            id="msg1",
            content="Test message with query",
            timestamp="2023-01-01T00:00:00Z",
            conversation_id="conv1"
        ),
        MagicMock(
            id="msg2",
            content="Another message",
            timestamp="2023-01-02T00:00:00Z",
            conversation_id="conv2"
        )
    ]
    
    # Additional mock for conversation data when include_conversations=True
    mock_msg_repo.list_by_conversation.return_value = [
        MagicMock(content="First message in conversation")
    ]
    
    # Call the function
    result = await search_history("user123", "query", 5, True)
    
    # Verify repository was called
    mock_msg_repo.list_by_sender.assert_called_once_with("user123", limit=100)
    
    # Verify the result
    assert result["count"] == 1  # Only one message matches the query
    assert len(result["results"]) == 1
    assert result["query"] == "query"
    assert result["results"][0]["id"] == "msg1"
    
    # Verify conversation data was included
    assert "_conversation_data" in result["results"][0]
    assert result["results"][0]["_conversation_data"]["message_count"] == 1