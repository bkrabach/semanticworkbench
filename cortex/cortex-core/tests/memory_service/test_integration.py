import json
from pathlib import Path
from typing import Generic, TypeVar
from unittest import mock

import pytest

from memory_service.models import MemoryEntry, MemoryRetrievalRequest, MemoryUpdateRequest
from memory_service.memory_store import MemoryStore
from memory_service.memory_updater import MemoryUpdater
from memory_service.server import delete_memory, get_memory, memory_resource, update_memory

# Define a generic type variable for our mock
T = TypeVar("T")

class MockAgentResults(Generic[T]):
    """Mock for Pydantic-AI Agent Results."""
    
    def __init__(self, data: T):
        self._data = data
        
    @property
    def data(self) -> T:
        return self._data
    
    def __await__(self):
        async def _coro():
            return self
        return _coro().__await__()


@pytest.mark.integration
class TestMemoryServiceIntegration:
    """Integration tests for the Memory Service components working together."""

    @pytest.fixture
    def mock_agent(self):
        """Mock the Pydantic-AI Agent for testing."""
        with mock.patch("memory_service.memory_updater.Agent") as mock_agent_class:
            mock_agent = mock.MagicMock()
            mock_agent_class.return_value = mock_agent
            
            # Set up default mock response
            mock_agent.run.return_value = MockAgentResults("Test memory content")
            
            yield mock_agent
            
    @pytest.fixture(autouse=True)
    def setup_storage_dir(self, temp_directory):
        """Set up the storage directory for tests."""
        # Patch the config directly since that's what the MemoryStore uses
        with mock.patch("memory_service.memory_store.config.STORAGE_DIR", temp_directory):
            yield

    @pytest.mark.asyncio
    async def test_create_and_retrieve_memory_flow(self, temp_directory, mock_agent):
        """Test the flow of creating and retrieving a memory entry."""
        # Set up the mock agent response
        mock_agent.run.return_value = MockAgentResults("User asked about Python. Assistant provided information.")
        
        # Create a memory updater and store
        memory_store = MemoryStore()
        memory_updater = MemoryUpdater()
        
        # Create the memory update request
        update_request = MemoryUpdateRequest(
            conversation_id="test-create-retrieve",
            new_messages=[
                {"role": "user", "content": "Tell me about Python"},
                {"role": "assistant", "content": "Python is a versatile programming language..."}
            ]
        )
        
        # Call the update_memory endpoint function directly
        # This mocks the MCP server interaction but tests the actual function logic
        with mock.patch("memory_service.server.memory_store", memory_store), \
             mock.patch("memory_service.server.memory_updater", memory_updater):
            update_response = await update_memory(update_request)
        
        # Check the update response
        assert update_response.conversation_id == "test-create-retrieve"
        assert update_response.updated_memory == "User asked about Python. Assistant provided information."
        assert update_response.success is True
        
        # Check that the file was created
        file_path = Path(temp_directory) / "test-create-retrieve.json"
        assert file_path.exists()
        
        # Now retrieve the memory
        get_request = MemoryRetrievalRequest(conversation_id="test-create-retrieve")
        
        # Call the get_memory endpoint function directly
        with mock.patch("memory_service.server.memory_store", memory_store):
            get_response = await get_memory(get_request)
        
        # Check the get response
        assert get_response.conversation_id == "test-create-retrieve"
        assert get_response.memory_content == "User asked about Python. Assistant provided information."
        assert get_response.exists is True

    @pytest.mark.asyncio
    async def test_update_existing_memory_flow(self, temp_directory, mock_agent):
        """Test the flow of updating an existing memory entry."""
        # First create a memory file directly
        memory_entry = MemoryEntry(
            conversation_id="test-update-existing",
            memory_content="Initial conversation about Python.",
            last_updated="2023-01-01T12:00:00"
        )
        
        memory_store = MemoryStore()
        memory_store.save_memory(memory_entry)
        
        # Set up the mock agent response for the update
        mock_agent.run.return_value = MockAgentResults("Conversation about Python and JavaScript.")
        
        # Create a memory updater
        memory_updater = MemoryUpdater()
        
        # Update the memory with new messages
        update_request = MemoryUpdateRequest(
            conversation_id="test-update-existing",
            new_messages=[
                {"role": "user", "content": "What about JavaScript?"},
                {"role": "assistant", "content": "JavaScript is a scripting language..."}
            ]
        )
        
        # Call the update_memory endpoint function directly
        with mock.patch("memory_service.server.memory_store", memory_store), \
             mock.patch("memory_service.server.memory_updater", memory_updater):
            update_response = await update_memory(update_request)
        
        # Check the update response
        assert update_response.conversation_id == "test-update-existing"
        assert update_response.updated_memory == "Conversation about Python and JavaScript."
        assert update_response.success is True
        
        # Check the updated file content
        file_path = Path(temp_directory) / "test-update-existing.json"
        with open(file_path, "r") as f:
            updated_data = json.load(f)
            assert updated_data["memory_content"] == "Conversation about Python and JavaScript."

    @pytest.mark.asyncio
    async def test_delete_memory_flow(self, temp_directory):
        """Test the flow of deleting a memory entry."""
        # First create a memory file directly
        memory_entry = MemoryEntry(
            conversation_id="test-delete",
            memory_content="Memory that will be deleted.",
            last_updated="2023-01-01T12:00:00"
        )
        
        memory_store = MemoryStore()
        memory_store.save_memory(memory_entry)
        
        # Check that the file exists
        file_path = Path(temp_directory) / "test-delete.json"
        assert file_path.exists()
        
        # Delete the memory
        delete_request = MemoryRetrievalRequest(conversation_id="test-delete")
        
        # Call the delete_memory endpoint function directly
        with mock.patch("memory_service.server.memory_store", memory_store):
            delete_response = await delete_memory(delete_request)
        
        # Check the delete response
        assert delete_response["conversation_id"] == "test-delete"
        assert delete_response["success"] is True
        
        # Check that the file was deleted
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_memory_resource_endpoint_flow(self, temp_directory):
        """Test the flow of accessing memory via the resource endpoint."""
        # First create a memory file directly
        memory_entry = MemoryEntry(
            conversation_id="test-resource",
            memory_content="Memory for resource endpoint test.",
            last_updated="2023-01-01T12:00:00"
        )
        
        memory_store = MemoryStore()
        memory_store.save_memory(memory_entry)
        
        # Call the memory_resource endpoint function directly
        with mock.patch("memory_service.server.memory_store", memory_store):
            resource_response = await memory_resource("test-resource")
        
        # Check the resource response
        assert resource_response["conversation_id"] == "test-resource"
        assert resource_response["memory_content"] == "Memory for resource endpoint test."
        assert resource_response["exists"] is True
        assert resource_response["last_updated"] == "2023-01-01T12:00:00"

    @pytest.mark.asyncio
    async def test_full_memory_lifecycle(self, temp_directory, mock_agent):
        """Test the complete lifecycle of memory: create, update, get, delete."""
        # Set up mocks and components
        memory_store = MemoryStore()
        memory_updater = MemoryUpdater()
        
        # 1. First create a memory
        mock_agent.run.return_value = MockAgentResults("Initial conversation about AI.")
        
        create_request = MemoryUpdateRequest(
            conversation_id="test-lifecycle",
            new_messages=[{"role": "user", "content": "Let's talk about AI"}]
        )
        
        with mock.patch("memory_service.server.memory_store", memory_store), \
             mock.patch("memory_service.server.memory_updater", memory_updater):
            create_response = await update_memory(create_request)
        
        assert create_response.conversation_id == "test-lifecycle"
        assert create_response.updated_memory == "Initial conversation about AI."
        assert create_response.success is True
        
        # 2. Get the memory
        get_request = MemoryRetrievalRequest(conversation_id="test-lifecycle")
        
        with mock.patch("memory_service.server.memory_store", memory_store):
            get_response = await get_memory(get_request)
        
        assert get_response.memory_content == "Initial conversation about AI."
        assert get_response.exists is True
        
        # 3. Update the memory
        mock_agent.run.return_value = MockAgentResults("Conversation about AI and ML.")
        
        update_request = MemoryUpdateRequest(
            conversation_id="test-lifecycle",
            new_messages=[{"role": "user", "content": "What about ML?"}]
        )
        
        with mock.patch("memory_service.server.memory_store", memory_store), \
             mock.patch("memory_service.server.memory_updater", memory_updater):
            update_response = await update_memory(update_request)
        
        assert update_response.updated_memory == "Conversation about AI and ML."
        assert update_response.success is True
        
        # 4. Get the updated memory
        with mock.patch("memory_service.server.memory_store", memory_store):
            get_updated_response = await get_memory(get_request)
        
        assert get_updated_response.memory_content == "Conversation about AI and ML."
        
        # 5. Delete the memory
        with mock.patch("memory_service.server.memory_store", memory_store):
            delete_response = await delete_memory(get_request)
        
        assert delete_response["success"] is True
        
        # 6. Verify it's gone
        with mock.patch("memory_service.server.memory_store", memory_store):
            get_deleted_response = await get_memory(get_request)
        
        assert get_deleted_response.exists is False
        assert get_deleted_response.memory_content is None