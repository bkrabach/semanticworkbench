"""
Unit tests for the cognition-related tools.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

from app.core.tools import get_context, analyze_conversation, search_history


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mocked MCP client."""
    mock = AsyncMock()
    mock.get_resource = AsyncMock(return_value={})
    return mock


@pytest.fixture
def mock_uow() -> tuple[MagicMock, AsyncMock]:
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
async def test_get_context_with_mcp(mock_get_client: MagicMock, mock_client: AsyncMock) -> None:
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
async def test_get_context_with_error(mock_get_client: MagicMock, mock_client: AsyncMock) -> None:
    """Test get_context when MCP client raises an error."""
    # Setup mocked MCP client to raise an exception
    mock_get_client.return_value = mock_client
    mock_client.get_resource.side_effect = Exception("MCP error")
    
    # Call the function
    result = await get_context("user123", "test", 5)
    
    # Verify the MCP client was called correctly
    mock_client.get_resource.assert_called_once_with(
        service_name="cognition",
        resource_name="context",
        params={"user_id": "user123", "query": "test", "limit": 5}
    )
    
    # Verify the result is an empty error response
    assert result["count"] == 0
    assert len(result["context"]) == 0
    assert result["user_id"] == "user123"
    assert result["query"] == "test"
    assert "error" in result


@pytest.mark.asyncio
@patch("app.core.tools.get_client")
async def test_analyze_conversation_with_mcp(mock_get_client: MagicMock, mock_client: AsyncMock) -> None:
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
async def test_analyze_conversation_with_error(mock_get_client: MagicMock, mock_client: AsyncMock) -> None:
    """Test analyze_conversation when MCP client raises an error."""
    # Setup mocked MCP client to raise an exception
    mock_get_client.return_value = mock_client
    mock_client.get_resource.side_effect = Exception("MCP error")
    
    # Call the function
    result = await analyze_conversation("user1", "conv123", "summary")
    
    # Verify the MCP client was called correctly
    mock_client.get_resource.assert_called_once_with(
        service_name="cognition",
        resource_name="analyze_conversation",
        params={"user_id": "user1", "conversation_id": "conv123", "analysis_type": "summary"}
    )
    
    # Verify the result is an error response with empty result
    assert result["type"] == "summary"
    assert result["conversation_id"] == "conv123"
    assert result["results"] == {}
    assert "error" in result


@pytest.mark.asyncio
@patch("app.core.tools.get_client")
async def test_search_history_with_mcp(mock_get_client: MagicMock, mock_client: AsyncMock) -> None:
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
async def test_search_history_with_error(mock_get_client: MagicMock, mock_client: AsyncMock) -> None:
    """Test search_history when MCP client raises an error."""
    # Setup mocked MCP client to raise an exception
    mock_get_client.return_value = mock_client
    mock_client.get_resource.side_effect = Exception("MCP error")
    
    # Call the function
    result = await search_history("user123", "query", 5, True)
    
    # Verify the MCP client was called correctly
    mock_client.get_resource.assert_called_once_with(
        service_name="cognition",
        resource_name="search_history",
        params={
            "user_id": "user123", 
            "query": "query", 
            "limit": 5,
            "include_conversations": True
        }
    )
    
    # Verify the result is an error response with empty results
    assert result["count"] == 0
    assert len(result["results"]) == 0
    assert result["query"] == "query"
    assert "error" in result