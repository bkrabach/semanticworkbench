import logging
from typing import Any, Dict, List, Optional, Tuple

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

# We need a more permissive type for the SSE context
# The MCP library doesn't export the exact type, so we use Any
# This follows the "Pragmatic trust" principle from the Implementation Philosophy
SSEContext = Any


# Set up logger for the client
logger = logging.getLogger(__name__)


class MCPConnectionError(Exception):
    """Exception raised when there is an error connecting to an MCP service."""

    pass


class MCPServiceError(Exception):
    """Exception raised when there is an error calling an MCP service method."""

    pass


class CognitionClient:
    """
    Client for the Cognition Service (LLM and analysis).
    Uses MCP over SSE to communicate with the service.

    Provides access to LLM-based cognition capabilities including:
    - Context evaluation and response generation
    - Future: Domain-specific analysis and insights
    """

    def __init__(self, service_url: str = "http://localhost:5000/sse"):
        """
        Initialize connection parameters for Cognition Service.

        Args:
            service_url: The URL of the SSE endpoint for the Cognition service
        """
        self.service_url = service_url
        self.session: Optional[ClientSession] = None
        self.streams_context: Optional[SSEContext] = None
        self.available_tools: List[str] = []

    async def connect(self) -> Tuple[bool, Optional[str]]:
        """
        Establish MCP connection to the Cognition service.

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

            # Verify connection by listing available tools
            tools_response = await self.session.list_tools()
            self.available_tools = [t.name for t in tools_response.tools]
            logger.info(f"Connected to cognition service at {self.service_url}, tools: {self.available_tools}")
            return (True, None)
        except Exception as e:
            self.session = None
            self.streams_context = None
            error_msg = f"Failed to connect to cognition service: {str(e)}"
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

    async def evaluate_context(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        memory_snippets: Optional[List[Dict[str, Any]]] = None,
        expert_insights: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Send context to the Cognition service for evaluation.

        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            message: The user's message
            memory_snippets: Optional list of memory snippets for context
            expert_insights: Optional list of domain expert insights

        Returns:
            The generated response text

        Raises:
            MCPConnectionError: If the connection cannot be established
            MCPServiceError: If there is an error calling the service
        """
        try:
            await self.ensure_connected()

            # Prepare context payload
            context_payload = {
                "user_input": message,
                "memory_snippets": memory_snippets or [],
                "expert_insights": expert_insights or [],
                "user_id": user_id,
                "conversation_id": conversation_id,
            }

            # Define RPC request
            method = "evaluate_context"
            params = context_payload

            # Call the tool - session must be non-None here after ensure_connected()
            assert self.session is not None, "Session unexpectedly None after ensure_connected"
            response = await self.session.call_tool(method, params)

            # Extract response
            # CallToolResult stores custom data in model_extra
            if response:
                # Access model_extra which contains the dynamic fields added via **extra_data
                extra_data = getattr(response, "model_extra", {})
                if extra_data and "message" in extra_data:
                    message = extra_data["message"]
                    # Ensure we always return a string
                    return str(message) if message is not None else "No response received."

                logger.warning(f"Unexpected response format from cognition service: {extra_data}")
                return "No message received from cognition service."

            logger.error("Empty response received from cognition service")
            return "No response received from cognition service."
        except MCPConnectionError:
            # Re-raise connection errors
            raise
        except Exception as e:
            error_msg = f"Error calling evaluate_context: {e}"
            logger.error(error_msg)
            raise MCPServiceError(error_msg)

    async def generate_reply(self, user_id: str, conversation_id: str, message: str) -> str:
        """
        Legacy method that calls evaluate_context for backward compatibility.
        Will be deprecated in favor of evaluate_context.

        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            message: The user's message

        Returns:
            The generated response text

        Raises:
            MCPConnectionError: If the connection cannot be established
            MCPServiceError: If there is an error calling the service
        """
        return await self.evaluate_context(user_id, conversation_id, message)

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
                logger.error(f"Error closing cognition session: {e}")

        if self.streams_context:
            try:
                await self.streams_context.__aexit__(None, None, None)
                self.streams_context = None
            except Exception as e:
                logger.error(f"Error closing cognition streams: {e}")

        logger.info("Cognition client connection closed")
