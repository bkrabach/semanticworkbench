"""
LLM Service for interacting with language models through LiteLLM.

This service provides methods for calling language models using LiteLLM as an abstraction
layer over various model providers like OpenAI, Anthropic, etc.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, AsyncIterable, Dict, List, Optional, Protocol, Union
from typing import TypeVar, Generic, cast

from app.config import settings

try:
    from litellm import acompletion as _litellm_acompletion
    HAS_LITELLM = True
except ImportError:
    _litellm_acompletion = None  # Define as None if import fails
    HAS_LITELLM = False
    logging.warning("LiteLLM not installed, LLM service will operate in mock mode")

# Define type aliases to avoid direct imports
ChatCompletionAudioParam = Dict[str, Any]
ChatCompletionModality = Any
ChatCompletionPredictionContentParam = Any
AnthropicThinkingParam = Any
BaseModel = Any


# Define types for LiteLLM responses to help with type checking
@dataclass
class MessageContent:
    content: Optional[str] = None


@dataclass
class DeltaContent:
    content: Optional[str] = None


@dataclass
class Choice:
    message: MessageContent
    finish_reason: Optional[str] = None
    index: int = 0


@dataclass
class DeltaChoice:
    delta: DeltaContent
    finish_reason: Optional[str] = None
    index: int = 0


@dataclass
class CompletionResponse:
    choices: List[Choice]
    id: Optional[str] = None
    model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


@dataclass
class StreamingResponse:
    choices: List[DeltaChoice]
    id: Optional[str] = None
    model: Optional[str] = None


class AsyncCompletionCallable(Protocol):
    async def __call__(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Union[CompletionResponse, AsyncIterable[StreamingResponse]]: ...


# Define fallback functions if LiteLLM isn't available
async def mock_acompletion(*args: Any, **kwargs: Any) -> Union[CompletionResponse, AsyncIterable[StreamingResponse]]:
    """Mock implementation of acompletion when LiteLLM is not available"""
    if kwargs.get("stream", False):

        async def mock_stream() -> AsyncGenerator[StreamingResponse, None]:
            yield StreamingResponse(choices=[DeltaChoice(delta=DeltaContent(content="[MOCK]"))])

        return mock_stream()
    else:
        return CompletionResponse(choices=[Choice(message=MessageContent(content="[MOCK] LiteLLM not available"))])


# Define an output type for ModelResponse to handle litellm responses
T = TypeVar("T")


class ModelResponse(Generic[T]):
    """Wrapper for model response types"""

    pass


class CustomStreamWrapper:
    """Wrapper for streaming response types"""

    pass


# Create a wrapper function for litellm that matches our Protocol
async def litellm_adapter(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    timeout: Optional[int] = None,
    stream: bool = False,
    **kwargs: Any
) -> Union[CompletionResponse, AsyncIterable[StreamingResponse]]:
    """Adapter for litellm acompletion that conforms to our AsyncCompletionCallable protocol"""
    if HAS_LITELLM and _litellm_acompletion:
        # Forward the call to litellm with the same parameters
        # Use type cast to ensure mypy understands the return type
        result = await _litellm_acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            stream=stream,
            **kwargs
        )
        
        # Type checking and conversion to ensure return type matches expected signature
        if stream:
            # For streaming responses, ensure it's an AsyncIterable of StreamingResponses
            return cast(AsyncIterable[StreamingResponse], result)
        else:
            # For regular responses, ensure it's a CompletionResponse
            return cast(CompletionResponse, result)
    else:
        # Fall back to mock implementation
        return await mock_acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            stream=stream,
            **kwargs
        )

# Define completion callable interface that matches our expected function signature
# Use our adapter function that implements the AsyncCompletionCallable protocol
acompletion: AsyncCompletionCallable = litellm_adapter


class LlmService:
    """
    Service for interacting with language models through LiteLLM.

    This service handles communication with various LLM providers using
    LiteLLM as an abstraction layer.
    """

    def __init__(self):
        """Initialize the LLM service."""
        self.logger = logging.getLogger(__name__)
        self.default_model = settings.llm.default_model
        self.use_mock = settings.llm.use_mock or not HAS_LITELLM
        self.timeout = settings.llm.timeout

        if self.use_mock:
            self.logger.warning("LLM service running in mock mode - no actual API calls will be made")

    async def get_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Get a completion from an LLM for the given prompt.

        Args:
            prompt: The user prompt to send to the LLM
            model: The model to use (defaults to config setting)
            temperature: Temperature for generation (0.0-2.0)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to set context

        Returns:
            The text response from the model
        """
        if self.use_mock:
            # In mock mode, just echo the prompt with info about the mock
            await asyncio.sleep(1)  # Simulate API delay
            return f"[MOCK LLM RESPONSE] Echo: {prompt}"

        try:
            # Prepare messages in the format LiteLLM expects
            messages: List[Dict[str, str]] = []

            # Add system message if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add user message
            messages.append({"role": "user", "content": prompt})

            # Use the model specified or fall back to default
            model_name = model or self.default_model

            # Call LiteLLM async completion
            response = await acompletion(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
            )

            # Since we're not streaming, we expect a CompletionResponse
            if isinstance(response, AsyncIterable):
                self.logger.error("Received streaming response when not requested")
                return "Error: Received unexpected streaming response"

            # Extract and return the content from the response using safe attribute access
            if (
                hasattr(response, "choices")
                and response.choices
                and len(response.choices) > 0
                and hasattr(response.choices[0], "message")
                and hasattr(response.choices[0].message, "content")
            ):
                return response.choices[0].message.content or ""
            else:
                self.logger.error(f"Invalid response structure from LLM: {response}")
                return ""

        except Exception as e:
            self.logger.error(f"Error calling LLM: {str(e)}")
            return f"Error processing request: {str(e)}"

    async def get_streaming_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Get a streaming completion from an LLM for the given prompt.

        Args:
            prompt: The user prompt to send to the LLM
            model: The model to use (defaults to config setting)
            temperature: Temperature for generation (0.0-2.0)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to set context

        Yields:
            Text chunks as they are generated by the model
        """
        if self.use_mock:
            # In mock mode, simulate streaming with artificial delays
            words = f"[MOCK LLM STREAMING RESPONSE] Echo: {prompt}".split()
            for word in words:
                await asyncio.sleep(0.1)
                yield word + " "
            return

        try:
            # Prepare messages in the format LiteLLM expects
            messages: List[Dict[str, str]] = []

            # Add system message if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add user message
            messages.append({"role": "user", "content": prompt})

            # Use the model specified or fall back to default
            model_name = model or self.default_model

            # Call LiteLLM async completion with streaming
            response_stream = await acompletion(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
                stream=True,
            )

            # Safely handle the stream response
            if not isinstance(response_stream, AsyncIterable):
                self.logger.error("Expected streaming response but got a regular response")
                yield "Error: Expected streaming response but received regular response"
                return

            # Yield content chunks as they come in, with safe attribute access
            async for chunk in response_stream:
                if (
                    hasattr(chunk, "choices")
                    and chunk.choices
                    and len(chunk.choices) > 0
                    and hasattr(chunk.choices[0], "delta")
                    and hasattr(chunk.choices[0].delta, "content")
                    and chunk.choices[0].delta.content is not None
                ):
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self.logger.error(f"Error in streaming LLM call: {str(e)}")
            yield f"Error processing request: {str(e)}"


# Singleton instance
_llm_service: Optional[LlmService] = None


def get_llm_service() -> LlmService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LlmService()
    return _llm_service
