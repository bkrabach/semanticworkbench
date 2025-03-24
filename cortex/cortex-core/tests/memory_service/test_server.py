from unittest import mock

import pytest

from memory_service.models import (
    MemoryEntry,
    MemoryRetrievalRequest,
    MemoryRetrievalResponse,
    MemoryUpdateRequest,
    MemoryUpdateResponse,
)
from memory_service.memory_updater import MemoryUpdateResult
from memory_service.server import delete_memory, get_memory, health, memory_resource, update_memory


# Create an awaitable mock class
class AsyncMock:
    """A simple awaitable mock."""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
        
    def __await__(self):
        async def _coro():
            return self.return_value
        return _coro().__await__()


class TestServerEndpoints:
    """Tests for the Memory Service MCP server endpoints."""

    def setup_method(self):
        """Set up mocks for each test."""
        # Patch the MemoryStore
        self.memory_store_patch = mock.patch("memory_service.server.memory_store")
        self.mock_memory_store = self.memory_store_patch.start()
        
        # Patch the MemoryUpdater
        self.memory_updater_patch = mock.patch("memory_service.server.memory_updater")
        self.mock_memory_updater = self.memory_updater_patch.start()

    def teardown_method(self):
        """Clean up after each test."""
        self.memory_store_patch.stop()
        self.memory_updater_patch.stop()

    @pytest.mark.asyncio
    async def test_get_memory_existing(self):
        """Test retrieving an existing memory."""
        # Set up mock memory
        mock_memory = MemoryEntry(
            conversation_id="test-convo-123",
            memory_content="This is a test memory",
            last_updated="2023-01-01T12:00:00"
        )
        self.mock_memory_store.get_memory.return_value = mock_memory
        
        # Create request
        request = MemoryRetrievalRequest(conversation_id="test-convo-123")
        
        # Call the endpoint
        response = await get_memory(request)
        
        # Check the response
        assert isinstance(response, MemoryRetrievalResponse)
        assert response.conversation_id == "test-convo-123"
        assert response.memory_content == "This is a test memory"
        assert response.exists is True
        
        # Verify the store was called correctly
        self.mock_memory_store.get_memory.assert_called_once_with("test-convo-123")

    @pytest.mark.asyncio
    async def test_get_memory_nonexistent(self):
        """Test retrieving a nonexistent memory."""
        # Set up mock to return None (memory doesn't exist)
        self.mock_memory_store.get_memory.return_value = None
        
        # Create request
        request = MemoryRetrievalRequest(conversation_id="nonexistent-convo")
        
        # Call the endpoint
        response = await get_memory(request)
        
        # Check the response
        assert isinstance(response, MemoryRetrievalResponse)
        assert response.conversation_id == "nonexistent-convo"
        assert response.memory_content is None
        assert response.exists is False

    @pytest.mark.asyncio
    async def test_update_memory_new(self):
        """Test updating memory when it doesn't exist yet (create new)."""
        # Set up mocks
        self.mock_memory_store.get_memory.return_value = None
        
        mock_memory = MemoryEntry(
            conversation_id="test-convo-123",
            memory_content="New memory content",
            last_updated="2023-01-01T12:00:00"
        )
        self.mock_memory_updater.create_memory.return_value = AsyncMock(mock_memory)
        self.mock_memory_store.save_memory.return_value = True
        
        # Create request
        request = MemoryUpdateRequest(
            conversation_id="test-convo-123",
            new_messages=[{"role": "user", "content": "Hello"}]
        )
        
        # Call the endpoint
        response = await update_memory(request)
        
        # Check the response
        assert isinstance(response, MemoryUpdateResponse)
        assert response.conversation_id == "test-convo-123"
        assert response.updated_memory == "New memory content"
        assert response.success is True
        
        # Verify method calls
        self.mock_memory_store.get_memory.assert_called_once_with("test-convo-123")
        self.mock_memory_updater.create_memory.assert_called_once_with(
            conversation_id="test-convo-123", 
            messages=[{"role": "user", "content": "Hello"}]
        )
        self.mock_memory_store.save_memory.assert_called_once_with(mock_memory)

    @pytest.mark.asyncio
    async def test_update_memory_existing(self):
        """Test updating an existing memory."""
        # Set up mocks
        mock_existing_memory = MemoryEntry(
            conversation_id="test-convo-123",
            memory_content="Original memory content",
            last_updated="2023-01-01T12:00:00"
        )
        self.mock_memory_store.get_memory.return_value = mock_existing_memory
        
        update_result = MemoryUpdateResult(
            updated_memory="Updated memory content",
            success=True
        )
        self.mock_memory_updater.update_memory.return_value = AsyncMock(update_result)
        
        self.mock_memory_store.save_memory.return_value = True
        
        # Create request
        request = MemoryUpdateRequest(
            conversation_id="test-convo-123",
            new_messages=[{"role": "user", "content": "New message"}]
        )
        
        # Call the endpoint
        response = await update_memory(request)
        
        # Check the response
        assert isinstance(response, MemoryUpdateResponse)
        assert response.conversation_id == "test-convo-123"
        assert response.updated_memory == "Updated memory content"
        assert response.success is True
        
        # Verify method calls
        self.mock_memory_store.get_memory.assert_called_once_with("test-convo-123")
        self.mock_memory_updater.update_memory.assert_called_once_with(
            current_memory=mock_existing_memory,
            new_messages=[{"role": "user", "content": "New message"}]
        )

    @pytest.mark.asyncio
    async def test_update_memory_save_failure(self):
        """Test handling a failure when saving the updated memory."""
        # Set up mocks
        mock_existing_memory = MemoryEntry(
            conversation_id="test-convo-123",
            memory_content="Original memory content",
            last_updated="2023-01-01T12:00:00"
        )
        self.mock_memory_store.get_memory.return_value = mock_existing_memory
        
        update_result = MemoryUpdateResult(
            updated_memory="Updated memory content",
            success=True
        )
        self.mock_memory_updater.update_memory.return_value = AsyncMock(update_result)
        
        # Make save_memory fail
        self.mock_memory_store.save_memory.return_value = False
        
        # Create request
        request = MemoryUpdateRequest(
            conversation_id="test-convo-123",
            new_messages=[{"role": "user", "content": "New message"}]
        )
        
        # Call the endpoint
        response = await update_memory(request)
        
        # Check the response
        assert isinstance(response, MemoryUpdateResponse)
        assert response.conversation_id == "test-convo-123"
        assert response.updated_memory == "Updated memory content"
        assert response.success is False

    @pytest.mark.asyncio
    async def test_update_memory_update_failure(self):
        """Test handling a failure when updating the memory."""
        # Set up mocks
        mock_existing_memory = MemoryEntry(
            conversation_id="test-convo-123",
            memory_content="Original memory content",
            last_updated="2023-01-01T12:00:00"
        )
        self.mock_memory_store.get_memory.return_value = mock_existing_memory
        
        update_result = MemoryUpdateResult(
            updated_memory="Original memory content",  # No change
            success=False
        )
        self.mock_memory_updater.update_memory.return_value = AsyncMock(update_result)
        
        # Create request
        request = MemoryUpdateRequest(
            conversation_id="test-convo-123",
            new_messages=[{"role": "user", "content": "New message"}]
        )
        
        # Call the endpoint
        response = await update_memory(request)
        
        # Check the response
        assert isinstance(response, MemoryUpdateResponse)
        assert response.conversation_id == "test-convo-123"
        assert response.updated_memory == "Original memory content"
        assert response.success is False
        
        # Verify that save_memory was not called
        self.mock_memory_store.save_memory.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_memory(self):
        """Test deleting a memory."""
        # Set up mock
        self.mock_memory_store.delete_memory.return_value = True
        
        # Create request
        request = MemoryRetrievalRequest(conversation_id="test-convo-123")
        
        # Call the endpoint
        response = await delete_memory(request)
        
        # Check the response
        assert response == {"conversation_id": "test-convo-123", "success": True}
        
        # Verify the store was called correctly
        self.mock_memory_store.delete_memory.assert_called_once_with("test-convo-123")

    @pytest.mark.asyncio
    async def test_delete_memory_failure(self):
        """Test deleting a memory that doesn't exist or can't be deleted."""
        # Set up mock to return False (deletion failed)
        self.mock_memory_store.delete_memory.return_value = False
        
        # Create request
        request = MemoryRetrievalRequest(conversation_id="nonexistent-convo")
        
        # Call the endpoint
        response = await delete_memory(request)
        
        # Check the response
        assert response == {"conversation_id": "nonexistent-convo", "success": False}

    @pytest.mark.asyncio
    async def test_memory_resource(self):
        """Test the memory resource endpoint."""
        # Set up mock memory
        mock_memory = MemoryEntry(
            conversation_id="test-convo-123",
            memory_content="This is a test memory",
            last_updated="2023-01-01T12:00:00"
        )
        self.mock_memory_store.get_memory.return_value = mock_memory
        
        # Call the endpoint
        response = await memory_resource("test-convo-123")
        
        # Check the response
        assert response == {
            "conversation_id": "test-convo-123",
            "exists": True,
            "memory_content": "This is a test memory",
            "last_updated": "2023-01-01T12:00:00"
        }

    @pytest.mark.asyncio
    async def test_memory_resource_nonexistent(self):
        """Test the memory resource endpoint for nonexistent memory."""
        # Set up mock to return None (memory doesn't exist)
        self.mock_memory_store.get_memory.return_value = None
        
        # Call the endpoint
        response = await memory_resource("nonexistent-convo")
        
        # Check the response
        assert response == {
            "conversation_id": "nonexistent-convo",
            "exists": False,
            "memory_content": None
        }

    @pytest.mark.asyncio
    async def test_health(self):
        """Test the health check endpoint."""
        # Call the endpoint
        response = await health()
        
        # Check the response
        assert response["status"] == "healthy"
        assert response["service"] == "memory"
        assert "version" in response