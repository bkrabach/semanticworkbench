import logging
from contextlib import AsyncExitStack
from typing import Any, List

from assistant_extensions.attachments import AttachmentsExtension
from assistant_extensions.mcp import (
    MCPServerConfig,
    MCPSession,
    OpenAISamplingHandler,
    establish_mcp_sessions,
    get_mcp_server_prompts,
    refresh_mcp_sessions,
)
from semantic_workbench_api_model.workbench_model import (
    ConversationMessage,
    MessageType,
    NewConversationMessage,
)
from semantic_workbench_assistant.assistant_app import ConversationContext

from ..config import AssistantConfigModel
from .step_handler import next_step

logger = logging.getLogger(__name__)


async def respond_to_conversation(
    message: ConversationMessage,
    attachments_extension: AttachmentsExtension,
    context: ConversationContext,
    config: AssistantConfigModel,
    metadata: dict[str, Any] = {},
) -> None:
    """
    Perform a multi-step response to a conversation message using dynamically loaded MCP servers with
    support for multiple tool invocations.
    """

    async with AsyncExitStack() as stack:
        # If tools are enabled, establish connections to the MCP servers
        mcp_sessions: List[MCPSession] = []

        async def error_handler(server_config: MCPServerConfig, error: Exception) -> None:
            logger.error(f"Failed to connect to MCP server {server_config.key}: {error}")
            # Also notify the user about this server failure here.
            await context.send_messages(
                NewConversationMessage(
                    content=f"Failed to connect to MCP server {server_config.key}: {error}",
                    message_type=MessageType.notice,
                    metadata=metadata,
                )
            )

        # Create a sampling handler with all available model configurations
        # This allows the handler to select the most appropriate model based on modelPreferences
        sampling_handler = OpenAISamplingHandler(
            client_configs=[
                config.generative_ai_client_config,
                config.reasoning_ai_client_config,
                # More configs can be added here in the future when available
            ]
        )

        mcp_sessions = await establish_mcp_sessions(
            tools_config=config.extensions_config.tools,
            stack=stack,
            error_handler=error_handler,
            sampling_handler=sampling_handler.handle_message,
        )

        if len(config.extensions_config.tools.mcp_servers) > 0 and len(mcp_sessions) == 0:
            # No MCP servers are available, so we should not continue
            logger.error("No MCP servers are available.")
            return

        # Retrieve prompts from the MCP servers
        mcp_prompts = get_mcp_server_prompts(config.extensions_config.tools)

        # Initialize a loop control variable
        max_steps = config.extensions_config.tools.max_steps
        interrupted = False
        encountered_error = False
        completed_within_max_steps = False
        step_count = 0

        # Loop until the response is complete or the maximum number of steps is reached
        while step_count < max_steps:
            step_count += 1

            # Check to see if we should interrupt our flow
            last_message = await context.get_messages(limit=1, message_types=[MessageType.chat])

            if step_count > 1 and last_message.messages[0].sender.participant_id != context.assistant.id:
                # The last message was from a sender other than the assistant, so we should
                # interrupt our flow as this would have kicked off a new response from this
                # assistant with the new message in mind and that process can decide if it
                # should continue with the current flow or not.
                interrupted = True
                logger.info("Response interrupted.")
                break

            # Reconnect to the MCP servers if they were disconnected
            mcp_sessions = await refresh_mcp_sessions(mcp_sessions)

            # Get the current request_config and service_config from the sampling_handler
            # These will be updated by the handler when it selects models based on preferences
            current_request_config = sampling_handler.request_config
            current_service_config = sampling_handler.service_config

            # Check for missing configs
            if not current_request_config or not current_service_config:
                logger.error("No request_config or service_config available in sampling_handler")
                await context.send_messages(
                    NewConversationMessage(
                        content="Configuration error: No models available for completion. Please check assistant configuration.",
                        message_type=MessageType.notice,
                        metadata=metadata,
                    )
                )
                break

            # Type check to ensure we're passing compatible configs to next_step
            from openai_client import AzureOpenAIServiceConfig, OpenAIRequestConfig, OpenAIServiceConfig

            # Verify request_config is an OpenAIRequestConfig
            if not isinstance(current_request_config, OpenAIRequestConfig):
                logger.error(f"Incompatible request_config type: {type(current_request_config).__name__}")
                await context.send_messages(
                    NewConversationMessage(
                        content=f"Configuration error: Incompatible model type {type(current_request_config).__name__}. Only OpenAI models are supported.",
                        message_type=MessageType.notice,
                        metadata=metadata,
                    )
                )
                break

            # Verify service_config is a compatible OpenAI service config
            if not isinstance(current_service_config, (AzureOpenAIServiceConfig, OpenAIServiceConfig)):
                logger.error(f"Incompatible service_config type: {type(current_service_config).__name__}")
                await context.send_messages(
                    NewConversationMessage(
                        content=f"Configuration error: Incompatible service type {type(current_service_config).__name__}. Only OpenAI services are supported.",
                        message_type=MessageType.notice,
                        metadata=metadata,
                    )
                )
                break

            # Now we know the types are compatible
            openai_request_config = current_request_config  # Now typed as OpenAIRequestConfig
            openai_service_config = (
                current_service_config  # Now typed as AzureOpenAIServiceConfig | OpenAIServiceConfig
            )

            step_result = await next_step(
                sampling_handler=sampling_handler,
                mcp_sessions=mcp_sessions,
                mcp_prompts=mcp_prompts,
                attachments_extension=attachments_extension,
                context=context,
                request_config=openai_request_config,
                service_config=openai_service_config,
                prompts_config=config.prompts,
                tools_config=config.extensions_config.tools,
                attachments_config=config.extensions_config.attachments,
                metadata=metadata,
                metadata_key=f"respond_to_conversation:step_{step_count}",
            )

            if step_result.status == "error":
                encountered_error = True
                break

            if step_result.status == "final":
                completed_within_max_steps = True
                break

        # If the response did not complete within the maximum number of steps, send a message to the user
        if not completed_within_max_steps and not encountered_error and not interrupted:
            await context.send_messages(
                NewConversationMessage(
                    content=config.extensions_config.tools.max_steps_truncation_message,
                    message_type=MessageType.notice,
                    metadata=metadata,
                )
            )
            logger.info("Response stopped early due to maximum steps.")

    # Log the completion of the response
    logger.info("Response completed.")
