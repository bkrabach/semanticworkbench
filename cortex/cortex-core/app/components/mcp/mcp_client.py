"""
MCP Client implementation for Cortex platform.

This module provides a simplified implementation of the Model Context Protocol client
for interacting with domain experts and other MCP-enabled services.
"""

import json
import uuid
import asyncio
from typing import Dict, Any, Optional
import httpx

from app.config import settings
from app.interfaces.mcp_client import McpClientInterface
from app.utils.logger import get_logger

logger = get_logger(__name__)


class McpClient(McpClientInterface):
    """
    Implementation of the MCP Client interface.
    
    Provides a simplified client for communicating with MCP servers and executing
    tools through the MCP protocol. Follows the implementation philosophy of
    ruthless simplicity while maintaining the core architectural pattern.
    """
    
    def __init__(self, endpoint: str, service_name: str):
        """
        Initialize the MCP client.
        
        Args:
            endpoint: The MCP server endpoint URL
            service_name: The name of the service this client is connecting to
        """
        self.endpoint = endpoint
        self.service_name = service_name
        self.client: Optional[httpx.AsyncClient] = None
        self._tools_cache: Optional[Dict[str, Any]] = None
        self._is_connected = False
        self._connection_lock = asyncio.Lock()
        logger.info(f"Initialized MCP client for {service_name} at {endpoint}")
    
    async def connect(self) -> None:
        """
        Connect to the MCP server.
        
        Raises:
            ConnectionError: If the connection fails
        """
        async with self._connection_lock:
            if self._is_connected:
                logger.debug(f"MCP client for {self.service_name} already connected")
                return
                
            try:
                if self.client is None:
                    self.client = httpx.AsyncClient(
                        base_url=self.endpoint,
                        timeout=30.0,  # 30 seconds timeout
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                            "X-Client-Id": str(uuid.uuid4()),
                        }
                    )
                
                # Test connection with a ping
                response = await self.client.get("/status")
                if response.status_code != 200:
                    raise ConnectionError(f"Failed to connect to MCP server: {response.text}")
                
                self._is_connected = True
                logger.info(f"Successfully connected to MCP server for {self.service_name}")
                
            except httpx.RequestError as e:
                logger.error(f"Error connecting to MCP server: {str(e)}")
                if self.client:
                    await self.client.aclose()
                    self.client = None
                self._is_connected = False
                raise ConnectionError(f"Failed to connect to MCP server: {str(e)}")
    
    async def close(self) -> None:
        """Close the MCP connection."""
        async with self._connection_lock:
            if self.client:
                await self.client.aclose()
                self.client = None
            self._is_connected = False
            logger.info(f"Closed MCP connection for {self.service_name}")
    
    async def list_tools(self) -> Dict[str, Any]:
        """
        List the available tools from the MCP server.
        
        Returns:
            A dictionary containing tool information
            
        Raises:
            ConnectionError: If the client is not connected
            TimeoutError: If the operation times out
        """
        if self._tools_cache is not None:
            return self._tools_cache
            
        await self._ensure_connected()
        
        try:
            # Ensure client is not None
            if self.client is None:
                raise ConnectionError("Client is not initialized")
                
            response = await self.client.get("/tools")
            if response.status_code != 200:
                raise ConnectionError(f"Failed to list tools: {response.text}")
                
            tools_data = response.json()
            self._tools_cache = tools_data
            return dict(tools_data)
            
        except httpx.TimeoutException as e:
            logger.error(f"Timeout listing tools: {str(e)}")
            raise TimeoutError(f"Timeout listing tools: {str(e)}")
        except httpx.RequestError as e:
            logger.error(f"Error listing tools: {str(e)}")
            self._is_connected = False
            raise ConnectionError(f"Error listing tools: {str(e)}")
    
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
        await self._ensure_connected()
        
        try:
            # Ensure client is not None
            if self.client is None:
                raise ConnectionError("Client is not initialized")
                
            logger.debug(f"Calling tool '{name}' with arguments: {json.dumps(arguments)[:100]}...")
            
            response = await self.client.post(
                f"/tools/{name}",
                json=arguments
            )
            
            if response.status_code == 404:
                raise ValueError(f"Tool '{name}' not found")
            elif response.status_code == 400:
                raise ValueError(f"Invalid arguments for tool '{name}': {response.text}")
            elif response.status_code != 200:
                raise ConnectionError(f"Error calling tool '{name}': {response.text}")
                
            result = response.json()
            return dict(result)
            
        except httpx.TimeoutException as e:
            logger.error(f"Timeout calling tool '{name}': {str(e)}")
            raise TimeoutError(f"Timeout calling tool '{name}': {str(e)}")
        except httpx.RequestError as e:
            logger.error(f"Error calling tool '{name}': {str(e)}")
            self._is_connected = False
            raise ConnectionError(f"Error calling tool '{name}': {str(e)}")
    
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
        await self._ensure_connected()
        
        try:
            # Ensure client is not None
            if self.client is None:
                raise ConnectionError("Client is not initialized")
                
            logger.debug(f"Reading resource '{uri}'")
            
            response = await self.client.get(f"/resources?uri={uri}")
            
            if response.status_code == 404:
                raise ValueError(f"Resource '{uri}' not found")
            elif response.status_code != 200:
                raise ConnectionError(f"Error reading resource '{uri}': {response.text}")
                
            result = response.json()
            return dict(result)
            
        except httpx.TimeoutException as e:
            logger.error(f"Timeout reading resource '{uri}': {str(e)}")
            raise TimeoutError(f"Timeout reading resource '{uri}': {str(e)}")
        except httpx.RequestError as e:
            logger.error(f"Error reading resource '{uri}': {str(e)}")
            self._is_connected = False
            raise ConnectionError(f"Error reading resource '{uri}': {str(e)}")
    
    @property
    def is_connected(self) -> bool:
        """
        Check if the client is currently connected.
        
        Returns:
            True if connected, False otherwise
        """
        return self._is_connected
    
    async def _ensure_connected(self) -> None:
        """
        Ensure the client is connected, connecting if necessary.
        
        Raises:
            ConnectionError: If the connection fails
        """
        if not self._is_connected:
            await self.connect()


# Global client instances
_mcp_clients: Dict[str, McpClient] = {}


def get_mcp_client(service_name: str = "default") -> McpClient:
    """
    Get a singleton MCP client instance for a specific service.
    
    Args:
        service_name: The name of the service to get a client for
        
    Returns:
        The MCP client instance
    """
    global _mcp_clients
    
    if service_name not in _mcp_clients:
        endpoint = settings.MCP_ENDPOINT
        if service_name != "default":
            # For specific services, we might have dedicated endpoints
            endpoint_setting = f"MCP_{service_name.upper()}_ENDPOINT"
            if hasattr(settings, endpoint_setting):
                endpoint = getattr(settings, endpoint_setting)
        
        _mcp_clients[service_name] = McpClient(endpoint, service_name)
    
    return _mcp_clients[service_name]