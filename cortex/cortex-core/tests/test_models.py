import pytest
from datetime import datetime

from app.models.domain import User, Workspace, Conversation, Message
from app.models.api import (
    LoginRequest, LoginResponse, 
    WorkspaceCreateRequest, ConversationCreateRequest,
    InputMessage
)
from app.models.llm import ToolRequest, FinalAnswer


def test_user_model():
    """Test the User domain model."""
    user = User(id="user-123", name="Test User", email="user@example.com")
    assert user.id == "user-123"
    assert user.name == "Test User"
    assert user.email == "user@example.com"


def test_workspace_model():
    """Test the Workspace domain model."""
    workspace = Workspace(id="ws-123", owner_id="user-123", name="Test Workspace")
    assert workspace.id == "ws-123"
    assert workspace.owner_id == "user-123"
    assert workspace.name == "Test Workspace"


def test_conversation_model():
    """Test the Conversation domain model."""
    # Test with title
    conversation = Conversation(
        id="conv-123", 
        workspace_id="ws-123", 
        title="Test Conversation"
    )
    assert conversation.id == "conv-123"
    assert conversation.workspace_id == "ws-123"
    assert conversation.title == "Test Conversation"
    
    # Test without title (should be None)
    conversation = Conversation(id="conv-123", workspace_id="ws-123")
    assert conversation.id == "conv-123"
    assert conversation.workspace_id == "ws-123"
    assert conversation.title is None


def test_message_model():
    """Test the Message domain model."""
    # Test with explicit timestamp
    timestamp = datetime.utcnow()
    message = Message(
        id="msg-123",
        conversation_id="conv-123",
        sender="user",
        content="Hello world",
        timestamp=timestamp
    )
    assert message.id == "msg-123"
    assert message.conversation_id == "conv-123"
    assert message.sender == "user"
    assert message.content == "Hello world"
    assert message.timestamp == timestamp
    
    # Test with auto-generated timestamp
    message = Message(
        id="msg-123",
        conversation_id="conv-123",
        sender="assistant",
        content="Hello there"
    )
    assert message.id == "msg-123"
    assert message.conversation_id == "conv-123"
    assert message.sender == "assistant"
    assert message.content == "Hello there"
    assert isinstance(message.timestamp, datetime)


def test_api_request_schemas():
    """Test the API request schemas."""
    # Test LoginRequest
    login_req = LoginRequest(username="user@example.com", password="password123")
    assert login_req.username == "user@example.com"
    assert login_req.password == "password123"
    
    # Test WorkspaceCreateRequest
    ws_req = WorkspaceCreateRequest(name="New Workspace")
    assert ws_req.name == "New Workspace"
    assert ws_req.description is None
    assert ws_req.metadata is None
    
    # Test with optional fields
    ws_req = WorkspaceCreateRequest(
        name="New Workspace", 
        description="A workspace for testing",
        metadata={"key": "value"}
    )
    assert ws_req.description == "A workspace for testing"
    assert ws_req.metadata == {"key": "value"}
    
    # Test ConversationCreateRequest
    conv_req = ConversationCreateRequest(workspace_id="ws-123")
    assert conv_req.workspace_id == "ws-123"
    assert conv_req.topic is None
    assert conv_req.metadata is None
    
    # Test InputMessage
    input_msg = InputMessage(content="Hello", conversation_id="conv-123")
    assert input_msg.content == "Hello"
    assert input_msg.conversation_id == "conv-123"
    assert input_msg.metadata is None


def test_llm_models():
    """Test the LLM structured output models."""
    # Test ToolRequest
    tool_req = ToolRequest(
        tool="memory_search",
        args={"query": "previous conversation", "limit": 5}
    )
    assert tool_req.tool == "memory_search"
    assert tool_req.args["query"] == "previous conversation"
    assert tool_req.args["limit"] == 5
    
    # Test FinalAnswer
    answer = FinalAnswer(answer="This is the answer to your question.")
    assert answer.answer == "This is the answer to your question."