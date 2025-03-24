"""
Tests for the repository module.
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.core.exceptions import DatabaseError
from app.core.repository import (
    Repository,
    RepositoryManager,
    MessageRepository,
    ConversationRepository,
    WorkspaceRepository,
    UserRepository
)


@pytest.fixture
def repository_manager() -> RepositoryManager:
    """Create a RepositoryManager instance for testing."""
    return RepositoryManager()


@pytest.mark.asyncio
async def test_repository_manager_initialize() -> None:
    """Test initializing the repository manager."""
    # Create a RepositoryManager instance
    manager = RepositoryManager()
    
    # Call initialize
    await manager.initialize()
    
    # Not much to assert here since initialize() just logs a message


def test_repository_manager_get_repository(repository_manager: RepositoryManager) -> None:
    """Test getting repositories by name."""
    # Get each type of repository
    message_repo = repository_manager.get_repository("messages")
    workspace_repo = repository_manager.get_repository("workspaces")
    conversation_repo = repository_manager.get_repository("conversations")
    user_repo = repository_manager.get_repository("users")
    
    # Verify the correct repository types are returned
    assert isinstance(message_repo, MessageRepository)
    assert isinstance(workspace_repo, WorkspaceRepository)
    assert isinstance(conversation_repo, ConversationRepository)
    assert isinstance(user_repo, UserRepository)


def test_repository_manager_get_invalid_repository(repository_manager: RepositoryManager) -> None:
    """Test getting an invalid repository name."""
    # Try to get a non-existent repository
    with pytest.raises(ValueError) as exc_info:
        repository_manager.get_repository("invalid")
    
    # Verify the error message
    assert "Unknown repository: invalid" in str(exc_info.value)


@pytest.mark.asyncio
async def test_message_repository_create() -> None:
    """Test creating a message."""
    # Create test message data
    message_data = {
        "conversation_id": "test-conversation",
        "user_id": "test-user",  # Will be mapped to sender_id
        "content": "Test message",
        "metadata": {"role": "user"}
    }
    
    # Mock the domain Message class and UnitOfWork
    with patch("app.models.Message") as mock_message_class, \
         patch("app.core.repository.UnitOfWork.for_transaction") as mock_uow_context:
        
        # Set up the mocks
        mock_message_instance = Mock()
        mock_message_class.return_value = mock_message_instance
        
        mock_message_repo = AsyncMock()
        mock_created_message = Mock()
        mock_created_message.id = "message-id-123"
        mock_message_repo.create = AsyncMock(return_value=mock_created_message)
        
        mock_uow = Mock()
        mock_uow.repositories = Mock()
        mock_uow.repositories.get_message_repository.return_value = mock_message_repo
        mock_uow.commit = AsyncMock()
        
        mock_uow_context_manager = AsyncMock()
        mock_uow_context_manager.__aenter__.return_value = mock_uow
        mock_uow_context.return_value = mock_uow_context_manager
        
        # Create a MessageRepository instance
        repo = MessageRepository()
        
        # Call create
        result_id = await repo.create(message_data)
        
        # Verify the result
        assert result_id == "message-id-123"
        
        # Verify Message constructor was called with the correct arguments
        mock_message_class.assert_called_once()
        _, kwargs = mock_message_class.call_args
        assert kwargs["conversation_id"] == "test-conversation"
        assert kwargs["sender_id"] == "test-user"  # Mapped from user_id
        assert kwargs["content"] == "Test message"
        assert kwargs["metadata"] == {"role": "user"}
        
        # Verify repository operations
        mock_message_repo.create.assert_called_once_with(mock_message_instance)
        mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_message_repository_create_error() -> None:
    """Test error handling when creating a message fails."""
    # Create test message data
    message_data = {
        "conversation_id": "test-conversation",
        "user_id": "test-user",
        "content": "Test message"
    }
    
    # Mock the domain Message class and UnitOfWork to raise an exception
    with patch("app.models.Message") as mock_message_class, \
         patch("app.core.repository.UnitOfWork.for_transaction") as mock_uow_context:
        
        # Set up the mocks to raise an exception
        mock_message_instance = Mock()
        mock_message_class.return_value = mock_message_instance
        
        mock_uow_context_manager = AsyncMock()
        mock_uow_context_manager.__aenter__.side_effect = Exception("Database error")
        mock_uow_context.return_value = mock_uow_context_manager
        
        # Create a MessageRepository instance
        repo = MessageRepository()
        
        # Call create, which should raise DatabaseError
        with pytest.raises(DatabaseError) as exc_info:
            await repo.create(message_data)
        
        # Verify the error message
        assert "Failed to create message" in str(exc_info.value)


@pytest.mark.asyncio
async def test_message_repository_find_one() -> None:
    """Test finding a single message."""
    # Create test query
    query = {
        "id": "message-id-123"
    }
    
    # Mock UnitOfWork and message repository
    with patch("app.core.repository.UnitOfWork.for_transaction") as mock_uow_context:
        # Set up the mocks
        mock_message = Mock()
        mock_message.id = "message-id-123"
        mock_message.sender_id = "test-user"
        mock_message.conversation_id = "test-conversation"
        mock_message.content = "Test message"
        mock_message.timestamp = "2023-01-01T12:00:00"
        mock_message.metadata = {"role": "user"}
        
        mock_message_repo = AsyncMock()
        mock_message_repo.get_by_id = AsyncMock(return_value=mock_message)
        
        mock_uow = Mock()
        mock_uow.repositories = Mock()
        mock_uow.repositories.get_message_repository.return_value = mock_message_repo
        
        mock_uow_context_manager = AsyncMock()
        mock_uow_context_manager.__aenter__.return_value = mock_uow
        mock_uow_context.return_value = mock_uow_context_manager
        
        # Create a MessageRepository instance
        repo = MessageRepository()
        
        # Call find_one
        result = await repo.find_one(query)
        
        # Verify the result
        assert result is not None
        assert result["id"] == "message-id-123"
        assert result["user_id"] == "test-user"  # Mapped from sender_id
        assert result["conversation_id"] == "test-conversation"
        assert result["content"] == "Test message"
        assert result["timestamp"] == "2023-01-01T12:00:00"
        assert result["metadata"] == {"role": "user"}
        
        # Verify repository operations
        mock_message_repo.get_by_id.assert_called_once_with("message-id-123")


@pytest.mark.asyncio
async def test_message_repository_find_one_no_id() -> None:
    """Test finding a single message without an ID (using list method)."""
    # Create test query without an ID
    query = {
        "user_id": "test-user",
        "conversation_id": "test-conversation"
    }
    
    # Mock UnitOfWork and message repository
    with patch("app.core.repository.UnitOfWork.for_transaction") as mock_uow_context:
        # Set up the mocks
        mock_message = Mock()
        mock_message.id = "message-id-123"
        mock_message.sender_id = "test-user"
        mock_message.conversation_id = "test-conversation"
        mock_message.content = "Test message"
        mock_message.timestamp = "2023-01-01T12:00:00"
        mock_message.metadata = {"role": "user"}
        
        mock_message_repo = AsyncMock()
        mock_message_repo.list = AsyncMock(return_value=[mock_message])
        
        mock_uow = Mock()
        mock_uow.repositories = Mock()
        mock_uow.repositories.get_message_repository.return_value = mock_message_repo
        
        mock_uow_context_manager = AsyncMock()
        mock_uow_context_manager.__aenter__.return_value = mock_uow
        mock_uow_context.return_value = mock_uow_context_manager
        
        # Create a MessageRepository instance
        repo = MessageRepository()
        
        # Call find_one
        result = await repo.find_one(query)
        
        # Verify the result
        assert result is not None
        assert result["id"] == "message-id-123"
        assert result["user_id"] == "test-user"
        assert result["conversation_id"] == "test-conversation"
        
        # Verify repository operations
        mock_message_repo.list.assert_called_once_with(
            filters={"sender_id": "test-user", "conversation_id": "test-conversation"}, 
            limit=1
        )


@pytest.mark.asyncio
async def test_message_repository_find_one_not_found() -> None:
    """Test finding a single message that doesn't exist."""
    # Create test query
    query = {
        "id": "non-existent-id"
    }
    
    # Mock UnitOfWork and message repository
    with patch("app.core.repository.UnitOfWork.for_transaction") as mock_uow_context:
        # Set up the mocks to return None (message not found)
        mock_message_repo = AsyncMock()
        mock_message_repo.get_by_id = AsyncMock(return_value=None)
        
        mock_uow = Mock()
        mock_uow.repositories = Mock()
        mock_uow.repositories.get_message_repository.return_value = mock_message_repo
        
        mock_uow_context_manager = AsyncMock()
        mock_uow_context_manager.__aenter__.return_value = mock_uow
        mock_uow_context.return_value = mock_uow_context_manager
        
        # Create a MessageRepository instance
        repo = MessageRepository()
        
        # Call find_one
        result = await repo.find_one(query)
        
        # Verify the result is None
        assert result is None
        
        # Verify repository operations
        mock_message_repo.get_by_id.assert_called_once_with("non-existent-id")


