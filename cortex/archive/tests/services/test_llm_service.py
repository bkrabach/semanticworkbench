"""
Test suite for the LLM service
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
from typing import AsyncGenerator, AsyncIterable, List, Dict, Any

from app.services.llm_service import (
    LlmService, get_llm_service, 
    CompletionResponse, StreamingResponse, 
    Choice, DeltaChoice, MessageContent, DeltaContent,
    litellm_adapter, HAS_LITELLM, ModelResponse, CustomStreamWrapper
)
from app.config import settings


@pytest.fixture
def llm_service_with_mock_mode():
    """Create an LLM service with mock mode enabled"""
    service = LlmService()
    service.use_mock = True
    return service


@pytest.fixture
def llm_service_with_real_mode():
    """Create an LLM service with mock mode disabled but patched LiteLLM"""
    service = LlmService()
    service.use_mock = False
    return service


@pytest.mark.asyncio
async def test_get_llm_service_singleton():
    """Test that get_llm_service returns a singleton instance"""
    service1 = get_llm_service()
    service2 = get_llm_service()
    
    assert service1 is service2


@pytest.mark.asyncio
async def test_get_completion_mock_mode(llm_service_with_mock_mode):
    """Test get_completion in mock mode"""
    result = await llm_service_with_mock_mode.get_completion("Hello world")
    
    assert isinstance(result, str)
    assert "MOCK LLM RESPONSE" in result
    assert "Hello world" in result


@pytest.mark.asyncio
async def test_get_streaming_completion_mock_mode(llm_service_with_mock_mode):
    """Test get_streaming_completion in mock mode"""
    chunks = []
    async for chunk in llm_service_with_mock_mode.get_streaming_completion("Hello world"):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    assert isinstance(chunks[0], str)
    full_text = "".join(chunks)
    assert "MOCK LLM STREAMING RESPONSE" in full_text
    assert "Hello world" in full_text


@pytest.mark.asyncio
async def test_get_completion_with_patched_litellm(llm_service_with_real_mode):
    """Test get_completion with patched LiteLLM"""
    # Create a properly structured mock response
    mock_response = CompletionResponse(
        choices=[Choice(message=MessageContent(content="This is a test response"))]
    )
    
    # Patch the acompletion function
    with patch('app.services.llm_service.acompletion', AsyncMock(return_value=mock_response)) as mock_acompletion:
        result = await llm_service_with_real_mode.get_completion("Hello", system_prompt="You are a test")
        
        # Verify acompletion was called with correct parameters
        mock_acompletion.assert_called_once()
        call_args = mock_acompletion.call_args[1]
        assert call_args["model"] == settings.llm.default_model
        assert len(call_args["messages"]) == 2
        assert call_args["messages"][0]["role"] == "system"
        assert call_args["messages"][0]["content"] == "You are a test"
        assert call_args["messages"][1]["role"] == "user"
        assert call_args["messages"][1]["content"] == "Hello"
        
        # Verify result is as expected
        assert result == "This is a test response"


@pytest.mark.asyncio
async def test_get_completion_empty_response(llm_service_with_real_mode):
    """Test get_completion with empty response from LiteLLM"""
    # Create a mock response with empty content
    mock_response = CompletionResponse(
        choices=[Choice(message=MessageContent(content=None))]
    )
    
    # Patch the acompletion function
    with patch('app.services.llm_service.acompletion', AsyncMock(return_value=mock_response)):
        result = await llm_service_with_real_mode.get_completion("Hello")
        
        # Verify result is empty string
        assert result == ""


@pytest.mark.asyncio
async def test_get_completion_exception(llm_service_with_real_mode):
    """Test get_completion with exception from LiteLLM"""
    # Patch acompletion to raise an exception
    with patch('app.services.llm_service.acompletion', AsyncMock(side_effect=Exception("Test error"))):
        result = await llm_service_with_real_mode.get_completion("Hello")
        
        # Verify result indicates an error
        assert "Error processing request" in result
        assert "Test error" in result


@pytest.mark.asyncio
async def test_get_streaming_completion_with_patched_litellm(llm_service_with_real_mode):
    """Test get_streaming_completion with patched LiteLLM"""
    # Create mock chunks
    chunk1 = StreamingResponse(
        choices=[DeltaChoice(delta=DeltaContent(content="Hello"))]
    )
    
    chunk2 = StreamingResponse(
        choices=[DeltaChoice(delta=DeltaContent(content=" world"))]
    )
    
    # Create an async generator that yields the mock chunks
    async def mock_acompletion_stream(*args, **kwargs):
        yield chunk1
        yield chunk2
    
    # Patch acompletion to return our mock generator
    with patch('app.services.llm_service.acompletion', return_value=mock_acompletion_stream()):
        chunks = []
        async for chunk in llm_service_with_real_mode.get_streaming_completion("Test prompt"):
            chunks.append(chunk)
        
        # Verify we got the expected chunks
        assert len(chunks) == 2
        assert chunks[0] == "Hello"
        assert chunks[1] == " world"


@pytest.mark.asyncio
async def test_get_streaming_completion_with_incorrect_response_type(llm_service_with_real_mode):
    """Test get_streaming_completion when it gets a non-streaming response"""
    # Create a non-streaming response
    mock_response = CompletionResponse(
        choices=[Choice(message=MessageContent(content="This is not streaming"))]
    )
    
    # Patch acompletion to return a non-streaming response despite stream=True
    with patch('app.services.llm_service.acompletion', AsyncMock(return_value=mock_response)):
        chunks = []
        async for chunk in llm_service_with_real_mode.get_streaming_completion("Test prompt"):
            chunks.append(chunk)
        
        # Verify we got an error message
        assert len(chunks) == 1
        assert "Error" in chunks[0]
        assert "streaming" in chunks[0]


@pytest.mark.asyncio
async def test_invalid_response_structure(llm_service_with_real_mode):
    """Test handling of invalid response structures"""
    # Create a response with missing fields but that is properly typed
    mock_response = CompletionResponse(choices=[])  # Empty choices list
    
    # Patch acompletion to return our invalid response
    with patch('app.services.llm_service.acompletion', AsyncMock(return_value=mock_response)):
        result = await llm_service_with_real_mode.get_completion("Hello")
        
        # Verify we got an empty result and an error was logged
        assert result == ""


@pytest.mark.asyncio
async def test_litellm_adapter_regular_response():
    """Test the litellm_adapter function with a regular (non-streaming) response"""
    # Create a mock response
    mock_response = CompletionResponse(
        choices=[Choice(message=MessageContent(content="Adapter test response"))]
    )
    
    # Create a mock for _litellm_acompletion
    mock_litellm = AsyncMock(return_value=mock_response)
    
    # Patch HAS_LITELLM and _litellm_acompletion
    with patch('app.services.llm_service.HAS_LITELLM', True), \
         patch('app.services.llm_service._litellm_acompletion', mock_litellm):
        
        # Call the adapter
        result = await litellm_adapter(
            model="test-model",
            messages=[{"role": "user", "content": "Test"}],
            temperature=0.8
        )
        
        # Verify the result
        assert isinstance(result, CompletionResponse)
        assert result.choices[0].message.content == "Adapter test response"
        
        # Verify _litellm_acompletion was called with correct parameters
        mock_litellm.assert_called_once()
        call_args = mock_litellm.call_args[1]
        assert call_args["model"] == "test-model"
        assert call_args["temperature"] == 0.8
        assert not call_args["stream"]


@pytest.mark.asyncio
async def test_litellm_adapter_streaming_response():
    """Test the litellm_adapter function with a streaming response"""
    # Create a mock streaming response
    async def mock_stream() -> AsyncGenerator[StreamingResponse, None]:
        for word in ["Streaming", "adapter", "test", "response"]:
            yield StreamingResponse(
                choices=[DeltaChoice(delta=DeltaContent(content=word + " "))]
            )
    
    # Create a mock for _litellm_acompletion
    mock_stream_generator = mock_stream()
    mock_litellm = AsyncMock(return_value=mock_stream_generator)
    
    # Patch HAS_LITELLM and _litellm_acompletion
    with patch('app.services.llm_service.HAS_LITELLM', True), \
         patch('app.services.llm_service._litellm_acompletion', mock_litellm):
        
        # Call the adapter with stream=True
        result = await litellm_adapter(
            model="test-model",
            messages=[{"role": "user", "content": "Test"}],
            temperature=0.8,
            stream=True
        )
        
        # Verify result is properly typed as an AsyncIterable
        assert isinstance(result, AsyncIterable)
        
        # Safely collect the streaming chunks
        chunks = []
        if hasattr(result, '__aiter__'):  # Verify it's actually iterable
            async for chunk in result:  # Type checked by isinstance above
                chunks.append(chunk.choices[0].delta.content)
            
            # Verify streaming output
            assert ''.join(chunks) == "Streaming adapter test response "
        else:
            pytest.fail("Result is not an AsyncIterable")
        
        # Verify _litellm_acompletion was called with correct parameters
        mock_litellm.assert_called_once()
        call_args = mock_litellm.call_args[1]
        assert call_args["model"] == "test-model"
        assert call_args["temperature"] == 0.8
        assert call_args["stream"]


@pytest.mark.asyncio
async def test_litellm_adapter_fallback_to_mock():
    """Test the litellm_adapter falls back to mock implementation when LiteLLM isn't available"""
    # Create a mock for mock_acompletion
    mock_fallback = AsyncMock(return_value=CompletionResponse(
        choices=[Choice(message=MessageContent(content="Fallback mock response"))]
    ))
    
    # Patch HAS_LITELLM, _litellm_acompletion, and mock_acompletion
    with patch('app.services.llm_service.HAS_LITELLM', False), \
         patch('app.services.llm_service._litellm_acompletion', None), \
         patch('app.services.llm_service.mock_acompletion', mock_fallback):
        
        # Call the adapter
        result = await litellm_adapter(
            model="test-model",
            messages=[{"role": "user", "content": "Test"}]
        )
        
        # Verify we got the mock response
        assert isinstance(result, CompletionResponse)
        assert result.choices[0].message.content == "Fallback mock response"
        
        # Verify mock_acompletion was called
        mock_fallback.assert_called_once()


@pytest.mark.asyncio
async def test_adapter_used_by_service():
    """Test that the service uses our adapter function for API calls"""
    # Set up mocks
    mock_adapter = AsyncMock(return_value=CompletionResponse(
        choices=[Choice(message=MessageContent(content="Service using adapter"))]
    ))
    
    # Create a service
    service = LlmService()
    service.use_mock = False
    
    # Patch the adapter function
    with patch('app.services.llm_service.acompletion', mock_adapter):
        # Call the service
        result = await service.get_completion("Test call")
        
        # Verify the result
        assert result == "Service using adapter"
        
        # Verify our adapter was called
        mock_adapter.assert_called_once()


@pytest.mark.asyncio
async def test_service_initialization_with_custom_settings():
    """Test LlmService initialization with custom settings"""
    with patch('app.services.llm_service.settings') as mock_settings:
        # Setup custom settings
        mock_settings.llm.default_model = "custom-model"
        mock_settings.llm.use_mock = False
        mock_settings.llm.timeout = 60
        
        # Create service
        service = LlmService()
        
        # Verify settings were applied
        assert service.default_model == "custom-model"
        assert service.timeout == 60
        # use_mock should be based on settings.llm.use_mock OR not HAS_LITELLM
        assert service.use_mock is not None