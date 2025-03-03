import logging
import time
from textwrap import dedent
from typing import Any, List, Optional

import deepmerge
from assistant_extensions.attachments import AttachmentsConfigModel, AttachmentsExtension
from assistant_extensions.mcp import MCPSession, MCPToolsConfigModel, OpenAISamplingHandler
from openai.types.chat import (
    ChatCompletion,
    ParsedChatCompletion,
)
from openai_client import AzureOpenAIServiceConfig, OpenAIRequestConfig, OpenAIServiceConfig, create_client
from semantic_workbench_api_model.workbench_model import (
    MessageType,
    NewConversationMessage,
)
from semantic_workbench_assistant.assistant_app import ConversationContext

from ..config import PromptsConfigModel
from .completion_handler import handle_completion
from .models import StepResult
from .request_builder import build_request
from .sampling import SamplingConfig, SamplingManager
from .utils import get_formatted_token_count

logger = logging.getLogger(__name__)


async def next_step(
    sampling_handler: OpenAISamplingHandler,
    mcp_sessions: List[MCPSession],
    mcp_prompts: List[str],
    attachments_extension: AttachmentsExtension,
    context: ConversationContext,
    request_config: OpenAIRequestConfig,
    service_config: AzureOpenAIServiceConfig | OpenAIServiceConfig,
    prompts_config: PromptsConfigModel,
    tools_config: MCPToolsConfigModel,
    attachments_config: AttachmentsConfigModel,
    metadata: dict[str, Any],
    metadata_key: str,
    sampling_manager: Optional[SamplingManager] = None,
) -> StepResult:
    step_result = StepResult(status="continue", metadata=metadata.copy())

    # helper function for handling errors
    async def handle_error(error_message: str, error_debug: dict[str, Any] | None = None) -> StepResult:
        if error_debug is not None:
            deepmerge.always_merger.merge(
                step_result.metadata,
                {
                    "debug": {
                        metadata_key: {
                            "error": error_debug,
                        },
                    },
                },
            )
        await context.send_messages(
            NewConversationMessage(
                content=error_message,
                message_type=MessageType.notice,
                metadata=step_result.metadata,
            )
        )
        step_result.status = "error"
        return step_result

    # Track the start time of the response generation
    response_start_time = time.time()

    # Establish a token to be used by the AI model to indicate no response
    silence_token = "{{SILENCE}}"

    # If no sampling manager is provided, create one using the current config
    if sampling_manager is None:
        # Create a sampling config for the manager
        sampling_config = SamplingConfig(
            request_config=request_config, service_config=service_config, tools_config=tools_config
        )
        sampling_manager = SamplingManager(sampling_config)

    # Get the tools from mcp_sessions
    tools = sampling_manager.get_tools_from_sessions(mcp_sessions, tools_config)

    # Update the sampling handler with the tools
    if sampling_handler.assistant_mcp_tools != tools:
        sampling_handler.assistant_mcp_tools = tools
    build_request_result = await build_request(
        sampling_handler=sampling_handler,
        mcp_prompts=mcp_prompts,
        attachments_extension=attachments_extension,
        context=context,
        prompts_config=prompts_config,
        request_config=request_config,
        tools_config=tools_config,
        tools=tools,
        attachments_config=attachments_config,
        silence_token=silence_token,
    )

    chat_message_params = build_request_result.chat_message_params

    # Generate AI response
    # initialize variables for the response content
    completion: ParsedChatCompletion | ChatCompletion | None = None

    # update the metadata with debug information
    deepmerge.always_merger.merge(
        step_result.metadata,
        {
            "debug": {
                metadata_key: {
                    "request": {
                        "model": request_config.model,
                        "messages": chat_message_params,
                        "max_tokens": request_config.response_tokens,
                        "tools": tools,
                    },
                },
            },
        },
    )

    # generate a response from the AI model
    async with create_client(service_config) as client:
        completion_status = "reasoning..." if request_config.is_reasoning_model else "thinking..."
        async with context.set_status(completion_status):
            try:
                # Use the sampling_manager to get the completion if available, otherwise use the handler directly
                if sampling_manager:
                    completion = await sampling_manager.get_completion(
                        client, request_config, chat_message_params, tools
                    )
                else:
                    # Fallback to direct completion if needed
                    from .utils import get_completion as direct_get_completion

                    completion = await direct_get_completion(client, request_config, chat_message_params, tools)

            except Exception as e:
                logger.exception(f"exception occurred calling openai chat completion: {e}")
                deepmerge.always_merger.merge(
                    step_result.metadata,
                    {
                        "debug": {
                            metadata_key: {
                                "error": str(e),
                            },
                        },
                    },
                )
                await context.send_messages(
                    NewConversationMessage(
                        content="An error occurred while calling the OpenAI API. Is it configured correctly?"
                        " View the debug inspector for more information.",
                        message_type=MessageType.notice,
                        metadata=step_result.metadata,
                    )
                )
                step_result.status = "error"
                return step_result

    if completion is None:
        return await handle_error("No response from OpenAI.")

    step_result = await handle_completion(
        sampling_handler,
        step_result,
        completion,
        mcp_sessions,
        context,
        request_config,
        silence_token,
        metadata_key,
        response_start_time,
    )

    if build_request_result.token_overage > 0:
        # send a notice message to the user to inform them of the situation
        await context.send_messages(
            NewConversationMessage(
                content=dedent(f"""
                    The conversation history exceeds the token limit by
                    {get_formatted_token_count(build_request_result.token_overage)}
                    tokens. Conversation history sent to the model was truncated. For best experience,
                    consider removing some attachments and/or messages and try again, or starting a new
                    conversation.
                """),
                message_type=MessageType.notice,
            )
        )

    return step_result
