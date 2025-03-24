"""
LLM Adapter module.

This module provides a structured interface to call different LLM providers
using a consistent abstraction layer for type-safe interactions and
standardized response handling.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, cast

from ..models.domain.pydantic_ai import ChatMessage as PydanticChatMessage
from ..models.domain.pydantic_ai import LLMInput, SystemMessage, UserMessage
from .exceptions import LLMException

# For type clarity in this module
ChatMessage = Dict[str, str]

logger = logging.getLogger(__name__)


class LLMAdapter:
    """Adapter for interacting with LLMs through a consistent abstraction layer."""

    def __init__(self) -> None:
        """
        Initialize the LLM adapter based on environment variables.

        Raises:
            ValueError: If required environment variables for the configured provider are missing
        """
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

        # Common parameters
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1024"))

        # Validate provider support
        supported_providers = ["openai", "azure_openai", "anthropic"]
        if not self.use_mock and self.provider not in supported_providers:
            logger.warning(f"Unsupported provider: {self.provider}, defaulting to openai")
            self.provider = "openai"

        # Set up model name based on provider
        self.model_name = self._get_model_name()

        # Set up configuration
        self.config = {
            "provider": self.provider,
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # Initialize the agent if not using mock
        if not self.use_mock:
            try:
                # Validate that required provider configuration is available
                self._validate_provider_config()
                logger.info(f"LLM Adapter initialized with provider: {self.provider}, model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM provider: {str(e)}. Falling back to mock LLM.")
                self.use_mock = True

        if self.use_mock:
            logger.info("Using Mock LLM for responses")

    def _get_model_name(self) -> str:
        """
        Get the appropriate model name based on provider.

        Returns:
            str: The model name for the configured provider
        """
        if self.provider == "openai":
            return os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        elif self.provider == "azure_openai":
            return os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
        elif self.provider == "anthropic":
            return os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        else:
            # Should not reach here due to provider validation
            return "gpt-3.5-turbo"

    def _validate_provider_config(self) -> None:
        """
        Validate that required provider configuration is available.

        Raises:
            ValueError: If required environment variables are missing
        """
        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
        elif self.provider == "azure_openai":
            api_key = os.getenv("AZURE_OPENAI_KEY")
            base_url = os.getenv("AZURE_OPENAI_BASE_URL")
            if not api_key or not base_url:
                raise ValueError("AZURE_OPENAI_KEY and AZURE_OPENAI_BASE_URL environment variables are required")
        elif self.provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is required")

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
        # In development mode, use a simple fixed response if mock is enabled
        if self.use_mock:
            logger.info("Development mode: Using simple mock LLM response")
            # Create a simple response for development without test dependencies
            return {"content": "This is a development mode response. In production, configure LLM_PROVIDER."}

        try:
            # Prepare input data for LLM from messages
            input_data = self._prepare_input(messages)

            # Call the appropriate provider based on configuration
            if self.provider == "openai":
                return await self._generate_openai(input_data)
            elif self.provider == "azure_openai":
                return await self._generate_azure_openai(input_data)
            elif self.provider == "anthropic":
                return await self._generate_anthropic(input_data)
            else:
                # This should not happen due to validation in __init__
                logger.error(f"Unsupported provider: {self.provider}")
                return None

        except Exception as e:
            logger.error(f"LLM API call failed: {type(e).__name__} - {str(e)}")
            return None

    def _prepare_input(self, messages: List[ChatMessage]) -> LLMInput:
        """
        Prepare input for the LLM in the appropriate format.

        Args:
            messages: List of message dictionaries

        Returns:
            LLMInput: Structured input for the LLM
        """
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
                # Add to history
                chat_history.append({"role": role, "content": content})

        # If no user message was found, use the last message
        if not user_message and messages:
            last_msg = messages[-1]
            user_message = UserMessage(content=last_msg.get("content", ""))

        # Make sure we have a user message
        if not user_message:
            user_message = UserMessage(content="")

        # Create and return input
        return LLMInput(
            user_message=user_message,
            system_message=system_message,
            history=cast(List[PydanticChatMessage], chat_history),
        )

    async def _generate_openai(self, input_data: LLMInput) -> Dict[str, Any]:
        """
        Generate a response using OpenAI API.

        Args:
            input_data: Structured input for the LLM

        Returns:
            Dict with response data

        Raises:
            LLMException: If there's an error communicating with OpenAI
        """
        try:
            # Import the necessary module
            from openai import AsyncOpenAI

            # Build messages array
            messages = []

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

            # Create OpenAI client
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Handle base_url if provided
            base_url = os.getenv("OPENAI_API_BASE")
            if base_url:
                # Create a new client with the base_url
                client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=base_url)

            # Make API call
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,  # type: ignore
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                tools=None if not api_tools else api_tools,  # type: ignore
            )

            # Check for tool calls
            if response.choices[0].message.tool_calls:
                # Extract tool calls
                api_tool_calls = response.choices[0].message.tool_calls

                # Get the first tool call
                tc = api_tool_calls[0]

                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}

                logger.info(f"OpenAI requested tool: {tc.function.name}")
                return {"tool": tc.function.name, "input": args}
            else:
                # Return content response
                content = response.choices[0].message.content or ""
                logger.info("OpenAI returned content response")
                return {"content": content}

        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise LLMException(f"Error from OpenAI: {str(e)}")

    async def _generate_azure_openai(self, input_data: LLMInput) -> Dict[str, Any]:
        """
        Generate a response using Azure OpenAI API.

        Args:
            input_data: Structured input for the LLM

        Returns:
            Dict with response data

        Raises:
            LLMException: If there's an error communicating with Azure OpenAI
        """
        try:
            # Import the necessary module
            from openai import AsyncAzureOpenAI

            # Build messages array
            messages = []

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

            # Create Azure OpenAI client
            client = AsyncAzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
                azure_endpoint=os.getenv("AZURE_OPENAI_BASE_URL", ""),
            )

            # Make API call
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,  # type: ignore
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                tools=None if not api_tools else api_tools,  # type: ignore
            )

            # Check for tool calls
            if response.choices[0].message.tool_calls:
                # Extract tool calls
                api_tool_calls = response.choices[0].message.tool_calls

                # Get the first tool call
                tc = api_tool_calls[0]

                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}

                logger.info(f"Azure OpenAI requested tool: {tc.function.name}")
                return {"tool": tc.function.name, "input": args}
            else:
                # Return content response
                content = response.choices[0].message.content or ""
                logger.info("Azure OpenAI returned content response")
                return {"content": content}

        except Exception as e:
            logger.error(f"Azure OpenAI API call failed: {str(e)}")
            raise LLMException(f"Error from Azure OpenAI: {str(e)}")

    async def _generate_anthropic(self, input_data: LLMInput) -> Dict[str, Any]:
        """
        Generate a response using Anthropic API.

        Args:
            input_data: Structured input for the LLM

        Returns:
            Dict with response data

        Raises:
            LLMException: If there's an error communicating with Anthropic
        """
        try:
            # Import the necessary module
            from anthropic import AsyncAnthropic

            # Create Anthropic client
            anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

            # Extract system prompt if provided
            system_prompt = None
            if input_data.system_message:
                system_prompt = input_data.system_message.content

            # Anthropic uses a different format for messages
            anthropic_messages: List[Dict[str, Any]] = []

            # Add history messages
            if input_data.history:
                for msg in input_data.history:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        role = msg["role"]
                        # Anthropic only supports user and assistant roles
                        if role in ["user", "assistant"]:
                            anthropic_messages.append({"role": role, "content": msg["content"]})

            # Add the current user message
            anthropic_messages.append({"role": "user", "content": input_data.user_message.content})

            # Make API call
            response = await anthropic_client.messages.create(
                model=self.model_name,
                messages=anthropic_messages,  # type: ignore
                system=system_prompt,  # type: ignore
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Process the response content
            content = ""
            if hasattr(response, "content") and response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        text = getattr(block, "text", "")  # type: ignore
                        if text:
                            content += text

            # Check for tool calls in the content
            # Claude models may format tool calls in the content with JSON
            if content and "```json" in content and ("tool" in content or "function" in content):
                # Attempt to extract JSON
                try:
                    # Find JSON blocks
                    start_idx = content.find("```json")
                    if start_idx != -1:
                        json_str = content[start_idx + 7 :]
                        end_idx = json_str.find("```")
                        if end_idx != -1:
                            json_str = json_str[:end_idx].strip()
                            tool_data = json.loads(json_str)

                            # Check if it's a tool call
                            if "tool" in tool_data or "function" in tool_data:
                                tool_name = tool_data.get("tool", tool_data.get("function", {}).get("name"))
                                tool_args = tool_data.get("input", tool_data.get("arguments", {}))

                                if isinstance(tool_args, str):
                                    # Try to parse JSON string arguments
                                    try:
                                        tool_args = json.loads(tool_args)
                                    except json.JSONDecodeError:
                                        # Keep tool_args as a string if it's not valid JSON
                                        logger.debug(f"Failed to parse tool arguments as JSON: {tool_args}")
                                        pass

                                if tool_name:
                                    logger.info(f"Anthropic requested tool: {tool_name}")
                                    return {"tool": tool_name, "input": tool_args}
                except Exception as json_err:
                    logger.debug(f"Failed to parse JSON tool call from Anthropic: {str(json_err)}")

            # Just return the content if no tool call detected
            logger.info("Anthropic returned content response")
            return {"content": content}

        except Exception as e:
            logger.error(f"Anthropic API call failed: {str(e)}")
            raise LLMException(f"Error from Anthropic: {str(e)}")


# Create a global instance
llm_adapter = LLMAdapter()
