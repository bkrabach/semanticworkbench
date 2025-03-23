from typing import Dict, Any, List, Optional

from mcp.client.sse import sse_client
from mcp.client.session import ClientSession


class MemoryClient:
    """
    Client for the Memory Service.
    Uses MCP over SSE to store and retrieve conversation history.
    """

    def __init__(self, service_url: str = "http://localhost:5001/sse"):
        """Initialize connection parameters for Memory Service."""
        self.service_url = service_url
        self.session: Optional[ClientSession] = None
        self.streams_context: Any = None

    async def connect(self) -> None:
        """Establish MCP connection to the Memory service."""
        if self.session is not None:
            return  # Already connected

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
            
            print(f"Connected to memory service at {self.service_url}")
        except Exception as e:
            self.session = None
            print(f"Error connecting to memory service: {e}")
            raise RuntimeError(f"Failed to connect to memory service: {str(e)}")

    async def store_message(self, user_id: str, conversation_id: str, content: str, 
                          role: str = "user", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store a message in the memory service.
        Returns True if successful, False otherwise.
        """
        if self.session is None:
            await self.connect()
            
        if self.session is None:  # Still None after connect attempt
            return False
            
        message_data = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "content": content,
            "role": role,
            "metadata": metadata or {},
            "timestamp": None  # Memory service will set this
        }
        
        try:
            # Call the tool
            await self.session.call_tool("store_memory", message_data)
            return True
        except Exception as e:
            print(f"Error storing message in memory: {e}")
            return False

    async def get_recent_messages(self, user_id: str, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent messages from the memory service for context.
        Returns a list of messages (most recent first).
        """
        if self.session is None:
            await self.connect()
            
        if self.session is None:  # Still None after connect attempt
            return []
            
        query = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "limit": limit
        }
        
        try:
            # Call the tool 
            response = await self.session.call_tool("retrieve_memory", query)
            
            # Extract memories from response
            # CallToolResult stores custom data in model_extra
            if response:
                # Access model_extra which contains the dynamic fields added via **extra_data
                extra_data = getattr(response, "model_extra", {})
                if extra_data and "memories" in extra_data:
                    return list(extra_data["memories"])
            return []
        except Exception as e:
            print(f"Error retrieving messages from memory: {e}")
            return []
            
    async def close(self) -> None:
        """Close the MCP connection."""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
                self.session = None
            except Exception as e:
                print(f"Error closing memory session: {e}")
                
        if self.streams_context:
            try:
                await self.streams_context.__aexit__(None, None, None)
                self.streams_context = None
            except Exception as e:
                print(f"Error closing memory streams: {e}")