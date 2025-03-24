import json
import shutil
import tempfile
from pathlib import Path
from unittest import mock


from memory_service.models import MemoryEntry
from memory_service.memory_store import MemoryStore


class TestMemoryStore:
    """Tests for the MemoryStore class."""

    def setup_method(self):
        """Set up a temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        # Patch the config to use our temp directory
        self.config_patch = mock.patch("memory_service.memory_store.config.STORAGE_DIR", self.temp_dir)
        self.config_patch.start()
        self.memory_store = MemoryStore()

    def teardown_method(self):
        """Clean up the temporary directory after each test."""
        self.config_patch.stop()
        shutil.rmtree(self.temp_dir)

    def test_initialize_creates_directory(self):
        """Test that initialization creates the storage directory."""
        # We already initialized in setup, so just check the directory exists
        assert Path(self.temp_dir).exists()
        assert Path(self.temp_dir).is_dir()

    def test_get_file_path(self):
        """Test that the file path is correctly generated."""
        conversation_id = "test-convo-123"
        expected_path = Path(self.temp_dir) / f"{conversation_id}.json"
        
        actual_path = self.memory_store._get_file_path(conversation_id)
        
        assert actual_path == expected_path

    def test_save_memory(self):
        """Test saving a memory entry to disk."""
        # Create a test memory entry
        entry = MemoryEntry(
            conversation_id="test-save-convo",
            memory_content="This is a test memory",
            last_updated="2023-01-01T12:00:00"
        )
        
        # Save it
        result = self.memory_store.save_memory(entry)
        
        # Check the result and file existence
        assert result is True
        file_path = self.memory_store._get_file_path("test-save-convo")
        assert file_path.exists()
        
        # Check the file contents
        with open(file_path, "r") as f:
            data = json.load(f)
            assert data["conversation_id"] == "test-save-convo"
            assert data["memory_content"] == "This is a test memory"
            assert data["last_updated"] == "2023-01-01T12:00:00"

    def test_save_memory_error_handling(self):
        """Test error handling when saving a memory entry fails."""
        entry = MemoryEntry(
            conversation_id="test-save-error",
            memory_content="This is a test memory",
            last_updated="2023-01-01T12:00:00"
        )
        
        # Mock open to raise an exception
        with mock.patch("builtins.open", mock.mock_open()) as mock_file:
            mock_file.side_effect = IOError("Test error")
            result = self.memory_store.save_memory(entry)
            
            assert result is False

    def test_get_memory(self):
        """Test retrieving a memory entry from disk."""
        # Create and save a test memory entry
        entry = MemoryEntry(
            conversation_id="test-get-convo",
            memory_content="This is a test memory for get",
            last_updated="2023-01-01T12:00:00"
        )
        self.memory_store.save_memory(entry)
        
        # Retrieve it
        retrieved_entry = self.memory_store.get_memory("test-get-convo")
        
        # Check the retrieved entry
        assert retrieved_entry is not None
        assert retrieved_entry.conversation_id == "test-get-convo"
        assert retrieved_entry.memory_content == "This is a test memory for get"
        assert retrieved_entry.last_updated == "2023-01-01T12:00:00"

    def test_get_memory_nonexistent(self):
        """Test retrieving a nonexistent memory entry."""
        # Try to retrieve a memory that doesn't exist
        retrieved_entry = self.memory_store.get_memory("nonexistent-convo")
        
        # Should return None
        assert retrieved_entry is None

    def test_get_memory_error_handling(self):
        """Test error handling when retrieving a memory entry fails."""
        # Create a file but mock json.load to raise an exception
        entry = MemoryEntry(
            conversation_id="test-get-error",
            memory_content="This is a test memory for error",
            last_updated="2023-01-01T12:00:00"
        )
        self.memory_store.save_memory(entry)
        
        with mock.patch("json.load", side_effect=json.JSONDecodeError("Test error", "", 0)):
            retrieved_entry = self.memory_store.get_memory("test-get-error")
            
            assert retrieved_entry is None

    def test_delete_memory(self):
        """Test deleting a memory entry from disk."""
        # Create and save a test memory entry
        entry = MemoryEntry(
            conversation_id="test-delete-convo",
            memory_content="This is a test memory for deletion",
            last_updated="2023-01-01T12:00:00"
        )
        self.memory_store.save_memory(entry)
        
        # Confirm it exists
        file_path = self.memory_store._get_file_path("test-delete-convo")
        assert file_path.exists()
        
        # Delete it
        result = self.memory_store.delete_memory("test-delete-convo")
        
        # Check the result and file existence
        assert result is True
        assert not file_path.exists()

    def test_delete_memory_nonexistent(self):
        """Test deleting a nonexistent memory entry."""
        # Try to delete a memory that doesn't exist
        result = self.memory_store.delete_memory("nonexistent-delete-convo")
        
        # Should return False
        assert result is False

    def test_delete_memory_error_handling(self):
        """Test error handling when deleting a memory entry fails."""
        # Create and save a test memory entry
        entry = MemoryEntry(
            conversation_id="test-delete-error",
            memory_content="This is a test memory for deletion error",
            last_updated="2023-01-01T12:00:00"
        )
        self.memory_store.save_memory(entry)
        
        # Mock Path.unlink to raise an exception
        with mock.patch.object(Path, "unlink", side_effect=IOError("Test error")):
            result = self.memory_store.delete_memory("test-delete-error")
            
            assert result is False

    def test_list_memories(self):
        """Test listing all memory entries."""
        # Create and save multiple test memory entries
        for i in range(3):
            entry = MemoryEntry(
                conversation_id=f"test-list-convo-{i}",
                memory_content=f"This is test memory {i}",
                last_updated="2023-01-01T12:00:00"
            )
            self.memory_store.save_memory(entry)
            
        # Also add a non-JSON file to test filtering
        non_json_path = Path(self.temp_dir) / "not-a-memory.txt"
        with open(non_json_path, "w") as f:
            f.write("This is not a memory file")
        
        # List memories
        memory_list = self.memory_store.list_memories()
        
        # Check the list
        assert len(memory_list) == 3
        assert "test-list-convo-0" in memory_list
        assert "test-list-convo-1" in memory_list
        assert "test-list-convo-2" in memory_list
        assert "not-a-memory" not in memory_list