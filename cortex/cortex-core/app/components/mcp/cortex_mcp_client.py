"""
Cortex MCP Client implementation.

This module provides the actual implementation for connecting to Domain Expert services
via the Model Context Protocol (MCP) using the official MCP Python SDK.
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional, TypeVar, Union

from app.utils.logger import logger
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.types import BlobResourceContents, InitializeResult, TextResourceContents
from pydantic import AnyUrl

logger = logger.getChild("mcp_client")


class ConnectionState:
    """Connection state tracking for MCP client"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


T = TypeVar("T")


class CortexMcpClient:
    """
    MCP client implementation using the official Python SDK.

    This class manages the lifecycle of a connection to an MCP server endpoint,
    providing tools for connection management, health monitoring, and error handling.

    Key features:
    - Explicit connection lifecycle management
    - Automatic reconnection with exponential backoff
    - Connection health monitoring
    - State tracking and observability
    - Proper async resource management via context manager support
    """

    def __init__(self, endpoint: str, service_name: str):
        self.endpoint = endpoint
        self.service_name = service_name
        self.client: Optional[ClientSession] = None
        self._sse_context = None
        self._read_stream = None
        self._write_stream = None
        self._state = ConnectionState.DISCONNECTED
        self._last_error: Optional[Exception] = None
        self._last_connect_time = 0
        self._connect_attempts = 0
        self._server_info: Optional[InitializeResult] = None
        self._health_check_task: Optional[asyncio.Task] = None

    @property
    def state(self) -> str:
        """Get the current connection state"""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if the client is currently connected"""
        return self._state == ConnectionState.CONNECTED

    @property
    def last_error(self) -> Optional[Exception]:
        """Get the last error that occurred during connection"""
        return self._last_error

    @property
    def server_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the connected server"""
        if self._server_info:
            return self._server_info.model_dump()
        return None

    async def __aenter__(self):
        """Async context manager entry point"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit point"""
        await self.close()

    async def connect(self) -> None:
        """Connect to the MCP server"""
        # If already in connecting state, wait for it to complete
        if self._state == ConnectionState.CONNECTING:
            # Wait for connection to complete with timeout
            for _ in range(30):  # 3 second timeout
                if self._state != ConnectionState.CONNECTING:
                    break
                await asyncio.sleep(0.1)
            else:
                raise TimeoutError(f"Connection attempt to {self.service_name} timed out")

            # If now connected, return
            if self._state == ConnectionState.CONNECTED:
                return

        # If already connected, just return
        if self._state == ConnectionState.CONNECTED and self.client is not None:
            return

        # Set state to connecting
        prev_state = self._state
        self._state = ConnectionState.CONNECTING
        self._connect_attempts += 1

        try:
            logger.info(f"Connecting to MCP endpoint: {self.service_name} at {self.endpoint}")

            # Implement exponential backoff for reconnection attempts
            if prev_state == ConnectionState.RECONNECTING and self._connect_attempts > 1:
                # Calculate backoff time: min(2^n * 100ms, 30s)
                backoff = min(pow(2, min(self._connect_attempts - 1, 8)) * 0.1, 30)
                logger.info(
                    f"Reconnection attempt {self._connect_attempts} for {self.service_name}, waiting {backoff:.1f}s"
                )
                await asyncio.sleep(backoff)

            # Create an SSE client connection to the MCP server
            self._sse_context = sse_client(self.endpoint)
            self._read_stream, self._write_stream = await self._sse_context.__aenter__()

            # Create and initialize the client session
            self.client = ClientSession(self._read_stream, self._write_stream)
            self._server_info = await self.client.initialize()

            # Connection successful
            self._state = ConnectionState.CONNECTED
            self._last_connect_time = time.time()
            self._last_error = None
            self._connect_attempts = 0

            logger.info(f"Connected to MCP endpoint: {self.service_name}")
            logger.debug(f"MCP server info: {json.dumps(self._server_info.model_dump())}")

            # Start health check if not already running
            self._start_health_check()

        except Exception as e:
            self._state = ConnectionState.ERROR
            self._last_error = e
            logger.error(f"Failed to connect to MCP endpoint {self.service_name}: {str(e)}")
            await self._cleanup_resources()  # Clean up any partially opened resources
            raise

    async def _cleanup_resources(self) -> None:
        """Clean up resources without changing state"""
        try:
            # Clean up client
            self.client = None

            # Properly exit the SSE context manager
            if self._sse_context:
                await self._sse_context.__aexit__(None, None, None)
                self._sse_context = None
                self._read_stream = None
                self._write_stream = None
        except Exception as e:
            logger.error(f"Error cleaning up MCP resources for {self.service_name}: {str(e)}")
            # Set to None anyway to avoid keeping potentially broken connections
            self.client = None
            self._sse_context = None
            self._read_stream = None
            self._write_stream = None

    async def close(self) -> None:
        """Close the MCP client and clean up resources"""
        # Cancel health check task if running
        if self._health_check_task:
            self._health_check_task.cancel()

            # Only attempt to await the task if it's not a mock (for testing)
            if not hasattr(self._health_check_task, "mock_calls"):
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass

            self._health_check_task = None

        # Clean up resources
        prev_state = self._state
        self._state = ConnectionState.DISCONNECTED
        await self._cleanup_resources()

        # Only log if we were actually connected
        if prev_state in (ConnectionState.CONNECTED, ConnectionState.RECONNECTING):
            logger.info(f"Closed connection to MCP endpoint: {self.service_name}")

    def _start_health_check(self) -> None:
        """Start periodic health check for the connection"""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _health_check_loop(self) -> None:
        """Periodically check connection health"""
        try:
            while True:
                await asyncio.sleep(30)  # Check every 30 seconds
                if not self.is_connected:
                    logger.debug(f"Health check skipped for {self.service_name}: Not connected")
                    continue

                try:
                    # Use echo to check connection
                    if self.client:
                        # Some MCP servers may not implement echo, so we use a simple tool list
                        # which all MCP servers must implement
                        await self.client.list_tools()
                        logger.debug(f"Health check passed for {self.service_name}")
                except Exception as e:
                    logger.warning(f"Health check failed for {self.service_name}: {str(e)}")
                    # Connection failed, attempt reconnection
                    self._state = ConnectionState.RECONNECTING
                    try:
                        await self._cleanup_resources()
                        await self.connect()
                    except Exception as reconnect_err:
                        logger.error(f"Reconnection failed for {self.service_name}: {str(reconnect_err)}")
        except asyncio.CancelledError:
            logger.debug(f"Health check loop cancelled for {self.service_name}")
        except Exception as e:
            logger.error(f"Error in health check loop for {self.service_name}: {str(e)}")

    async def _ensure_connected(self) -> None:
        """Ensure the client is connected before operations"""
        if not self.is_connected or self.client is None:
            await self.connect()

    async def list_tools(self) -> Dict[str, Any]:
        """List available tools from the MCP server"""
        await self._ensure_connected()

        # At this point, self.client should be initialized
        assert self.client is not None
        result = await self.client.list_tools()

        # Convert the result to a dict if needed
        return self._normalize_result(result)

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        await self._ensure_connected()

        assert self.client is not None
        result = await self.client.call_tool(name=name, arguments=arguments)

        # Convert the result to a dict if needed
        return self._normalize_result(result)

    async def read_resource(self, uri: Union[str, AnyUrl]) -> Dict[str, Any]:
        """Read a resource from the MCP server"""
        await self._ensure_connected()

        assert self.client is not None

        try:
            # Convert string to AnyUrl if needed before passing to MCP client
            uri_param = uri if isinstance(uri, AnyUrl) else AnyUrl(uri)
            
            # The MCP SDK returns a ReadResourceResult with a contents field
            result = await self.client.read_resource(uri=uri_param)

            # Extract the first content item (if any)
            if result.contents and len(result.contents) > 0:
                content_item = result.contents[0]

                # Get content based on type
                if isinstance(content_item, TextResourceContents):
                    content = content_item.text
                elif isinstance(content_item, BlobResourceContents):
                    content = content_item.blob
                else:
                    content = ""

                # Get mime type
                mime_type = content_item.mimeType if hasattr(content_item, "mimeType") else "text/plain"
            else:
                content = ""
                mime_type = "text/plain"

            # Get mime type as string for proper checking
            mime_type_str = str(mime_type)

            # Convert to Cortex's expected format
            return {
                "content": [
                    {
                        "type": "text" if mime_type_str.startswith("text/") else "data",
                        "text": content if isinstance(content, str) else None,
                        "data": content if not isinstance(content, str) else None,
                        "mimeType": mime_type_str,
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error reading resource {uri} from {self.service_name}: {str(e)}")
            raise

    def _normalize_result(self, result: Any) -> Dict[str, Any]:
        """
        Convert various result types to a dictionary.

        Handles different return types from MCP operations:
        - Dictionaries are returned as is
        - Pydantic models are converted using model_dump()
        - Lists are wrapped in a dict with an 'items' key
        - Other types are converted to dicts or wrapped in a 'value' key
        """
        # If the result is None, return an empty dict
        if result is None:
            return {}

        # If the result is already a dict, return it directly
        if isinstance(result, dict):
            return result

        # If it has model_dump method, use it (Pydantic model)
        if hasattr(result, "model_dump"):
            return result.model_dump()

        # If it's a list, convert each item then return as a dict with 'items' key
        if isinstance(result, list):
            return {"items": [self._normalize_item(item) for item in result]}

        # Otherwise, convert to a dict by assuming it has a dict-like interface
        try:
            return dict(result)
        except (TypeError, ValueError):
            # If all else fails, wrap the raw value
            return {"value": result}

    def _normalize_item(self, item: Any) -> Any:
        """Normalize a single item that might be nested in a collection"""
        if isinstance(item, dict):
            return item
        if hasattr(item, "model_dump"):
            return item.model_dump()
        if isinstance(item, (list, tuple)):
            return [self._normalize_item(subitem) for subitem in item]
        # For primitive types, return as is
        return item
