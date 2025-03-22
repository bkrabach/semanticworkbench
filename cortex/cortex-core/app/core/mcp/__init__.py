from app.core.mcp.client import MCPClient
from app.core.mcp.in_process_client import InProcessMCPClient
from app.core.mcp.registry import registry
from app.core.mcp.decorators import tool, resource
from app.core.mcp.exceptions import (
    MCPError, 
    ServiceNotFoundError, 
    ToolNotFoundError, 
    ResourceNotFoundError,
    ToolExecutionError,
    ResourceAccessError,
    ValidationError,
    ServiceInitializationError,
    TransportError
)


__all__ = [
    'MCPClient',
    'InProcessMCPClient',
    'registry',
    'tool',
    'resource',
    'MCPError',
    'ServiceNotFoundError',
    'ToolNotFoundError',
    'ResourceNotFoundError',
    'ToolExecutionError',
    'ResourceAccessError',
    'ValidationError',
    'ServiceInitializationError',
    'TransportError'
]


# Create default client instance
default_client = InProcessMCPClient()


def get_client() -> MCPClient:
    """Get the default MCP client instance.
    
    Returns:
        Default MCP client
    """
    return default_client