@pytest.mark.asyncio
async def test_message_repository_find_one_error() -> None:
    """Test error handling when finding a message fails."""
    # Create test query
    query = {
        "id": "message-id"
    }
    
    # Mock UnitOfWork to raise an exception
    with patch("app.core.repository.UnitOfWork.for_transaction") as mock_uow_context:
        # Set up the mocks to raise an exception
        mock_uow_context_manager = AsyncMock()
        mock_uow_context_manager.__aenter__.side_effect = Exception("Database error")
        mock_uow_context.return_value = mock_uow_context_manager
        
        # Create a MessageRepository instance
        repo = MessageRepository()
        
        # Call find_one, which should return None when an exception occurs
        result = await repo.find_one(query)
        
        # Verify the result is None
        assert result is None


@pytest.mark.asyncio
async def test_message_repository_find_many_by_conversation() -> None:
    """Test finding messages by conversation ID."""
    # Create test query for messages in a conversation
    query = {
        "conversation_id": "test-conversation"
    }
    
    # Mock UnitOfWork and message repository
    with patch("app.core.repository.UnitOfWork.for_transaction") as mock_uow_context:
        # Set up the mocks
        mock_message1 = Mock()
        mock_message1.id = "message-1"
        mock_message1.sender_id = "user-1"
        mock_message1.conversation_id = "test-conversation"
        mock_message1.content = "Message 1"
        mock_message1.timestamp = "2023-01-01T12:00:00"
        mock_message1.metadata = {"role": "user"}
        
        mock_message2 = Mock()
        mock_message2.id = "message-2"
        mock_message2.sender_id = "user-2"
        mock_message2.conversation_id = "test-conversation"
        mock_message2.content = "Message 2"
        mock_message2.timestamp = "2023-01-01T12:01:00"
        mock_message2.metadata = {"role": "assistant"}
        
        mock_message_repo = AsyncMock()
        mock_message_repo.list_by_conversation = AsyncMock(
            return_value=[mock_message1, mock_message2]
        )
        
        mock_uow = Mock()
        mock_uow.repositories = Mock()
        mock_uow.repositories.get_message_repository.return_value = mock_message_repo
        
        mock_uow_context_manager = AsyncMock()
        mock_uow_context_manager.__aenter__.return_value = mock_uow
        mock_uow_context.return_value = mock_uow_context_manager
        
        # Create a MessageRepository instance
        repo = MessageRepository()
        
        # Call find_many
        results = await repo.find_many(query, limit=10)
        
        # Verify the results
        assert len(results) == 2
        assert results[0]["id"] == "message-1"
        assert results[0]["user_id"] == "user-1"
        assert results[1]["id"] == "message-2"
        assert results[1]["user_id"] == "user-2"
        
        # Verify repository operations
        mock_message_repo.list_by_conversation.assert_called_once_with(
            "test-conversation", limit=10
        )


