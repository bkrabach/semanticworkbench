"""
Tests for the Cognition Service core logic.
"""
import pytest
from unittest.mock import AsyncMock, patch

from cognition_service.logic import (
    # agent removed as unused
    
    generate_ai_response, 
    evaluate_context, 
    get_conversation_history,
    convert_to_pydantic_ai_messages
)
from cognition_service.models import Message
from cognition_service.memory_client import MemoryServiceError
from tests.cognition_service.conftest import MockPydanticAIResult


@pytest.mark.asyncio
async def test_get_conversation_history_disabled(mock_settings):
    """Test that get_conversation_history returns empty list when memory is disabled."""
    with patch("cognition_service.logic.settings", mock_settings):
        # Disable memory integration
        mock_settings.enable_memory_integration = False
        
        result = await get_conversation_history("test-conversation-id")
        
        assert result == []
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_get_conversation_history_error(mock_memory_client):
    """Test that get_conversation_history handles errors gracefully."""
    # Make the memory client raise an exception
    mock_memory_client.get_conversation_history.side_effect = MemoryServiceError("Test error")
    
    result = await get_conversation_history("test-conversation-id")
    
    assert result == []
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_get_conversation_history_success(sample_messages, mock_settings):
    """Test that get_conversation_history returns messages on success."""
    # Create a fresh mock memory client
    with patch("cognition_service.logic.memory_client") as mock_client, \
         patch("cognition_service.logic.settings", mock_settings):
        
        # Ensure memory integration is enabled
        mock_settings.enable_memory_integration = True
        
        # Configure it to return sample messages
        mock_client.get_conversation_history = AsyncMock(return_value=sample_messages)
        
        # Call the function
        result = await get_conversation_history("test-conversation-id")
        
        # Verify the result
        assert result == sample_messages
        assert len(result) == len(sample_messages)
        assert all(isinstance(msg, Message) for msg in result)
        
        # Verify the mock was called correctly
        mock_client.get_conversation_history.assert_called_once_with("test-conversation-id")


def test_convert_to_pydantic_ai_messages(sample_messages):
    """Test conversion of internal message models to Pydantic AI format."""
    converted = convert_to_pydantic_ai_messages(sample_messages)
    
    assert len(converted) == len(sample_messages)
    assert all(isinstance(msg, dict) for msg in converted)
    assert all("role" in msg and "content" in msg for msg in converted)
    
    # Verify the conversion is correct
    for i, original in enumerate(sample_messages):
        assert converted[i]["role"] == original.role.value
        assert converted[i]["content"] == original.content


@pytest.mark.asyncio
async def test_generate_ai_response_basic():
    """Test that generate_ai_response returns a response with minimal input."""
    # Set up the mock agent
    expected_response = "This is a test response"
    
    with patch("cognition_service.logic.agent") as mock_agent, \
         patch("cognition_service.logic.get_conversation_history", return_value=AsyncMock(return_value=[])):
        
        # Configure the agent to return our test response
        mock_agent.run = AsyncMock(return_value=MockPydanticAIResult(expected_response))
        
        # Call the function
        response = await generate_ai_response(
            user_id="test_user",
            conversation_id="test_conversation",
            content="Hello, world!"
        )
        
        # Check that we got the expected response
        assert response == expected_response
        
        # Verify the agent was called
        mock_agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_generate_ai_response_with_history(sample_messages):
    """Test generate_ai_response with conversation history."""
    # Set up the expected response
    expected_response = "Response with history context"
    
    # Create fresh mocks
    with patch("cognition_service.logic.agent") as mock_agent, \
         patch("cognition_service.logic.get_conversation_history") as mock_get_history:
            
        # Set up mocks
        mock_agent.run = AsyncMock(return_value=MockPydanticAIResult(expected_response))
        mock_get_history.return_value = sample_messages  # No coroutine wrapper needed
        
        # Call the function
        response = await generate_ai_response(
            user_id="test_user",
            conversation_id="test_conversation",
            content="How are you today?"
        )
        
        # Check that we got the expected response
        assert response == expected_response
        
        # Verify the history function was called
        mock_get_history.assert_called_once_with("test_conversation")
        
        # Verify the agent was called with a prompt containing relevant text
        assert mock_agent.run.called
        call_args = mock_agent.run.call_args[0][0]
        assert "Previous conversation" in call_args


