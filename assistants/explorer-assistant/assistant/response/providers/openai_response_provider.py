# Copyright (c) Microsoft. All rights reserved.

import json
import logging
import re
from textwrap import dedent
from typing import Any, List, Optional, Sequence, Tuple

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
from openai.types.shared_params import FunctionDefinition
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

        # convert the messages to chat completion message parameters
        chat_message_params: List[ChatCompletionMessageParam] = openai_client.convert_from_completion_messages(messages)

        # convert the tools to make them compatible with the OpenAI API
        tools = convert_mcp_tools_to_openai_tools(mcp_tools)

        if self.request_config.is_reasoning_model:
            chat_message_params = customize_chat_message_params_for_reasoning(chat_message_params, tools)

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
            tool_actions = get_tool_actions_from_response(completion)
            response_result.tool_actions = tool_actions
            if len(tool_actions) > 0:
                # check within the tool actions for any that have an "aiContext" argument
                # and if so, set the content to the value of the "aiContext" arguments
                updated_content, updated_tool_actions = extract_content_from_tool_actions(tool_actions)
                response_result.content = updated_content
                response_result.tool_actions = updated_tool_actions

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
            # for reasoning models, use max_completion_tokens instead of max_tokens
            completion = await client.chat.completions.create(
                messages=chat_message_params,
                model=self.request_config.model,
                max_completion_tokens=self.request_config.response_tokens,
            )

        else:
            # call the OpenAI API to generate a completion, include tools if provided
            completion = await client.chat.completions.create(
                messages=chat_message_params,
                model=self.request_config.model,
                max_tokens=self.request_config.response_tokens,
                tools=tools,
                tool_choice="auto",
            )

        return completion


def customize_chat_message_params_for_reasoning(
    chat_message_params: List[ChatCompletionMessageParam],
    tools: List[ChatCompletionToolParam],
) -> List[ChatCompletionMessageParam]:
    """
    Applies some hacks to the chat completions to make them work with reasoning models.
    """

    # reasoning models do not support tool calls, so we will hack it via instruction
    chat_message_params = inject_tools_into_system_message(chat_message_params, tools)

    # convert all messages that use system role to user role as reasoning models do not
    # support system role - at all, not even the first message/instruction
    chat_message_params = [
        {
            "role": "user",
            "content": message["content"],
        }
        if message["role"] == "system"
        else message
        for message in chat_message_params
    ]

    return chat_message_params


def extract_content_from_tool_actions(
    tool_actions: List[ToolAction],
) -> Tuple[str | None, List[ToolAction]]:
    """
    Extracts the AI content from the tool actions.

    This function takes a list of ToolAction objects and extracts the AI content from them. It returns a tuple
    containing the AI content and the updated list of ToolAction objects.

    Args:
        tool_actions (List[ToolAction]): The list of ToolAction objects.

    Returns:
        Tuple[str | None, List[ToolAction]]: A tuple containing the AI content and the updated list of ToolAction
        objects.
    """
    ai_content = ""
    updated_tool_actions = []

    for tool_action in tool_actions:
        # Split the AI content from the tool action
        content, updated_tool_action = split_ai_content_from_tool_action(tool_action)

        if content is not None:
            ai_content += f"{content}\n\n"

        updated_tool_actions.append(updated_tool_action)

    return ai_content.strip(), updated_tool_actions


def split_ai_content_from_tool_action(
    tool_action: ToolAction,
) -> Tuple[str | None, ToolAction]:
    """
    Splits the AI content from the tool action.
    """

    # Check if the tool action has an "aiContext" argument
    if "aiContext" in tool_action.arguments:
        # Extract the AI content
        ai_content = tool_action.arguments.pop("aiContext")

        # Return the AI content and the updated tool action
        return ai_content, tool_action

    return None, tool_action


def clean_json_content(json_content: str) -> str:
    """
    Removes '+' operators used for string concatenation in JSON strings.
    """
    # Remove '+' operators and concatenate the strings
    cleaned_content = re.sub(r'"\s*\+\s*\n\s*"', "", json_content)
    return cleaned_content