@pytest.mark.asyncio
async def test_message_repository_find_many_with_sort() -> None:
    """Test finding messages with sorting."""
    # Create test query with sort
    query = {
        "conversation_id": "test-conversation"
    }
    sort = [("timestamp", -1)]  # Sort by timestamp descending
    
    # Mock UnitOfWork and message repository
    with patch("app.core.repository.UnitOfWork.for_transaction") as mock_uow_context:
        # Set up the mocks
        mock_message1 = Mock()
        mock_message1.id = "message-1"
        mock_message1.sender_id = "user-1"
        mock_message1.conversation_id = "test-conversation"
        mock_message1.content = "Message 1"
        mock_message1.timestamp = "2023-01-01T12:00:00"
        mock_message1.metadata = {"role": "user"}
        
        mock_message2 = Mock()
        mock_message2.id = "message-2"
        mock_message2.sender_id = "user-2"
        mock_message2.conversation_id = "test-conversation"
        mock_message2.content = "Message 2"
        mock_message2.timestamp = "2023-01-01T12:01:00"
        mock_message2.metadata = {"role": "assistant"}
        
        # For descending order, return in the order we want them reversed
        mock_message_repo = AsyncMock()
        mock_message_repo.list_by_conversation = AsyncMock(
            return_value=[mock_message1, mock_message2]
        )
        
        mock_uow = Mock()
        mock_uow.repositories = Mock()
        mock_uow.repositories.get_message_repository.return_value = mock_message_repo
        
        mock_uow_context_manager = AsyncMock()
        mock_uow_context_manager.__aenter__.return_value = mock_uow
        mock_uow_context.return_value = mock_uow_context_manager
        
        # Create a MessageRepository instance
        repo = MessageRepository()
        
        # Call find_many
        results = await repo.find_many(query, limit=10, sort=sort)
        
        # Verify the results - they should be reversed for descending order
        assert len(results) == 2
        assert results[0]["id"] == "message-2"  # This is because we reversed the list
        assert results[1]["id"] == "message-1"
        
        # Verify repository operations
        mock_message_repo.list_by_conversation.assert_called_once_with(
            "test-conversation", limit=10
        )


