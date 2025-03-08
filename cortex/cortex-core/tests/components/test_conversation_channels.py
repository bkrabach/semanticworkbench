"""
Test suite for the conversation channels implementation
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json
from datetime import datetime

from app.components.conversation_channels import ConversationOutputPublisher
from app.interfaces.router import OutputMessage, ChannelType
from app.components.event_system import EventPayload


@pytest.fixture
def mock_event_system():
    """Create a mock event system"""
    event_system = AsyncMock()
    event_system.subscribe = AsyncMock(return_value="mock-subscription-id")
    event_system.unsubscribe = AsyncMock(return_value=True)
    return event_system


@pytest.fixture
def mock_send_event():
    """Create a mock for the send_event_to_conversation function"""
    with patch("app.components.conversation_channels.send_event_to_conversation") as mock:
        yield mock


@pytest.fixture
def conversation_publisher(mock_event_system):
    """Create a conversation publisher with the mocked dependencies"""
    with patch("app.components.conversation_channels.get_event_system", return_value=mock_event_system):
        publisher = ConversationOutputPublisher("test-conversation-id")
        publisher.event_system = mock_event_system
        yield publisher


@pytest.mark.asyncio
async def test_publisher_init():
    """Test publisher initialization"""
    # Setup mock
    mock_system = AsyncMock()
    mock_system.subscribe = AsyncMock(return_value="test-subscription-id")
    
    # Create publisher
    with patch("app.components.conversation_channels.get_event_system", return_value=mock_system):
        publisher = ConversationOutputPublisher("test-conversation-id")
        
        # Verify initialization
        assert publisher.conversation_id == "test-conversation-id"
        assert publisher.channel_id == "conversation-test-conversation-id"
        assert publisher.subscriptions == []
        
        # Initialize subscriptions
        await publisher._subscribe_to_events()
        
        # Verify event system interactions
        assert mock_system.subscribe.call_count == 2
        assert len(publisher.subscriptions) == 2


@pytest.mark.asyncio
async def test_handle_message_event(conversation_publisher, mock_send_event):
    """Test handling message events with the new payload structure"""
    # Setup a mock output message
    output_message = OutputMessage(
        message_id="test-message-id",
        channel_id=conversation_publisher.channel_id,
        channel_type=ChannelType.CONVERSATION,
        content="Test message content",
        timestamp=datetime.now()
    )
    
    # Create a mock event payload
    payload = EventPayload(
        event_type="output.conversation.message",
        data={"message": output_message},
        source="test_source",
        trace_id="test-trace-id"
    )
    
    # Setup publisher with a mock for publish method
    conversation_publisher.publish = AsyncMock()
    
    # Call the handler
    await conversation_publisher._handle_message_event(
        event_type="output.conversation.message", 
        payload=payload
    )
    
    # Verify publish was called with the output message
    conversation_publisher.publish.assert_called_once_with(output_message)


@pytest.mark.asyncio
async def test_handle_status_event(conversation_publisher, mock_send_event):
    """Test handling status events with the new payload structure"""
    # Setup a mock output message
    output_message = OutputMessage(
        message_id="test-message-id",
        channel_id=conversation_publisher.channel_id,
        channel_type=ChannelType.CONVERSATION,
        content="Processing...",
        timestamp=datetime.now(),
        metadata={"status": "in_progress"}
    )
    
    # Create a mock event payload
    payload = EventPayload(
        event_type="output.conversation.status",
        data={"message": output_message},
        source="test_source",
        trace_id="test-trace-id"
    )
    
    # Call the handler
    await conversation_publisher._handle_status_event(
        event_type="output.conversation.status", 
        payload=payload
    )
    
    # Verify send_event_to_conversation was called with the right arguments
    mock_send_event.assert_called_once()
    assert mock_send_event.call_args[0][0] == "test-conversation-id"
    assert mock_send_event.call_args[0][1] == "status_update"
    assert "message" in mock_send_event.call_args[0][2]
    assert mock_send_event.call_args[0][2]["message"] == "Processing..."


@pytest.mark.asyncio
async def test_handle_event_with_wrong_channel(conversation_publisher):
    """Test that events for other channels are ignored"""
    # Setup a mock output message with different channel ID
    output_message = OutputMessage(
        message_id="test-message-id",
        channel_id="conversation-other-id",  # Different channel
        channel_type=ChannelType.CONVERSATION,
        content="Test message content",
        timestamp=datetime.now()
    )
    
    # Create a mock event payload
    payload = EventPayload(
        event_type="output.conversation.message",
        data={"message": output_message},
        source="test_source",
        trace_id="test-trace-id"
    )
    
    # Setup publisher with a mock for publish method
    conversation_publisher.publish = AsyncMock()
    
    # Call the handler
    await conversation_publisher._handle_message_event(
        event_type="output.conversation.message", 
        payload=payload
    )
    
    # Verify publish was NOT called
    conversation_publisher.publish.assert_not_called()


@pytest.mark.asyncio
async def test_handle_event_with_invalid_data(conversation_publisher):
    """Test handling events with invalid data structure"""
    # Create a mock event payload with missing or incorrect data
    payload1 = EventPayload(
        event_type="output.conversation.message",
        data={},  # Missing message
        source="test_source",
        trace_id="test-trace-id"
    )
    
    payload2 = EventPayload(
        event_type="output.conversation.message",
        data={"message": "not an OutputMessage"},  # Wrong type
        source="test_source",
        trace_id="test-trace-id"
    )
    
    # Setup publisher with a mock for publish method
    conversation_publisher.publish = AsyncMock()
    
    # Call the handler with both payloads
    await conversation_publisher._handle_message_event(
        event_type="output.conversation.message", 
        payload=payload1
    )
    
    await conversation_publisher._handle_message_event(
        event_type="output.conversation.message", 
        payload=payload2
    )
    
    # Verify publish was NOT called in either case
    assert conversation_publisher.publish.call_count == 0


@pytest.mark.asyncio
async def test_cleanup(conversation_publisher):
    """Test cleanup method unsubscribes from events"""
    # Setup test
    conversation_publisher.subscriptions = ["sub1", "sub2", "sub3"]
    
    # Call cleanup
    await conversation_publisher.cleanup()
    
    # Verify unsubscribe was called for each subscription
    assert conversation_publisher.event_system.unsubscribe.call_count == 3
    assert conversation_publisher.subscriptions == []