# utils/tool_utils.py
import json
import logging
from typing import Any, List

import deepmerge
from attr import dataclass
from mcp import ClientSession, Tool
from mcp.types import TextContent
from semantic_workbench_api_model.workbench_model import (
    MessageType,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolAction:
    id: str
    name: str
    arguments: dict[str, Any]

    def to_json(self, **kwargs) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, **kwargs)


@dataclass
class ToolActionResult:
    id: str
    content: str
    message_type: MessageType
    metadata: dict[str, Any]


async def retrieve_tools_from_sessions(sessions: List[ClientSession]) -> List[Tool]:
    """
    Retrieve tools from all MCP sessions.
    """
    all_tools: List[Tool] = []
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
    sessions: List[ClientSession],
    tool_action: ToolAction,
    all_mcp_tools: List[Tool],
    method_metadata_key: str,
) -> ToolActionResult:
    """
    Handle the tool action by invoking the appropriate tool and returning a ToolActionsResult.
    """

    metadata = {}

    tool = next((t for t in all_mcp_tools if t.name == tool_action.name), None)
    if not tool:
        return ToolActionResult(
            id=tool_action.id,
            content=f"Tool '{tool_action.name}' not found.",
            message_type=MessageType.notice,
            metadata={},
        )

    target_session = next(
        (session for session in sessions if tool_action.name in [tool.name for tool in all_mcp_tools]), None
    )

    if not target_session:
        raise ValueError(f"Tool '{tool_action.name}' not found in any of the sessions.")

    # Update metadata with tool action details
    deepmerge.always_merger.merge(
        metadata,
        {
            "debug": {
                method_metadata_key: {
                    "tool_action": tool_action.to_json(),
                },
            },
        },
    )

    # Initialize tool_result
    tool_result = None

    # Invoke the tool
    try:
        tool_result = await target_session.call_tool(tool_action.name, tool_action.arguments)
        tool_output = tool_result.content[0] if tool_result.content else ""
    except Exception as e:
        logger.exception(f"Error executing tool '{tool_action.name}': {e}")
        tool_output = f"An error occurred while executing the tool '{tool_action.to_json()}': {e}"

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

    # Return the tool action result
    content: str | None = None
    if isinstance(tool_output, str):
        content = tool_output

    if isinstance(tool_output, TextContent):
        content = tool_output.text

    # Return the tool action result
    return ToolActionResult(
        id=tool_action.id,
        content=content or "Error executing tool, unsupported output type.",
        message_type=MessageType.tool_result,
        metadata=metadata,
    )
