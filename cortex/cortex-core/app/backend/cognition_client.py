from typing import Optional, List, Dict, Any

from mcp.client.sse import sse_client
from mcp.client.session import ClientSession


class CognitionClient:
    """
    Client for the Cognition Service (LLM and analysis).
    Uses MCP over SSE to communicate with the service.
    """

    def __init__(self, service_url: str = "http://localhost:5000/sse"):
        """Initialize connection parameters for Cognition Service."""
        self.service_url = service_url
        self.session: Optional[ClientSession] = None
        self.streams_context: Any = None

    async def connect(self) -> None:
        """Establish MCP connection to the Cognition service."""
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
            
            # Optional: verify connection by listing available tools
            tools_response = await self.session.list_tools()
            available_tools = [t.name for t in tools_response.tools]
            print(f"Connected to cognition service at {self.service_url}, tools: {available_tools}")
        except Exception as e:
            self.session = None
            print(f"Error connecting to cognition service: {e}")
            raise RuntimeError(f"Failed to connect to cognition service: {str(e)}")

    async def evaluate_context(self, user_id: str, conversation_id: str, message: str, 
                              memory_snippets: Optional[List[Dict[str, Any]]] = None, 
                              expert_insights: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Send context to the Cognition service for evaluation.
        Returns the generated response.
        """
        if self.session is None:
            await self.connect()
            
        if self.session is None:  # Still None after connect attempt
            return "Error: Could not connect to cognition service"
            
        # Prepare context payload
        context_payload = {
            "user_input": message,
            "memory_snippets": memory_snippets or [],
            "expert_insights": expert_insights or [],
            "user_id": user_id,
            "conversation_id": conversation_id
        }
        
        try:            
            # Define RPC request
            method = "evaluate_context"
            params = context_payload
            
            # Call the tool
            response = await self.session.call_tool(method, params)
            
            # Extract response 
            # CallToolResult stores custom data in model_extra
            if response:
                # Access model_extra which contains the dynamic fields added via **extra_data
                extra_data = getattr(response, "model_extra", {})
                if extra_data and "message" in extra_data:
                    return str(extra_data["message"])
            return "No response received from cognition service."
        except Exception as e:
            print(f"Error calling evaluate_context: {e}")
            return f"Error generating response: {str(e)}"
            
    async def generate_reply(self, user_id: str, conversation_id: str, message: str) -> str:
        """
        Legacy method that calls evaluate_context for backward compatibility.
        Will be deprecated in favor of evaluate_context.
        """
        return await self.evaluate_context(user_id, conversation_id, message)
        
    async def close(self) -> None:
        """Close the MCP connection."""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
                self.session = None
            except Exception as e:
                print(f"Error closing cognition session: {e}")
                
        if self.streams_context:
            try:
                await self.streams_context.__aexit__(None, None, None)
                self.streams_context = None
            except Exception as e:
                print(f"Error closing cognition streams: {e}")