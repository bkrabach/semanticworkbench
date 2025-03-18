"""
Test case for conversation message echo functionality
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from app.models.domain.conversation import Message


@pytest.mark.asyncio
async def test_add_message_with_auto_echo():
    """
    Test that when adding a message to a conversation, it gets routed to the CortexRouter
    """
    # Mock the conversation service
    mock_service = AsyncMock()
    
    # Create test data
    test_conversation_id = str(uuid.uuid4())
    test_user_id = str(uuid.uuid4())
    
    # Create mock user
    mock_user = MagicMock()
    mock_user.id = test_user_id
    mock_user.email = "test@example.com"
    
    # Create mock message that service will return
    mock_message = Message(
        id=str(uuid.uuid4()),
        content="Test message",
        role="user",
        workspace_id=str(uuid.uuid4()),  # Add this for the InputMessage
        created_at=datetime.now(timezone.utc),
        metadata={}
    )
    
    # Configure service mocks
    mock_service.add_message = AsyncMock(return_value=mock_message)
    
    # Mock the router
    mock_router = MagicMock()
    mock_router.process_input = AsyncMock(return_value=True)

    # Setup patches
    with patch("app.api.conversations.get_conversation_service", return_value=mock_service), \
         patch("app.components.cortex_router.get_router", return_value=mock_router):
        
        # Import the add_message function
        from app.api.conversations import add_message
        from app.models.api.request.conversation import AddMessageRequest
        
        # Create message request
        message_request = AddMessageRequest(
            content="Test message",
            role="user",
            metadata={}
        )
        
        # Call the function
        response = await add_message(
            conversation_id=test_conversation_id,
            message_request=message_request,
            user=mock_user,
            service=mock_service
        )
        
        # Check message was added to database
        mock_service.add_message.assert_called_once_with(
            conversation_id=test_conversation_id,
            content="Test message",
            role="user",
            metadata={}
        )
        
        # Check router was called
        mock_router.process_input.assert_called_once()
        
        # Check proper response was returned
        assert response["status"] == "message_received"
        assert response["message_id"] == mock_message.id