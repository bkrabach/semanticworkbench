import logging
from typing import Any, Callable, List, Optional, Union

import deepmerge
from mcp import ClientSession, CreateMessageResult, SamplingMessage
from mcp.shared.context import RequestContext
from mcp.types import CreateMessageRequestParams, ErrorData, ImageContent, TextContent
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionContentPartImageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)
from openai_client import (
    AzureOpenAIServiceConfig,
    OpenAIRequestConfig,
    OpenAIServiceConfig,
    ServiceConfig,
    create_client,
)

from ..ai_clients.config import AIClientConfig
from ._model import MCPSamplingMessageHandler
from ._model_preferences import ModelPreferences
from ._sampling_handler import SamplingHandler

logger = logging.getLogger(__name__)

# FIXME: add metadata/debug data to entire flow
# FIXME: investigate blocking issue that causes the sampling request to wait for something else to finish
# For now it does work, but it takes much longer than it should and shows the assistant as offline while
# it does - merging before investigating to unblock others who are waiting on the first version of this.
# It works ok in office server but not giphy, so it is likely a server issue.

OpenAIMessageProcessor = Callable[
    [List[SamplingMessage]],
    List[ChatCompletionMessageParam],
]


class OpenAISamplingHandler(SamplingHandler):
    @property
    def message_handler(self) -> MCPSamplingMessageHandler:
        return self._message_handler

    def __init__(
        self,
        service_config: ServiceConfig | None = None,
        request_config: OpenAIRequestConfig | None = None,
        client_configs: list[AIClientConfig] | None = None,
        assistant_mcp_tools: list[ChatCompletionToolParam] | None = None,
        message_processor: OpenAIMessageProcessor | None = None,
        handler: MCPSamplingMessageHandler | None = None,
        model_preferences: Optional[ModelPreferences] = None,
    ) -> None:
        # Store client configurations for model selection
        self.client_configs = client_configs or []

        # Store model preferences for model selection
        self.model_preferences = model_preferences

        # Initialize service_config and request_config for backward compatibility
        # If client_configs is provided, use the first config as default
        if client_configs and len(client_configs) > 0:
            self.service_config = service_config or client_configs[0].service_config
            self.request_config = request_config or client_configs[0].request_config
        else:
            self.service_config = service_config
            self.request_config = request_config

        self.assistant_mcp_tools = assistant_mcp_tools

        # set a default message processor that converts sampling messages to
        # chat completion messages and performs any necessary transformations
        # such as injecting content as replacements for placeholders, etc.
        self.message_processor: OpenAIMessageProcessor = (
            message_processor or self._default_message_processor
        )

        # set a default handler so that it can be registered during client
        # session connection, prior to having access to the actual handler
        # allowing the handler to be set after the client session is created
        # and more context is available
        self._message_handler: MCPSamplingMessageHandler = (
            handler or self._default_message_handler
        )

    def _is_openai_config(self, config: AIClientConfig) -> bool:
        """Check if the config is an OpenAI-compatible config."""
        return hasattr(config, "ai_service_type") and config.ai_service_type in [
            "azure_openai",
            "openai",
        ]

    def _select_model(
        self, external_preferences: Optional[ModelPreferences] = None
    ) -> Optional[AIClientConfig]:
        """
        Select the appropriate model configuration based on preferences.

        Args:
            external_preferences: Model preferences to guide selection (overrides self.model_preferences)

        Returns:
            The selected AI client configuration or None if no configurations available
        """
        # Use external_preferences if provided, otherwise use self.model_preferences
        preferences = external_preferences or self.model_preferences

        # If no preferences or no configs, use the first config
        if not preferences or not self.client_configs:
            return self.client_configs[0] if self.client_configs else None

        # Try to match by hints first
        if preferences.hints:
            for hint in preferences.hints:
                if hint.name:
                    for config in self.client_configs:
                        # Check for partial match in model name
                        if (
                            hasattr(config.request_config, "model")
                            and hint.name.lower() in config.request_config.model.lower()
                        ):
                            return config

        # Match by priorities - treat None as 0
        speed_priority = preferences.speedPriority or 0
        intelligence_priority = preferences.intelligencePriority or 0
        cost_priority = preferences.costPriority or 0

        # Filter for OpenAI configurations since they have is_reasoning_model attribute
        # We need to be very careful with types here to avoid Pylance errors
        openai_configs = []
        for config in self.client_configs:
            if (
                hasattr(config, "ai_service_type")
                and config.ai_service_type in ["azure_openai", "openai"]
                and hasattr(config.request_config, "is_reasoning_model")
            ):
                # This is a valid OpenAI config with is_reasoning_model attribute
                openai_configs.append(config)

        if speed_priority > intelligence_priority and openai_configs:
            # Speed is more important, find non-reasoning model
            for config in openai_configs:
                # We already verified these configs have is_reasoning_model attribute
                request_config = config.request_config
                if (
                    hasattr(request_config, "is_reasoning_model")
                    and not request_config.is_reasoning_model
                ):
                    return config

        elif intelligence_priority > speed_priority and openai_configs:
            # Intelligence is more important, find reasoning model
            for config in openai_configs:
                # We already verified these configs have is_reasoning_model attribute
                request_config = config.request_config
                if (
                    hasattr(request_config, "is_reasoning_model")
                    and request_config.is_reasoning_model
                ):
                    return config

        # If cost is the only priority or highest priority, we could add logic here
        # to select the most cost-effective model (e.g., smaller models)

        # Default to first config if no match
        return self.client_configs[0] if self.client_configs else None

    def _default_message_processor(
        self, messages: List[SamplingMessage]
    ) -> List[ChatCompletionMessageParam]:
        """
        Default template processor that passes messages through.
        """
        return [
            sampling_message_to_chat_completion_message(message) for message in messages
        ]

    async def _default_message_handler(
        self,
        context: RequestContext[ClientSession, Any],
        params: CreateMessageRequestParams,
    ) -> CreateMessageResult | ErrorData:
        logger.info(f"Sampling handler invoked with context: {context}")

        if not self.service_config or not self.request_config:
            raise ValueError(
                "Service config and request config must be set before handling messages."
            )

        # Verify we have OpenAI-compatible configs before proceeding
        # This avoids type errors when non-OpenAI configs are used
        is_openai_service = hasattr(self.service_config, "service_type") and getattr(
            self.service_config, "service_type"
        ) in ["openai", "azure_openai"]

        is_openai_request = isinstance(self.request_config, OpenAIRequestConfig)

        if not is_openai_service or not is_openai_request:
            # This is a non-OpenAI config (like Anthropic) which we don't yet fully support
            error_msg = (
                f"Unsupported configuration: service_type={getattr(self.service_config, 'service_type', 'unknown')}, "
                f"request_config type={type(self.request_config).__name__}. "
                "Only OpenAI and Azure OpenAI are fully supported."
            )
            logger.warning(error_msg)
            return ErrorData(
                code=500,
                message=error_msg,
            )

        try:
            # Cast to the correct type for Pylance
            from typing import cast

            # Now we know self.request_config is an OpenAIRequestConfig through our is_openai_request check
            request_config = cast(OpenAIRequestConfig, self.request_config)
            completion_args = await self._create_completion_request(
                request=params,
                request_config=request_config,  # Now properly typed for Pylance
                template_processor=self.message_processor,
            )
        except Exception as e:
            logger.exception(f"Error creating completion request: {e}")
            return ErrorData(
                code=500,
                message="Error creating completion request.",
                data=e,
            )

        completion: ChatCompletion | None = None

        # We already verified this is an OpenAI-compatible service config
        # No need to check again - we know it's safe to use with create_client

        # Get the concrete ServiceConfig type for create_client
        # We've already verified this is compatible, so we can force the type
        from typing import cast

        if (
            hasattr(self.service_config, "service_type")
            and self.service_config.service_type == "azure_openai"
        ):
            # It's an Azure OpenAI config
            service_config = cast(AzureOpenAIServiceConfig, self.service_config)
            async with create_client(service_config) as client:
                completion = await client.chat.completions.create(**completion_args)
        elif (
            hasattr(self.service_config, "service_type")
            and self.service_config.service_type == "openai"
        ):
            # It's an OpenAI config
            service_config = cast(OpenAIServiceConfig, self.service_config)
            async with create_client(service_config) as client:
                completion = await client.chat.completions.create(**completion_args)
        else:
            # This should never happen due to earlier checks, but just in case
            raise ValueError(
                f"Unsupported service config type: {type(self.service_config).__name__}"
            )

        if completion is None:
            return ErrorData(
                code=500,
                message="No completion returned from OpenAI.",
            )

        choice = completion.choices[0]
        if choice.message.content is None:
            return ErrorData(
                code=500,
                message="No content returned from completion choice.",
            )

        content = choice.message.content
        if content is None:
            content = "[no content]"

        return CreateMessageResult(
            role="assistant",
            content=TextContent(
                type="text",
                text=content,
            ),
            model=completion.model,
            stopReason=choice.finish_reason,
            _meta={
                "request": completion_args,
                "response": completion.model_dump(mode="json"),
            },
        )

    async def handle_message(
        self,
        context: RequestContext[ClientSession, Any],
        params: CreateMessageRequestParams,
    ) -> CreateMessageResult | ErrorData:
        return await self._message_handler(context, params)

    async def _create_completion_request(
        self,
        request: CreateMessageRequestParams,
        request_config: OpenAIRequestConfig,  # For backward compatibility
        template_processor: OpenAIMessageProcessor,
    ) -> dict:
        """
        Creates a completion request.

        Args:
            request: The parameters for the message request
            request_config: The fallback request configuration (used if no client_configs)
            template_processor: Function to process sampling messages into chat completion messages

        Returns:
            A dictionary with the completion request parameters
        """
        # Extract model preferences if they exist
        model_preferences = None
        if hasattr(request, "modelPreferences") and request.modelPreferences:
            try:
                model_preferences = ModelPreferences.model_validate(
                    request.modelPreferences
                )
                logger.info(f"Processing model preferences: {model_preferences}")
            except Exception as e:
                logger.warning(f"Failed to parse modelPreferences: {e}")

        # Select appropriate model configuration
        selected_config = None
        if self.client_configs:
            # If we have model_preferences from the request, those take priority
            if model_preferences:
                logger.info(
                    f"Using model preferences from request: {model_preferences}"
                )
                selected_config = self._select_model(model_preferences)
            # Otherwise check if we have model_preferences set on the handler
            elif self.model_preferences:
                logger.info(
                    f"Using model preferences from handler: {self.model_preferences}"
                )
                selected_config = self._select_model()
            else:
                # No preferences, use default selection logic
                selected_config = self._select_model()

            if selected_config:
                # Update instance variables for this request
                self.service_config = selected_config.service_config
                self.request_config = selected_config.request_config
                logger.info(
                    f"Selected model: {self.request_config.model if hasattr(self.request_config, 'model') else 'unknown'}"
                )

        # Use selected config or fall back to the passed request_config
        active_request_config = self.request_config or request_config

        # Verify we have a compatible OpenAI configuration
        if not hasattr(active_request_config, "model"):
            raise ValueError(
                "The selected request configuration does not have a 'model' attribute"
            )

        messages: list[ChatCompletionMessageParam] = []

        # Add system prompt if provided
        if request.systemPrompt:
            messages.append(
                ChatCompletionSystemMessageParam(
                    role="system",
                    content=request.systemPrompt,
                )
            )
        # Add sampling messages
        messages += template_processor(request.messages)

        # TODO: not yet, but we can provide an option for running tools at the assistant
        # level and then pass the results to in the results
        # tools = self._assistant_mcp_tools
        # for now:
        tools = None

        # Build the completion arguments, adding tools if provided
        completion_args: dict = {
            "messages": messages,
            "model": active_request_config.model,
            "tools": tools,
        }

        # Add model-specific parameters based on the type - with explicit type checking for Pylance
        # Check if this is an OpenAI-compatible configuration
        is_openai_config = isinstance(active_request_config, OpenAIRequestConfig)

        if is_openai_config:
            # Now we know it's an OpenAIRequestConfig type, so we can safely access its properties
            openai_config = active_request_config  # Type hint for Pylance

            if (
                hasattr(openai_config, "is_reasoning_model")
                and openai_config.is_reasoning_model
            ):
                # Configure for reasoning models
                completion_args["max_completion_tokens"] = openai_config.response_tokens

                if hasattr(openai_config, "reasoning_effort"):
                    completion_args["reasoning_effort"] = openai_config.reasoning_effort
            else:
                # Configure for standard OpenAI models
                completion_args["max_tokens"] = openai_config.response_tokens
        else:
            # For non-OpenAI models (e.g., Anthropic), just use response_tokens as max_tokens
            # without trying to access OpenAI-specific properties
            completion_args["max_tokens"] = active_request_config.response_tokens

        # Allow overriding completion arguments with extra_args from metadata
        # This is useful for experimentation and is a use-at-your-own-risk feature
        if (
            request.metadata is not None
            and "extra_args" in request.metadata
            and isinstance(request.metadata["extra_args"], dict)
        ):
            completion_args = deepmerge.always_merger.merge(
                completion_args,
                request.metadata["extra_args"],
            )

        return completion_args


