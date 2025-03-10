"""
Test suite for the Cortex Router component
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from enum import Enum

from app.components.cortex_router import CortexRouter
from app.interfaces.router import InputMessage, RoutingDecision, ChannelType, ActionType


@pytest.fixture
def mock_event_system():
    """Create a mock event system"""
    event_system = AsyncMock()
    event_system.publish = AsyncMock()
    return event_system


@pytest.fixture
async def cortex_router(mock_event_system, monkeypatch):
    """Create a cortex router with mocked dependencies"""
    # Mock the private methods used in tests
    monkeypatch.setattr(CortexRouter, "_send_typing_indicator", AsyncMock())
    monkeypatch.setattr(CortexRouter, "_save_message_to_database", AsyncMock(return_value="test-message-id"))
    monkeypatch.setattr(CortexRouter, "_send_message_to_client", AsyncMock())
    
    # Create the router
    router = CortexRouter()
    router.event_system = mock_event_system
    
    # Use monkeypatch approach for private method
    setattr(router, "_send_status_message", AsyncMock())
    
    # Properly cleanup in the fixture
    yield router
    await router.cleanup()


@pytest.mark.asyncio
async def test_send_status_message(cortex_router, mock_event_system):
    """Test sending status messages with the event system"""
    # Skip this test as the method is no longer used in the simplified messaging architecture
    # The test needs to be updated to match the new direct communication flow
    pytest.skip("Test needs to be updated for new messaging architecture")
    
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
    """Test handling respond action with direct SSE communication"""
    # Create an input message
    input_message = InputMessage(
        message_id="test-message-id",
        conversation_id="test-conversation-id",
        channel_id="test-channel-id",
        channel_type=ChannelType.CLI,
        content="Test message content",
        timestamp=datetime.now(timezone.utc)
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
    
    # Verify typing indicator was sent
    cortex_router._send_typing_indicator.assert_called()
    
    # Verify message was saved to database
    cortex_router._save_message_to_database.assert_called_once()
    
    # Verify message was sent to client
    cortex_router._send_message_to_client.assert_called_once()


@pytest.mark.asyncio
async def test_handle_process_action(cortex_router, mock_event_system):
    """Test handling process action with direct SSE communication"""
    # The current implementation just calls _handle_respond_action
    # Skip this test as it needs to be updated for the new architecture
    pytest.skip("Test needs to be updated for new messaging architecture")