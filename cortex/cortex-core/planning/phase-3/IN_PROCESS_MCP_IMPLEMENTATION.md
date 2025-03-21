# In-Process MCP Implementation Guide

## Overview

This guide provides detailed implementation instructions for the in-process Model Context Protocol (MCP) architecture in Phase 3 of the Cortex Core project. The in-process implementation establishes service boundaries and communication patterns while keeping everything within a single process, setting the foundation for distributed services in Phase 4.

While the `MCP_ARCHITECTURE.md` document explains the overall architecture and concepts, this guide focuses specifically on the concrete implementation details, code patterns, and integration steps needed to successfully implement in-process MCP services.

## Prerequisites

Before implementing the in-process MCP architecture, ensure you have the following:

- Familiarity with the existing Cortex Core codebase (Phases 1 and 2)
- Understanding of the MCP architecture concepts (from `MCP_ARCHITECTURE.md`)
- Python 3.10 or higher with asyncio support
- FastAPI and related dependencies installed

## Implementation Roadmap

The implementation process follows these stages:

1. **Core Infrastructure**: Implement MCP client, server interfaces, and service registry
2. **Memory Service**: Create the in-process Memory Service
3. **Cognition Service**: Create the in-process Cognition Service
4. **API Integration**: Update the API endpoints to use MCP services
5. **Event Bus Integration**: Connect the event bus with MCP services
6. **Testing**: Create comprehensive tests for the MCP implementation

## 1. Core MCP Infrastructure Implementation

### 1.1 MCP Exceptions

First, define the exception hierarchy for MCP-related errors:

```python
# app/core/mcp/exceptions.py

class McpError(Exception):
    """Base class for all MCP exceptions."""
    pass

class ConnectionError(McpError):
    """Error connecting to MCP server."""
    pass

class ToolNotFoundError(McpError):
    """Tool not found on MCP server."""
    pass

class ToolExecutionError(McpError):
    """Error executing tool on MCP server."""
    pass

class ResourceNotFoundError(McpError):
    """Resource not found on MCP server."""
    pass

class ResourceAccessError(McpError):
    """Error accessing resource on MCP server."""
    pass

class ServiceNotFoundError(McpError):
    """Service not found in registry."""
    pass

class ServiceInitializationError(McpError):
    """Error initializing service."""
    pass

class ServiceShutdownError(McpError):
    """Error shutting down service."""
    pass
```

### 1.2 MCP Client Interface

Define the interface that all MCP clients will implement:

```python
# app/core/mcp/client.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class McpClient(ABC):
    """Abstract base class for MCP clients."""

    @abstractmethod
    async def connect(self) -> None:
        """
        Connect to the MCP server.

        Raises:
            ConnectionError: If unable to connect to the server
        """
        pass

    @abstractmethod
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.

        Args:
            name: The name of the tool to call
            arguments: Dictionary of arguments for the tool

        Returns:
            Tool execution result

        Raises:
            ToolNotFoundError: If the tool does not exist
            ToolExecutionError: If the tool execution fails
            ConnectionError: If the connection to the server is lost
        """
        pass

    @abstractmethod
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """
        Get a resource from the MCP server.

        Args:
            uri: The URI of the resource to get

        Returns:
            Resource data

        Raises:
            ResourceNotFoundError: If the resource does not exist
            ResourceAccessError: If the resource access fails
            ConnectionError: If the connection to the server is lost
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the connection to the MCP server.

        Raises:
            ConnectionError: If an error occurs while closing the connection
        """
        pass
```

### 1.3 In-Process MCP Client Implementation

Implement the in-process version of the MCP client:

