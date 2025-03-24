"""
Tests for the models and configuration of the Memory Service.
"""
import pytest
from pydantic import ValidationError

from memory_service.config import config, MemoryServiceConfig
from memory_service.models import (
    MemoryEntry, MemoryUpdateRequest, MemoryUpdateResponse,
    MemoryRetrievalRequest, MemoryRetrievalResponse
)


def test_memory_service_config_defaults():
    """Test that MemoryServiceConfig has appropriate defaults."""
    # Create a config instance with default values
    default_config = MemoryServiceConfig()
    
    # Basic checks
    assert isinstance(default_config.HOST, str)
    assert isinstance(default_config.PORT, int)
    assert isinstance(default_config.MCP_BASE_ROUTE, str)
    assert isinstance(default_config.STORAGE_DIR, str)
    assert isinstance(default_config.LLM_MODEL, str)
    assert isinstance(default_config.LLM_TEMPERATURE, float)
    assert isinstance(default_config.MAX_MEMORY_LENGTH, int)
    
    # Check service_url property
    expected_url = f"http://{default_config.HOST}:{default_config.PORT}{default_config.MCP_BASE_ROUTE}"
    assert default_config.service_url == expected_url


def test_config_properties():
    """Test that the config object has expected properties."""
    # Create a test instance with custom values
    test_config = MemoryServiceConfig()
    test_config.HOST = "testhost"
    test_config.PORT = 5050
    test_config.STORAGE_DIR = "/tmp/test_memory"
    test_config.LLM_MODEL = "test-model"
    test_config.LLM_TEMPERATURE = 0.5
    test_config.MAX_MEMORY_LENGTH = 1000
    
    # Verify values were set correctly
    assert test_config.HOST == "testhost"
    assert test_config.PORT == 5050
    assert test_config.STORAGE_DIR == "/tmp/test_memory"
    assert test_config.LLM_MODEL == "test-model"
    assert test_config.LLM_TEMPERATURE == 0.5
    assert test_config.MAX_MEMORY_LENGTH == 1000
    
    # Check service_url property with custom values
    expected_url = f"http://testhost:5050{test_config.MCP_BASE_ROUTE}"
    assert test_config.service_url == expected_url


def test_global_config_instance():
    """Test that the global config instance is properly initialized."""
    assert config is not None
    assert isinstance(config, MemoryServiceConfig)


def test_memory_entry_model():
    """Test the MemoryEntry model."""
    # Create a valid memory entry
    entry = MemoryEntry(
        conversation_id="test-conversation",
        memory_content="This is a test memory.",
        last_updated="2023-01-01T12:00:00"
    )
    
    # Check fields
    assert entry.conversation_id == "test-conversation"
    assert entry.memory_content == "This is a test memory."
    assert entry.last_updated == "2023-01-01T12:00:00"
    
    # Test validation failure - missing required fields
    with pytest.raises(ValidationError):
        MemoryEntry(conversation_id="test-conversation")


def test_memory_update_request():
    """Test the MemoryUpdateRequest model."""
    # Create a valid request
    request = MemoryUpdateRequest(
        conversation_id="test-conversation",
        new_messages=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
    )
    
    # Check fields
    assert request.conversation_id == "test-conversation"
    assert len(request.new_messages) == 2
    assert request.new_messages[0]["role"] == "user"
    assert request.new_messages[0]["content"] == "Hello"
    
    # Test validation failure - missing required fields
    with pytest.raises(ValidationError):
        MemoryUpdateRequest(conversation_id="test-conversation")


def test_memory_update_response():
    """Test the MemoryUpdateResponse model."""
    # Create a valid response
    response = MemoryUpdateResponse(
        conversation_id="test-conversation",
        updated_memory="Updated memory content",
        success=True
    )
    
    # Check fields
    assert response.conversation_id == "test-conversation"
    assert response.updated_memory == "Updated memory content"
    assert response.success is True
    
    # Test validation failure - missing required fields
    with pytest.raises(ValidationError):
        MemoryUpdateResponse(conversation_id="test-conversation", updated_memory="test")


def test_memory_retrieval_request():
    """Test the MemoryRetrievalRequest model."""
    # Create a valid request
    request = MemoryRetrievalRequest(conversation_id="test-conversation")
    
    # Check fields
    assert request.conversation_id == "test-conversation"
    
    # Test validation failure - missing required fields
    with pytest.raises(ValidationError):
        MemoryRetrievalRequest()


def test_memory_retrieval_response():
    """Test the MemoryRetrievalResponse model."""
    # Create a valid response - memory exists
    response = MemoryRetrievalResponse(
        conversation_id="test-conversation",
        memory_content="Memory content",
        exists=True
    )
    
    # Check fields
    assert response.conversation_id == "test-conversation"
    assert response.memory_content == "Memory content"
    assert response.exists is True
    
    # Create a valid response - memory does not exist
    response_not_exists = MemoryRetrievalResponse(
        conversation_id="test-conversation",
        exists=False
    )
    
    # Check fields
    assert response_not_exists.conversation_id == "test-conversation"
    assert response_not_exists.memory_content is None
    assert response_not_exists.exists is False
    
    # Test validation failure - missing required fields
    with pytest.raises(ValidationError):
        MemoryRetrievalResponse(conversation_id="test-conversation")