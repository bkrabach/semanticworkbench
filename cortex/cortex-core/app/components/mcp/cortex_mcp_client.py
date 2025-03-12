"""
Cortex MCP Client implementation.

This module provides the actual implementation for connecting to Domain Expert services
via the Model Context Protocol (MCP) using the official MCP Python SDK.
"""

from typing import Dict, Any, Optional
import json

from pydantic import AnyUrl
from app.utils.logger import logger
from mcp.client.session import ClientSession
from mcp.types import TextResourceContents, BlobResourceContents
from mcp.client.sse import sse_client


logger = logger.getChild("mcp_client")


class CortexMcpClient:
    """MCP client implementation using the official Python SDK"""

    def __init__(self, endpoint: str, service_name: str):
        self.endpoint = endpoint
        self.service_name = service_name
        self.client: Optional[ClientSession] = None
        self._read_stream = None
        self._write_stream = None

    async def connect(self) -> None:
        """Connect to the MCP server"""
        if self.client is not None:
            # Already connected
            return

        try:
            logger.info(f"Connecting to MCP endpoint: {self.service_name} at {self.endpoint}")

            # Create an SSE client connection to the MCP server
            streams = await sse_client(self.endpoint).__aenter__()
            self._read_stream, self._write_stream = streams

            # Create and initialize the client session
            self.client = ClientSession(self._read_stream, self._write_stream)
            info = await self.client.initialize()

            logger.info(f"Connected to MCP endpoint: {self.service_name}")
            logger.debug(f"MCP server info: {json.dumps(info)}")
        except Exception as e:
            logger.error(f"Failed to connect to MCP endpoint {self.service_name}: {str(e)}")
            await self.close()  # Close any partially opened resources
            raise

    async def list_tools(self) -> Dict[str, Any]:
        """List available tools from the MCP server"""
        if not self.client:
            await self.connect()

        # At this point, self.client should be initialized
        assert self.client is not None
        result = await self.client.list_tools()

        # Convert the result to a dict if needed
        return self._normalize_result(result)

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        if not self.client:
            await self.connect()

        assert self.client is not None
        result = await self.client.call_tool(name=name, arguments=arguments)

        # Convert the result to a dict if needed
        return self._normalize_result(result)

    async def read_resource(self, uri: AnyUrl) -> Dict[str, Any]:
        """Read a resource from the MCP server"""
        if not self.client:
            await self.connect()

        assert self.client is not None

        try:
            # The MCP SDK returns a ReadResourceResult with a contents field
            result = await self.client.read_resource(uri=uri)

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
                        "mimeType": mime_type_str
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error reading resource {uri} from {self.service_name}: {str(e)}")
            raise

    async def close(self) -> None:
        """Close the MCP client and clean up resources"""
        try:
            # Close resources in reverse order of creation
            if self.client:
                # Client will be set to None to indicate we're no longer connected
                self.client = None

            # Close the streams if they were created
            if self._read_stream and self._write_stream:
                # Since we're using the context manager, we need to exit it properly
                # This is normally handled by the context manager itself, but we need to do it manually
                # because we're using the streams directly
                await self._read_stream.aclose()
                await self._write_stream.aclose()
                self._read_stream = None
                self._write_stream = None

            logger.info(f"Closed connection to MCP endpoint: {self.service_name}")
        except Exception as e:
            logger.error(f"Error during MCP client shutdown: {str(e)}")
            # Set to None anyway to avoid keeping potentially broken connections
            self.client = None
            self._read_stream = None
            self._write_stream = None

    def _normalize_result(self, result: Any) -> Dict[str, Any]:
        """Convert various result types to a dictionary"""
        # If the result is already a dict, return it directly
        if isinstance(result, dict):
            return result

        # If it has model_dump method, use it (Pydantic model)
        if hasattr(result, "model_dump"):
            return result.model_dump()

        # Otherwise, convert to a dict by assuming it has a dict-like interface
        return dict(result)