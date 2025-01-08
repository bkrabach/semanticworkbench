# utils/tool_utils.py
import logging
from typing import Any, List

import deepmerge
from assistant_extensions.ai_clients.model import CompletionMessage
from attr import dataclass
from semantic_workbench_api_model.workbench_model import (
    MessageType,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolActionsResult:
    content: str
    message_type: MessageType
    completion_total_tokens: int
    metadata: dict[str, Any]


async def retrieve_tools_from_sessions(sessions: List[Any]) -> List[Any]:
    """
    Retrieve tools from all MCP sessions.
    """
    all_tools = []
    for session in sessions:
        try:
            tools_response = await session.list_tools()
            tools = tools_response.tools
            all_tools.extend(tools)
            logger.debug(f"Retrieved tools from session: {[tool.name for tool in tools]}")
        except Exception as e:
            logger.exception(f"Error retrieving tools from session: {e}")
    return all_tools


async def handle_tool_action(
    sessions: List[Any],
    tool_action: dict,
    all_tools: List[Any],
    context,
    completion_messages: List[CompletionMessage],
    response_provider,
    metadata: dict[str, Any],
    method_metadata_key: str,
) -> ToolActionsResult:
    """
    Handle the tool action specified by the AI assistant.
    """
    tool_name = tool_action.get("tool_name")
    arguments = tool_action.get("arguments", {})

    if not tool_name:
        raise ValueError("The tool action JSON object must contain a 'tool_name' key.")

    target_session = next((s for s in sessions if tool_name in [tool.name for tool in all_tools]), None)

    if not target_session:
        raise ValueError(f"Tool '{tool_name}' not found in any of the sessions.")

    # Update metadata with tool action details
    deepmerge.always_merger.merge(
        metadata,
        {
            method_metadata_key: {
                "tool_action": {
                    "tool_name": tool_name,
                    "arguments": arguments,
                },
            },
        },
    )

    try:
        tool_result = await target_session.call_tool(tool_name, arguments=arguments)
        tool_output = tool_result.content[0] if tool_result.content else ""
    except Exception as e:
        logger.exception(f"Error executing tool '{tool_name}': {e}")
        tool_output = f"An error occurred while executing the tool '{tool_name}': {e}"

    # Update metadata with tool result
    deepmerge.always_merger.merge(
        metadata,
        {
            method_metadata_key: {
                "tool_result": tool_output,
            },
        },
    )

    # Add tool output to the conversation
    completion_messages.append(
        CompletionMessage(
            role="user",
            content=f"Tool '{tool_name}' output:\n{tool_output}",
        )
    )

    # Generate the final response incorporating the tool output
    try:
        final_response = await response_provider.get_response(
            messages=completion_messages,
            metadata_key=method_metadata_key + "_after_tool",
        )

        content = final_response.content
        message_type = final_response.message_type
        completion_total_tokens = final_response.completion_total_tokens
    except Exception as e:
        raise ValueError(f"Error generating response after tool execution: {e}")

    deepmerge.always_merger.merge(metadata, final_response.metadata)

    return ToolActionsResult(
        content=content,
        message_type=message_type,
        completion_total_tokens=completion_total_tokens,
        metadata=metadata,
    )
