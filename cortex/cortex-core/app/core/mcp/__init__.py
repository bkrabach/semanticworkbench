from app.core.mcp.client import MCPClient
from app.core.mcp.decorators import resource, tool
from app.core.mcp.exceptions import (
    MCPError,
    ResourceAccessError,
    ResourceNotFoundError,
    ServiceInitializationError,
    ServiceNotFoundError,
    ToolExecutionError,
    ToolNotFoundError,
    TransportError,
    ValidationError,
)
from app.core.mcp.in_process_client import InProcessMCPClient
from app.core.mcp.registry import registry

__all__ = [
    "MCPClient",
    "InProcessMCPClient",
    "registry",
    "tool",
    "resource",
    "MCPError",
    "ServiceNotFoundError",
    "ToolNotFoundError",
    "ResourceNotFoundError",
    "ToolExecutionError",
    "ResourceAccessError",
    "ValidationError",
    "ServiceInitializationError",
    "TransportError",
]


# Create default client instance
default_client = InProcessMCPClient()


def get_client() -> MCPClient:
    """Get the default MCP client instance.

    Returns:
        Default MCP client
    """
    return default_client
