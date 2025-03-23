"""
LLM Adapter module.

This module provides a structured interface to call different LLM providers
using Pydantic AI's Agent abstraction for type-safe interactions and
consistent response handling.
"""

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional, Protocol, cast

from ..models.domain.pydantic_ai import AssistantMessage, LLMInput, LLMOutput, SystemMessage, ToolCall, UserMessage
from ..models.domain.pydantic_ai import ChatMessage as PydanticChatMessage
from .exceptions import LLMException
from .mock_llm import mock_llm

# For type clarity in this module
ChatMessage = Dict[str, str]


# Define a protocol for model interfaces
class ModelProtocol(Protocol):
    async def generate(self, *args: Any, **kwargs: Any) -> Any: ...


class PydAIBaseModel:
    pass


class OpenAIModel(PydAIBaseModel):
    def __init__(self, model_name: str, api_key: Optional[str] = None) -> None:
        self.model_name = model_name
        self.api_key = api_key


class OpenAICompatibleModel(PydAIBaseModel):
    def __init__(self, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None, api_version: Optional[str] = None, azure_deployment: Optional[str] = None) -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.api_version = api_version
        self.azure_deployment = azure_deployment


class AnthropicModel(PydAIBaseModel):
    def __init__(self, model_name: str, api_key: Optional[str] = None) -> None:
        self.model_name = model_name
        self.api_key = api_key


logger = logging.getLogger(__name__)


