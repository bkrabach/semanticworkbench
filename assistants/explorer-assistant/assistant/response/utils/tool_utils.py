# utils/tool_utils.py
import logging
from typing import Any, List

import deepmerge
from attr import dataclass
from semantic_workbench_api_model.workbench_model import (
    MessageType,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolActionsResult:
    content: str
    message_type: MessageType
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
    sessions,
    tool_action,
    all_tools,
    method_metadata_key,
) -> ToolActionsResult:
    """
    Handle the tool action by invoking the appropriate tool and returning a ToolActionsResult.
    """

    metadata = {}

    tool_name = tool_action.get("tool_name")
    arguments = tool_action.get("arguments", {})

    tool = next((t for t in all_tools if t.name == tool_name), None)
    if not tool:
        return ToolActionsResult(
            content=f"Tool '{tool_name}' not found.",
            message_type=MessageType.notice,
            metadata={},
        )

    target_session = next((s for s in sessions if tool_name in [tool.name for tool in all_tools]), None)

    if not target_session:
        raise ValueError(f"Tool '{tool_name}' not found in any of the sessions.")

    # Update metadata with tool action details
    deepmerge.always_merger.merge(
        metadata,
        {
            "debug": {
                method_metadata_key: {
                    "tool_action": {
                        "tool_name": tool_name,
                        "arguments": arguments,
                    },
                },
            },
        },
    )

    # Initialize tool_result
    tool_result = None

    # Invoke the tool
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
            "debug": {
                method_metadata_key: {
                    "tool_result": tool_output,
                },
            },
        },
    )

    # Prepare the result content
    tool_message = f"Result from {tool_name}: {tool_result}"

    # Return the tool action result
    return ToolActionsResult(
        content=tool_message,
        message_type=MessageType.chat,
        metadata=metadata,
    )
