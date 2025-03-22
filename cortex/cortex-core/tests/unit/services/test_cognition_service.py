import uuid
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

import pytest

from app.services.cognition import CognitionService
from app.models import Message


@pytest.fixture
def memory_service_mock() -> Mock:
    mock = Mock()
    mock.get_limited_history = AsyncMock()
    mock.get_conversation = AsyncMock()
    mock.get_history = AsyncMock()
    return mock


@pytest.fixture
def cognition_service(memory_service_mock: Mock) -> CognitionService:
    return CognitionService(memory_service=memory_service_mock)


@pytest.mark.asyncio
async def test_get_context_filters_error_information(cognition_service: CognitionService, memory_service_mock: Mock) -> None:
    """Test that get_context filters out error information from message metadata."""
    # Arrange
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    
    # Create a message with error information in the context metadata
    message_with_error = Message(
        id=str(uuid.uuid4()),
        sender_id=user_id,  # sender_id is the required field
        conversation_id=conversation_id,
        content="Test message",
        metadata={
            "context": {
                "context": [],
                "user_id": user_id,
                "query": None,
                "count": 0,
                "error": "InProcessMCPClient.get_resource() got an unexpected keyword argument 'service'"
            }
        }
    )
    
    # Configure the mock to return a message with error information
    memory_service_mock.get_limited_history.return_value = [message_with_error.model_dump()]
    
    # Act
    result = await cognition_service.get_context(user_id=user_id)
    
    # Assert
    # Verify that the result doesn't contain the error information
    assert "error" not in result["context"][0]["metadata"]["context"]
    
    # Verify that the other fields are preserved
    assert result["context"][0]["metadata"]["context"]["user_id"] == user_id
    assert result["context"][0]["metadata"]["context"]["query"] is None
    assert result["context"][0]["metadata"]["context"]["count"] == 0
    
    # Verify that the memory service was called with the correct parameters
    memory_service_mock.get_limited_history.assert_called_once_with(user_id, "20")


@pytest.mark.asyncio
async def test_get_context_handles_missing_context_metadata(cognition_service: CognitionService, memory_service_mock: Mock) -> None:
    """Test that get_context handles missing context in message metadata."""
    # Arrange
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    
    # Create a message without context in the metadata
    message_without_context = Message(
        id=str(uuid.uuid4()),
        sender_id=user_id,  # sender_id is the required field
        conversation_id=conversation_id,
        content="Test message",
        metadata={
            "client_id": "test-client",
            "client_version": "1.0.0"
        }
    )
    
    # Configure the mock to return a message without context metadata
    memory_service_mock.get_limited_history.return_value = [message_without_context.model_dump()]
    
    # Act
    result = await cognition_service.get_context(user_id=user_id)
    
    # Assert
    # Verify that the result contains the message's metadata
    assert result["context"][0]["metadata"]["client_id"] == "test-client"
    assert result["context"][0]["metadata"]["client_version"] == "1.0.0"
    
    # Verify that the memory service was called with the correct parameters
    memory_service_mock.get_limited_history.assert_called_once_with(user_id, "20")


@pytest.mark.asyncio
async def test_analyze_conversation_filters_error_information(cognition_service: CognitionService, memory_service_mock: Mock) -> None:
    """Test that analyze_conversation filters out error information from message metadata."""
    # Arrange
    user_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    
    # Create a message with error information in the context metadata
    message_with_error = Message(
        id=str(uuid.uuid4()),
        sender_id=user_id,  # sender_id is the required field
        conversation_id=conversation_id,
        content="Test message",
        metadata={
            "context": {
                "context": [],
                "user_id": user_id,
                "query": None,
                "count": 0,
                "error": "InProcessMCPClient.get_resource() got an unexpected keyword argument 'service'"
            }
        }
    )
    
    # Configure the mock to return a message with error information
    memory_service_mock.get_conversation.return_value = [message_with_error.model_dump()]
    
    # Mock the private methods that would be called
    with patch.object(CognitionService, '_generate_conversation_summary', return_value={"message_count": 1}) as mock_summary:
        # Act
        result = await cognition_service.analyze_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            analysis_type="summary"
        )
        
        # Assert
        # Verify that the mock was called with data that doesn't contain error information
        conversation_items = mock_summary.call_args[0][0]
        assert "error" not in conversation_items[0]["metadata"]["context"]
        
        # Verify that the memory service was called with the correct parameters
        memory_service_mock.get_conversation.assert_called_once_with(conversation_id)


@pytest.mark.asyncio
async def test_search_history_filters_error_information(cognition_service: CognitionService, memory_service_mock: Mock) -> None:
    """Test that search_history filters out error information from message metadata."""
    # Arrange
    user_id = str(uuid.uuid4())
    query = "test query"
    
    # Create a message with error information in the context metadata
    message_with_error = Message(
        id=str(uuid.uuid4()),
        sender_id=user_id,  # sender_id is the required field
        conversation_id=str(uuid.uuid4()),
        content="Test message containing the query",
        metadata={
            "context": {
                "context": [],
                "user_id": user_id,
                "query": None,
                "count": 0,
                "error": "InProcessMCPClient.get_resource() got an unexpected keyword argument 'service'"
            }
        }
    )
    
    # Configure the mock to return a message with error information
    memory_service_mock.get_history.return_value = [message_with_error.model_dump()]
    
    # Act
    result = await cognition_service.search_history(
        user_id=user_id,
        query=query
    )
    
    # Assert
    # Verify that our test query matches the message content
    assert len(result["results"]) == 1
    
    # Verify that the result doesn't contain the error information
    assert "error" not in result["results"][0]["metadata"]["context"]
    
    # Verify that the other fields are preserved
    assert result["results"][0]["metadata"]["context"]["user_id"] == user_id
    assert result["results"][0]["metadata"]["context"]["query"] is None
    assert result["results"][0]["metadata"]["context"]["count"] == 0
    
    # Verify that the memory service was called with the correct parameters
    memory_service_mock.get_history.assert_called_once_with(user_id)