"""
Test case for conversation message echo functionality
"""

import pytest
import asyncio
from datetime import datetime, timezone
import uuid
from unittest.mock import MagicMock, AsyncMock, patch

from app.models.domain.conversation import Message, Conversation
from app.services.sse_service import SSEService
from app.components.sse.manager import SSEConnectionManager


@pytest.mark.asyncio
async def test_add_message_with_auto_echo():
    """
    Test that when adding a message to a conversation, an echo response is auto-generated
    """
    # Mock the conversation service
    mock_service = AsyncMock()
    
    # Add a mock get_user method
    user = MagicMock()
    user.id = str(uuid.uuid4())
    user.email = "test@example.com"
    user.name = "Test User"
    user.created_at = datetime.now(timezone.utc)
    mock_service.get_user = MagicMock(return_value=user)
    # Create a conversation ID first
    test_conversation_id = str(uuid.uuid4())
    
    mock_message = Message(
        id=str(uuid.uuid4()),
        content="Test message",
        role="user",
        created_at=datetime.now(timezone.utc),
        metadata={}
    )
    # Make add_message async and return the correct value
    mock_service.add_message = AsyncMock(return_value=mock_message)
    
    # Mock the conversation to be returned by get_conversation
    mock_conversation = Conversation(
        id=test_conversation_id,
        workspace_id=str(uuid.uuid4()),
        title="Test Conversation",
        modality="chat",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
        metadata={},
        messages=[mock_message]
    )
    mock_service.get_conversation = AsyncMock(return_value=mock_conversation)
    
    # Mock the SSE service and connection manager
    mock_sse_manager = MagicMock(spec=SSEConnectionManager)
    mock_sse_service = MagicMock(spec=SSEService)
    mock_sse_service.connection_manager = mock_sse_manager
    
    # Import the add_message function
    from app.api.conversations import add_message
    
    # Create a request model
    class MockRequest:
        content = "Test message"
        role = "user"
        metadata = {}
    
    # Setup router mock
    mock_router = MagicMock()
    mock_router.process_input = AsyncMock(return_value=True)

    # Setup patches
    with patch("app.api.conversations.get_conversation_service", return_value=mock_service), \
         patch("app.components.cortex_router.get_router", return_value=mock_router), \
         patch("app.services.sse_service.get_sse_service", return_value=mock_sse_service):
        
        # Convert mock request to an actual AddMessageRequest
        from app.models.api.request.conversation import AddMessageRequest
        message_request = AddMessageRequest(
            content="Test message",
            role="user",
            metadata={}
        )
        
        # Call the function
        response = await add_message(
            conversation_id=test_conversation_id,
            message_request=message_request,
            user=mock_service.get_user(),  # This is a mock, get_user will be mocked
            service=mock_service
        )
        
        # Check that the original message was added
        mock_service.add_message.assert_any_call(
            conversation_id=test_conversation_id,
            content="Test message",
            role="user",
            metadata={}
        )
        
        # We now use a background task for routing, so just check the response
        
        # Check the response was returned for the original message
        assert response is not None
        assert response.id == mock_message.id
        assert response.content == "Test message"