@pytest.mark.asyncio
async def test_message_repository_update() -> None:
    """Test updating a message."""
    # Create test query and update data
    query = {
        "id": "message-id-123"
    }
    update = {
        "$set": {
            "content": "Updated content",
            "metadata": {"status": "edited"},
            "updated_at": "2023-01-01T13:00:00"
        }
    }
    
    # Mock UnitOfWork and message repository
    with patch("app.core.repository.UnitOfWork.for_transaction") as mock_uow_context:
        # Set up the mocks
        mock_message = Mock()
        mock_message.id = "message-id-123"
        mock_message.content = "Original content"
        mock_message.metadata = {}
        
        mock_message_repo = AsyncMock()
        mock_message_repo.get_by_id = AsyncMock(return_value=mock_message)
        mock_message_repo.update = AsyncMock(return_value=True)
        
        mock_uow = Mock()
        mock_uow.repositories = Mock()
        mock_uow.repositories.get_message_repository.return_value = mock_message_repo
        mock_uow.commit = AsyncMock()
        
        mock_uow_context_manager = AsyncMock()
        mock_uow_context_manager.__aenter__.return_value = mock_uow
        mock_uow_context.return_value = mock_uow_context_manager
        
        # Create a MessageRepository instance
        repo = MessageRepository()
        
        # Call update
        result = await repo.update(query, update)
        
        # Verify the result
        assert result is True
        
        # Verify the message was updated correctly
        assert mock_message.content == "Updated content"
        assert mock_message.metadata == {"status": "edited", "updated_at": "2023-01-01T13:00:00"}
        
        # Verify repository operations
        mock_message_repo.get_by_id.assert_called_once_with("message-id-123")
        mock_message_repo.update.assert_called_once_with(mock_message)
        mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_message_repository_update_not_found() -> None:
    """Test updating a message that doesn't exist."""
    # Create test query and update data
    query = {
        "id": "non-existent-id"
    }
    update = {
        "$set": {
            "content": "Updated content"
        }
    }
    
    # Mock UnitOfWork and message repository
    with patch("app.core.repository.UnitOfWork.for_transaction") as mock_uow_context:
        # Set up the mocks to return None (message not found)
        mock_message_repo = AsyncMock()
        mock_message_repo.get_by_id = AsyncMock(return_value=None)
        
        mock_uow = Mock()
        mock_uow.repositories = Mock()
        mock_uow.repositories.get_message_repository.return_value = mock_message_repo
        
        mock_uow_context_manager = AsyncMock()
        mock_uow_context_manager.__aenter__.return_value = mock_uow
        mock_uow_context.return_value = mock_uow_context_manager
        
        # Create a MessageRepository instance
        repo = MessageRepository()
        
        # Call update
        result = await repo.update(query, update)
        
        # Verify the result is False (update failed)
        assert result is False
        
        # Verify repository operations
        mock_message_repo.get_by_id.assert_called_once_with("non-existent-id")


