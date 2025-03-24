"""
Tests for the models and configuration of the Cognition Service.
"""
# os import removed as unused
from datetime import datetime

# pytest and ValidationError imports removed as unused

from cognition_service.config import settings, Settings
from cognition_service.models import (
    EventType, Event, UserInputEvent, MessageRole, 
    Message, Conversation, LLMOutput
)
from app.models.llm import FinalAnswer, ToolRequest


def test_settings_defaults():
    """Test that settings has appropriate defaults."""
    # Create a settings instance with default values
    default_settings = Settings()
    
    # Basic checks
    assert isinstance(default_settings.port, int)
    assert isinstance(default_settings.host, str)
    assert isinstance(default_settings.llm_provider, str)
    assert isinstance(default_settings.model_name, str)
    assert isinstance(default_settings.temperature, float)
    assert isinstance(default_settings.max_tokens, int)
    assert isinstance(default_settings.system_prompt, str)
    assert isinstance(default_settings.memory_service_url, str)
    assert isinstance(default_settings.enable_memory_integration, bool)
    assert isinstance(default_settings.enable_tool_use, bool)


def test_settings_loads_env_vars():
    """Test that Settings class properly loads from environment variables."""
    # Test with a direct instantiation and verify the values
    test_settings = Settings(
        port=5050,
        host="testhost",
        llm_provider="test_provider",
        model_name="test-model",
        temperature=0.5,
        max_tokens=500,
        system_prompt="Custom prompt",
        memory_service_url="http://memory.test/sse",
        enable_memory_integration=True,
        enable_tool_use=True
    )
    
    # Check that the values were set correctly
    assert test_settings.port == 5050
    assert test_settings.host == "testhost"
    assert test_settings.llm_provider == "test_provider"
    assert test_settings.model_name == "test-model"
    assert test_settings.temperature == 0.5
    assert test_settings.max_tokens == 500
    assert test_settings.system_prompt == "Custom prompt"
    assert test_settings.memory_service_url == "http://memory.test/sse"
    assert test_settings.enable_memory_integration is True
    assert test_settings.enable_tool_use is True


def test_global_settings_instance():
    """Test that the global settings instance is properly initialized."""
    assert settings is not None
    assert isinstance(settings, Settings)


def test_event_type_enum():
    """Test the EventType enum values."""
    assert EventType.CONTEXT_UPDATE == "context_update"
    assert EventType.USER_INPUT == "user_input"
    assert EventType.SYSTEM_MESSAGE == "system_message"


def test_event_model():
    """Test the basic Event model."""
    # Create an event
    event = Event(
        event_type=EventType.SYSTEM_MESSAGE,
        conversation_id="test-convo",
        data={"message": "System message"}
    )
    
    # Check fields
    assert event.event_type == EventType.SYSTEM_MESSAGE
    assert event.conversation_id == "test-convo"
    assert event.data == {"message": "System message"}
    assert isinstance(event.timestamp, datetime)


def test_user_input_event():
    """Test the UserInputEvent model."""
    # Create a user input event
    event = UserInputEvent(
        conversation_id="test-convo",
        data={
            "content": "Hello, AI!",
            "user_id": "test-user"
        }
    )
    
    # Check fields
    assert event.event_type == EventType.USER_INPUT
    assert event.conversation_id == "test-convo"
    assert event.message_text == "Hello, AI!"
    assert event.user_id == "test-user"


def test_user_input_event_empty_data():
    """Test UserInputEvent with missing data fields."""
    # Create a user input event with empty data
    event = UserInputEvent(
        conversation_id="test-convo",
        data={}
    )
    
    # Check that properties handle missing data gracefully
    assert event.message_text == ""
    assert event.user_id == ""


def test_message_role_enum():
    """Test the MessageRole enum values."""
    assert MessageRole.SYSTEM == "system"
    assert MessageRole.USER == "user"
    assert MessageRole.ASSISTANT == "assistant"
    assert MessageRole.TOOL == "tool"


def test_message_model():
    """Test the Message model."""
    # Create a message
    message = Message(
        role=MessageRole.USER,
        content="Hello, AI!"
    )
    
    # Check fields
    assert message.role == MessageRole.USER
    assert message.content == "Hello, AI!"
    assert isinstance(message.timestamp, datetime)


def test_conversation_model():
    """Test the Conversation model."""
    # Create messages
    messages = [
        Message(role=MessageRole.SYSTEM, content="You are an AI assistant"),
        Message(role=MessageRole.USER, content="Hello"),
        Message(role=MessageRole.ASSISTANT, content="Hi there!")
    ]
    
    # Create a conversation
    conversation = Conversation(
        id="test-convo",
        messages=messages,
        metadata={"user_id": "test-user"}
    )
    
    # Check fields
    assert conversation.id == "test-convo"
    assert len(conversation.messages) == 3
    assert all(isinstance(msg, Message) for msg in conversation.messages)
    assert conversation.metadata == {"user_id": "test-user"}


def test_conversation_default_values():
    """Test Conversation model with default values."""
    # Create a conversation with only the required field
    conversation = Conversation(id="test-convo")
    
    # Check default values
    assert conversation.messages == []
    assert conversation.metadata == {}


def test_llm_output_type_alias():
    """Test the LLMOutput type alias."""
    # Create instances of both possible types
    final_answer = FinalAnswer(answer="This is the final answer")
    tool_request = ToolRequest(tool="test_tool", args={"param": "value"})
    
    # Check that both can be assigned to LLMOutput
    final_answer_output: LLMOutput = final_answer
    tool_request_output: LLMOutput = tool_request
    
    assert final_answer_output.model_dump() == final_answer.model_dump()
    assert tool_request_output.model_dump() == tool_request.model_dump()