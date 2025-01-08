import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger(__name__)


class MCPServer:
    """Represents an MCP server with its connection parameters."""

    def __init__(self, name: str, command: str, args: List[str], env: Optional[dict] = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env


@asynccontextmanager
async def connect_to_mcp_server(server_config):
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
