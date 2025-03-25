import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.main import app
from app.utils.auth import create_access_token
from app.core.event_bus import EventBus
from app.core.response_handler import ResponseHandler
from app.core.storage_service import storage_service
from app.models.api import InputMessage


@pytest.mark.asyncio
async def test_input_endpoint_event_publishing():
    """
    Test that the input endpoint properly publishes events to the event bus.
    
    This is a focused test that validates just the input endpoint's behavior
    by mocking dependencies but retaining the real endpoint logic.
    """
    # Set up mock event_bus
    mock_event_bus = MagicMock(spec=EventBus)
    mock_event_bus.publish = AsyncMock()
    
    # Mock storage_service.get_conversation to return True
    original_get_conversation = storage_service.get_conversation
    storage_service.get_conversation = MagicMock(return_value={"id": "test-conv-123"})
    
    # Create a valid token
    token_data = {"sub": "test-user", "id": "test-user-123", "name": "Test User"}
    token = create_access_token(token_data)
    
    # Create a test client with the mocked dependencies
    with TestClient(app) as client:
        # Save original event_bus
        original_event_bus = getattr(app.state, "event_bus", None)
        
        # Replace app.state.event_bus with our mock
        app.state.event_bus = mock_event_bus
        
        try:
            # Make the request with valid token and data
            response = client.post(
                "/input/",
                json={"content": "Hello, test message", "conversation_id": "test-conv-123"},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Verify the response
            assert response.status_code == 200
            assert response.json()["status"] == "received"
            
            # Verify event bus was called correctly
            mock_event_bus.publish.assert_awaited_once()
            call_args = mock_event_bus.publish.await_args
            
            # First arg should be "input"
            assert call_args[0][0] == "input"
            
            # Second arg should be the event payload
            event_data = call_args[0][1]
            # The input endpoint gets the user_id from current_user["id"], which is "test-user"
            # from the JWT token's "sub" field, not the "id" field
            assert event_data["user_id"] == "test-user"
            assert event_data["conversation_id"] == "test-conv-123"
            assert event_data["content"] == "Hello, test message"
            assert event_data["role"] == "user"
            
        finally:
            # Restore the original components
            app.state.event_bus = original_event_bus
            storage_service.get_conversation = original_get_conversation


@pytest.mark.asyncio
async def test_response_handler_processes_input_events():
    """Test that the response handler processes input events correctly."""
    # Create mocks
    mock_event_bus = MagicMock(spec=EventBus)
    mock_event_bus.publish = AsyncMock()
    mock_event_bus.subscribe = MagicMock(return_value=asyncio.Queue())
    
    mock_memory_client = MagicMock()
    mock_memory_client.ensure_connected = AsyncMock()
    mock_memory_client.store_message = AsyncMock()
    
    mock_cognition_client = MagicMock()
    mock_cognition_client.evaluate_context = AsyncMock(return_value="This is a test response")
    
    # Create a response handler with mocked dependencies
    handler = ResponseHandler(
        event_bus=mock_event_bus,
        memory_client=mock_memory_client,
        cognition_client=mock_cognition_client
    )
    
    # Create test event
    test_event = {
        "user_id": "test-user",
        "conversation_id": "test-conv",
        "content": "Hello, test message",
        "metadata": {},
        "role": "user"
    }
    
    # Process the event
    await handler.handle_input_event(test_event)
    
    # Verify memory client interactions
    mock_memory_client.ensure_connected.assert_called_once()
    assert mock_memory_client.store_message.call_count == 2  # Once for user, once for assistant
    
    # Verify first store_message call (user message)
    user_call = mock_memory_client.store_message.call_args_list[0]
    assert user_call.kwargs["user_id"] == "test-user"
    assert user_call.kwargs["conversation_id"] == "test-conv"
    assert user_call.kwargs["content"] == "Hello, test message"
    assert user_call.kwargs["role"] == "user"
    
    # Verify LLM client called
    mock_cognition_client.evaluate_context.assert_called_once_with(
        user_id="test-user", conversation_id="test-conv", message="Hello, test message"
    )
    
    # Verify output event published
    mock_event_bus.publish.assert_awaited_once()
    call_args = mock_event_bus.publish.await_args
    assert call_args[0][0] == "output"  # First arg is event_type
    assert call_args[0][1]["user_id"] == "test-user"
    assert call_args[0][1]["conversation_id"] == "test-conv"
    assert call_args[0][1]["content"] == "This is a test response"
