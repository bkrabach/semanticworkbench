"""
Tests for the database migration module.
"""

import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.migration import migrate_to_sqlite


@pytest.fixture
def mock_storage_data() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Mock data for storage module."""
    return {
        "users": {
            "user-1": {"user_id": "user-1", "name": "Test User", "email": "test@example.com", "metadata": {}},
            "user-2": {"user_id": "user-2", "name": "Another User", "email": "another@example.com", "metadata": {}},
        },
        "workspaces": {
            "workspace-1": {
                "id": "workspace-1", 
                "name": "Test Workspace", 
                "description": "A test workspace", 
                "owner_id": "user-1",
                "metadata": {},
            },
        },
        "conversations": {
            "conv-1": {
                "id": "conv-1", 
                "workspace_id": "workspace-1", 
                "topic": "Test Conversation", 
                "participant_ids": ["user-1", "user-2"],
                "metadata": {},
            },
        },
        "messages": {
            "msg-1": {
                "id": "msg-1", 
                "conversation_id": "conv-1", 
                "sender_id": "user-1", 
                "content": "Hello world",
                "timestamp": "2023-01-01T12:00:00",
                "metadata": {},
            },
            "msg-2": {
                "id": "msg-2", 
                "conversation_id": "conv-1", 
                "sender_id": "user-2", 
                "content": "Hi there!",
                "timestamp": "2023-01-01T12:01:00",
                "metadata": {},
            },
        },
    }


@pytest.mark.asyncio
async def test_migrate_to_sqlite_success(mock_storage_data: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
    """Test successful migration from in-memory storage to SQLite."""
    # Mock the storage dictionaries
    with patch("app.database.migration.storage") as mock_storage:
        # Set up the mock storage data
        mock_storage.users = mock_storage_data["users"]
        mock_storage.workspaces = mock_storage_data["workspaces"]
        mock_storage.conversations = mock_storage_data["conversations"]
        mock_storage.messages = mock_storage_data["messages"]
        
        # Mock repositories
        mock_user_repo = AsyncMock()
        mock_workspace_repo = AsyncMock()
        mock_conversation_repo = AsyncMock()
        mock_message_repo = AsyncMock()
        
        # Mock unit of work and repository factory
        mock_repo_factory = MagicMock()
        mock_repo_factory.get_user_repository.return_value = mock_user_repo
        mock_repo_factory.get_workspace_repository.return_value = mock_workspace_repo
        mock_repo_factory.get_conversation_repository.return_value = mock_conversation_repo
        mock_repo_factory.get_message_repository.return_value = mock_message_repo
        
        mock_uow = AsyncMock()
        mock_uow.repositories = mock_repo_factory
        mock_uow.commit = AsyncMock()
        
        # Mock the context manager
        mock_uow_context = AsyncMock()
        mock_uow_context.__aenter__.return_value = mock_uow
        mock_uow_context.__aexit__.return_value = None
        
        # Run the migration with mocked dependencies
        with patch("app.database.migration.UnitOfWork.for_transaction", return_value=mock_uow_context):
            stats = await migrate_to_sqlite()
        
        # Verify the correct repositories were called with the right models
        assert mock_user_repo.create.call_count == 2
        assert mock_workspace_repo.create.call_count == 1
        assert mock_conversation_repo.create.call_count == 1
        assert mock_message_repo.create.call_count == 2
        
        # Verify UoW commit was called
        mock_uow.commit.assert_called_once()
        
        # Verify the stats
        assert stats["users"] == 2
        assert stats["workspaces"] == 1
        assert stats["conversations"] == 1
        assert stats["messages"] == 2
        assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_migrate_to_sqlite_with_errors(mock_storage_data: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
    """Test migration with some errors during the process."""
    # Mock the storage dictionaries
    with patch("app.database.migration.storage") as mock_storage:
        # Set up the mock storage data
        mock_storage.users = mock_storage_data["users"]
        mock_storage.workspaces = mock_storage_data["workspaces"]
        mock_storage.conversations = mock_storage_data["conversations"]
        mock_storage.messages = mock_storage_data["messages"]
        
        # Mock repositories
        mock_user_repo = AsyncMock()
        mock_user_repo.create.side_effect = [None, Exception("User creation error")]
        
        mock_workspace_repo = AsyncMock()
        mock_conversation_repo = AsyncMock()
        mock_message_repo = AsyncMock()
        
        # Mock unit of work and repository factory
        mock_repo_factory = MagicMock()
        mock_repo_factory.get_user_repository.return_value = mock_user_repo
        mock_repo_factory.get_workspace_repository.return_value = mock_workspace_repo
        mock_repo_factory.get_conversation_repository.return_value = mock_conversation_repo
        mock_repo_factory.get_message_repository.return_value = mock_message_repo
        
        mock_uow = AsyncMock()
        mock_uow.repositories = mock_repo_factory
        mock_uow.commit = AsyncMock()
        
        # Mock the context manager
        mock_uow_context = AsyncMock()
        mock_uow_context.__aenter__.return_value = mock_uow
        mock_uow_context.__aexit__.return_value = None
        
        # Run the migration with mocked dependencies
        with patch("app.database.migration.UnitOfWork.for_transaction", return_value=mock_uow_context):
            stats = await migrate_to_sqlite()
        
        # Verify the counts and error
        assert stats["users"] == 1  # Only one user created successfully
        assert stats["errors"] == 1  # One error occurred


@pytest.mark.asyncio
async def test_migrate_to_sqlite_transaction_error() -> None:
    """Test migration when the transaction itself fails."""
    # Mock an exception during the UoW context
    mock_uow_context = AsyncMock()
    mock_uow_context.__aenter__.side_effect = Exception("Transaction failed")
    
    # Run the migration with mocked dependency
    with patch("app.database.migration.UnitOfWork.for_transaction", return_value=mock_uow_context):
        stats = await migrate_to_sqlite()
    
    # Verify the error count
    assert stats["errors"] == 1
    assert stats["users"] == 0
    assert stats["workspaces"] == 0
    assert stats["conversations"] == 0
    assert stats["messages"] == 0


@pytest.mark.asyncio
async def test_migrate_to_sqlite_model_validation_error(mock_storage_data: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
    """Test migration with model validation errors."""
    # Modify the data to create validation errors
    invalid_data = mock_storage_data.copy()
    invalid_data["users"]["user-1"]["email"] = None  # Missing required email
    
    # Mock the storage dictionaries
    with patch("app.database.migration.storage") as mock_storage:
        # Set up the mock storage data
        mock_storage.users = invalid_data["users"]
        mock_storage.workspaces = invalid_data["workspaces"]
        mock_storage.conversations = invalid_data["conversations"]
        mock_storage.messages = invalid_data["messages"]
        
        # Mock repositories with a validation exception on first user
        mock_user_repo = AsyncMock()
        mock_user_repo.create.side_effect = Exception("Validation error: email is required")
        
        mock_workspace_repo = AsyncMock()
        mock_conversation_repo = AsyncMock()
        mock_message_repo = AsyncMock()
        
        # Mock unit of work and repository factory
        mock_repo_factory = MagicMock()
        mock_repo_factory.get_user_repository.return_value = mock_user_repo
        mock_repo_factory.get_workspace_repository.return_value = mock_workspace_repo
        mock_repo_factory.get_conversation_repository.return_value = mock_conversation_repo
        mock_repo_factory.get_message_repository.return_value = mock_message_repo
        
        mock_uow = AsyncMock()
        mock_uow.repositories = mock_repo_factory
        mock_uow.commit = AsyncMock()
        
        # Mock the context manager
        mock_uow_context = AsyncMock()
        mock_uow_context.__aenter__.return_value = mock_uow
        mock_uow_context.__aexit__.return_value = None
        
        # Run the migration with mocked dependencies
        with patch("app.database.migration.UnitOfWork.for_transaction", return_value=mock_uow_context):
            stats = await migrate_to_sqlite()
        
        # Verify the error count
        assert stats["errors"] >= 1
        assert stats["users"] == 0  # No users created due to validation error