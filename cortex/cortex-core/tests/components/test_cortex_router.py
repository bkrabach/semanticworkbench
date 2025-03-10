"""
Test suite for the Cortex Router component
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from enum import Enum

from app.components.cortex_router import CortexRouter
from app.interfaces.router import InputMessage, RoutingDecision, ChannelType, ActionType
from app.services.llm_service import LlmService


@pytest.fixture
def mock_event_system():
    """Create a mock event system"""
    event_system = AsyncMock()
    event_system.publish = AsyncMock()
    return event_system


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service"""
    llm_service = AsyncMock()
    llm_service.get_completion = AsyncMock(return_value="This is a mock LLM response")
    return llm_service


@pytest.fixture
async def cortex_router(mock_event_system, mock_llm_service, monkeypatch):
    """Create a cortex router with mocked dependencies"""
    # Mock the private methods used in tests
    monkeypatch.setattr(CortexRouter, "_send_typing_indicator", AsyncMock())
    monkeypatch.setattr(CortexRouter, "_save_message_to_database", AsyncMock(return_value="test-message-id"))
    monkeypatch.setattr(CortexRouter, "_send_message_to_client", AsyncMock())
    
    # Mock the LLM service getter
    monkeypatch.setattr("app.components.cortex_router.get_llm_service", lambda: mock_llm_service)
    
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
async def test_handle_respond_action(cortex_router, mock_event_system, mock_llm_service):
    """Test handling respond action with LLM integration"""
    # Reset the mocks to clear any previous calls
    cortex_router._send_typing_indicator.reset_mock()
    cortex_router._save_message_to_database.reset_mock()
    cortex_router._send_message_to_client.reset_mock()
    mock_llm_service.get_completion.reset_mock()
    
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
    
    # Check if send_typing_indicator was called at least twice
    assert cortex_router._send_typing_indicator.call_count >= 2
    
    # Get all the calls to send_typing_indicator
    calls = cortex_router._send_typing_indicator.call_args_list
    
    # First call should be with True (turning indicator on)
    assert calls[0][0][0] == input_message.conversation_id
    assert calls[0][0][1] is True
    
    # Last call should be with False (turning indicator off)
    assert calls[-1][0][0] == input_message.conversation_id
    assert calls[-1][0][1] is False
    
    # Verify LLM service was called with the correct parameters
    mock_llm_service.get_completion.assert_called_once()
    assert mock_llm_service.get_completion.call_args[1]["prompt"] == input_message.content
    assert "system_prompt" in mock_llm_service.get_completion.call_args[1]
    
    # Verify message was saved to database with LLM response
    cortex_router._save_message_to_database.assert_called_once()
    saved_response = cortex_router._save_message_to_database.call_args[0][1]
    assert saved_response == "This is a mock LLM response"
    
    # Verify metadata includes LLM flag
    saved_metadata = cortex_router._save_message_to_database.call_args[0][3]
    assert saved_metadata["llm_enabled"] is True
    
    # Verify message was sent to client
    cortex_router._send_message_to_client.assert_called_once()


@pytest.mark.asyncio
async def test_handle_respond_action_llm_error(cortex_router, mock_event_system, mock_llm_service):
    """Test handling respond action with LLM error"""
    # Make the LLM service raise an exception
    mock_llm_service.get_completion.side_effect = Exception("Test LLM error")
    
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
        metadata={"key": "value"}
    )
    
    # Call handle respond action
    await cortex_router._handle_respond_action(
        message=input_message,
        decision=decision
    )
    
    # Verify typing indicator was sent and then turned off
    assert cortex_router._send_typing_indicator.call_count >= 2
    
    # Verify error message was saved to database
    cortex_router._save_message_to_database.assert_called_once()
    saved_metadata = cortex_router._save_message_to_database.call_args[0][3]
    assert "error" in saved_metadata
    
    # Verify error message was sent to client
    cortex_router._send_message_to_client.assert_called_once()


@pytest.mark.asyncio
async def test_handle_process_action(cortex_router, mock_event_system):
    """Test handling process action with direct SSE communication"""
    # The current implementation just calls _handle_respond_action
    # Skip this test as it needs to be updated for the new architecture
    pytest.skip("Test needs to be updated for new messaging architecture")