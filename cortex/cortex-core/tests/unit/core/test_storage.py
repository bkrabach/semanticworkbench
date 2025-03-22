"""
Unit tests for the storage module.
"""

import json
from datetime import datetime

import pytest
from app.core.storage import (
    DataType,
    FileSystemStorage,
    MemoryStorage,
    format_item_key,
    load_file,
    save_file,
)


@pytest.fixture
def memory_storage():
    """Create a memory storage instance for testing."""
    return MemoryStorage()


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for file storage testing."""
    return tmp_path


@pytest.fixture
def file_storage(temp_dir):
    """Create a file storage instance with a temporary directory."""
    storage = FileSystemStorage(storage_path=str(temp_dir))
    return storage


def test_format_item_key():
    """Test the format_item_key function."""
    # Test with standard inputs
    key = format_item_key(DataType.CONVERSATION, "user123", "conv456")
    assert key == "conversation:user123:conv456"

    # Test with workspace
    key = format_item_key(DataType.WORKSPACE, "user123", "ws789")
    assert key == "workspace:user123:ws789"

    # Test without item_id
    key = format_item_key(DataType.USER, "user123")
    assert key == "user:user123"


def test_memory_storage_store_and_retrieve(memory_storage):
    """Test storing and retrieving items from memory storage."""
    # Store a test item
    test_item = {"id": "test123", "name": "Test Item", "created_at": datetime.now().isoformat()}

    key = format_item_key(DataType.CONVERSATION, "user456", "test123")
    memory_storage.store(key, test_item)

    # Retrieve the item
    retrieved = memory_storage.retrieve(key)
    assert retrieved == test_item

    # Check non-existent item
    nonexistent = memory_storage.retrieve("nonexistent:key")
    assert nonexistent is None


def test_memory_storage_list_items(memory_storage):
    """Test listing items by prefix from memory storage."""
    # Store multiple items
    items = {
        "conversation:user1:conv1": {"id": "conv1", "user_id": "user1"},
        "conversation:user1:conv2": {"id": "conv2", "user_id": "user1"},
        "conversation:user2:conv3": {"id": "conv3", "user_id": "user2"},
        "workspace:user1:ws1": {"id": "ws1", "user_id": "user1"},
    }

    for key, item in items.items():
        memory_storage.store(key, item)

    # List user1's conversations
    user1_convs = memory_storage.list_items("conversation:user1:")
    assert len(user1_convs) == 2
    assert any(item["id"] == "conv1" for item in user1_convs)
    assert any(item["id"] == "conv2" for item in user1_convs)

    # List user2's conversations
    user2_convs = memory_storage.list_items("conversation:user2:")
    assert len(user2_convs) == 1
    assert user2_convs[0]["id"] == "conv3"

    # List user1's workspaces
    user1_ws = memory_storage.list_items("workspace:user1:")
    assert len(user1_ws) == 1
    assert user1_ws[0]["id"] == "ws1"


def test_memory_storage_delete(memory_storage):
    """Test deleting items from memory storage."""
    # Store a test item
    test_item = {"id": "delete_test", "content": "Delete me"}
    key = "test:delete_test"
    memory_storage.store(key, test_item)

    # Verify item exists
    assert memory_storage.retrieve(key) == test_item

    # Delete the item
    memory_storage.delete(key)

    # Verify item is gone
    assert memory_storage.retrieve(key) is None


@pytest.mark.asyncio
async def test_file_storage_store_and_retrieve(file_storage, temp_dir):
    """Test storing and retrieving items from file storage."""
    # Store a test item
    test_item = {"id": "file123", "name": "File Test", "created_at": datetime.now().isoformat()}

    key = format_item_key(DataType.CONVERSATION, "user789", "file123")
    await file_storage.store(key, test_item)

    # Check that the file exists
    expected_path = temp_dir / "conversation" / "user789" / "file123.json"
    assert expected_path.exists()

    # Verify file contents
    with open(expected_path, "r") as f:
        stored_data = json.load(f)
    assert stored_data == test_item

    # Retrieve the item
    retrieved = await file_storage.retrieve(key)
    assert retrieved == test_item


@pytest.mark.asyncio
async def test_file_storage_list_items(file_storage, temp_dir):
    """Test listing items by prefix from file storage."""
    # Create directory structure
    conv_dir = temp_dir / "conversation" / "list_user"
    conv_dir.mkdir(parents=True, exist_ok=True)

    # Create test files
    test_items = [
        {"id": "list1", "name": "List Test 1"},
        {"id": "list2", "name": "List Test 2"},
        {"id": "list3", "name": "List Test 3"},
    ]

    for item in test_items:
        with open(conv_dir / f"{item['id']}.json", "w") as f:
            json.dump(item, f)

    # List items
    items = await file_storage.list_items("conversation:list_user:")
    assert len(items) == 3

    # Verify all items are found
    for expected in test_items:
        assert any(item["id"] == expected["id"] for item in items)


@pytest.mark.asyncio
async def test_file_storage_delete(file_storage, temp_dir):
    """Test deleting items from file storage."""
    # Create test file
    delete_dir = temp_dir / "test" / "delete_user"
    delete_dir.mkdir(parents=True, exist_ok=True)

    test_item = {"id": "delete_file", "content": "Delete me"}
    file_path = delete_dir / "delete_file.json"

    with open(file_path, "w") as f:
        json.dump(test_item, f)

    # Verify file exists
    assert file_path.exists()

    # Delete the item
    await file_storage.delete("test:delete_user:delete_file")

    # Verify file is gone
    assert not file_path.exists()


def test_save_load_file(temp_dir):
    """Test the save_file and load_file utility functions."""
    file_path = temp_dir / "test_save_load.json"
    test_data = {"key": "value", "nested": {"inner": "data"}}

    # Save file
    save_file(str(file_path), test_data)

    # Verify file exists
    assert file_path.exists()

    # Load file
    loaded_data = load_file(str(file_path))
    assert loaded_data == test_data

    # Test loading non-existent file
    nonexistent = load_file(str(temp_dir / "nonexistent.json"))
    assert nonexistent is None