```python
# app/core/mcp/in_process_client.py

import inspect
import logging
import re
from typing import Any, Dict, Optional

from .client import McpClient
from .exceptions import ConnectionError, ToolNotFoundError, ToolExecutionError
from .exceptions import ResourceNotFoundError, ResourceAccessError

logger = logging.getLogger(__name__)

class InProcessMcpClient(McpClient):
    """In-process implementation of MCP client."""

    def __init__(self, server_instance: Any):
        """
        Initialize the in-process MCP client.

        Args:
            server_instance: The server instance to connect to
        """
        self.server = server_instance
        self.connected = False

    async def connect(self) -> None:
        """
        Connect to the in-process MCP server.

        For in-process clients, this simply sets the connected flag.

        Raises:
            ConnectionError: If unable to connect to the server
        """
        try:
            # Check if the server has an initialize method
            if hasattr(self.server, "initialize") and inspect.iscoroutinefunction(self.server.initialize):
                # Call initialize if it hasn't been called yet
                await self.server.initialize()

            self.connected = True
            logger.debug(f"Connected to in-process MCP server: {self.server.__class__.__name__}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to server: {e}")

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the in-process MCP server.

        Args:
            name: The name of the tool to call
            arguments: Dictionary of arguments for the tool

        Returns:
            Tool execution result

        Raises:
            ToolNotFoundError: If the tool does not exist
            ToolExecutionError: If the tool execution fails
            ConnectionError: If the connection to the server is lost
        """
        if not self.connected:
            await self.connect()

        # Find the tool by name
        if not hasattr(self.server, name):
            raise ToolNotFoundError(f"Tool '{name}' not found on server")

        tool_func = getattr(self.server, name)

        # Check if it's a coroutine function
        if not inspect.iscoroutinefunction(tool_func):
            raise ToolNotFoundError(f"Tool '{name}' is not a coroutine function")

        try:
            # Call the tool with the provided arguments
            logger.debug(f"Calling tool '{name}' with arguments: {arguments}")
            result = await tool_func(**arguments)
            logger.debug(f"Tool '{name}' returned: {result}")
            return result
        except TypeError as e:
            # This could be due to incorrect arguments
            raise ToolExecutionError(f"Error executing tool '{name}': Invalid arguments: {e}")
        except Exception as e:
            raise ToolExecutionError(f"Error executing tool '{name}': {e}")

    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """
        Get a resource from the in-process MCP server.

        Args:
            uri: The URI of the resource to get

        Returns:
            Resource data

        Raises:
            ResourceNotFoundError: If the resource does not exist
            ResourceAccessError: If the resource access fails
            ConnectionError: If the connection to the server is lost
        """
        if not self.connected:
            await self.connect()

        # Parse the URI to extract resource name and parameters
        # Example URI: "history/user123" or "conversation/conv123/messages"
        parts = uri.split('/')

        if not parts:
            raise ResourceNotFoundError(f"Invalid resource URI: {uri}")

        # Find a resource method that matches the URI pattern
        resource_method = self._find_resource_method(uri)

        if not resource_method:
            raise ResourceNotFoundError(f"Resource not found for URI: {uri}")

        try:
            # Extract parameters from the URI using regex
            params = self._extract_resource_params(resource_method, uri)

            # Call the resource method with the extracted parameters
            logger.debug(f"Accessing resource '{uri}' with parameters: {params}")
            result = await resource_method(**params)
            logger.debug(f"Resource '{uri}' returned data")
            return result
        except TypeError as e:
            # This could be due to incorrect parameters
            raise ResourceAccessError(f"Error accessing resource '{uri}': Invalid parameters: {e}")
        except Exception as e:
            raise ResourceAccessError(f"Error accessing resource '{uri}': {e}")

    def _find_resource_method(self, uri: str) -> Optional[callable]:
        """
        Find a resource method that matches the given URI.

        Args:
            uri: The URI to match

        Returns:
            Matching resource method or None if not found
        """
        # Check if the server has a resource_patterns attribute
        if hasattr(self.server, "resource_patterns"):
            # This is a map of regex patterns to method names
            for pattern, method_name in self.server.resource_patterns.items():
                if re.match(pattern, uri):
                    # Found a matching pattern, get the method
                    return getattr(self.server, method_name)

        # If no explicit resource patterns, try standard naming conventions
        parts = uri.split('/')
        resource_name = parts[0]

        # Try different method naming patterns
        method_patterns = [
            f"get_{resource_name}",  # get_history
            f"get_{resource_name}_resource",  # get_history_resource
            resource_name  # history
        ]

        for method_name in method_patterns:
            if hasattr(self.server, method_name) and inspect.iscoroutinefunction(getattr(self.server, method_name)):
                return getattr(self.server, method_name)

        return None

    def _extract_resource_params(self, resource_method: callable, uri: str) -> Dict[str, str]:
        """
        Extract parameters from the URI based on the resource method's signature.

        Args:
            resource_method: The resource method
            uri: The URI to extract parameters from

        Returns:
            Dictionary of parameter names and values
        """
        # Get the parameter names from the method signature
        sig = inspect.signature(resource_method)
        param_names = list(sig.parameters.keys())

        # Skip 'self' parameter if it exists
        if param_names and param_names[0] == 'self':
            param_names = param_names[1:]

        # Split the URI into parts
        parts = uri.split('/')

        # Map parts to parameters
        params = {}
        for i, param_name in enumerate(param_names):
            if i + 1 < len(parts):  # +1 because we skip the resource name
                params[param_name] = parts[i + 1]

        return params

    async def close(self) -> None:
        """
        Close the connection to the in-process MCP server.

        For in-process clients, this simply clears the connected flag.

        Raises:
            ConnectionError: If an error occurs while closing the connection
        """
        if not self.connected:
            return

        try:
            # Call shutdown if the server has it
            if hasattr(self.server, "shutdown") and inspect.iscoroutinefunction(self.server.shutdown):
                await self.server.shutdown()

            self.connected = False
            logger.debug(f"Closed connection to in-process MCP server: {self.server.__class__.__name__}")
        except Exception as e:
            raise ConnectionError(f"Error closing connection: {e}")
```

### 1.4 MCP Service Registry

Implement the service registry for managing MCP services:

```python
# app/core/mcp/registry.py

import logging
from typing import Dict, Any

from .client import McpClient
from .in_process_client import InProcessMcpClient
from .exceptions import ServiceNotFoundError, ServiceInitializationError, ServiceShutdownError

logger = logging.getLogger(__name__)

class McpServiceRegistry:
    """Registry for MCP services and clients."""

    def __init__(self):
        """Initialize the MCP service registry."""
        self.services = {}  # Service name -> Service instance
        self.clients = {}   # Service name -> MCP client instance

    def register_service(self, name: str, service_instance: Any) -> None:
        """
        Register an MCP service.

        Args:
            name: The name of the service
            service_instance: The service instance
        """
        self.services[name] = service_instance
        logger.info(f"Registered MCP service: {name}")

    def get_service(self, name: str) -> Any:
        """
        Get a registered service instance.

        Args:
            name: The name of the service

        Returns:
            The service instance

        Raises:
            ServiceNotFoundError: If the service is not registered
        """
        if name not in self.services:
            raise ServiceNotFoundError(f"Service '{name}' not registered")

        return self.services[name]

    def get_client(self, service_name: str) -> McpClient:
        """
        Get an MCP client for a registered service.

        Args:
            service_name: The name of the service

        Returns:
            MCP client for the service

        Raises:
            ServiceNotFoundError: If the service is not registered
        """
        # Create client on first request and cache it
        if service_name not in self.clients:
            service = self.get_service(service_name)
            client = InProcessMcpClient(service)
            self.clients[service_name] = client
            logger.info(f"Created MCP client for service: {service_name}")

        return self.clients[service_name]

    async def initialize_all(self) -> None:
        """
        Initialize all registered services.

        Raises:
            ServiceInitializationError: If service initialization fails
        """
        for name, service in self.services.items():
            try:
                if hasattr(service, "initialize"):
                    logger.info(f"Initializing service: {name}")
                    await service.initialize()
            except Exception as e:
                raise ServiceInitializationError(f"Error initializing service '{name}': {e}")

        logger.info(f"All MCP services initialized ({len(self.services)} services)")

    async def shutdown_all(self) -> None:
        """
        Shutdown all registered services.

        Raises:
            ServiceShutdownError: If service shutdown fails
        """
        # First, close all clients
        for name, client in self.clients.items():
            try:
                logger.info(f"Closing client for service: {name}")
                await client.close()
            except Exception as e:
                logger.warning(f"Error closing client for service '{name}': {e}")

        # Then, shutdown all services if needed
        for name, service in self.services.items():
            try:
                if hasattr(service, "shutdown"):
                    logger.info(f"Shutting down service: {name}")
                    await service.shutdown()
            except Exception as e:
                raise ServiceShutdownError(f"Error shutting down service '{name}': {e}")

        # Clear all registrations
        self.services.clear()
        self.clients.clear()
        logger.info("All MCP services shut down")
```

### 1.5 FastMCP Decorators

Create a simplified version of the FastMCP decorator system:

