"""
Cognition Service - Memory Client

Provides client functionality to interact with the Memory Service for retrieving
and storing conversation history.
"""

import logging
from datetime import datetime
from typing import Any, List, Optional

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

from .models import Message, MessageRole

# Configure logging
logger = logging.getLogger(__name__)


class MemoryServiceError(Exception):
    """Exception raised when there is an error with the Memory Service."""

    pass


class MemoryClient:
    """Client for interacting with the Memory Service."""

    def __init__(self, service_url: str):
        """Initialize the Memory Service client.

        Args:
            service_url: Base URL of the Memory Service
        """
        self.service_url = service_url
        self.session: Optional[ClientSession] = None
        self.streams_context: Any = None  # Type will be context manager from sse_client
        logger.info(f"Initialized Memory Client with URL: {service_url}")

    async def connect(self) -> bool:
        """Establish connection to the Memory Service.

        Returns:
            True if successful, False otherwise
        """
        if self.session is not None:
            return True  # Already connected

        try:
            # Create SSE client context
            self.streams_context = sse_client(url=self.service_url)
            # Open the SSE connection and get the streams
            read_stream, write_stream = await self.streams_context.__aenter__()

            # Create a client session using the streams
            session_context = ClientSession(read_stream, write_stream)
            self.session = await session_context.__aenter__()

            # Perform MCP initialization handshake
            await self.session.initialize()

            logger.info(f"Connected to memory service at {self.service_url}")
            return True
        except Exception as e:
            self.session = None
            self.streams_context = None
            logger.error(f"Failed to connect to memory service: {str(e)}")
            return False

    async def ensure_connected(self) -> None:
        """Ensure that the client is connected to the service.

        Raises:
            MemoryServiceError: If the connection cannot be established
        """
        if self.session is not None:
            return

        success = await self.connect()
        if not success:
            raise MemoryServiceError("Failed to connect to Memory Service")

    async def get_conversation_history(self, conversation_id: str) -> List[Message]:
        """Retrieve conversation history from the Memory Service.

        Args:
            conversation_id: ID of the conversation to retrieve

        Returns:
            List of Message objects representing the conversation history

        Raises:
            MemoryServiceError: If an error occurs during retrieval
        """
        try:
            await self.ensure_connected()

            # Define the method and parameters
            method = "get_conversation_history"
            params = {"conversation_id": conversation_id}

            # Call the tool
            assert self.session is not None
            response = await self.session.call_tool(method, params)

            if not response:
                logger.warning(f"Empty response from memory service for conversation {conversation_id}")
                return []

            # Extract messages from response
            extra_data = getattr(response, "model_extra", {})
            messages_data = extra_data.get("messages", [])

            # Parse messages
            messages = []
            for msg_data in messages_data:
                try:
                    messages.append(
                        Message(
                            role=MessageRole(msg_data.get("role", "user")),
                            content=msg_data.get("content", ""),
                            timestamp=msg_data.get("timestamp", datetime.utcnow()),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing message: {e}")

            logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
            return messages

        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            raise MemoryServiceError(f"Error retrieving conversation history: {e}")

    async def close(self) -> None:
        """Close the MCP connection."""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
                self.session = None
            except Exception as e:
                logger.error(f"Error closing memory service session: {e}")

        if self.streams_context:
            try:
                await self.streams_context.__aexit__(None, None, None)
                self.streams_context = None
            except Exception as e:
                logger.error(f"Error closing memory service streams: {e}")

        logger.info("Memory client connection closed")
