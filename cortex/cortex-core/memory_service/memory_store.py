# memory_store.py for memory service
import json
from pathlib import Path
from typing import List, Optional

from .config import config
from .models import MemoryEntry


class MemoryStore:
    """File-based storage for memory entries."""

    def __init__(self):
        """Initialize the memory store."""
        self.storage_dir = Path(config.STORAGE_DIR)
        self.storage_dir.mkdir(exist_ok=True, parents=True)

    def _get_file_path(self, conversation_id: str) -> Path:
        """Get the file path for a memory entry."""
        return self.storage_dir / f"{conversation_id}.json"

    def save_memory(self, entry: MemoryEntry) -> bool:
        """Save a memory entry to disk."""
        try:
            file_path = self._get_file_path(entry.conversation_id)
            with open(file_path, "w") as f:
                f.write(entry.model_dump_json())
            return True
        except Exception as e:
            print(f"Error saving memory: {e}")
            return False

    def get_memory(self, conversation_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry from disk."""
        file_path = self._get_file_path(conversation_id)
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return MemoryEntry(**data)
        except Exception as e:
            print(f"Error retrieving memory: {e}")
            return None

    def delete_memory(self, conversation_id: str) -> bool:
        """Delete a memory entry from disk."""
        file_path = self._get_file_path(conversation_id)
        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            return True
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False

    def list_memories(self) -> List[str]:
        """List all conversation IDs with memory entries."""
        return [f.stem for f in self.storage_dir.glob("*.json")]