```python
# app/core/mcp/decorators.py

import inspect
import re
from functools import wraps
from typing import Dict, Callable, Any, Optional

class FastMCP:
    """
    Simple decorator-based MCP implementation.

    This class provides tool and resource decorators for MCP services,
    and manages registration of tools and resource patterns.
    """

    def __init__(self, service_name: str):
        """
        Initialize the FastMCP decorator registry.

        Args:
            service_name: The name of the service
        """
        self.service_name = service_name
        self.tools = {}  # Tool name -> Tool function
        self.resources = {}  # Resource URI pattern -> Resource function

    def tool(self, name: Optional[str] = None):
        """
        Decorator for MCP tools.

        Args:
            name: Optional custom name for the tool (defaults to function name)

        Returns:
            Decorated function
        """
        def decorator(func):
            # Register the tool
            tool_name = name or func.__name__
            self.tools[tool_name] = func

            @wraps(func)
            async def wrapper(instance, *args, **kwargs):
                return await func(instance, *args, **kwargs)

            return wrapper
        return decorator

    def resource(self, uri_template: str):
        """
        Decorator for MCP resources.

        Args:
            uri_template: URI template for the resource (e.g., "history/{user_id}")

        Returns:
            Decorated function
        """
        def decorator(func):
            # Convert URI template to regex pattern
            pattern = self._uri_template_to_regex(uri_template)
            self.resources[pattern] = func.__name__

            @wraps(func)
            async def wrapper(instance, *args, **kwargs):
                return await func(instance, *args, **kwargs)

            return wrapper
        return decorator

    def _uri_template_to_regex(self, uri_template: str) -> str:
        """
        Convert a URI template to a regex pattern.

        Args:
            uri_template: URI template (e.g., "history/{user_id}")

        Returns:
            Regex pattern string
        """
        # Replace {param} with (?P<param>[^/]+)
        pattern = re.sub(r'\{([^}]+)\}', lambda m: f'(?P<{m.group(1)}>[^/]+)', uri_template)
        return f'^{pattern}$'

    def _apply_to_class(self, cls):
        """
        Apply registered tools and resources to a class.

        Args:
            cls: The class to apply to

        Returns:
            The modified class
        """
        # Add resource_patterns attribute to the class
        cls.resource_patterns = self.resources
        return cls

    def implements(self, cls):
        """
        Class decorator to mark a class as implementing this MCP service.

        Args:
            cls: The class to decorate

        Returns:
            The decorated class
        """
        return self._apply_to_class(cls)
```

## 2. Memory Service Implementation

Implement the Memory Service using the MCP architecture:

```python
# app/services/memory.py

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from app.core.mcp.decorators import FastMCP
from app.core.repository import RepositoryManager

logger = logging.getLogger(__name__)

# Create FastMCP instance for the Memory Service
memory_mcp = FastMCP("Memory")

@memory_mcp.implements
class MemoryService:
    """
    MCP service for memory operations.

    This service provides tools and resources for storing and retrieving data.
    """

    def __init__(self, repository_manager: RepositoryManager):
        """
        Initialize the Memory Service.

        Args:
            repository_manager: The repository manager for data access
        """
        self.repository_manager = repository_manager
        self.initialized = False
        logger.info("Memory service created")

    async def initialize(self) -> None:
        """
        Initialize the Memory Service.

        This is called when the service is first connected to.
        """
        if self.initialized:
            return

        # Perform any necessary initialization
        logger.info("Memory service initialized")
        self.initialized = True

    async def shutdown(self) -> None:
        """
        Shutdown the Memory Service.

        This is called when the application is shutting down.
        """
        if not self.initialized:
            return

        # Perform any necessary cleanup
        logger.info("Memory service shut down")
        self.initialized = False

    @memory_mcp.tool()
    async def store_input(self, user_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store input data for a specific user.

        Args:
            user_id: The unique user identifier
            input_data: The input data to store

        Returns:
            Status object with operation result
        """
        try:
            # Add ID if not present
            if "id" not in input_data:
                input_data["id"] = str(uuid.uuid4())

            # Add timestamp if not present
            if "timestamp" not in input_data:
                input_data["timestamp"] = datetime.now().isoformat()

            # Get the appropriate repository
            message_repo = self.repository_manager.get_repository("messages")

            # Create the message data
            message_data = {
                "user_id": user_id,
                "content": input_data.get("content", ""),
                "conversation_id": input_data.get("conversation_id"),
                "timestamp": input_data["timestamp"],
                "metadata": input_data.get("metadata", {})
            }

            # Store the input
            message_id = await message_repo.create(message_data)

            logger.info(f"Stored input for user {user_id}: {message_id}")

            # Return success status
            return {
                "status": "stored",
                "user_id": user_id,
                "item_id": message_id
            }
        except Exception as e:
            logger.error(f"Error storing input for user {user_id}: {e}")

            # Return error status
            return {
                "status": "error",
                "user_id": user_id,
                "error": str(e)
            }

    @memory_mcp.resource("history/{user_id}")
    async def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get history for a specific user.

        Args:
            user_id: The unique user identifier

        Returns:
            List containing the user's history
        """
        try:
            # Get the appropriate repository
            message_repo = self.repository_manager.get_repository("messages")

            # Find messages for the user
            messages = await message_repo.find_many({"user_id": user_id})

            logger.info(f"Retrieved history for user {user_id}: {len(messages)} items")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving history for user {user_id}: {e}")
            return []

    @memory_mcp.resource("history/{user_id}/limit/{limit}")
    async def get_limited_history(self, user_id: str, limit: str) -> List[Dict[str, Any]]:
        """
        Get limited history for a specific user.

        Args:
            user_id: The unique user identifier
            limit: Maximum number of items to return (as string)

        Returns:
            List containing the user's limited history
        """
        try:
            # Convert limit to integer
            limit_int = int(limit)

            # Get the appropriate repository
            message_repo = self.repository_manager.get_repository("messages")

            # Find messages for the user with limit
            messages = await message_repo.find_many(
                {"user_id": user_id},
                limit=limit_int,
                sort=[("timestamp", -1)]  # Sort by timestamp descending
            )

            logger.info(f"Retrieved limited history for user {user_id}: {len(messages)} items (limit {limit})")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving limited history for user {user_id}: {e}")
            return []

    @memory_mcp.resource("conversation/{conversation_id}")
    async def get_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get messages for a specific conversation.

        Args:
            conversation_id: The unique conversation identifier

        Returns:
            List containing the conversation messages
        """
        try:
            # Get the appropriate repository
            message_repo = self.repository_manager.get_repository("messages")

            # Find messages for the conversation
            messages = await message_repo.find_many(
                {"conversation_id": conversation_id},
                sort=[("timestamp", 1)]  # Sort by timestamp ascending
            )

            logger.info(f"Retrieved conversation {conversation_id}: {len(messages)} messages")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving conversation {conversation_id}: {e}")
            return []
```

