import pytest
from unittest.mock import AsyncMock, MagicMock

import uuid
from datetime import datetime

from app.services.memory import MemoryService


class TestMemoryService:
    """Tests for the Memory Service."""

    @pytest.fixture
    def mock_repository_manager(self):
        """Create a mock repository manager."""
        manager = MagicMock()

        # Create mock repositories
        message_repo = MagicMock()
        workspace_repo = MagicMock()
        conversation_repo = MagicMock()

        # Set up repository manager to return the mock repositories
        manager.get_repository = MagicMock(side_effect=lambda name: {
            "messages": message_repo,
            "workspaces": workspace_repo,
            "conversations": conversation_repo
        }.get(name))

        return manager, message_repo, workspace_repo, conversation_repo

    @pytest.mark.asyncio
    async def test_initialize(self, mock_repository_manager):
        """Test service initialization."""
        manager, _, _, _ = mock_repository_manager
        service = MemoryService(manager)

        await service.initialize()

        assert service.initialized
        assert manager.get_repository.call_count == 3

    @pytest.mark.asyncio
    async def test_store_input(self, mock_repository_manager):
        """Test storing input."""
        manager, message_repo, _, _ = mock_repository_manager
        message_repo.create = AsyncMock(return_value="message_id")

        service = MemoryService(manager)
        await service.initialize()

        # Test with valid input
        result = await service.store_input("user123", {
            "content": "Hello, world!",
            "conversation_id": "conv456",
            "metadata": {"source": "test"}
        })

        # Verify repository was called
        message_repo.create.assert_called_once()

        # Verify the message data
        call_args = message_repo.create.call_args[0][0]
        assert call_args["user_id"] == "user123"
        assert call_args["content"] == "Hello, world!"
        assert call_args["conversation_id"] == "conv456"
        assert call_args["metadata"] == {"source": "test"}
        assert "timestamp" in call_args

        # Verify the result
        assert result["status"] == "stored"
        assert result["user_id"] == "user123"
        assert result["item_id"] == "message_id"

    @pytest.mark.asyncio
    async def test_update_message(self, mock_repository_manager):
        """Test updating a message."""
        manager, message_repo, _, _ = mock_repository_manager
        message_repo.find_one = AsyncMock(return_value={
            "id": "msg123",
            "user_id": "user456",
            "content": "Original content",
            "metadata": {"key": "value"}
        })
        message_repo.update = AsyncMock(return_value=True)

        service = MemoryService(manager)
        await service.initialize()

        # Test with valid update
        result = await service.update_message(
            "user456",
            "msg123",
            {"content": "Updated content"}
        )

        # Verify repository calls
        message_repo.find_one.assert_called_once()
        message_repo.update.assert_called_once()

        # Verify the update data
        update_args = message_repo.update.call_args[0]
        assert update_args[0] == {"id": "msg123", "user_id": "user456"}
        assert "content" in update_args[1]["$set"]
        assert update_args[1]["$set"]["content"] == "Updated content"
        assert "updated_at" in update_args[1]["$set"]

        # Verify the result
        assert result["status"] == "updated"
        assert result["user_id"] == "user456"
        assert result["message_id"] == "msg123"

    @pytest.mark.asyncio
    async def test_get_conversation(self, mock_repository_manager):
        """Test getting conversation messages."""
        manager, message_repo, _, _ = mock_repository_manager
        messages = [
            {"id": "msg1", "content": "Message 1"},
            {"id": "msg2", "content": "Message 2"}
        ]
        message_repo.find_many = AsyncMock(return_value=messages)

        service = MemoryService(manager)
        await service.initialize()

        # Test getting conversation
        result = await service.get_conversation("conv123")

        # Verify repository call
        message_repo.find_many.assert_called_once_with(
            {"conversation_id": "conv123"},
            sort=[("timestamp", 1)]
        )

        # Verify the result
        assert result == messages