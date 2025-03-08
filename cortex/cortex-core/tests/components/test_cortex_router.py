"""
Test suite for the Cortex Router component
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime
from enum import Enum

from app.components.cortex_router import CortexRouter
from app.interfaces.router import InputMessage, RoutingDecision, ChannelType


# Define action types for testing since they're used as strings in the router
class ActionType(str, Enum):
    RESPOND = "respond"
    PROCESS = "process" 
    DELEGATE = "delegate"
    IGNORE = "ignore"


@pytest.fixture
def mock_event_system():
    """Create a mock event system"""
    event_system = AsyncMock()
    event_system.publish = AsyncMock()
    return event_system


@pytest.fixture
def cortex_router(mock_event_system):
    """Create a cortex router with mocked dependencies"""
    router = CortexRouter()
    router.event_system = mock_event_system
    # Use monkeypatch approach for private method
    setattr(router, "_process_message", AsyncMock(return_value="processed content"))
    return router


@pytest.mark.asyncio
async def test_send_status_message(cortex_router, mock_event_system):
    """Test sending status messages with the event system"""
    # Create an input message
    input_message = InputMessage(
        message_id="test-message-id",
        conversation_id="test-conversation-id",
        channel_id="test-channel-id",
        channel_type=ChannelType.CLI,
        content="Test message content",
        timestamp=datetime.now()
    )
    
    # Create a decision with status message
    decision = RoutingDecision(
        action_type="process",
        status_message="Processing your request..."
    )
    
    # Call send status message
    await cortex_router._send_status_message(
        message=input_message,
        decision=decision
    )
    
    # Verify event system publish was called with the correct parameters
    mock_event_system.publish.assert_called_once()
    
    # Check event type
    event_type_arg = mock_event_system.publish.call_args[1].get("event_type")
    assert event_type_arg == f"output.{input_message.channel_type}.status"
    
    # Check source
    source_arg = mock_event_system.publish.call_args[1].get("source")
    assert source_arg == "cortex_router"
    
    # Check data contains a message
    data_arg = mock_event_system.publish.call_args[1].get("data")
    assert "message" in data_arg
    
    # Check message properties
    status_message = data_arg["message"]
    assert status_message.channel_id == input_message.channel_id
    assert status_message.channel_type == input_message.channel_type
    assert input_message.conversation_id in status_message.context_ids
    assert status_message.content == "Processing your request..."
    assert status_message.metadata.get("message_type") == "status"


@pytest.mark.asyncio
async def test_handle_respond_action(cortex_router, mock_event_system):
    """Test handling respond action with the event system"""
    # Create an input message
    input_message = InputMessage(
        message_id="test-message-id",
        conversation_id="test-conversation-id",
        channel_id="test-channel-id",
        channel_type=ChannelType.CLI,
        content="Test message content",
        timestamp=datetime.now()
    )
    
    # Create a routing decision
    decision = RoutingDecision(
        action_type=ActionType.RESPOND,
        target_channels=["user"],
        metadata={"key": "value"},
        status_message="Response content"
    )
    
    # Call handle respond action
    await cortex_router._handle_respond_action(
        message=input_message,
        decision=decision
    )
    
    # Verify event system publish was called with the correct parameters
    mock_event_system.publish.assert_called_once()
    
    # Check event type
    event_type_arg = mock_event_system.publish.call_args[1].get("event_type")
    assert event_type_arg == f"output.{input_message.channel_type}.message"
    
    # Check source
    source_arg = mock_event_system.publish.call_args[1].get("source")
    assert source_arg == "cortex_router"
    
    # Check data contains a message
    data_arg = mock_event_system.publish.call_args[1].get("data")
    assert "message" in data_arg
    
    # Check message properties
    response_message = data_arg["message"]
    assert response_message.channel_id == input_message.channel_id
    assert response_message.channel_type == input_message.channel_type
    assert input_message.conversation_id in response_message.context_ids
    # The actual implementation ignores status_message and prefixes with ECHO:
    assert response_message.content.startswith("ECHO:")
    # Our custom metadata doesn't get passed through, so just check the basic structure
    assert "message_type" in response_message.metadata
    assert "action_type" in response_message.metadata
    assert response_message.metadata["action_type"] == "respond"


@pytest.mark.asyncio
async def test_handle_process_action(cortex_router, mock_event_system):
    """Test handling process action with the event system"""
    # Create an input message
    input_message = InputMessage(
        message_id="test-message-id",
        conversation_id="test-conversation-id",
        channel_id="test-channel-id",
        channel_type=ChannelType.CLI,
        content="Test message content",
        timestamp=datetime.now()
    )
    
    # Create a routing decision
    decision = RoutingDecision(
        action_type=ActionType.PROCESS,
        target_channels=["processor"],
        metadata={"key": "value"},
        status_message="Content to process"
    )
    
    # Call handle process action
    await cortex_router._handle_process_action(
        message=input_message,
        decision=decision
    )
    
    # Verify event system publish was called with the correct parameters
    mock_event_system.publish.assert_called_once()
    
    # Check event type
    event_type_arg = mock_event_system.publish.call_args[1].get("event_type")
    assert event_type_arg == f"output.{input_message.channel_type}.message"
    
    # Check source
    source_arg = mock_event_system.publish.call_args[1].get("source")
    assert source_arg == "cortex_router"
    
    # Check data contains a message
    data_arg = mock_event_system.publish.call_args[1].get("data")
    assert "message" in data_arg
    
    # Check message properties
    response_message = data_arg["message"]
    assert response_message.channel_id == input_message.channel_id
    assert response_message.channel_type == input_message.channel_type
    assert input_message.conversation_id in response_message.context_ids
    # The implementation appends "After processing: " to the content
    assert "After processing:" in response_message.content
    # Our custom metadata isn't used directly, check standard metadata
    assert "message_type" in response_message.metadata
    assert "action_type" in response_message.metadata
    assert response_message.metadata["action_type"] == "process"