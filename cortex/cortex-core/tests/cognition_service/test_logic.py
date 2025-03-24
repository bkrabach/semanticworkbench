"""
Tests for the Cognition Service logic.
"""
import asyncio
import pytest
from unittest.mock import patch

from cognition_service.logic import agent, generate_ai_response
from cognition_service.models import Message, MessageRole


@pytest.mark.asyncio
async def test_generate_ai_response_basic():
    """Test that generate_ai_response returns a response."""
    # Mock the agent.run method to return a fixed response
    with patch.object(agent, 'run', return_value="Test response"):
        response = await generate_ai_response(
            user_id="test_user",
            conversation_id="test_conversation",
            content="Hello, world!"
        )
        
    # Check that we got the expected response
    assert response == "Test response"


@pytest.mark.asyncio
async def test_generate_ai_response_with_history():
    """Test generate_ai_response with conversation history."""
    # Mock the get_conversation_history function to return test messages
    test_history = [
        Message(role=MessageRole.USER, content="Hello"),
        Message(role=MessageRole.ASSISTANT, content="Hi there!")
    ]
    
    with patch.object(agent, 'run', return_value="Response with history context"), \
         patch('cognition_service.logic.get_conversation_history', return_value=asyncio.Future()) as mock_get_history:
        
        # Set the result of the future
        mock_get_history.return_value.set_result(test_history)
        
        response = await generate_ai_response(
            user_id="test_user",
            conversation_id="test_conversation",
            content="How are you today?"
        )
    
    # Check that we got the expected response
    assert response == "Response with history context"


@pytest.mark.asyncio
async def test_generate_ai_response_error_handling():
    """Test that generate_ai_response handles errors gracefully."""
    # Patch run to simulate an exception
    with patch.object(agent, 'run', side_effect=Exception("Test exception")):
        response = await generate_ai_response(
            user_id="test_user",
            conversation_id="test_conversation",
            content="This should fail"
        )
    
    # Verify error response contains expected text
    assert "apologize" in response.lower()
    assert "error" in response.lower()