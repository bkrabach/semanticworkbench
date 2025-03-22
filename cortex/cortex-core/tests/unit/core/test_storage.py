"""
Unit tests for the storage module.
"""

import pytest
from app.core.storage import InMemoryStorage
from app.models.core_domain import Conversation, Message, User, Workspace


@pytest.fixture
def memory_storage():
    """Create an in-memory storage instance for testing."""
    return InMemoryStorage()


def test_user_operations(memory_storage):
    """Test user creation and retrieval."""
    # Create test user
    user = User(
        user_id="test_user_id",
        name="Test User",
        email="test@example.com"
    )
    
    # Store user
    stored_user = memory_storage.create_user(user)
    assert stored_user["user_id"] == "test_user_id"
    assert stored_user["name"] == "Test User"
    assert stored_user["email"] == "test@example.com"
    
    # Retrieve user
    retrieved_user = memory_storage.get_user("test_user_id")
    assert retrieved_user == stored_user
    
    # Non-existent user
    assert memory_storage.get_user("nonexistent") is None


def test_workspace_operations(memory_storage):
    """Test workspace creation, retrieval and listing."""
    # Create test workspaces
    workspace1 = Workspace(
        id="workspace1",
        name="Workspace 1",
        owner_id="owner1",
        description="Test workspace 1"
    )
    workspace2 = Workspace(
        id="workspace2",
        name="Workspace 2",
        owner_id="owner1",
        description="Test workspace 2"
    )
    workspace3 = Workspace(
        id="workspace3",
        name="Workspace 3",
        owner_id="owner2",
        description="Test workspace 3"
    )
    
    # Store workspaces
    memory_storage.create_workspace(workspace1)
    memory_storage.create_workspace(workspace2)
    memory_storage.create_workspace(workspace3)
    
    # Get workspace by ID
    retrieved = memory_storage.get_workspace("workspace1")
    assert retrieved["id"] == "workspace1"
    assert retrieved["name"] == "Workspace 1"
    
    # List workspaces by owner
    owner1_workspaces = memory_storage.list_workspaces("owner1")
    assert len(owner1_workspaces) == 2
    assert any(ws["id"] == "workspace1" for ws in owner1_workspaces)
    assert any(ws["id"] == "workspace2" for ws in owner1_workspaces)
    
    owner2_workspaces = memory_storage.list_workspaces("owner2")
    assert len(owner2_workspaces) == 1
    assert owner2_workspaces[0]["id"] == "workspace3"


def test_conversation_operations(memory_storage):
    """Test conversation creation, retrieval and listing."""
    # Create test conversations
    conversation1 = Conversation(
        id="conv1",
        topic="Conversation Topic 1",
        workspace_id="workspace1",
        participant_ids=["user1", "user2"]
    )
    conversation2 = Conversation(
        id="conv2",
        topic="Conversation Topic 2",
        workspace_id="workspace1",
        participant_ids=["user1", "user3"]
    )
    conversation3 = Conversation(
        id="conv3",
        topic="Conversation Topic 3",
        workspace_id="workspace2",
        participant_ids=["user2", "user3"]
    )
    
    # Store conversations
    memory_storage.create_conversation(conversation1)
    memory_storage.create_conversation(conversation2)
    memory_storage.create_conversation(conversation3)
    
    # Get conversation by ID
    retrieved = memory_storage.get_conversation("conv1")
    assert retrieved["id"] == "conv1"
    assert retrieved["topic"] == "Conversation Topic 1"
    
    # List conversations by workspace
    ws1_conversations = memory_storage.list_conversations("workspace1")
    assert len(ws1_conversations) == 2
    assert any(conv["id"] == "conv1" for conv in ws1_conversations)
    assert any(conv["id"] == "conv2" for conv in ws1_conversations)
    
    ws2_conversations = memory_storage.list_conversations("workspace2")
    assert len(ws2_conversations) == 1
    assert ws2_conversations[0]["id"] == "conv3"


def test_message_operations(memory_storage):
    """Test message creation, retrieval and listing."""
    # Create test messages
    message1 = Message(
        id="msg1",
        conversation_id="conv1",
        sender_id="user1",
        content="Hello"
    )
    message2 = Message(
        id="msg2",
        conversation_id="conv1",
        sender_id="assistant",
        content="Hi there"
    )
    message3 = Message(
        id="msg3",
        conversation_id="conv2",
        sender_id="user2",
        content="Different conversation"
    )
    
    # Store messages
    memory_storage.create_message(message1)
    memory_storage.create_message(message2)
    memory_storage.create_message(message3)
    
    # Get message by ID
    retrieved = memory_storage.get_message("msg1")
    assert retrieved["id"] == "msg1"
    assert retrieved["content"] == "Hello"
    
    # List messages by conversation
    conv1_messages = memory_storage.list_messages("conv1")
    assert len(conv1_messages) == 2
    assert any(msg["id"] == "msg1" for msg in conv1_messages)
    assert any(msg["id"] == "msg2" for msg in conv1_messages)
    
    conv2_messages = memory_storage.list_messages("conv2")
    assert len(conv2_messages) == 1
    assert conv2_messages[0]["id"] == "msg3"
