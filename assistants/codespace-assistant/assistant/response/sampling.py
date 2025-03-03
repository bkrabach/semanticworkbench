"""
Module for handling sampling requests and model selection.

This module provides functionality to create and manage sampling handlers
that can be used to process model requests with appropriate configurations.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from assistant_extensions.ai_clients.config import (
    AnthropicClientConfigModel,
    AzureOpenAIClientConfigModel,
    OpenAIClientConfigModel,
)
from assistant_extensions.mcp import MCPSession, MCPToolsConfigModel, OpenAISamplingHandler
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam, ChatCompletionToolParam, ParsedChatCompletion
from openai_client import AzureOpenAIServiceConfig, OpenAIRequestConfig, OpenAIServiceConfig

from .utils import get_completion, get_openai_tools_from_mcp_sessions

logger = logging.getLogger(__name__)


@dataclass
class ModelPreferences:
    """
    Configuration for model preferences, including default settings and
    request-specific overrides.
    """

    default_model: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt_tokens: int = 1000


@dataclass
class SamplingConfig:
    """
    Configuration for sampling operations, containing all necessary settings
    to create and manage sampling handlers.
    """

    client_configs: List[Union[AzureOpenAIClientConfigModel, OpenAIClientConfigModel, AnthropicClientConfigModel]] = (
        field(default_factory=list)
    )
    tools_config: Optional[MCPToolsConfigModel] = None
    default_model_preferences: Optional[ModelPreferences] = None
    request_config: Optional[OpenAIRequestConfig] = None
    service_config: Optional[Union[AzureOpenAIServiceConfig, OpenAIServiceConfig]] = None


class SamplingManager:
    """
    Manages sampling handlers and model selection for the assistant.
    This centralizes sampling configuration and setup to make it easier to
    extend with additional features like model selection.
    """

    def __init__(self, config: Optional[SamplingConfig] = None):
        self._sampling_handler: Optional[OpenAISamplingHandler] = None
        self._service_config: Optional[Union[AzureOpenAIServiceConfig, OpenAIServiceConfig]] = None
        self._request_config: Optional[OpenAIRequestConfig] = None
        self._config = config or SamplingConfig()

    @property
    def request_config(self) -> Optional[OpenAIRequestConfig]:
        """Get the current request configuration."""
        return self._request_config

    @property
    def service_config(self) -> Optional[Union[AzureOpenAIServiceConfig, OpenAIServiceConfig]]:
        """Get the current service configuration."""
        return self._service_config

    def create_sampling_handler(
        self,
        service_config: Union[AzureOpenAIServiceConfig, OpenAIServiceConfig],
        request_config: OpenAIRequestConfig,
    ) -> OpenAISamplingHandler:
        """
        Create and configure a sampling handler for handling requests from MCP servers.

        Args:
            service_config: The configuration for the OpenAI service
            request_config: The configuration for the OpenAI request

        Returns:
            Configured OpenAISamplingHandler instance
        """
        self._service_config = service_config
        self._request_config = request_config

        self._sampling_handler = OpenAISamplingHandler(
            service_config=service_config,
            request_config=request_config,
        )

        return self._sampling_handler

    def create_handler(self) -> OpenAISamplingHandler:
        """
        Create a sampling handler using the current configuration.

        Returns:
            Configured OpenAISamplingHandler instance
        """
        if not self._config.service_config or not self._config.request_config:
            raise ValueError("Service config and request config must be set in sampling config")

        return self.create_sampling_handler(
            service_config=self._config.service_config,
            request_config=self._config.request_config,
        )

    def get_model_preferences_for_request(self, request_type: Literal["reasoning", "generative"]) -> ModelPreferences:
        """
        Get model preferences tailored for a specific request type.

        Args:
            request_type: The type of request ("reasoning" or "generative")

        Returns:
            Model preferences for the request type
        """
        # Create basic preferences with increased tokens for reasoning
        preferences = ModelPreferences()

        if request_type == "reasoning":
            preferences.max_tokens = 4096
            preferences.system_prompt_tokens = 2000

        return preferences

    def update_model(self, model_name: str) -> None:
        """
        Update the model used by the sampling handler.

        Args:
            model_name: The name of the model to use
        """
        if not self._request_config or not self._sampling_handler:
            raise ValueError("Sampling handler not initialized")

        # Create a new request config with the updated model
        updated_config = OpenAIRequestConfig(
            model=model_name,
            response_tokens=self._request_config.response_tokens,
            max_tokens=self._request_config.max_tokens,
            is_reasoning_model=self._request_config.is_reasoning_model,
            reasoning_effort=self._request_config.reasoning_effort,
            enable_markdown_in_reasoning_response=self._request_config.enable_markdown_in_reasoning_response,
            reasoning_token_allocation=self._request_config.reasoning_token_allocation,
        )

        # Update the request config in the sampling handler
        self._sampling_handler.request_config = updated_config
        self._request_config = updated_config

        logger.info(f"Updated sampling handler model to: {model_name}")

    def get_current_model(self) -> Optional[str]:
        """
        Get the name of the model currently being used.

        Returns:
            The model name, or None if no sampling handler is configured
        """
        if not self._request_config:
            return None

        return self._request_config.model

    def update_mcp_tools(self, tools: List[ChatCompletionToolParam]) -> None:
        """
        Update the MCP tools available to the sampling handler.

        Args:
            tools: The list of tools to make available
        """
        if not self._sampling_handler:
            raise ValueError("Sampling handler not initialized")

        self._sampling_handler.assistant_mcp_tools = tools

    def get_tools_from_sessions(
        self, mcp_sessions: List[MCPSession], tools_config: MCPToolsConfigModel
    ) -> List[ChatCompletionToolParam]:
        """
        Get OpenAI-compatible tools from MCP sessions.

        Args:
            mcp_sessions: List of active MCP sessions
            tools_config: Tools configuration

        Returns:
            List of tools in OpenAI format
        """
        tools = get_openai_tools_from_mcp_sessions(mcp_sessions, tools_config)
        # Ensure we always return a list, never None
        return tools if tools is not None else []

    async def get_completion(
        self,
        client: Any,
        request_config: OpenAIRequestConfig,
        messages: List[ChatCompletionMessageParam],
        tools: List[ChatCompletionToolParam],
    ) -> Union[ParsedChatCompletion, ChatCompletion]:
        """
        Get a completion from the OpenAI API.

        Args:
            client: The OpenAI client
            request_config: Request configuration
            messages: Chat message parameters
            tools: Available tools

        Returns:
            The completion response
        """
        return await get_completion(client, request_config, messages, tools)

    def configure_for_request_type(
        self,
        request_type: Literal["reasoning", "generative"],
        service_configs: Dict[
            Literal["reasoning", "generative"],
            Tuple[OpenAIRequestConfig, Union[AzureOpenAIServiceConfig, OpenAIServiceConfig]],
        ],
    ) -> OpenAISamplingHandler:
        """
        Configure the sampling handler for a specific request type.

        Args:
            request_type: The type of request ("reasoning" or "generative")
            service_configs: Dictionary mapping request types to configurations

        Returns:
            The configured sampling handler
        """
        request_config, service_config = service_configs[request_type]

        # If we already have a sampling handler but need to change configs
        if self._sampling_handler and (
            self._service_config != service_config
            or (self._request_config and self._request_config.model != request_config.model)
        ):
            # Create a new one with updated configs
            logger.info(f"Switching sampling handler to {request_type} mode with model {request_config.model}")
            return self.create_sampling_handler(service_config, request_config)

        # Create new handler if none exists
        if not self._sampling_handler:
            return self.create_sampling_handler(service_config, request_config)

        # Return existing handler if configs match
        return self._sampling_handler
