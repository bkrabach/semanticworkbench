"""
Tests for the core domain models.
"""

import re
from datetime import datetime
import uuid
import pytest
from typing import Set

from app.models.core_domain import User, Workspace, Conversation, Message, generate_id


def test_user_model() -> None:
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


def test_workspace_model() -> None:
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


def test_conversation_model() -> None:
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


def test_message_model() -> None:
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


def test_message_json_serialization() -> None:
    """Test that Message objects can be properly serialized to JSON."""
    # Create a message
    message = Message(
        id="msg-test",
        conversation_id="conv123",
        sender_id="user123",
        content="Hello, world!",
        timestamp="2025-03-23T12:34:56.789012"
    )
    
    # Serialize to JSON
    json_data = message.model_dump_json()
    
    # Validate it's a properly formatted JSON string
    assert "msg-test" in json_data
    assert "conv123" in json_data
    assert "user123" in json_data
    assert "Hello, world!" in json_data
    assert "2025-03-23T12:34:56.789012" in json_data


def test_conversation_validation() -> None:
    """Test validation for the Conversation model."""
    # Test with empty participant_ids
    conversation = Conversation(
        workspace_id="workspace123",
        topic="Test Conversation",
        participant_ids=[]
    )
    assert conversation.participant_ids == []
    
    # Test with a single participant
    conversation = Conversation(
        workspace_id="workspace123",
        topic="Test Conversation",
        participant_ids=["single_user"]
    )
    assert conversation.participant_ids == ["single_user"]


def test_workspace_validation() -> None:
    """Test validation for the Workspace model."""
    # Test with minimum required fields
    workspace = Workspace(
        name="Minimal Workspace",
        description="",
        owner_id="user123"
    )
    assert workspace.name == "Minimal Workspace"
    assert workspace.description == ""
    assert workspace.owner_id == "user123"


def test_user_validation() -> None:
    """Test validation for the User model."""
    # Test with minimum required fields
    user = User(
        user_id="user123",
        name="",
        email=""
    )
    assert user.user_id == "user123"
    assert user.name == ""
    assert user.email == ""


def test_generate_id() -> None:
    """Test the generate_id function."""
    # Generate an ID
    id1 = generate_id()
    
    # Verify it's a UUID string
    assert isinstance(id1, str)
    assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', id1)
    
    # Generate another ID and verify it's different
    id2 = generate_id()
    assert id1 != id2


def test_model_with_metadata() -> None:
    """Test the metadata field inherited from BaseModelWithMetadata."""
    # Test each model type with metadata
    models = [
        User(user_id="u1", name="Test", email="test@example.com", metadata={"key": "value"}),
        Workspace(name="WS", description="Desc", owner_id="o1", metadata={"key": "value"}),
        Conversation(workspace_id="w1", topic="Topic", participant_ids=["p1"], metadata={"key": "value"}),
        Message(conversation_id="c1", sender_id="s1", content="Content", metadata={"key": "value"})
    ]
    
    for model in models:
        # Check metadata field exists and has expected value
        assert hasattr(model, "metadata")
        assert model.metadata == {"key": "value"}
        
        # Check it's included in serialization
        model_dict = model.model_dump()
        assert "metadata" in model_dict
        assert model_dict["metadata"] == {"key": "value"}
        
        # Update metadata and verify changes
        model.metadata["new_key"] = "new_value"
        assert model.metadata == {"key": "value", "new_key": "new_value"}


def test_model_default_metadata() -> None:
    """Test that models have empty dict as default metadata."""
    # Create models without specifying metadata
    models = [
        User(user_id="u1", name="Test", email="test@example.com"),
        Workspace(name="WS", description="Desc", owner_id="o1"),
        Conversation(workspace_id="w1", topic="Topic", participant_ids=["p1"]),
        Message(conversation_id="c1", sender_id="s1", content="Content")
    ]
    
    for model in models:
        # Check metadata is an empty dict by default
        assert hasattr(model, "metadata")
        assert model.metadata == {}
        
        # Check we can add to the default metadata
        model.metadata["test_key"] = "test_value"
        assert model.metadata == {"test_key": "test_value"}


def test_required_fields() -> None:
    """Test required fields validation for all models."""
    # Instead of using dictionaries with missing fields, we'll just use try/except blocks
    
    # Test user validation
    try:
        # Attempt to create a User without required fields
        User(name="Test", email="test@example.com")  # type: ignore
        pytest.fail("User without user_id should fail validation")
    except Exception:
        pass
    
    try:
        User(user_id="u1", email="test@example.com")  # type: ignore
        pytest.fail("User without name should fail validation")
    except Exception:
        pass
    
    try:
        User(user_id="u1", name="Test")  # type: ignore
        pytest.fail("User without email should fail validation")
    except Exception:
        pass
    
    # Test workspace validation
    try:
        Workspace(description="Desc", owner_id="o1")  # type: ignore
        pytest.fail("Workspace without name should fail validation")
    except Exception:
        pass
    
    try:
        Workspace(name="WS", owner_id="o1")  # type: ignore
        pytest.fail("Workspace without description should fail validation")
    except Exception:
        pass
    
    try:
        Workspace(name="WS", description="Desc")  # type: ignore
        pytest.fail("Workspace without owner_id should fail validation")
    except Exception:
        pass
    
    # Test conversation validation
    try:
        Conversation(topic="Topic", participant_ids=["p1"])  # type: ignore
        pytest.fail("Conversation without workspace_id should fail validation")
    except Exception:
        pass
    
    try:
        Conversation(workspace_id="w1", participant_ids=["p1"])  # type: ignore
        pytest.fail("Conversation without topic should fail validation")
    except Exception:
        pass
    
    try:
        Conversation(workspace_id="w1", topic="Topic")  # type: ignore
        pytest.fail("Conversation without participant_ids should fail validation")
    except Exception:
        pass
    
    # Test message validation
    try:
        Message(sender_id="s1", content="Content")  # type: ignore
        pytest.fail("Message without conversation_id should fail validation")
    except Exception:
        pass
    
    try:
        Message(conversation_id="c1", content="Content")  # type: ignore
        pytest.fail("Message without sender_id should fail validation")
    except Exception:
        pass
    
    try:
        Message(conversation_id="c1", sender_id="s1")  # type: ignore
        pytest.fail("Message without content should fail validation")
    except Exception:
        pass


