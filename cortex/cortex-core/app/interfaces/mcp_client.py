"""
MCP Client Interface for Cortex Core.

This module defines the interface for the Model Context Protocol (MCP) client,
which is used to communicate with domain experts and other MCP-enabled services.
"""

from typing import Dict, Any, List, Optional, Protocol
from uuid import UUID


class McpClientInterface(Protocol):
    """
    Interface for MCP client operations.
    
    The MCP client is responsible for connecting to MCP servers (domain experts
    and other services) and interacting with them through the standard MCP protocol.
    """
    
    async def connect(self) -> None:
        """
        Connect to the MCP server.
        
        Raises:
            ConnectionError: If the connection fails
        """
        ...
    
    async def close(self) -> None:
        """
        Close the MCP connection.
        """
        ...
    
    async def list_tools(self) -> Dict[str, Any]:
        """
        List the available tools from the MCP server.
        
        Returns:
            A dictionary containing tool information
            
        Raises:
            ConnectionError: If the client is not connected
            TimeoutError: If the operation times out
        """
        ...
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.
        
        Args:
            name: The name of the tool to call
            arguments: The arguments to pass to the tool
            
        Returns:
            The result of the tool execution
            
        Raises:
            ConnectionError: If the client is not connected
            ValueError: If the tool doesn't exist or the arguments are invalid
            TimeoutError: If the operation times out
        """
        ...
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a resource from the MCP server.
        
        Args:
            uri: The URI of the resource to read
            
        Returns:
            The resource content and metadata
            
        Raises:
            ConnectionError: If the client is not connected
            ValueError: If the resource doesn't exist
            TimeoutError: If the operation times out
        """
        ...
    
    @property
    def is_connected(self) -> bool:
        """
        Check if the client is currently connected.
        
        Returns:
            True if connected, False otherwise
        """
        ...