def get_tool_actions_from_response(
    response: ChatCompletion,
) -> List[ToolAction]:
    """
    Extract tool calls from the response.

    This function takes a ChatCompletion response and extracts the tool calls from it. It returns a list of
    ToolAction objects, which contain the tool call ID, name, and arguments.

    Args:
        response (ChatCompletion): The ChatCompletion response.

    Returns:
        List[ToolAction]: A list of ToolAction objects.
    """
    tool_actions = []
    if response.choices[0].message.tool_calls:
        for json_data in response.choices[0].message.tool_calls:
            tool_action = ToolAction(
                id=json_data.id,
                name=json_data.function.name,
                arguments=json.loads(json_data.function.arguments),
            )
            tool_actions.append(tool_action)

    # also handle the case where we're using a reasoning model and the tool calls are in the content
    if response.choices[0].message.content:
        content = response.choices[0].message.content

        # extract the JSON content from the markdown
        json_content = extract_json_from_markdown(content)

        if json_content:
            # clean the JSON content
            json_content = clean_json_content(json_content)
            # parse the JSON content
            try:
                json_data = json.loads(json_content)

                # check if the JSON content has the required fields
                if "tool_calls" in json_data:
                    # iterate over the tool calls
                    for tool_call in json_data["tool_calls"]:
                        # check if the tool call has the required fields
                        if (
                            "id" in tool_call
                            and "function" in tool_call
                            and "name" in tool_call["function"]
                            and "arguments" in tool_call["function"]
                        ):
                            # create a ToolAction object from the tool call
                            tool_action = ToolAction(
                                id=tool_call["id"],
                                name=tool_call["function"]["name"],
                                arguments=tool_call["function"]["arguments"],
                            )
                            # add the tool action to the list
                            tool_actions.append(tool_action)

            except json.JSONDecodeError:
                logger.debug(f"Failed to parse JSON content: {json_content}")
            except Exception as e:
                logger.debug(f"Failed to extract tool calls from content: {content}. Error: {e}")

    # return the list of tool calls
    return tool_actions


def convert_mcp_tools_to_openai_tools(mcp_tools: List[Tool]) -> List[ChatCompletionToolParam]:
    tools_list: List[ChatCompletionToolParam] = []
    for mcp_tool in mcp_tools:
        # add parameter for explaining the step for the user observing the assistant
        aiContext: dict[str, Any] = {
            "type": "string",
            "description": (
                "Explanation of why the AI is using this tool and what it expects to accomplish."
                "This message is displayed to the user, coming from the point of view of the assistant"
                " and should fit within the flow of the ongoing conversation, responding to the"
                " preceding user message."
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


def inject_tools_into_system_message(
    chat_message_params: List[ChatCompletionMessageParam],
    tools: List[ChatCompletionToolParam],
) -> List[ChatCompletionMessageParam]:
    """
    Inject tools into the system message.

    This function takes a list of chat message parameters and a list of tools, and injects the tools into the
    system message. The system message is updated to include the tool descriptions and instructions for using
    the tools.

    Args:
        chat_message_params (List[ChatCompletionMessageParam]): The list of chat message parameters.
        tools (List[ChatCompletionToolParam]): The list of tools.

    Returns:
        List[ChatCompletionMessageParam]: The updated list of chat message parameters with the tools injected.
    """
    # assume the first message is the system message
    # TODO: decide if we need something more robust here
    first_system_message_index = 0

    # get the system message
    first_system_message_content = chat_message_params[first_system_message_index].get("content", "")

    # append the tools list and descriptions to the system message
    tools_prompt = create_tool_descriptions(tools)

    # update the system message content to include the tools prompt
    chat_message_params[first_system_message_index]["content"] = f"{first_system_message_content}\n\n{tools_prompt}"

    return chat_message_params


def create_tool_descriptions(tools: List[ChatCompletionToolParam]) -> str:
    descriptions = ""
    for tool in tools:
        function: FunctionDefinition = tool.get("function")
        descriptions += (
            f"Tool Name: {function.get('name')}\n"
            f"Description: {function.get('description')}\n"
            f"Input Parameters: {json.dumps(function.get('parameters'))}\n\n"
        )
    return dedent(f"""
    You can perform specific tasks using available tools. When you need to use a tool, respond
    with a strict JSON object containing only the tool's `id` and function name and arguments.

    Available Tools:
    {descriptions}

    ### Instructions:
    - If you need to use a tool to answer the user's query, respond with **ONLY** a JSON object in the following format:
    {{
        "tool_calls": [
            {{
                "id": "tool_id",
                "function": {{
                    "name": "tool_name",
                    "arguments": {{
                        "parameter1": "value1",
                        ...
                    }}
                }}
            }}
        ]
    }}
    - If you can answer without using a tool, provide the answer directly.
    - Ensure the JSON is properly formatted, using the exact format shown above.
    - **No code, no text, no markdown** within the JSON.
    - Ensure that all values are plain data types (e.g., strings, numbers).
    - **Do not** include any additional characters, functions, or expressions within the JSON.
    """)


def extract_json_from_markdown(content: str) -> Optional[str]:
    """
    Extracts JSON content from a markdown code block.

    Args:
        content (str): The content containing the markdown code block.

    Returns:
        [Optional] The extracted JSON string if successful, else None.
    """
    # Define a regex pattern to match ```json ... ```
    pattern = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
    match = pattern.search(content)

    if match:
        json_content = match.group(1)
        return json_content
    else:
        return None
