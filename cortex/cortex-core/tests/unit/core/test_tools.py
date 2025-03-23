"""
Unit tests for the tools module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.core.tools import (
    get_conversation_summary,
    get_current_time,
    get_user_info,
    list_workspaces,
    ConversationSummaryOutput,
    TimeOutput,
    UserInfoOutput,
    WorkspaceListOutput
)
from app.models import Conversation, Message, User, Workspace


@pytest.mark.asyncio
async def test_get_current_time() -> None:
    """Test the get_current_time tool."""
    # Execute the tool
    result = await get_current_time()
    
    # Verify basic structure
    assert isinstance(result, dict)
    assert "iso_format" in result
    assert "date" in result
    assert "time" in result
    assert "year" in result
    assert "month" in result
    assert "day" in result
    assert "day_of_week" in result
    
    # Verify that the returned date is reasonable
    now = datetime.now()
    assert now.strftime("%Y") == result["year"]
    assert now.strftime("%d") == result["day"]


@pytest.mark.asyncio
async def test_get_user_info() -> None:
    """Test the get_user_info tool with mock repository."""
    # Mock the UnitOfWork and repository
    mock_user = User(user_id="test-user", name="Test User", email="test@example.com")
    
    with patch("app.core.tools.UnitOfWork.for_transaction") as mock_uow:
        # Set up the mock repositories
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
        
        # Set up the mock unit of work
        mock_uow_context = AsyncMock()
        mock_uow_context.__aenter__ = AsyncMock(return_value=mock_uow_context)
        mock_uow_context.__aexit__ = AsyncMock(return_value=None)
        mock_uow_context.repositories = MagicMock()
        mock_uow_context.repositories.get_user_repository = MagicMock(return_value=mock_user_repo)
        mock_uow.return_value = mock_uow_context
        
        # Call the tool
        result = await get_user_info("test-user")
        
        # Verify the result
        assert result["user_id"] == "test-user"
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"
        assert result["status"] == "active"


@pytest.mark.asyncio
async def test_get_user_info_not_found() -> None:
    """Test the get_user_info tool with a non-existent user."""
    with patch("app.core.tools.UnitOfWork.for_transaction") as mock_uow:
        # Set up the mock repositories
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=None)
        
        # Set up the mock unit of work
        mock_uow_context = AsyncMock()
        mock_uow_context.__aenter__ = AsyncMock(return_value=mock_uow_context)
        mock_uow_context.__aexit__ = AsyncMock(return_value=None)
        mock_uow_context.repositories = MagicMock()
        mock_uow_context.repositories.get_user_repository = MagicMock(return_value=mock_user_repo)
        mock_uow.return_value = mock_uow_context
        
        # Call the tool
        result = await get_user_info("non-existent-user")
        
        # Verify the result for non-existent user
        assert result["user_id"] == "non-existent-user"
        assert result["name"] == "Unknown User"
        assert result["email"] is None
        assert result["status"] == "not_found"


@pytest.mark.asyncio
async def test_list_workspaces() -> None:
    """Test the list_workspaces tool."""
    # Create mock workspaces
    mock_workspaces = [
        Workspace(id="ws1", name="Workspace 1", description="First workspace", owner_id="user1"),
        Workspace(id="ws2", name="Workspace 2", description="Second workspace", owner_id="user1"),
    ]
    
    with patch("app.core.tools.UnitOfWork.for_transaction") as mock_uow:
        # Set up the mock repositories
        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.list_by_owner = AsyncMock(return_value=mock_workspaces)
        
        # Set up the mock unit of work
        mock_uow_context = AsyncMock()
        mock_uow_context.__aenter__ = AsyncMock(return_value=mock_uow_context)
        mock_uow_context.__aexit__ = AsyncMock(return_value=None)
        mock_uow_context.repositories = MagicMock()
        mock_uow_context.repositories.get_workspace_repository = MagicMock(return_value=mock_workspace_repo)
        mock_uow.return_value = mock_uow_context
        
        # Call the tool
        result = await list_workspaces("user1", limit=10)
        
        # Verify the result
        assert result["count"] == 2
        assert len(result["workspaces"]) == 2
        workspace_ids = {ws["id"] for ws in result["workspaces"]}
        assert workspace_ids == {"ws1", "ws2"}


@pytest.mark.asyncio
async def test_get_conversation_summary() -> None:
    """Test the get_conversation_summary tool."""
    # Mock data
    mock_conversation = Conversation(
        id="conv1", 
        workspace_id="ws1", 
        topic="Test Conversation", 
        participant_ids=["user1", "user2"]
    )
    
    mock_messages = [
        Message(id="msg1", conversation_id="conv1", sender_id="user1", content="Hello"),
        Message(id="msg2", conversation_id="conv1", sender_id="user2", content="Hi there"),
    ]
    
    with patch("app.core.tools.UnitOfWork.for_transaction") as mock_uow:
        # Set up the mock repositories
        mock_conversation_repo = AsyncMock()
        mock_conversation_repo.get_by_id = AsyncMock(return_value=mock_conversation)
        
        mock_message_repo = AsyncMock()
        mock_message_repo.list_by_conversation = AsyncMock(return_value=mock_messages)
        
        # Set up the mock unit of work
        mock_uow_context = AsyncMock()
        mock_uow_context.__aenter__ = AsyncMock(return_value=mock_uow_context)
        mock_uow_context.__aexit__ = AsyncMock(return_value=None)
        mock_uow_context.repositories = MagicMock()
        mock_uow_context.repositories.get_conversation_repository = MagicMock(return_value=mock_conversation_repo)
        mock_uow_context.repositories.get_message_repository = MagicMock(return_value=mock_message_repo)
        mock_uow.return_value = mock_uow_context
        
        # Call the tool
        result = await get_conversation_summary("conv1", "user1")
        
        # Verify the result
        assert result["message_count"] == 2
        assert result["topic"] == "Test Conversation"
        assert result["participant_count"] == 2
        assert "Conversation with topic: Test Conversation" in result["summary"]


@pytest.mark.asyncio
async def test_get_conversation_summary_not_found() -> None:
    """Test the get_conversation_summary tool with a non-existent conversation."""
    with patch("app.core.tools.UnitOfWork.for_transaction") as mock_uow:
        # Set up the mock repositories
        mock_conversation_repo = AsyncMock()
        mock_conversation_repo.get_by_id = AsyncMock(return_value=None)
        
        mock_message_repo = AsyncMock()
        mock_message_repo.list_by_conversation = AsyncMock(return_value=[])
        
        # Set up the mock unit of work
        mock_uow_context = AsyncMock()
        mock_uow_context.__aenter__ = AsyncMock(return_value=mock_uow_context)
        mock_uow_context.__aexit__ = AsyncMock(return_value=None)
        mock_uow_context.repositories = MagicMock()
        mock_uow_context.repositories.get_conversation_repository = MagicMock(return_value=mock_conversation_repo)
        mock_uow_context.repositories.get_message_repository = MagicMock(return_value=mock_message_repo)
        mock_uow.return_value = mock_uow_context
        
        # Call the tool
        result = await get_conversation_summary("non-existent-conv", "user1")
        
        # Verify the result for non-existent conversation
        assert result["message_count"] == 0
        assert result["topic"] == "unknown"
        assert result["participant_count"] == 0
        assert result["summary"] == "Conversation not found"