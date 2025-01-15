# Copyright (c) Microsoft. All rights reserved.

import json
import logging
from typing import Any, Iterable, List, Sequence

import deepmerge
import openai_client
from assistant_extensions.ai_clients.config import AzureOpenAIClientConfigModel, OpenAIClientConfigModel
from assistant_extensions.ai_clients.model import CompletionMessage
from assistant_extensions.artifacts import ArtifactsExtension
from mcp import ClientSession, Tool
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
    ParsedChatCompletion,
)
from openai.types.shared_params.function_definition import FunctionDefinition
from semantic_workbench_api_model.workbench_model import (
    AssistantStateEvent,
    MessageType,
)
from semantic_workbench_assistant.assistant_app import (
    ConversationContext,
)

from ...config import AssistantConfigModel
from .base_provider import NumberTokensResult, ResponseProvider, ResponseResult, ToolAction

logger = logging.getLogger(__name__)


class OpenAIResponseProvider(ResponseProvider):
    def __init__(
        self,
        artifacts_extension: ArtifactsExtension,
        conversation_context: ConversationContext,
        assistant_config: AssistantConfigModel,
        openai_client_config: OpenAIClientConfigModel | AzureOpenAIClientConfigModel,
    ) -> None:
        self.artifacts_extension = artifacts_extension
        self.conversation_context = conversation_context
        self.assistant_config = assistant_config
        self.service_config = openai_client_config.service_config
        self.request_config = openai_client_config.request_config

    async def num_tokens_from_messages(
        self,
        messages: Sequence[CompletionMessage],
        model: str,
        metadata_key: str,
    ) -> NumberTokensResult:
        """
        Calculate the number of tokens in a message.
        """
        count = openai_client.num_tokens_from_messages(
            model=model, messages=openai_client.convert_from_completion_messages(messages)
        )

        return NumberTokensResult(
            count=count,
            metadata={
                "debug": {
                    metadata_key: {
                        "request": {
                            "model": model,
                            "messages": messages,
                        },
                        "response": count,
                    },
                },
            },
            metadata_key=metadata_key,
        )

    async def get_response(
        self,
        messages: List[CompletionMessage],
        metadata_key: str,
        mcp_tools: List[Tool],
        mcp_sessions: List[ClientSession],
    ) -> ResponseResult:
        """
        Respond to a conversation message.

        This method uses the OpenAI API to generate a response to the message.

        It includes any attachments as individual system messages before the chat history, along with references
        to the attachments in the point in the conversation where they were mentioned. This allows the model to
        consider the full contents of the attachments separate from the conversation, but with the context of
        where they were mentioned and any relevant surrounding context such as how to interpret the attachment
        or why it was shared or what to do with it.
        """

        response_result = ResponseResult(
            content=None,
            tool_actions=None,
            message_type=MessageType.chat,
            metadata={},
            completion_total_tokens=0,
        )

        # define the metadata key for any metadata created within this method
        method_metadata_key = f"{metadata_key}:openai"

        # initialize variables for the response content
        completion: ParsedChatCompletion | ChatCompletion | None = None

        # convert the tools to make them compatible with the OpenAI API
        tools = convert_mcp_tools_to_openai_tools(mcp_tools)

        # convert the messages to chat completion message parameters
        chat_message_params: Iterable[ChatCompletionMessageParam] = openai_client.convert_from_completion_messages(
            messages
        )

        # generate a response from the AI model
        async with openai_client.create_client(self.service_config) as client:
            try:
                if self.assistant_config.extensions_config.artifacts.enabled:
                    # FIXME: consider if/how we want to use tools here
                    response = await self.artifacts_extension.get_openai_completion_response(
                        client,
                        chat_message_params,
                        self.request_config.model,
                        self.request_config.response_tokens,
                    )

                    completion = response.completion
                    response_result.content = response.assistant_response
                    artifacts_to_create_or_update = response.artifacts_to_create_or_update

                    for artifact in artifacts_to_create_or_update:
                        self.artifacts_extension.create_or_update_artifact(
                            self.conversation_context,
                            artifact,
                        )
                    # send an event to notify the artifact state was updated
                    await self.conversation_context.send_conversation_state_event(
                        AssistantStateEvent(
                            state_id="artifacts",
                            event="updated",
                            state=None,
                        )
                    )
                    # send a focus event to notify the assistant to focus on the artifacts
                    await self.conversation_context.send_conversation_state_event(
                        AssistantStateEvent(
                            state_id="artifacts",
                            event="focus",
                            state=None,
                        )
                    )

                else:
                    completion = await self.get_completion(client, chat_message_params, tools)
                    response_result.content = completion.choices[0].message.content

            except Exception as e:
                logger.exception(f"exception occurred calling openai chat completion: {e}")
                response_result.content = (
                    "An error occurred while calling the OpenAI API. Is it configured correctly?"
                    " View the debug inspector for more information."
                )
                response_result.message_type = MessageType.notice
                deepmerge.always_merger.merge(
                    response_result.metadata,
                    {"debug": {method_metadata_key: {"error": str(e)}}},
                )

        if completion is not None:
            # get the total tokens used for the completion
            response_result.completion_total_tokens = completion.usage.total_tokens if completion.usage else 0

            # check if the completion has tool calls
            tool_calls = completion.choices[0].message.tool_calls
            if tool_calls:
                for tool_call in tool_calls:
                    tool_action = ToolAction(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=json.loads(tool_call.function.arguments),
                    )
                    if response_result.tool_actions is None:
                        response_result.tool_actions = []
                    response_result.tool_actions.append(tool_action)
                    if response_result.content is None:
                        response_result.content = tool_action.arguments.get("aiContext")

        # update the metadata with debug information
        deepmerge.always_merger.merge(
            response_result.metadata,
            {
                "debug": {
                    method_metadata_key: {
                        "request": {
                            "model": self.request_config.model,
                            "messages": chat_message_params,
                            "max_tokens": self.request_config.response_tokens,
                        },
                        "response": completion.model_dump() if completion else "[no response from openai]",
                    },
                },
            },
        )

        # send the response to the conversation
        return response_result

    async def get_completion(
        self,
        client: AsyncOpenAI,
        chat_message_params: List[ChatCompletionMessageParam],
        tools: List[ChatCompletionToolParam],
    ) -> ChatCompletion:
        """
        Generate a completion from the OpenAI API.
        """

        # initialize variables for the response content
        completion: ChatCompletion | None = None

        if self.request_config.is_reasoning_model:
            # convert all messages that use system role to user role as reasoning models do not support system role
            chat_message_params = [
                {
                    "role": "user",
                    "content": message["content"],
                }
                if message["role"] == "system"
                else message
                for message in chat_message_params
            ]

            # for reasoning models, use max_completion_tokens instead of max_tokens
            completion = await client.chat.completions.create(
                messages=chat_message_params,
                model=self.request_config.model,
                max_completion_tokens=self.request_config.response_tokens,
                tools=tools,
                tool_choice="auto",
            )

        else:
            # call the OpenAI API to generate a completion
            completion = await client.chat.completions.create(
                messages=chat_message_params,
                model=self.request_config.model,
                max_tokens=self.request_config.response_tokens,
                tools=tools,
                tool_choice="auto",
            )

        return completion


def convert_mcp_tools_to_openai_tools(mcp_tools: List[Tool]) -> List[ChatCompletionToolParam]:
    tools_list: List[ChatCompletionToolParam] = []
    for mcp_tool in mcp_tools:
        # add parameter for explaining the step for the user observing the assistant
        aiContext: dict[str, Any] = {
            "type": "string",
            "description": (
                "Explanation of why the AI is using this tool and what it expects to accomplish."
                "This message is displayed to the user, coming from the point of view of the assistant"
                " and should fit within the flow of the ongoing conversation."
            ),
        }

        tools_list.append(
            ChatCompletionToolParam(
                function=FunctionDefinition(
                    name=mcp_tool.name,
                    description=mcp_tool.description if mcp_tool.description else "[no description provided]",
                    parameters=deepmerge.always_merger.merge(
                        mcp_tool.inputSchema,
                        {
                            "properties": {
                                "aiContext": aiContext,
                            },
                        },
                    ),
                ),
                type="function",
            )
        )
    return tools_list