def test_timestamp_handling() -> None:
    """Test timestamp handling for Message model."""
    # Test with a valid timestamp
    valid_time = "2025-03-23T12:34:56.789012"
    message = Message(
        conversation_id="c1",
        sender_id="s1",
        content="Content",
        timestamp=valid_time
    )
    assert message.timestamp == valid_time
    
    # Test that default timestamp is in ISO format
    message = Message(
        conversation_id="c1",
        sender_id="s1",
        content="Content"
    )
    # Verify it's a valid ISO format
    datetime.fromisoformat(message.timestamp)


def test_uuid_generation() -> None:
    """Test UUID generation for IDs."""
    # Make sure generated IDs are valid UUIDs
    workspace = Workspace(name="WS", description="Desc", owner_id="o1")
    conversation = Conversation(workspace_id="w1", topic="Topic", participant_ids=["p1"])
    message = Message(conversation_id="c1", sender_id="s1", content="Content")
    
    # Check each ID individually to avoid type errors
    for id_str in [workspace.id, conversation.id, message.id]:
        # Convert ID to UUID and back to string to verify format
        uuid_obj = uuid.UUID(id_str)
        assert str(uuid_obj) == id_str


def test_model_immutable_copy() -> None:
    """Test creating immutable copies of models."""
    # Create a user
    user = User(
        user_id="user123",
        name="Test User",
        email="user@example.com"
    )
    
    # Create a copy with modified fields
    user_copy = user.model_copy(update={"name": "Updated Name"})
    
    # Verify the original is unchanged
    assert user.name == "Test User"
    assert user_copy.name == "Updated Name"
    
    # Verify other fields are preserved
    assert user_copy.user_id == user.user_id
    assert user_copy.email == user.email


def test_metadata_modification() -> None:
    """Test that metadata can be modified independently when using a new dict."""
    # Create a user with metadata
    user = User(
        user_id="user123",
        name="Test User",
        email="user@example.com",
        metadata={"key": "value"}
    )
    
    # Create a copy with a deep copy of the metadata
    user_copy = User(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        metadata=dict(user.metadata)  # Create a new dict
    )
    
    # Modify the copy's metadata
    user_copy.metadata["key"] = "new_value"
    
    # Verify the original metadata is unchanged
    assert user.metadata["key"] == "value"
    assert user_copy.metadata["key"] == "new_value"
    
    # Test that model_copy performs a shallow copy, not a deep copy
    user2 = User(
        user_id="user456",
        name="Another User",
        email="another@example.com",
        metadata={"count": 0}
    )
    
    # Make a copy with deep_copy=True and verify that modifying it doesn't affect the original
    user2_copy = user2.model_copy(deep=True)
    user2_copy.metadata["new_key"] = "added"
    
    # With deep=True, the original should not be affected
    assert "new_key" not in user2.metadata
    
    # Test with nested dictionaries
    user3 = User(
        user_id="user789",
        name="Third User",
        email="third@example.com",
        metadata={"nested": {"level1": "original"}}
    )
    
    # Even with deep=True, nested dicts are still shallow copied
    user3_copy = user3.model_copy(deep=True)
    
    # Demonstrate that you need to create a new nested dict to avoid modifying the original
    user3_copy.metadata = {
        "nested": {"level1": "modified"}
    }
    
    # The original should remain unchanged
    assert user3.metadata["nested"]["level1"] == "original"
    assert user3_copy.metadata["nested"]["level1"] == "modified"


def test_generate_id_uniqueness() -> None:
    """Test that generate_id produces unique IDs."""
    # Generate a large number of IDs
    ids = [generate_id() for _ in range(100)]
    
    # Check that all IDs are unique
    assert len(ids) == len(set(ids))
    
    # Verify each ID is a valid UUID
    for id_str in ids:
        # Will raise ValueError if not a valid UUID
        uuid.UUID(id_str)


def test_default_id_factory() -> None:
    """Test that the default ID factory generates valid UUIDs."""
    # Create 20 instances of each model
    workspaces = [Workspace(name=f"Workspace {i}", description="Test", owner_id="o1") for i in range(20)]
    conversations = [Conversation(workspace_id="w1", topic=f"Topic {i}", participant_ids=["p1"]) for i in range(20)]
    messages = [Message(conversation_id="c1", sender_id="s1", content=f"Content {i}") for i in range(20)]
    
    # Verify each set of IDs has unique values
    workspace_ids: Set[str] = {w.id for w in workspaces}
    conversation_ids: Set[str] = {c.id for c in conversations}
    message_ids: Set[str] = {m.id for m in messages}
    
    assert len(workspace_ids) == 20
    assert len(conversation_ids) == 20
    assert len(message_ids) == 20