def openai_template_processor(
    value: SamplingMessage,
) -> Union[SamplingMessage, List[SamplingMessage]]:
    """
    Processes a SamplingMessage using OpenAI's template processor.
    """

    return value


def sampling_message_to_chat_completion_user_message(
    sampling_message: SamplingMessage,
) -> ChatCompletionUserMessageParam:
    """
    Converts a SamplingMessage to a ChatCompletionUserMessage.
    """

    if sampling_message.role != "user":
        raise ValueError(f"Unsupported role: {sampling_message.role}")

    if isinstance(sampling_message.content, TextContent):
        return ChatCompletionUserMessageParam(
            role="user", content=sampling_message.content.text
        )
    elif isinstance(sampling_message.content, ImageContent):
        return ChatCompletionUserMessageParam(
            role="user",
            content=[
                ChatCompletionContentPartImageParam(
                    type="image_url",
                    image_url={
                        "url": sampling_message.content.data,
                        "detail": "high",
                    },
                )
            ],
        )
    else:
        raise ValueError(f"Unsupported content type: {type(sampling_message.content)}")


def sampling_message_to_chat_completion_assistant_message(
    sampling_message: SamplingMessage,
) -> ChatCompletionAssistantMessageParam:
    """
    Converts a SamplingMessage to a ChatCompletionAssistantMessage.
    """
    if sampling_message.role != "assistant":
        raise ValueError(f"Unsupported role: {sampling_message.role}")

    if not isinstance(sampling_message.content, TextContent):
        raise ValueError(
            f"Unsupported content type: {type(sampling_message.content)} for assistant"
        )

    return ChatCompletionAssistantMessageParam(
        role="assistant",
        content=sampling_message.content.text,
    )


def sampling_message_to_chat_completion_message(
    sampling_message: SamplingMessage,
) -> ChatCompletionMessageParam:
    """
    Converts a SamplingMessage to ChatCompletionMessageParam
    """

    match sampling_message.role:
        case "user":
            return sampling_message_to_chat_completion_user_message(sampling_message)
        case "assistant":
            return sampling_message_to_chat_completion_assistant_message(
                sampling_message
            )
        case _:
            raise ValueError(f"Unsupported role: {sampling_message.role}")