## 3. Cognition Service Implementation

Implement the Cognition Service using the MCP architecture:

```python
# app/services/cognition.py

import logging
from typing import Dict, List, Any, Optional

from app.core.mcp.client import McpClient
from app.core.mcp.decorators import FastMCP

logger = logging.getLogger(__name__)

# Create FastMCP instance for the Cognition Service
cognition_mcp = FastMCP("Cognition")

@cognition_mcp.implements
class CognitionService:
    """
    MCP service for cognition operations.

    This service provides tools for processing and analyzing data.
    """

    def __init__(self, memory_client: Optional[McpClient] = None):
        """
        Initialize the Cognition Service.

        Args:
            memory_client: Optional MCP client for the Memory Service
        """
        self.memory_client = memory_client
        self.initialized = False
        logger.info("Cognition service created")

    async def initialize(self) -> None:
        """
        Initialize the Cognition Service.

        This is called when the service is first connected to.
        """
        if self.initialized:
            return

        # Perform any necessary initialization
        logger.info("Cognition service initialized")
        self.initialized = True

    async def shutdown(self) -> None:
        """
        Shutdown the Cognition Service.

        This is called when the application is shutting down.
        """
        if not self.initialized:
            return

        # Perform any necessary cleanup
        logger.info("Cognition service shut down")
        self.initialized = False

    @cognition_mcp.tool()
    async def get_context(
        self,
        user_id: str,
        query: Optional[str] = None,
        limit: Optional[int] = 10
    ) -> Dict[str, Any]:
        """
        Get relevant context for a user.

        Args:
            user_id: The unique user identifier
            query: Optional search query to filter context
            limit: Maximum number of items to return

        Returns:
            Object containing relevant context items
        """
        try:
            # Get user history from Memory Service
            history = []

            if self.memory_client:
                try:
                    # Get limited history
                    history = await self.memory_client.get_resource(f"history/{user_id}/limit/{limit}")
                    logger.info(f"Retrieved history for user {user_id} from Memory Service: {len(history)} items")
                except Exception as e:
                    logger.error(f"Error retrieving history from Memory Service: {e}")

            # In a real implementation, this would perform more sophisticated relevance matching
            # For Phase 3, we'll just return the history as context

            # If query is provided, perform basic filtering
            context = history
            if query:
                # Simple case-insensitive substring matching
                query_lower = query.lower()
                context = [
                    item for item in history
                    if query_lower in item.get("content", "").lower()
                ]

            return {
                "context": context,
                "user_id": user_id,
                "query": query,
                "count": len(context)
            }
        except Exception as e:
            logger.error(f"Error getting context for user {user_id}: {e}")

            # Return empty context on error
            return {
                "context": [],
                "user_id": user_id,
                "query": query,
                "count": 0,
                "error": str(e)
            }

    @cognition_mcp.tool()
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze the sentiment of a text.

        Args:
            text: The text to analyze

        Returns:
            Sentiment analysis result
        """
        try:
            # This is a simplified placeholder implementation
            # A real implementation would use a proper sentiment analysis model

            # Lists of positive and negative words for basic sentiment analysis
            positive_words = [
                "good", "great", "excellent", "wonderful", "amazing", "awesome",
                "happy", "joy", "love", "like", "best", "fantastic", "perfect",
                "pleased", "delight", "positive", "better", "success", "enjoy"
            ]
            negative_words = [
                "bad", "terrible", "awful", "horrible", "worst", "hate",
                "sad", "angry", "disappointed", "poor", "negative", "fail",
                "failure", "worst", "problem", "issue", "broken", "wrong",
                "unhappy", "dislike", "disappoint", "sucks", "annoying"
            ]

            # Convert to lowercase for case-insensitive matching
            text_lower = text.lower()

            # Count positive and negative words
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)

            # Calculate sentiment score (-1 to 1)
            total = positive_count + negative_count
            score = 0.0
            if total > 0:
                score = (positive_count - negative_count) / total

            # Determine sentiment category
            sentiment = "neutral"
            if score > 0.2:
                sentiment = "positive"
            elif score < -0.2:
                sentiment = "negative"

            logger.info(f"Analyzed sentiment: {sentiment} (score: {score:.2f})")

            return {
                "sentiment": sentiment,
                "score": score,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "total_words": len(text.split())
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")

            # Return neutral sentiment on error
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "total_words": 0,
                "error": str(e)
            }
```

## 4. API Integration

Update the API endpoints to use the MCP services:

### 4.1 Input API Integration

```python
# app/api/input.py

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from app.models.api.request import InputRequest
from app.models.api.response import InputResponse
from app.utils.auth import get_current_user
from app.core.event_bus import event_bus
from app.core.mcp.registry import McpServiceRegistry

# Get the service registry instance
service_registry = McpServiceRegistry()

logger = logging.getLogger(__name__)
router = APIRouter(tags=["input"])

@router.post("/input", response_model=InputResponse)
async def receive_input(
    request: InputRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Receive input from a client.

    Args:
        request: The input request
        current_user: The authenticated user

    Returns:
        Status response
    """
    user_id = current_user["user_id"]

    # Create input data
    input_data = {
        "content": request.content,
        "conversation_id": request.conversation_id,
        "timestamp": datetime.now().isoformat(),
        "metadata": request.metadata or {}
    }

    try:
        # Get the Memory Service client
        memory_client = service_registry.get_client("memory")

        # Call the store_input tool
        result = await memory_client.call_tool("store_input", {
            "user_id": user_id,
            "input_data": input_data
        })

        # Check if the operation was successful
        if result.get("status") != "stored":
            # Log the error but don't fail the request
            logger.error(f"Failed to store input: {result}")

        # Create event for the event bus
        event = {
            "type": "input",
            "data": input_data,
            "user_id": user_id,
            "timestamp": input_data["timestamp"]
        }

        # Publish event to event bus
        await event_bus.publish(event)

        # Return success response
        return InputResponse(
            status="received",
            data=input_data
        )
    except Exception as e:
        logger.error(f"Error processing input: {e}")

        # Publish error event
        error_event = {
            "type": "error",
            "data": {
                "message": f"Error processing input: {str(e)}",
                "conversation_id": request.conversation_id
            },
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        await event_bus.publish(error_event)

        # Return error response
        return InputResponse(
            status="error",
            data=input_data,
            error=str(e)
        )
```

