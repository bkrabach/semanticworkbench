import logging
from typing import Dict, Any, List, Optional, Tuple

from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

# Import shared exceptions
from app.backend.cognition_client import MCPConnectionError, MCPServiceError

# Set up logger for the client
logger = logging.getLogger(__name__)


class MemoryClient:
    """
    Client for the Memory Service.
    Uses MCP over SSE to store and retrieve conversation history.
    
    Provides access to conversation memory capabilities including:
    - Message storage
    - Message retrieval for context
    - Future: Advanced search and filtering
    """

    def __init__(self, service_url: str = "http://localhost:5001/sse"):
        """
        Initialize connection parameters for Memory Service.
        
        Args:
            service_url: The URL of the SSE endpoint for the Memory service
        """
        self.service_url = service_url
        self.session: Optional[ClientSession] = None
        self.streams_context: Any = None

    async def connect(self) -> Tuple[bool, Optional[str]]:
        """
        Establish MCP connection to the Memory service.
        
        Returns:
            A tuple of (success, error_message) where success is a boolean
            indicating if the connection was successful, and error_message
            is an optional string containing the error message if the connection failed.
        """
        if self.session is not None:
            return (True, None)  # Already connected

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
            return (True, None)
        except Exception as e:
            self.session = None
            self.streams_context = None
            error_msg = f"Failed to connect to memory service: {str(e)}"
            logger.error(error_msg)
            return (False, error_msg)

    async def ensure_connected(self) -> None:
        """
        Ensure that the client is connected to the service.
        
        Raises:
            MCPConnectionError: If the connection cannot be established
        """
        if self.session is not None:
            return
            
        success, error_msg = await self.connect()
        if not success:
            raise MCPConnectionError(error_msg)

    async def store_message(self, user_id: str, conversation_id: str, content: str, 
                          role: str = "user", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store a message in the memory service.
        
        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            content: The message content
            role: The role of the sender (user, assistant, system)
            metadata: Optional metadata for the message
            
        Returns:
            True if the message was stored successfully
            
        Raises:
            MCPConnectionError: If the connection cannot be established
            MCPServiceError: If there is an error calling the service
        """
        try:
            await self.ensure_connected()
                
            message_data = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "content": content,
                "role": role,
                "metadata": metadata or {},
                "timestamp": None  # Memory service will set this
            }
            
            # Call the tool - session must be non-None here after ensure_connected()
            assert self.session is not None, "Session unexpectedly None after ensure_connected"
            await self.session.call_tool("store_memory", message_data)
            return True
        except MCPConnectionError:
            # Re-raise connection errors
            raise
        except Exception as e:
            error_msg = f"Error storing message in memory: {e}"
            logger.error(error_msg)
            raise MCPServiceError(error_msg)

    async def get_recent_messages(self, user_id: str, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent messages from the memory service for context.
        
        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            limit: The maximum number of messages to retrieve
            
        Returns:
            A list of messages (most recent first)
            
        Raises:
            MCPConnectionError: If the connection cannot be established
            MCPServiceError: If there is an error calling the service
        """
        try:
            await self.ensure_connected()
                
            query = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "limit": limit
            }
            
            # Call the tool - session must be non-None here after ensure_connected()
            assert self.session is not None, "Session unexpectedly None after ensure_connected"
            response = await self.session.call_tool("retrieve_memory", query)
            
            # Extract memories from response
            # CallToolResult stores custom data in model_extra
            if response:
                # Access model_extra which contains the dynamic fields added via **extra_data
                extra_data = getattr(response, "model_extra", {})
                if extra_data and "memories" in extra_data:
                    return list(extra_data["memories"])
                    
                logger.warning(f"Unexpected response format from memory service: {extra_data}")
            
            logger.warning("Empty response received from memory service")
            return []
        except MCPConnectionError:
            # Re-raise connection errors
            raise
        except Exception as e:
            error_msg = f"Error retrieving messages from memory: {e}"
            logger.error(error_msg)
            raise MCPServiceError(error_msg)
            
    async def close(self) -> None:
        """
        Close the MCP connection.
        Should be called when the client is no longer needed.
        """
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
                self.session = None
            except Exception as e:
                logger.error(f"Error closing memory session: {e}")
                
        if self.streams_context:
            try:
                await self.streams_context.__aexit__(None, None, None)
                self.streams_context = None
            except Exception as e:
                logger.error(f"Error closing memory streams: {e}")
                
        logger.info("Memory client connection closed")