# Copyright (c) Microsoft. All rights reserved.

# Prospector Assistant
#
# This assistant helps you mine ideas from artifacts.
#

import logging
import time
from contextlib import AsyncExitStack
from typing import Any, List

import deepmerge
from assistant_extensions.ai_clients.model import CompletionMessage
from assistant_extensions.artifacts import ArtifactsExtension
from assistant_extensions.attachments import AttachmentsExtension
from semantic_workbench_api_model.workbench_model import (
    ConversationMessage,
    MessageType,
    NewConversationMessage,
)
from semantic_workbench_assistant.assistant_app import ConversationContext

from assistant.response.utils.tool_utils import handle_tool_action, retrieve_tools_from_sessions

from ..config import AssistantConfigModel
from ..mcp_servers import connect_to_mcp_server
from .providers import AnthropicResponseProvider, OpenAIResponseProvider
from .tool_handler import parse_tool_response
from .utils import (
    conversation_message_to_completion_messages,
    get_history_messages,
    get_response_duration_message,
    get_token_usage_message,
    inject_attachments_inline,
    load_server_configs,
    num_tokens_from_messages,
)

logger = logging.getLogger(__name__)


async def respond_to_conversation(
    artifacts_extension: ArtifactsExtension,
    attachments_extension: AttachmentsExtension,
    context: ConversationContext,
    config: AssistantConfigModel,
    message: ConversationMessage,
    metadata: dict[str, Any] = {},
    config_file: str = "mcp_servers_config.json",  # Specify the config file path
) -> None:
    """
    Respond to a conversation message using dynamically loaded MCP servers.
    """

    # Load server configurations
    server_configs = load_server_configs(config_file)

    async with AsyncExitStack() as stack:
        sessions = []
        for server_config in server_configs:
            session = await stack.enter_async_context(connect_to_mcp_server(server_config))
            if session:
                sessions.append(session)
            else:
                logger.warning(f"Could not establish session with {server_config.get('name')}")

        if not sessions:
            await context.send_messages(
                NewConversationMessage(
                    content="Unable to connect to any MCP servers. Please ensure the servers are running.",
                    message_type=MessageType.notice,
                    metadata=metadata,
                )
            )
            return

        # Retrieve tools from the MCP sessions
        all_tools = await retrieve_tools_from_sessions(sessions)

        # Initialize the response provider based on configuration
        if config.ai_client_config.ai_service_type == "anthropic":
            response_provider = AnthropicResponseProvider(
                assistant_config=config, anthropic_client_config=config.ai_client_config
            )
        else:
            response_provider = OpenAIResponseProvider(
                artifacts_extension=artifacts_extension,
                conversation_context=context,
                assistant_config=config,
                openai_client_config=config.ai_client_config,
            )

        request_config = config.ai_client_config.request_config

        # Define the metadata key for any metadata created within this method
        method_metadata_key = "respond_to_conversation"

        # Track the start time of the response generation
        response_start_time = time.time()

        # Get the list of conversation participants
        participants_response = await context.get_participants(include_inactive=True)

        # Establish a token to be used by the AI model to indicate no response
        silence_token = "{{SILENCE}}"

        # Prepare tool descriptions for the system prompt
        tool_descriptions = [
            f"Tool Name: {tool.name}\nDescription: {tool.description}\nInput Parameters: {tool.inputSchema}\n"
            for tool in all_tools
        ]

        # Construct system message content
        system_message_content = (
            f'{config.instruction_prompt}\n\nYour name is "{context.assistant.name}".\n'
            "You have access to the following tools:\n"
            f"{''.join(tool_descriptions)}"
            "\nWhen you need to use a tool, output a JSON object in the following format:\n"
            '{"action": "call_tool", "tool_name": "TOOL_NAME", "arguments": {"arg1": "value1", ...}}\n'
            "After receiving the tool's output, incorporate it into your response."
        )

        if len(participants_response.participants) > 2:
            system_message_content += (
                "\n\n"
                f"There are {len(participants_response.participants)} participants in the conversation, "
                "including you as the assistant and the following users: "
                + ", ".join([
                    f'"{participant.name}"'
                    for participant in participants_response.participants
                    if participant.id != context.assistant.id
                ])
                + "\n\nYou do not need to respond to every message. Do not respond if the last thing said was a closing "
                "statement such as 'bye' or 'goodbye', or just a general acknowledgement like 'ok' or 'thanks'. Do not "
                f'respond as another user in the conversation, only as "{context.assistant.name}". '
                "Sometimes the other users need to talk amongst themselves and that is ok. If the conversation seems to "
                f'be directed at you or the general audience, go ahead and respond.\n\nSay "{silence_token}" to skip '
                "your turn."
            )

        # Add the artifact agent instruction prompt and guardrails
        if config.extensions_config.artifacts.enabled:
            system_message_content += f"\n\n{config.extensions_config.artifacts.instruction_prompt}"

        system_message_content += f"\n\n{config.guardrails_prompt}"

        # Initialize the completion messages with the system message
        completion_messages: List[CompletionMessage] = [
            CompletionMessage(
                role="system",
                content=system_message_content,
            )
        ]

        token_count = 0

        # Calculate the token count for the messages so far
        result = await num_tokens_from_messages(
            context=context,
            response_provider=response_provider,
            messages=completion_messages,
            model=request_config.model,
            metadata=metadata,
            metadata_key="system_message",
        )
        if result is not None:
            token_count += result.count
        else:
            return

        # Generate the attachment messages
        attachment_messages = await attachments_extension.get_completion_messages_for_attachments(
            context,
            config=config.extensions_config.attachments,
        )
        result = await num_tokens_from_messages(
            context=context,
            response_provider=response_provider,
            messages=attachment_messages,
            model=request_config.model,
            metadata=metadata,
            metadata_key="attachment_messages",
        )
        if result is not None:
            token_count += result.count
        else:
            return

        # Calculate available tokens
        available_tokens = request_config.max_tokens - request_config.response_tokens

        # Get history messages
        history_messages = await get_history_messages(
            response_provider=response_provider,
            context=context,
            participants=participants_response.participants,
            converter=conversation_message_to_completion_messages,
            model=request_config.model,
            token_limit=available_tokens - token_count,
        )

        # Inject or append attachment messages
        if config.use_inline_attachments:
            history_messages = inject_attachments_inline(history_messages, attachment_messages)
        else:
            completion_messages.extend(attachment_messages)

        # Add history messages
        completion_messages.extend(history_messages)

        # Add the incoming message
        completion_messages.extend(
            await conversation_message_to_completion_messages(context, message, participants_response.participants)
        )

        # Check token count
        result = await num_tokens_from_messages(
            context=context,
            response_provider=response_provider,
            messages=completion_messages,
            model=request_config.model,
            metadata=metadata,
            metadata_key=method_metadata_key,
        )
        if result is not None:
            estimated_token_count = result.count
            if estimated_token_count > request_config.max_tokens:
                await context.send_messages(
                    NewConversationMessage(
                        content=(
                            f"You've exceeded the token limit of {request_config.max_tokens} in this conversation "
                            f"({estimated_token_count}). This assistant does not support recovery from this state. "
                            "Please start a new conversation and let us know you ran into this."
                        ),
                        message_type=MessageType.chat,
                        metadata=metadata,
                    )
                )
                return
        else:
            return

        # Generate AI response
        try:
            response_result = await response_provider.get_response(
                messages=completion_messages,
                metadata_key=method_metadata_key,
            )
        except Exception as e:
            logger.exception(f"Error generating AI response: {e}")
            await context.send_messages(
                NewConversationMessage(
                    content="An error occurred while generating your response.",
                    message_type=MessageType.notice,
                    metadata=metadata,
                )
            )
            return

        content = response_result.content
        message_type = response_result.message_type
        completion_total_tokens = response_result.completion_total_tokens

        deepmerge.always_merger.merge(metadata, response_result.metadata)

        if not content:
            await context.send_messages(
                NewConversationMessage(
                    content="[no response from AI]",
                    message_type=MessageType.chat,
                    metadata=metadata,
                )
            )
            return

        # Handle tool actions
        tool_action, remaining_content = parse_tool_response(content)
        if tool_action:
            try:
                tool_action_result = await handle_tool_action(
                    sessions,
                    tool_action,
                    all_tools,
                    context,
                    completion_messages,
                    response_provider,
                    metadata,
                    method_metadata_key,
                )
            except Exception as e:
                logger.exception(f"Error handling tool action: {e}")
                await context.send_messages(
                    NewConversationMessage(
                        content="An error occurred while handling the tool action.",
                        message_type=MessageType.notice,
                        metadata=metadata,
                    )
                )
                return

            content = tool_action_result.content
            message_type = tool_action_result.message_type
            completion_total_tokens += tool_action_result.completion_total_tokens
            deepmerge.always_merger.merge(metadata, tool_action_result.metadata)

        # Create the footer items for the response
        footer_items = []

        # Add the token usage message to the footer items
        if completion_total_tokens > 0:
            footer_items.append(get_token_usage_message(request_config.max_tokens, completion_total_tokens))

        # Track the end time of the response generation and calculate duration
        response_end_time = time.time()
        response_duration = response_end_time - response_start_time

        # Add the response duration to the footer items
        footer_items.append(get_response_duration_message(response_duration))

        # Update the metadata with the footer items
        deepmerge.always_merger.merge(
            metadata,
            {
                "footer_items": footer_items,
            },
        )

        if content:
            # Handle silence token
            if content.replace(" ", "") == silence_token:
                # If debug output is enabled, notify that the assistant chose to remain silent
                if config.enable_debug_output:
                    # Add debug metadata to indicate the assistant chose to remain silent
                    deepmerge.always_merger.merge(
                        metadata,
                        {
                            "debug": {
                                method_metadata_key: {
                                    "silence_token": True,
                                },
                            },
                            "attribution": "debug output",
                            "generated_content": False,
                        },
                    )
                    # Send a notice message to the conversation
                    await context.send_messages(
                        NewConversationMessage(
                            message_type=MessageType.notice,
                            content="[assistant chose to remain silent]",
                            metadata=metadata,
                        )
                    )
                return  # Exit the function if the assistant remains silent

            # Override message type if content starts with '/'
            if content.startswith("/"):
                message_type = MessageType.command_response

        # Send the final response to the conversation
        await context.send_messages(
            NewConversationMessage(
                content=content or "[no response from AI]",
                message_type=message_type,
                metadata=metadata,
            )
        )

        # Send token usage warning if applicable
        if completion_total_tokens and config.high_token_usage_warning.enabled:
            token_count_for_warning = request_config.max_tokens * (config.high_token_usage_warning.threshold / 100)
            if completion_total_tokens > token_count_for_warning:
                warning_content = (
                    f"{config.high_token_usage_warning.message}\n\nTotal tokens used: {completion_total_tokens}"
                )
                await context.send_messages(
                    NewConversationMessage(
                        content=warning_content,
                        message_type=MessageType.notice,
                        metadata={
                            "debug": {
                                "high_token_usage_warning": {
                                    "completion_total_tokens": completion_total_tokens,
                                    "threshold": config.high_token_usage_warning.threshold,
                                    "token_count_for_warning": token_count_for_warning,
                                }
                            },
                            "attribution": "system",
                        },
                    )
                )


# endregion
