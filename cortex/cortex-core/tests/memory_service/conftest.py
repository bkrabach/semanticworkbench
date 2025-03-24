import os
import shutil
import tempfile
from typing import Generator

import pytest

from memory_service.models import MemoryEntry
from memory_service.memory_store import MemoryStore


@pytest.fixture
def temp_directory() -> Generator[str, None, None]:
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    os.environ["MEMORY_STORAGE_DIR"] = temp_dir
    
    yield temp_dir
    
    shutil.rmtree(temp_dir)
    if "MEMORY_STORAGE_DIR" in os.environ:
        del os.environ["MEMORY_STORAGE_DIR"]


@pytest.fixture
def memory_store(temp_directory: str) -> MemoryStore:
    """Create a MemoryStore instance using a temporary directory."""
    return MemoryStore()


@pytest.fixture
def sample_memory_entry() -> MemoryEntry:
    """Create a sample memory entry for testing."""
    return MemoryEntry(
        conversation_id="test-conversation",
        memory_content="This is a test memory entry.",
        last_updated="2023-01-01T12:00:00"
    )