### 4.2 Output API Integration

```python
# app/api/output.py

import json
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.utils.auth import get_current_user
from app.core.event_bus import event_bus
from app.core.mcp.registry import McpServiceRegistry

# Get the service registry instance
service_registry = McpServiceRegistry()

logger = logging.getLogger(__name__)
router = APIRouter(tags=["output"])

@router.get("/output/stream")
async def output_stream(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Server-Sent Events (SSE) endpoint for streaming output to clients.

    Args:
        request: The HTTP request
        current_user: The authenticated user

    Returns:
        SSE streaming response
    """
    user_id = current_user["user_id"]

    # Create queue for this connection
    queue = asyncio.Queue()

    # Subscribe to event bus
    event_bus.subscribe(queue)

    # Send connection established event
    connection_event = {
        "type": "connection_established",
        "data": {},
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }
    await event_bus.publish(connection_event)

    async def event_generator():
        """Generate SSE events from the queue."""
        try:
            # Get initial context from Cognition Service
            try:
                # Get the Cognition Service client
                cognition_client = service_registry.get_client("cognition")

                # Call the get_context tool
                context_result = await cognition_client.call_tool("get_context", {
                    "user_id": user_id,
                    "limit": 10
                })

                # If context was retrieved successfully, create a context event
                if context_result and "context" in context_result:
                    context_event = {
                        "type": "context",
                        "data": context_result,
                        "user_id": user_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(context_event)}\n\n"
            except Exception as e:
                logger.error(f"Error getting initial context: {e}")

            # Now process events from the queue
            while True:
                # Wait for next event
                event = await queue.get()

                # Filter events for this user
                if event.get("user_id") == user_id or event.get("type") == "heartbeat":
                    # Format as SSE event
                    yield f"data: {json.dumps(event)}\n\n"

                # Add small delay to prevent CPU hogging
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            # Client disconnected
            event_bus.unsubscribe(queue)
            logger.debug(f"Client disconnected: {user_id}")
            raise
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            event_bus.unsubscribe(queue)
            raise
        finally:
            # Always clean up subscription
            event_bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

## 5. Application Startup Integration

Update the main application to initialize the MCP services:

```python
# app/main.py

import asyncio
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, input, output, config
from app.core.event_bus import event_bus
from app.core.repository import RepositoryManager
from app.core.mcp.registry import McpServiceRegistry
from app.services.memory import MemoryService
from app.services.cognition import CognitionService

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Cortex Core")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create service registry
service_registry = McpServiceRegistry()

# Include routers
app.include_router(auth.router)
app.include_router(input.router)
app.include_router(output.router)
app.include_router(config.router)

# Root endpoint
@app.get("/", tags=["status"])
async def root():
    """API status endpoint."""
    return {"status": "online", "service": "Cortex Core"}

