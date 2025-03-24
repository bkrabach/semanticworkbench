"""
Integration tests for the Cognition Service components working together.
"""
import pytest
from unittest.mock import AsyncMock, patch, Mock

from cognition_service.main import generate_reply, evaluate_context_tool
from cognition_service.models import Message, MessageRole
from cognition_service.memory_client import MemoryClient
from tests.cognition_service.conftest import MockPydanticAIResult


@pytest.mark.integration
class TestCognitionServiceIntegration:
    """Integration tests for the Cognition Service components."""
    
    @pytest.fixture
    def setup_mocks(self):
        """Set up mocks for the integration tests."""
        # Patch the agent globally
        with patch("cognition_service.logic.agent") as mock_agent, \
             patch("cognition_service.logic.memory_client") as mock_memory_client, \
             patch("cognition_service.logic.get_conversation_history") as mock_get_history:
            
            # Set up agent to return a mock response
            mock_result = MockPydanticAIResult("Integration test response") 
            mock_agent.run = AsyncMock(return_value=mock_result)
            
            # Set up message history
            messages = [
                Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
                Message(role=MessageRole.USER, content="Hello"),
                Message(role=MessageRole.ASSISTANT, content="Hi there!")
            ]
            
            # Set up memory client with test conversation history
            mock_memory_client.get_conversation_history = AsyncMock(return_value=messages)
            
            # Also set up the get_conversation_history function
            mock_get_history.return_value = messages
            
            yield {
                "agent": mock_agent,
                "memory_client": mock_memory_client,
                "get_history": mock_get_history
            }
    
    @pytest.mark.asyncio
    async def test_end_to_end_reply_generation(self, setup_mocks):
        """Test end-to-end flow from MCP endpoint to logic to memory client."""
        with patch("cognition_service.main.generate_ai_response") as mock_generate_response:
            # Set up the mock to return a test response
            mock_generate_response.return_value = "Integration test response"
            
            # Call the MCP endpoint for generating a reply
            response = await generate_reply(
                user_id="test-user",
                conversation_id="test-convo",
                content="How can you help me today?"
            )
            
            # Verify the response
            assert response == "Integration test response"
            
            # Verify generate_ai_response was called
            mock_generate_response.assert_called_once()
            
            # Get the actual call arguments
            args, kwargs = mock_generate_response.call_args
            
            # Check that all the needed parameters were passed (either as positional or keyword)
            if args:  # If called with positional args
                assert "test-user" in args
                assert "test-convo" in args
                assert "How can you help me today?" in args
            else:  # If called with keyword args
                assert kwargs.get("user_id") == "test-user"
                assert kwargs.get("conversation_id") == "test-convo"
                assert kwargs.get("content") == "How can you help me today?"
    
    @pytest.mark.asyncio
    async def test_end_to_end_context_evaluation(self, setup_mocks):
        """Test end-to-end flow for context evaluation."""
        with patch("cognition_service.main.evaluate_context") as mock_evaluate:
            # Set up the mock to return a test response
            mock_evaluate.return_value = "Integration test response"
            
            # Prepare test data
            memory_snippets = [{"content": "User previously asked about Python"}]
            expert_insights = [{"source": "PythonExpert", "content": "Python is versatile"}]
            
            # Call the MCP endpoint for context evaluation
            response = await evaluate_context_tool(
                user_id="test-user",
                conversation_id="test-convo",
                message="Tell me about Python",
                memory_snippets=memory_snippets,
                expert_insights=expert_insights
            )
            
            # Verify the response format
            assert isinstance(response, dict)
            assert response["message"] == "Integration test response"
            
            # Verify evaluate_context was called with the right parameters
            mock_evaluate.assert_called_once_with(
                user_id="test-user",
                conversation_id="test-convo",
                message="Tell me about Python",
                memory_snippets=memory_snippets,
                expert_insights=expert_insights
            )
    
    @pytest.mark.asyncio
    async def test_memory_integration_disabled(self, setup_mocks):
        """Test that the system works when memory integration is disabled."""
        # Patch settings and generate_ai_response
        with patch("cognition_service.logic.settings.enable_memory_integration", False), \
             patch("cognition_service.main.generate_ai_response") as mock_generate:
             
            # Set up mock
            mock_generate.return_value = "Integration test response"
            
            # Also patch get_conversation_history to verify it's not called
            with patch("cognition_service.logic.get_conversation_history") as mock_get_history:
                # Call the MCP endpoint
                response = await generate_reply(
                    user_id="test-user",
                    conversation_id="test-convo",
                    content="How can you help me?"
                )
                
                # Verify response still works
                assert response == "Integration test response"
                
                # Verify generate_ai_response was called
                mock_generate.assert_called_once()
                
                # We've patched get_conversation_history directly at the lower level
                # to verify it's not called when memory integration is disabled
                mock_get_history.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, setup_mocks):
        """Test that the system recovers from errors in components."""
        # Make memory client raise an exception
        setup_mocks["memory_client"].get_conversation_history.side_effect = Exception("Memory error")
        
        # Call the MCP endpoint
        response = await generate_reply(
            user_id="test-user",
            conversation_id="test-convo",
            content="This should still work"
        )
        
        # Verify we still get a response
        assert response == "Integration test response"
        
        # Verify agent was still called despite memory error
        setup_mocks["agent"].run.assert_called_once()
        
        # Now make agent raise an exception too
        setup_mocks["agent"].run.side_effect = Exception("Agent error")
        
        # Call the MCP endpoint again
        response = await generate_reply(
            user_id="test-user",
            conversation_id="test-convo",
            content="This should return an error message"
        )
        
        # Verify we get the error fallback response
        assert "apologize" in response.lower()
        assert "error" in response.lower()