class CortexLLMAgent:
    """Agent implementation using Pydantic AI for LLM interactions."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the Pydantic AI agent with configuration."""
        self.config = config
        self.model_name = config.get("model")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 1024)

        # Initialize the model
        self.model = self._get_model()

    def _get_model(self) -> PydAIBaseModel:
        """Create the appropriate Pydantic AI model based on configuration."""
        provider = self.config.get("provider", "openai").lower()

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_API_BASE")
            model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

            if base_url:
                return OpenAICompatibleModel(model_name, api_key=api_key, base_url=base_url)
            else:
                return OpenAIModel(model_name, api_key=api_key)

        elif provider == "azure_openai":
            api_key = os.getenv("AZURE_OPENAI_KEY")
            base_url = os.getenv("AZURE_OPENAI_BASE_URL")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

            # Azure OpenAI is handled as a compatible model with Azure-specific config
            return OpenAICompatibleModel(
                deployment, api_key=api_key, base_url=base_url, api_version=api_version, azure_deployment=deployment
            )

        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")

            return AnthropicModel(model_name, api_key=api_key)

        else:
            # Default to OpenAI for unsupported providers
            logger.warning(f"Unsupported provider: {provider}, defaulting to OpenAI")
            api_key = os.getenv("OPENAI_API_KEY")
            model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            return OpenAIModel(model_name, api_key=api_key)

    def model_config(self) -> Dict[str, Any]:
        """Define the model configuration for the agent."""
        return {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    async def run(self, input_data: LLMInput) -> LLMOutput:
        """
        Execute the agent with the given input.

        Args:
            input_data: The structured input for the LLM

        Returns:
            The structured output from the LLM

        Raises:
            LLMProviderError: If there's an error interacting with the LLM
        """
        try:
            # Build the messages array for the model
            messages: List[ChatMessage] = []

            # Add system message if provided
            if input_data.system_message:
                messages.append({"role": "system", "content": input_data.system_message.content})

            # Add history messages
            if input_data.history:
                for msg in input_data.history:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        messages.append({"role": msg["role"], "content": msg["content"]})

            # Add the current user message
            messages.append({"role": "user", "content": input_data.user_message.content})

            # Set up tools if provided
            api_tools = None
            if input_data.tools:
                # Convert tools to OpenAI format for function calling
                api_tools = [{"type": "function", "function": tool} for tool in input_data.tools]

            # Get provider type from the model
            provider = self.config.get("provider", "openai").lower()

            # Make the actual API call based on provider
            if provider == "openai":
                # Import the necessary module
                from openai import AsyncOpenAI

                # Create OpenAI client
                client = AsyncOpenAI(api_key=getattr(self.model, "api_key", None))

                # Handle base_url attribute access with type ignore for Pylance
                if hasattr(self.model, "base_url") and getattr(self.model, "base_url", None):  # type: ignore
                    client.base_url = getattr(self.model, "base_url")  # type: ignore

                # Make API call - type ignore for OpenAI API messages format
                response = await client.chat.completions.create(
                    model=getattr(self.model, "model_name", "gpt-3.5-turbo"),
                    messages=messages,  # type: ignore
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    tools=None if not api_tools else api_tools,  # type: ignore
                )

                # Check for tool calls
                if response.choices[0].message.tool_calls:
                    # Extract tool calls
                    api_tool_calls = response.choices[0].message.tool_calls
                    tool_calls = []

                    for tc in api_tool_calls:
                        try:
                            args = json.loads(tc.function.arguments)
                        except Exception:
                            args = {}

                        tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

                    return LLMOutput(response=AssistantMessage(content=""), tool_calls=tool_calls)
                else:
                    # Return content response
                    content = response.choices[0].message.content or ""
                    return LLMOutput(response=AssistantMessage(content=content), tool_calls=None)

            elif provider == "azure_openai":
                # Import the necessary module
                from openai import AsyncAzureOpenAI

                # Create Azure OpenAI client
                client = AsyncAzureOpenAI(
                    api_key=getattr(self.model, "api_key", None),
                    api_version=getattr(self.model, "api_version", "2023-05-15"),
                    azure_endpoint=getattr(self.model, "base_url", ""),
                )

                # Get deployment name
                deployment = getattr(self.model, "azure_deployment", "gpt-35-turbo")

                # Make API call - type ignore for OpenAI API messages format
                response = await client.chat.completions.create(
                    model=deployment,
                    messages=messages,  # type: ignore
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    tools=None if not api_tools else api_tools,  # type: ignore
                )

                # Check for tool calls
                if response.choices[0].message.tool_calls:
                    # Extract tool calls
                    api_tool_calls = response.choices[0].message.tool_calls
                    tool_calls = []

                    for tc in api_tool_calls:
                        try:
                            args = json.loads(tc.function.arguments)
                        except Exception:
                            args = {}

                        tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

                    return LLMOutput(response=AssistantMessage(content=""), tool_calls=tool_calls)
                else:
                    # Return content response
                    content = response.choices[0].message.content or ""
                    return LLMOutput(response=AssistantMessage(content=content), tool_calls=None)

            elif provider == "anthropic":
                # Import the necessary module
                from anthropic import AsyncAnthropic

                # Create Anthropic client
                anthropic_client = AsyncAnthropic(api_key=getattr(self.model, "api_key", None))

                # Anthropic uses a different format for messages
                # Convert our messages to Anthropic format
                system_prompt = None

                # Using Any type for API compatibility
                anthropic_messages: List[Dict[str, Any]] = []

                # Convert from our messages to Anthropic format
                # Type ignore for mypy since we know the structure is compatible
                for msg in messages:  # type: ignore
                    if msg["role"] == "system":
                        system_prompt = msg["content"]
                    elif msg["role"] == "user":
                        anthropic_messages.append({"role": "user", "content": msg["content"]})  # type: ignore
                    elif msg["role"] == "assistant":
                        anthropic_messages.append({"role": "assistant", "content": msg["content"]})  # type: ignore

                # Make API call - type ignore for Anthropic API message format
                response = await anthropic_client.messages.create(
                    model=getattr(self.model, "model_name", "claude-3-opus-20240229"),
                    messages=anthropic_messages,  # type: ignore
                    system=system_prompt,  # type: ignore
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                # Process the response content
                content = ""
                if hasattr(response, "content") and response.content:
                    for block in response.content:
                        # Generic access to text attribute with type ignore for Pylance
                        # This handles different content block types from Anthropic API
                        if hasattr(block, "text"):
                            text = getattr(block, "text", "")  # type: ignore
                            if text:
                                content += text

                # Claude doesn't have native tool calls in the same way
                # Just return the content
                return LLMOutput(response=AssistantMessage(content=content), tool_calls=None)

            else:
                # Unknown provider or not implemented yet
                # Fall back to mock for unsupported providers
                logger.warning(f"Provider {provider} not fully implemented, using mock")

                # Call mock_llm as fallback
                mock_result = await mock_llm.generate_mock_response(messages)

                if "tool" in mock_result:
                    tool_calls = [
                        ToolCall(id=str(uuid.uuid4()), name=mock_result["tool"], arguments=mock_result["input"])
                    ]
                    content = ""
                else:
                    tool_calls = None
                    content = mock_result.get("content", "I'm not sure how to respond to that.")

                return LLMOutput(response=AssistantMessage(content=content), tool_calls=tool_calls)
        except Exception as e:
            raise LLMException(f"Error from LLM provider: {str(e)}")


class LLMAdapter:
    """Adapter for interacting with LLMs through the Pydantic AI framework."""

    def __init__(self) -> None:
        """Initialize the LLM adapter based on environment variables."""
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

        # Common parameters
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1024"))

        # Set up configuration for the agent
        self.config = {
            "provider": self.provider,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # Provider-specific configuration
        if self.provider == "openai":
            self.config["model"] = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        elif self.provider == "azure_openai":
            self.config["model"] = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        elif self.provider == "anthropic":
            self.config["model"] = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")

        # Initialize the Pydantic AI agent if not using mock
        if not self.use_mock:
            try:
                self.agent = CortexLLMAgent(self.config)
                logger.info(f"LLM Adapter initialized with provider: {self.provider}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM provider: {str(e)}. Falling back to mock LLM.")
                self.use_mock = True

        if self.use_mock:
            logger.info("Using Mock LLM for responses")

    async def generate(self, messages: List[ChatMessage]) -> Optional[Dict[str, Any]]:
        """
        Call the configured LLM provider with the given conversation messages.

        Args:
            messages: List of message dictionaries with "role" and "content" keys

        Returns:
            Dict with either {"content": "..."} for a final answer,
            or {"tool": "...", "input": {...}} for a tool request.
            Returns None if the call fails.
        """
        # Check if we should use the mock LLM (only for development/testing)
        if self.use_mock:
            logger.info("Using mock LLM for response generation")
            # Check last 3 messages to see if we've already made a tool call
            recent_tool_call = False
            for i in range(min(3, len(messages))):
                idx = len(messages) - 1 - i
                if idx >= 0 and "Tool '" in messages[idx].get("content", ""):
                    recent_tool_call = True
                    break

            # Don't use tool if we've already made a recent tool call to avoid loops
            return await mock_llm.generate_mock_response(messages, with_tool=not recent_tool_call)

        try:
            # Extract system message if present
            system_message = None
            chat_history: List[ChatMessage] = []
            user_message = None

            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                if role == "system":
                    system_message = SystemMessage(content=content)
                elif role == "user":
                    # Keep track of the last user message
                    user_message = UserMessage(content=content)
                else:
                    # Add to history (Note: using our local ChatMessage type)
                    chat_history.append({"role": role, "content": content})

            # If no user message was found, use the last message
            if not user_message and messages:
                last_msg = messages[-1]
                user_message = UserMessage(content=last_msg.get("content", ""))

            # Make sure we have a user message
            if not user_message:
                user_message = UserMessage(content="")

            # Create input for the agent
            # Cast history to the expected type for LLMInput
            input_data = LLMInput(
                user_message=user_message,
                system_message=system_message,
                history=cast(List[PydanticChatMessage], chat_history),
            )

            # Log that we're calling the real LLM
            provider = str(self.config.get("provider", "openai")).lower()
            model_name = self.config.get("model", "unknown")
            logger.info(f"Calling real LLM provider: {provider}, model: {model_name}")

            # Run the agent with actual implementation
            output = await self.agent.run(input_data)

            # Convert the output to the expected format
            if output.tool_calls:
                # Return the first tool call
                tool_call = output.tool_calls[0]
                logger.info(f"LLM requested tool: {tool_call.name}")
                return {"tool": tool_call.name, "input": tool_call.arguments}
            else:
                # Return the content
                logger.info("LLM returned content response")
                return {"content": output.response.content}

        except Exception as e:
            logger.error(f"LLM API call failed: {type(e).__name__} - {str(e)}")
            return None


# Create a global instance
llm_adapter = LLMAdapter()
