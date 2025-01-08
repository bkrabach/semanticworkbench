import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, List, Optional

# Import the relevant classes and functions
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPServer:
    def __init__(self, name: str, command: str, args: List[str], env: Optional[dict] = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env


# Setup logger
logger = logging.getLogger(__name__)

# Define the list of MCP servers with parameters
mcp_servers = [
    # MCPServer(
    #     name='Filesystem MCP Server',
    #     command='npx',
    #     args=['-y', '@modelcontextprotocol/server-filesystem', '/workspaces/semanticworkbench']
    # ),
    MCPServer(
        name="Filesystem MCP Server",
        command="node",
        args=["vendor/mcp-servers/src/filesystem/dist/index.js", "/workspaces/semanticworkbench"],
    ),
    MCPServer(name="Web Research MCP Server", command="npx", args=["-y", "@mzxrai/mcp-webresearch@latest"]),
]


# Refactor to iterate through the list of servers
@asynccontextmanager
async def connect_to_mcp_servers() -> AsyncIterator:
    sessions = {}
    try:
        for server in mcp_servers:
            server_params = StdioServerParameters(command=server.command, args=server.args, env=server.env)
            try:
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        sessions[server.name] = session
            except Exception as e:
                logger.exception(f"Error connecting to {server.name}: {e}")
                sessions[server.name] = None
        yield sessions
    finally:
        # Ensure any final cleanup if needed
        pass