@pytest.mark.asyncio
async def test_generate_ai_response_error_handling(mock_agent):
    """Test that generate_ai_response handles errors gracefully."""
    # Make the agent raise an exception
    mock_agent.run.side_effect = Exception("Test exception")
    
    response = await generate_ai_response(
        user_id="test_user",
        conversation_id="test_conversation",
        content="This should fail"
    )
    
    # Verify error response contains expected text
    assert "apologize" in response.lower()
    assert "error" in response.lower()


@pytest.mark.asyncio
async def test_evaluate_context_basic():
    """Test evaluate_context with minimal input."""
    # Set up the expected response
    expected_response = "Evaluation response"
    
    # Create fresh mocks
    with patch("cognition_service.logic.agent") as mock_agent, \
         patch("cognition_service.logic.get_conversation_history") as mock_get_history:
            
        # Set up mocks
        mock_agent.run = AsyncMock(return_value=MockPydanticAIResult(expected_response))
        mock_get_history.return_value = []  # No coroutine wrapper needed
        
        # Call the function
        response = await evaluate_context(
            user_id="test_user",
            conversation_id="test_conversation",
            message="Evaluate this"
        )
        
        # Check that we got the expected response
        assert response == expected_response
        
        # Verify the agent was called
        mock_agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_context_with_memory_snippets(sample_messages):
    """Test evaluate_context with memory snippets."""
    # Set up memory snippets
    memory_snippets = [
        {"content": "User asked about Python programming"},
        {"content": "User seems interested in machine learning"}
    ]
    
    # Set up the expected response
    expected_response = "Response with memory snippets"
    
    # Create fresh mocks
    with patch("cognition_service.logic.agent") as mock_agent, \
         patch("cognition_service.logic.get_conversation_history") as mock_get_history:
            
        # Set up mocks
        mock_agent.run = AsyncMock(return_value=MockPydanticAIResult(expected_response))
        mock_get_history.return_value = sample_messages  # No coroutine wrapper needed
        
        # Call the function
        response = await evaluate_context(
            user_id="test_user",
            conversation_id="test_conversation",
            message="Tell me more",
            memory_snippets=memory_snippets
        )
        
        # Check that we got the expected response
        assert response == expected_response
        
        # Verify the agent was called with a prompt containing memory snippets
        assert mock_agent.run.called
        call_args = mock_agent.run.call_args[0][0]
        assert "Previous conversation" in call_args
        assert "Python programming" in call_args
        assert "machine learning" in call_args


@pytest.mark.asyncio
async def test_evaluate_context_with_expert_insights(mock_agent):
    """Test evaluate_context with expert insights."""
    # Set up expert insights
    expert_insights = [
        {"source": "PythonExpert", "content": "Python is a versatile language."},
        {"source": "MLExpert", "content": "Machine learning requires quality data."}
    ]
    
    # Set up the mock response
    expected_response = "Response with expert insights"
    mock_agent.run.return_value = MockPydanticAIResult(expected_response)
    
    response = await evaluate_context(
        user_id="test_user",
        conversation_id="test_conversation",
        message="Tell me about Python and ML",
        expert_insights=expert_insights
    )
    
    # Check that we got the expected response
    assert response == expected_response
    
    # Verify the agent was called with a prompt containing expert insights
    call_args = mock_agent.run.call_args[0][0]
    assert "Domain expert insights" in call_args
    assert "[PythonExpert]: Python is a versatile language" in call_args
    assert "[MLExpert]: Machine learning requires quality data" in call_args


@pytest.mark.asyncio
async def test_evaluate_context_error_handling(mock_agent):
    """Test that evaluate_context handles errors gracefully."""
    # Make the agent raise an exception
    mock_agent.run.side_effect = Exception("Test exception")
    
    response = await evaluate_context(
        user_id="test_user",
        conversation_id="test_conversation",
        message="This should fail"
    )
    
    # Verify error response contains expected text
    assert "apologize" in response.lower()
    assert "error" in response.lower()
    assert "context" in response.lower()  # Specific to evaluate_context error message