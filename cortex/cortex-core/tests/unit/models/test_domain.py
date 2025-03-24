"""
Tests for the core domain models.
"""

import re
import pytest
from datetime import datetime

from app.models.core_domain import User, Workspace, Conversation, Message, generate_id


def test_user_model():
    """Test the User model."""
    # Create a user
    user = User(
        user_id="user123",
        name="Test User",
        email="user@example.com",
        metadata={"role": "admin"}
    )
    
    # Verify fields
    assert user.user_id == "user123"
    assert user.name == "Test User"
    assert user.email == "user@example.com"
    assert user.metadata == {"role": "admin"}
    
    # Test serialization
    user_dict = user.model_dump()
    assert user_dict["user_id"] == "user123"
    assert user_dict["name"] == "Test User"
    assert user_dict["email"] == "user@example.com"
    assert user_dict["metadata"] == {"role": "admin"}


def test_workspace_model():
    """Test the Workspace model."""
    # Create a workspace
    workspace = Workspace(
        name="Test Workspace",
        description="A test workspace",
        owner_id="user123",
        metadata={"created_at": "2025-01-01"}
    )
    
    # Verify fields
    assert workspace.name == "Test Workspace"
    assert workspace.description == "A test workspace"
    assert workspace.owner_id == "user123"
    assert workspace.metadata == {"created_at": "2025-01-01"}
    
    # Verify ID is generated
    assert workspace.id is not None
    assert isinstance(workspace.id, str)
    assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', workspace.id)
    
    # Test with explicit ID
    workspace2 = Workspace(
        id="custom-id",
        name="Test Workspace 2",
        description="Another test workspace",
        owner_id="user456"
    )
    assert workspace2.id == "custom-id"


def test_conversation_model():
    """Test the Conversation model."""
    # Create a conversation
    conversation = Conversation(
        workspace_id="workspace123",
        topic="Test Conversation",
        participant_ids=["user123", "user456"],
        metadata={"priority": "high"}
    )
    
    # Verify fields
    assert conversation.workspace_id == "workspace123"
    assert conversation.topic == "Test Conversation"
    assert conversation.participant_ids == ["user123", "user456"]
    assert conversation.metadata == {"priority": "high"}
    
    # Verify ID is generated
    assert conversation.id is not None
    assert isinstance(conversation.id, str)
    
    # Test serialization
    conv_dict = conversation.model_dump()
    assert conv_dict["workspace_id"] == "workspace123"
    assert conv_dict["topic"] == "Test Conversation"
    assert conv_dict["participant_ids"] == ["user123", "user456"]


def test_message_model():
    """Test the Message model."""
    # Create a message with minimum fields
    message = Message(
        conversation_id="conv123",
        sender_id="user123",
        content="Hello, world!"
    )
    
    # Verify fields
    assert message.conversation_id == "conv123"
    assert message.sender_id == "user123"
    assert message.content == "Hello, world!"
    
    # Verify ID and timestamp are generated
    assert message.id is not None
    assert isinstance(message.id, str)
    assert message.timestamp is not None
    
    # Verify timestamp format
    datetime.fromisoformat(message.timestamp)  # Should not raise exception
    
    # Test with explicit values
    custom_time = "2025-03-23T12:34:56.789012"
    message2 = Message(
        id="msg-custom-id",
        conversation_id="conv456",
        sender_id="user456",
        content="Custom message",
        timestamp=custom_time
    )
    assert message2.id == "msg-custom-id"
    assert message2.timestamp == custom_time


def test_generate_id():
    """Test the generate_id function."""
    # Generate an ID
    id1 = generate_id()
    
    # Verify it's a UUID string
    assert isinstance(id1, str)
    assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', id1)
    
    # Generate another ID and verify it's different
    id2 = generate_id()
    assert id1 != id2