@pytest.mark.asyncio
async def test_message_repository_delete_one() -> None:
    """Test deleting a message."""
    # Create test query
    query = {
        "id": "message-id-123",
        "user_id": "user-123"  # Include user_id for ownership check
    }
    
    # Mock UnitOfWork and message repository
    with patch("app.core.repository.UnitOfWork.for_transaction") as mock_uow_context:
        # Set up the mocks
        mock_message = Mock()
        mock_message.id = "message-id-123"
        mock_message.sender_id = "user-123"
        
        mock_message_repo = AsyncMock()
        mock_message_repo.get_by_id = AsyncMock(return_value=mock_message)
        mock_message_repo.delete = AsyncMock(return_value=True)
        
        mock_uow = Mock()
        mock_uow.repositories = Mock()
        mock_uow.repositories.get_message_repository.return_value = mock_message_repo
        mock_uow.commit = AsyncMock()
        
        mock_uow_context_manager = AsyncMock()
        mock_uow_context_manager.__aenter__.return_value = mock_uow
        mock_uow_context.return_value = mock_uow_context_manager
        
        # Create a MessageRepository instance
        repo = MessageRepository()
        
        # Call delete_one
        result = await repo.delete_one(query)
        
        # Verify the result
        assert result is True
        
        # Verify repository operations
        mock_message_repo.get_by_id.assert_called_once_with("message-id-123")
        mock_message_repo.delete.assert_called_once_with("message-id-123")
        mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_message_repository_delete_one_wrong_owner() -> None:
    """Test deleting a message with incorrect ownership."""
    # Create test query with wrong user_id
    query = {
        "id": "message-id-123",
        "user_id": "wrong-user"  # This user is not the message owner
    }
    
    # Mock UnitOfWork and message repository
    with patch("app.core.repository.UnitOfWork.for_transaction") as mock_uow_context:
        # Set up the mocks
        mock_message = Mock()
        mock_message.id = "message-id-123"
        mock_message.sender_id = "correct-user"  # Different from query user_id
        
        mock_message_repo = AsyncMock()
        mock_message_repo.get_by_id = AsyncMock(return_value=mock_message)
        
        mock_uow = Mock()
        mock_uow.repositories = Mock()
        mock_uow.repositories.get_message_repository.return_value = mock_message_repo
        
        mock_uow_context_manager = AsyncMock()
        mock_uow_context_manager.__aenter__.return_value = mock_uow
        mock_uow_context.return_value = mock_uow_context_manager
        
        # Create a MessageRepository instance
        repo = MessageRepository()
        
        # Call delete_one
        result = await repo.delete_one(query)
        
        # Verify the result is False (delete failed due to wrong owner)
        assert result is False
        
        # Verify repository operations
        mock_message_repo.get_by_id.assert_called_once_with("message-id-123")
        # Verify delete was not called
        mock_message_repo.delete.assert_not_called()


def test_abstract_repository_methods() -> None:
    """Test that abstract Repository methods raise NotImplementedError."""
    # Create a base Repository instance
    repo = Repository()
    
    # Test each abstract method
    with pytest.raises(NotImplementedError):
        asyncio.run(repo.create({}))
    
    with pytest.raises(NotImplementedError):
        asyncio.run(repo.find_one({}))
    
    with pytest.raises(NotImplementedError):
        asyncio.run(repo.find_many({}))
    
    with pytest.raises(NotImplementedError):
        asyncio.run(repo.update({}, {}))
    
    with pytest.raises(NotImplementedError):
        asyncio.run(repo.delete_one({}))