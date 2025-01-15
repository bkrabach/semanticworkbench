import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, List, Optional

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger(__name__)


class MCPServer:
    """Represents an MCP server with its connection parameters."""

    def __init__(self, name: str, command: str, args: List[str], env: Optional[dict] = None) -> None:
        self.name = name
        self.command = command
        self.args = args
        self.env = env


@asynccontextmanager
async def connect_to_mcp_server(server_config) -> AsyncIterator[Optional[ClientSession]]:
    """Connect to a single MCP server defined in the config."""
    server = MCPServer(
        name=server_config.get("name"),
        command=server_config.get("command"),
        args=server_config.get("args", []),
        env=server_config.get("env", None),  # Use None to inherit environment variables
    )
    server_params = StdioServerParameters(command=server.command, args=server.args, env=server.env)
    try:
        logger.debug(f"Attempting to connect to {server.name} with command: {server.command} {' '.join(server.args)}")
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session  # Yield the session for use
    except Exception as e:
        logger.exception(f"Error connecting to {server.name}: {e}")
        yield None  # Yield None if connection fails


def load_server_configs(config_file: str) -> List[dict[str, Any]]:
    """
    Load server configurations from a JSON file.
    """
    if os.path.exists(config_file):
        with open(config_file, "r") as config_data:
            server_configs = json.load(config_data)
        logger.debug(f"Loaded server configurations from {config_file}")
        return server_configs
    else:
        logger.error(f"Configuration file {config_file} not found.")
        return []


async def establish_mcp_sessions(config_file: str, stack) -> List[ClientSession]:
    """
    Establish connections to MCP servers using the provided AsyncExitStack.
    """

    server_configs = load_server_configs(config_file)

    sessions: List[ClientSession] = []
    for server_config in server_configs:
        session: ClientSession | None = await stack.enter_async_context(connect_to_mcp_server(server_config))
        if session:
            sessions.append(session)
        else:
            logger.warning(f"Could not establish session with {server_config.get('name')}")
    return sessions