@app.on_event("startup")
async def startup_event():
    """
    Startup event handler.

    Initialize repositories and MCP services.
    """
    logger.info("Starting Cortex Core")

    # Initialize repository manager
    repository_manager = RepositoryManager()
    await repository_manager.initialize()

    # Create and register Memory Service
    memory_service = MemoryService(repository_manager)
    service_registry.register_service("memory", memory_service)

    # Get Memory Client for Cognition Service
    memory_client = service_registry.get_client("memory")

    # Create and register Cognition Service
    cognition_service = CognitionService(memory_client)
    service_registry.register_service("cognition", cognition_service)

    # Initialize all services
    await service_registry.initialize_all()

    logger.info("Cortex Core started")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Shutdown event handler.

    Shut down MCP services and event bus.
    """
    logger.info("Shutting down Cortex Core")

    # Shutdown all services
    await service_registry.shutdown_all()

    # Shutdown event bus
    await event_bus.shutdown()

    logger.info("Cortex Core shut down")
```

## 6. Testing the MCP Implementation

### 6.1 Testing the In-Process MCP Client

```python
# tests/unit/core/mcp/test_in_process_client.py

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.mcp.exceptions import ToolNotFoundError, ToolExecutionError
from app.core.mcp.exceptions import ResourceNotFoundError, ResourceAccessError
from app.core.mcp.in_process_client import InProcessMcpClient

class TestInProcessMcpClient:
    """Tests for the in-process MCP client."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock server for testing."""
        server = MagicMock()
        server.initialize = AsyncMock()
        server.shutdown = AsyncMock()
        server.test_tool = AsyncMock(return_value={"result": "success"})
        server.get_test_resource = AsyncMock(return_value={"data": "test"})

        # Add resource patterns
        server.resource_patterns = {
            r"^test/(\w+)$": "get_test_resource"
        }

        return server

    def test_init(self, mock_server):
        """Test client initialization."""
        client = InProcessMcpClient(mock_server)
        assert client.server == mock_server
        assert not client.connected

    @pytest.mark.asyncio
    async def test_connect(self, mock_server):
        """Test connecting to the server."""
        client = InProcessMcpClient(mock_server)
        await client.connect()

        assert client.connected
        mock_server.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_error(self, mock_server):
        """Test error handling during connect."""
        mock_server.initialize.side_effect = Exception("Test error")
        client = InProcessMcpClient(mock_server)

        with pytest.raises(Exception):
            await client.connect()

        assert not client.connected

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_server):
        """Test successful tool call."""
        client = InProcessMcpClient(mock_server)
        await client.connect()

        result = await client.call_tool("test_tool", {"param": "value"})

        mock_server.test_tool.assert_called_once_with(param="value")
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, mock_server):
        """Test tool not found error."""
        client = InProcessMcpClient(mock_server)
        await client.connect()

        with pytest.raises(ToolNotFoundError):
            await client.call_tool("non_existent_tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_execution_error(self, mock_server):
        """Test tool execution error."""
        mock_server.test_tool.side_effect = Exception("Test error")
        client = InProcessMcpClient(mock_server)
        await client.connect()

        with pytest.raises(ToolExecutionError):
            await client.call_tool("test_tool", {})

    @pytest.mark.asyncio
    async def test_get_resource_success(self, mock_server):
        """Test successful resource access."""
        client = InProcessMcpClient(mock_server)
        await client.connect()

        result = await client.get_resource("test/resource")

        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_get_resource_not_found(self, mock_server):
        """Test resource not found error."""
        client = InProcessMcpClient(mock_server)
        await client.connect()

        with pytest.raises(ResourceNotFoundError):
            await client.get_resource("non_existent/resource")

    @pytest.mark.asyncio
    async def test_get_resource_access_error(self, mock_server):
        """Test resource access error."""
        mock_server.get_test_resource.side_effect = Exception("Test error")
        client = InProcessMcpClient(mock_server)
        await client.connect()

        with pytest.raises(ResourceAccessError):
            await client.get_resource("test/resource")

    @pytest.mark.asyncio
    async def test_close(self, mock_server):
        """Test closing the connection."""
        client = InProcessMcpClient(mock_server)
        await client.connect()

        await client.close()

        assert not client.connected
        mock_server.shutdown.assert_called_once()
```

### 6.2 Testing the Memory Service

```python
# tests/unit/services/test_memory_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.memory import MemoryService

class TestMemoryService:
    """Tests for the Memory Service."""

    @pytest.fixture
    def mock_repository_manager(self):
        """Create a mock repository manager."""
        manager = MagicMock()
        message_repo = MagicMock()
        manager.get_repository.return_value = message_repo
        return manager, message_repo

    def test_init(self, mock_repository_manager):
        """Test service initialization."""
        manager, _ = mock_repository_manager
        service = MemoryService(manager)

        assert service.repository_manager == manager
        assert not service.initialized

    @pytest.mark.asyncio
    async def test_initialize(self, mock_repository_manager):
        """Test service initialization."""
        manager, _ = mock_repository_manager
        service = MemoryService(manager)

        await service.initialize()

        assert service.initialized

        # Calling initialize again should be a no-op
        await service.initialize()

    @pytest.mark.asyncio
    async def test_shutdown(self, mock_repository_manager):
        """Test service shutdown."""
        manager, _ = mock_repository_manager
        service = MemoryService(manager)

        await service.initialize()
        await service.shutdown()

        assert not service.initialized

        # Calling shutdown again should be a no-op
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_store_input(self, mock_repository_manager):
        """Test storing input."""
        manager, message_repo = mock_repository_manager
        message_repo.create = AsyncMock(return_value="message_id")

        service = MemoryService(manager)
        await service.initialize()

        result = await service.store_input("user123", {
            "content": "Test message",
            "conversation_id": "conv123",
            "metadata": {"test": True}
        })

        # Verify repository was called
        manager.get_repository.assert_called_once_with("messages")
        message_repo.create.assert_called_once()

        # Verify the message data
        call_args = message_repo.create.call_args[0][0]
        assert call_args["user_id"] == "user123"
        assert call_args["content"] == "Test message"
        assert call_args["conversation_id"] == "conv123"
        assert call_args["metadata"] == {"test": True}
        assert "timestamp" in call_args

        # Verify the result
        assert result["status"] == "stored"
        assert result["user_id"] == "user123"
        assert result["item_id"] == "message_id"

    @pytest.mark.asyncio
    async def test_store_input_error(self, mock_repository_manager):
        """Test error handling when storing input."""
        manager, message_repo = mock_repository_manager
        message_repo.create = AsyncMock(side_effect=Exception("Test error"))

        service = MemoryService(manager)
        await service.initialize()

        result = await service.store_input("user123", {
            "content": "Test message"
        })

        # Verify error response
        assert result["status"] == "error"
        assert result["user_id"] == "user123"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_history(self, mock_repository_manager):
        """Test getting user history."""
        manager, message_repo = mock_repository_manager
        history = [{"id": "msg1"}, {"id": "msg2"}]
        message_repo.find_many = AsyncMock(return_value=history)

        service = MemoryService(manager)
        await service.initialize()

        result = await service.get_history("user123")

        # Verify repository was called
        manager.get_repository.assert_called_once_with("messages")
        message_repo.find_many.assert_called_once_with({"user_id": "user123"})

        # Verify the result
        assert result == history

    @pytest.mark.asyncio
    async def test_get_history_error(self, mock_repository_manager):
        """Test error handling when getting history."""
        manager, message_repo = mock_repository_manager
        message_repo.find_many = AsyncMock(side_effect=Exception("Test error"))

        service = MemoryService(manager)
        await service.initialize()

        result = await service.get_history("user123")

        # Verify empty list on error
        assert result == []

    @pytest.mark.asyncio
    async def test_get_limited_history(self, mock_repository_manager):
        """Test getting limited user history."""
        manager, message_repo = mock_repository_manager
        history = [{"id": "msg1"}]
        message_repo.find_many = AsyncMock(return_value=history)

        service = MemoryService(manager)
        await service.initialize()

        result = await service.get_limited_history("user123", "5")

        # Verify repository was called with correct parameters
        manager.get_repository.assert_called_once_with("messages")
        message_repo.find_many.assert_called_once_with(
            {"user_id": "user123"},
            limit=5,
            sort=[("timestamp", -1)]
        )

        # Verify the result
        assert result == history
```

### 6.3 Testing the Cognition Service

```python
# tests/unit/services/test_cognition_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.cognition import CognitionService

class TestCognitionService:
    """Tests for the Cognition Service."""

    @pytest.fixture
    def mock_memory_client(self):
        """Create a mock memory client."""
        client = MagicMock()
        client.get_resource = AsyncMock()
        return client

    def test_init(self, mock_memory_client):
        """Test service initialization."""
        # Without memory client
        service = CognitionService()
        assert service.memory_client is None
        assert not service.initialized

        # With memory client
        service = CognitionService(mock_memory_client)
        assert service.memory_client == mock_memory_client
        assert not service.initialized

    @pytest.mark.asyncio
    async def test_initialize(self, mock_memory_client):
        """Test service initialization."""
        service = CognitionService(mock_memory_client)

        await service.initialize()

        assert service.initialized

        # Calling initialize again should be a no-op
        await service.initialize()

    @pytest.mark.asyncio
    async def test_shutdown(self, mock_memory_client):
        """Test service shutdown."""
        service = CognitionService(mock_memory_client)

        await service.initialize()
        await service.shutdown()

        assert not service.initialized

        # Calling shutdown again should be a no-op
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_get_context_with_memory(self, mock_memory_client):
        """Test getting context with memory client."""
        history = [
            {"id": "msg1", "content": "Test message 1"},
            {"id": "msg2", "content": "Test message 2"}
        ]
        mock_memory_client.get_resource.return_value = history

        service = CognitionService(mock_memory_client)
        await service.initialize()

        result = await service.get_context("user123", limit=5)

        # Verify memory client was called
        mock_memory_client.get_resource.assert_called_once_with("history/user123/limit/5")

        # Verify the result
        assert result["context"] == history
        assert result["user_id"] == "user123"
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_get_context_with_memory_error(self, mock_memory_client):
        """Test error handling when getting context."""
        mock_memory_client.get_resource.side_effect = Exception("Test error")

        service = CognitionService(mock_memory_client)
        await service.initialize()

        result = await service.get_context("user123")

        # Verify empty context on error
        assert result["context"] == []
        assert result["user_id"] == "user123"
        assert result["count"] == 0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_context_without_memory(self):
        """Test getting context without memory client."""
        service = CognitionService()  # No memory client
        await service.initialize()

        result = await service.get_context("user123")

        # Verify empty context
        assert result["context"] == []
        assert result["user_id"] == "user123"
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_get_context_with_query(self, mock_memory_client):
        """Test getting context with query filter."""
        history = [
            {"id": "msg1", "content": "This is about apples"},
            {"id": "msg2", "content": "This is about bananas"}
        ]
        mock_memory_client.get_resource.return_value = history

        service = CognitionService(mock_memory_client)
        await service.initialize()

        result = await service.get_context("user123", query="apple")

        # Verify filtering
        assert len(result["context"]) == 1
        assert result["context"][0]["id"] == "msg1"

    @pytest.mark.asyncio
    async def test_analyze_sentiment_positive(self, mock_memory_client):
        """Test analyzing positive sentiment."""
        service = CognitionService(mock_memory_client)
        await service.initialize()

        result = await service.analyze_sentiment("This is great and I'm happy!")

        # Verify positive sentiment
        assert result["sentiment"] == "positive"
        assert result["score"] > 0
        assert result["positive_count"] > 0

    @pytest.mark.asyncio
    async def test_analyze_sentiment_negative(self, mock_memory_client):
        """Test analyzing negative sentiment."""
        service = CognitionService(mock_memory_client)
        await service.initialize()

        result = await service.analyze_sentiment("This is terrible and I hate it.")

        # Verify negative sentiment
        assert result["sentiment"] == "negative"
        assert result["score"] < 0
        assert result["negative_count"] > 0

    @pytest.mark.asyncio
    async def test_analyze_sentiment_neutral(self, mock_memory_client):
        """Test analyzing neutral sentiment."""
        service = CognitionService(mock_memory_client)
        await service.initialize()

        result = await service.analyze_sentiment("This is a regular statement with no strong emotions.")

        # Verify neutral sentiment
        assert result["sentiment"] == "neutral"
        assert -0.2 <= result["score"] <= 0.2
```

### 6.4 Integration Testing

```python
# tests/integration/test_mcp_integration.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.mcp.registry import McpServiceRegistry
from app.services.memory import MemoryService
from app.services.cognition import CognitionService

class TestMcpIntegration:
    """Integration tests for the MCP architecture."""

    @pytest.fixture
    async def service_registry(self):
        """Create a service registry with test services."""
        # Create the registry
        registry = McpServiceRegistry()

        # Create a mock repository manager
        repo_manager = MagicMock()
        message_repo = MagicMock()
        repo_manager.get_repository.return_value = message_repo

        # Set up the message repository mock
        message_repo.create = AsyncMock(return_value="message_id")
        message_repo.find_many = AsyncMock(return_value=[
            {
                "id": "msg1",
                "content": "Test message 1",
                "timestamp": "2023-01-01T00:00:00Z"
            },
            {
                "id": "msg2",
                "content": "Test message 2",
                "timestamp": "2023-01-02T00:00:00Z"
            }
        ])

        # Create and register the Memory Service
        memory_service = MemoryService(repo_manager)
        registry.register_service("memory", memory_service)

        # Get the Memory Client
        memory_client = registry.get_client("memory")

        # Create and register the Cognition Service
        cognition_service = CognitionService(memory_client)
        registry.register_service("cognition", cognition_service)

        # Initialize all services
        await registry.initialize_all()

        yield registry

        # Clean up
        await registry.shutdown_all()

    @pytest.mark.asyncio
    async def test_memory_service_store_and_retrieve(self, service_registry):
        """Test storing input and retrieving history."""
        # Get Memory client
        memory_client = service_registry.get_client("memory")

        # Store input
        store_result = await memory_client.call_tool("store_input", {
            "user_id": "test_user",
            "input_data": {
                "content": "Hello, world!",
                "conversation_id": "test_conv"
            }
        })

        # Verify store result
        assert store_result["status"] == "stored"
        assert store_result["user_id"] == "test_user"
        assert store_result["item_id"] == "message_id"

        # Get history
        history = await memory_client.get_resource("history/test_user")

        # Verify history
        assert len(history) == 2
        assert history[0]["id"] == "msg1"
        assert history[1]["id"] == "msg2"

    @pytest.mark.asyncio
    async def test_cognition_service_with_memory(self, service_registry):
        """Test Cognition Service using Memory Service."""
        # Get Cognition client
        cognition_client = service_registry.get_client("cognition")

        # Get context
        context_result = await cognition_client.call_tool("get_context", {
            "user_id": "test_user",
            "limit": 5
        })

        # Verify context
        assert context_result["user_id"] == "test_user"
        assert len(context_result["context"]) == 2
        assert context_result["context"][0]["id"] == "msg1"
        assert context_result["context"][1]["id"] == "msg2"

    @pytest.mark.asyncio
    async def test_service_registry_operations(self, service_registry):
        """Test service registry operations."""
        # Verify registered services
        assert "memory" in service_registry.services
        assert "cognition" in service_registry.services

        # Verify clients
        assert "memory" in service_registry.clients
        assert "cognition" in service_registry.clients

        # Get service
        memory_service = service_registry.get_service("memory")
        assert isinstance(memory_service, MemoryService)

        # Get non-existent service
        with pytest.raises(Exception):
            service_registry.get_service("non_existent")

        # Get client
        memory_client = service_registry.get_client("memory")
        assert memory_client is not None

        # Get non-existent client
        with pytest.raises(Exception):
            service_registry.get_client("non_existent")
```

## 7. Common Problems and Solutions

### 7.1 Connection Issues

**Problem**: MCP client fails to connect to a service.

**Solution**:

1. Check if the service is registered in the service registry
2. Verify that the service instance is properly initialized
3. Check for exceptions in the service's `initialize` method
4. Ensure the service name is correct

**Example Fix**:

```python
# Problem code
try:
    client = service_registry.get_client("memory")
    # ... use client
except Exception as e:
    logger.error(f"Error: {e}")

# Fixed code
try:
    # First, verify that the service exists
    if "memory" not in service_registry.services:
        logger.error("Memory service not registered")
        # Handle missing service gracefully
        return

    # Then get the client
    client = service_registry.get_client("memory")
    # ... use client
except Exception as e:
    logger.error(f"Error connecting to Memory service: {e}")
    # Provide fallback behavior
```

### 7.2 Tool Not Found Errors

**Problem**: `ToolNotFoundError` when calling a tool.

**Solution**:

1. Verify the tool name matches exactly what's registered in the service
2. Check that the tool is properly decorated with `@mcp.tool()`
3. Make sure the tool is an async function
4. Inspect the service implementation to ensure the tool is registered

**Example Fix**:

```python
# Problem code
result = await client.call_tool("storeInput", arguments)  # Wrong name

# Fixed code
result = await client.call_tool("store_input", arguments)  # Correct name
```

### 7.3 Resource Not Found Errors

**Problem**: `ResourceNotFoundError` when accessing a resource.

**Solution**:

1. Check that the URI format matches the resource pattern exactly
2. Verify that the resource is properly decorated with `@mcp.resource()`
3. Make sure the resource is an async function
4. Check the resource pattern matching in the client implementation

**Example Fix**:

```python
# Problem code
history = await client.get_resource("history")  # Missing user_id

# Fixed code
history = await client.get_resource(f"history/{user_id}")  # Correct format
```

### 7.4 Parameter Errors

**Problem**: Tool or resource call fails with a parameter error.

**Solution**:

1. Verify all required parameters are provided
2. Check parameter types match the function signature
3. Ensure parameters are passed in the correct format
4. Review the function implementation for parameter validation

**Example Fix**:

```python
# Problem code
await client.call_tool("analyze_sentiment", {"txt": "Hello"})  # Wrong parameter name

# Fixed code
await client.call_tool("analyze_sentiment", {"text": "Hello"})  # Correct parameter name
```

### 7.5 Service Initialization Order

**Problem**: Services with dependencies fail to initialize properly.

**Solution**:

1. Ensure services are registered in the correct order (dependencies first)
2. Verify clients are created after the corresponding services are registered
3. Check that the `initialize_all` method is called after all services are registered
4. Implement proper error handling in service initialization

**Example Fix**:

```python
# Problem code (wrong order)
cognition_service = CognitionService(memory_client)
service_registry.register_service("cognition", cognition_service)

memory_service = MemoryService(repository_manager)
service_registry.register_service("memory", memory_service)

# Fixed code (correct order)
memory_service = MemoryService(repository_manager)
service_registry.register_service("memory", memory_service)

memory_client = service_registry.get_client("memory")

cognition_service = CognitionService(memory_client)
service_registry.register_service("cognition", cognition_service)
```

## 8. Performance Considerations

### 8.1 In-Process Communication Overhead

Even though the MCP implementation is in-process, there is still some overhead compared to direct function calls:

1. **Client Creation**: Creating clients adds object instantiation overhead
2. **Connection Handling**: The connect/close lifecycle adds function call overhead
3. **Parameter Marshalling**: Converting between parameter dictionaries and function arguments
4. **Error Handling**: Additional error handling layers

However, this overhead is minimal in the in-process implementation and is outweighed by the benefits of clear service boundaries and forward compatibility with the distributed architecture in Phase 4.

### 8.2 Resource Usage

The in-process MCP architecture uses resources efficiently:

1. **Memory Usage**: No additional memory beyond what the functions would normally use
2. **CPU Usage**: Minimal additional CPU overhead from the MCP layer
3. **I/O**: No network I/O since all communication is in-process
4. **Thread Usage**: Remains within the asyncio event loop

### 8.3 Optimization Opportunities

If performance becomes a concern, consider these optimizations:

1. **Client Caching**: Cache client instances to avoid recreation
2. **Resource Caching**: Cache frequently accessed resources
3. **Batch Operations**: Combine multiple operations into a single call
4. **Async Parallelism**: Use `asyncio.gather` to parallelize independent operations

**Example Optimization**:

```python
# Before optimization: Sequential calls
result1 = await memory_client.get_resource("history/user1")
result2 = await memory_client.get_resource("history/user2")

# After optimization: Parallel calls
result1, result2 = await asyncio.gather(
    memory_client.get_resource("history/user1"),
    memory_client.get_resource("history/user2")
)
```

## 9. Preparing for Phase 4

Phase 3 implements MCP as an in-process architecture, while Phase 4 will move to a distributed architecture. To ensure a smooth transition:

### 9.1 Forward Compatibility Guidelines

1. **Use Serializable Data**: Only pass JSON-serializable data in tool arguments and resource results
2. **Implement Connection Lifecycle**: Properly implement connect and close methods
3. **Handle Timeout Scenarios**: Consider what happens when operations take too long
4. **Implement Proper Error Handling**: Design error responses that work in a distributed context
5. **Avoid Shared State**: Don't rely on shared memory or process state
6. **Document Dependencies**: Clearly define service dependencies
7. **Implement Health Checks**: Add service health checking capabilities

### 9.2 Potential Phase 4 Changes

In Phase 4, these components will change:

1. **MCP Client**: Will use HTTP/SSE for communication instead of direct function calls
2. **Service Discovery**: Will use a network-based registry instead of in-memory
3. **Error Handling**: Will need to handle network errors and timeouts
4. **Serialization**: Will need full serialization/deserialization for all data

## Conclusion

This guide has provided detailed implementation instructions for the in-process MCP architecture in Phase 3 of the Cortex Core project. By following these instructions, you can successfully implement:

1. The core MCP infrastructure (client, server interfaces, service registry)
2. Memory and Cognition services using the MCP pattern
3. Integration with the existing API and event bus
4. Comprehensive tests for the MCP implementation

The in-process implementation establishes clear service boundaries and communication patterns while keeping everything within a single process, setting the foundation for the distributed services in Phase 4. By following the forward compatibility guidelines, you'll ensure a smooth transition to the distributed architecture in the next phase.
