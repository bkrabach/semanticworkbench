# MCP Implementation Guide

This guide provides step-by-step instructions for implementing the Model Context Protocol (MCP) integration within the Cortex Core architecture. MCP is used for internal service-to-service communication between Cortex Core and Domain Expert services.

## Table of Contents

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Implementation Steps](#implementation-steps)
  - [1. Create the Integration Hub Component ✅](#1-create-the-integration-hub-component-)
  - [2. Update Configuration ✅](#2-update-configuration-)
  - [3. Update Application Lifecycle ✅](#3-update-application-lifecycle-)
  - [4. Add API Routes ✅](#4-add-api-routes-)
  - [5. Implement Event System Integration ❌](#5-implement-event-system-integration-)
  - [6. Update Dependencies ✅](#6-update-dependencies-)
- [Domain Expert Implementation ❌](#domain-expert-implementation-)
- [Testing ✅](#testing-)
- [Troubleshooting](#troubleshooting)

## Overview

The Model Context Protocol (MCP) serves as the standardized communication method between Cortex Core and various Domain Expert services. Using MCP allows us to:

- Separate core orchestration from specialized domain expertise
- Enable tool discovery and execution across services
- Share resources and context between components
- Maintain a clean, modular architecture

This implementation uses the official Python MCP SDK, which provides client and server capabilities along with the FastMCP API for simplified server implementation.

## Architecture

```
┌────────────────────┐           ┌────────────────────┐
│    Cortex Core     │           │   Domain Experts   │
│                    │◄────────►│                    │
│ ┌────────────────┐ │           │ ┌────────────────┐ │
│ │Integration Hub │ │   MCP     │ │  FastMCP API   │ │
│ │with MCP Client │◄┼──────────┼►│  Server         │ │
│ └────────────────┘ │           │ └────────────────┘ │
└────────────────────┘           └────────────────────┘
```

Key components:

1. **Integration Hub**: Manages MCP client sessions to domain expert services
2. **MCP Transport**: Uses the Server-Sent Events (SSE) transport for HTTP communication
3. **Domain Expert Services**: Independent services implementing MCP servers using FastMCP
4. **Event System**: Tracks and monitors MCP operations for observability

## Implementation Steps

### 1. Create the Integration Hub Component ✅

Create a new file `app/components/integration_hub.py` that implements the Integration Hub.

**Status: Completed**

The Integration Hub component has been successfully implemented with additional enhancements:

- Uses a `CortexMcpClient` wrapper class to manage MCP client sessions
- Implements a circuit breaker pattern for resilient communication
- Uses a singleton pattern for system-wide access
- Includes comprehensive error handling and type safety improvements
- Has full test coverage in `tests/components/test_integration_hub.py`

The implementation follows the general pattern shown below, with enhancements:

```python
# app/components/integration_hub.py
from typing import Dict, Any, List, Optional, AsyncIterator
from contextlib import asynccontextmanager
import logging
from mcp.client import ClientSession
from mcp.client.sse import sse_client
from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.circuit_breaker import CircuitBreaker

logger = get_logger(__name__)

class CortexMcpClient:
    """Wrapper for MCP client using the official Python SDK"""

    def __init__(self, endpoint: str, service_name: str):
        self.endpoint = endpoint
        self.service_name = service_name
        self.client: Optional[ClientSession] = None

    async def connect(self) -> None:
        """Connect to the MCP server"""
        # Implementation...

    async def list_tools(self) -> Dict[str, Any]:
        """List available tools from the MCP server"""
        # Implementation...

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        # Implementation...

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the MCP server"""
        # Implementation...

    async def close(self) -> None:
        """Close the MCP client"""
        # Implementation...

class IntegrationHub:
    """Manages connections to Domain Expert services via MCP"""

    def __init__(self):
        self.settings = get_settings()
        self.clients: Dict[str, CortexMcpClient] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

    async def startup(self):
        """Initialize connections to all configured MCP endpoints"""
        # Implementation...

    async def shutdown(self):
        """Close all MCP connections"""
        # Implementation...

    async def list_experts(self) -> List[str]:
        """List all available domain experts"""
        # Implementation...

    async def list_expert_tools(self, expert_name: str) -> Dict[str, Any]:
        """List all tools available from a specific domain expert"""
        # Implementation with circuit breaker pattern...

    async def invoke_expert_tool(self, expert_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool on a specific domain expert"""
        # Implementation with circuit breaker pattern...

    async def read_expert_resource(self, expert_name: str, uri: str) -> Dict[str, Any]:
        """Read a resource from a specific domain expert"""
        # Implementation with circuit breaker pattern...

# Singleton instance
_integration_hub: Optional[IntegrationHub] = None

def get_integration_hub() -> IntegrationHub:
    """Get the singleton IntegrationHub instance"""
    global _integration_hub
    if _integration_hub is None:
        _integration_hub = IntegrationHub()
    return _integration_hub
```

### 2. Update Configuration ✅

Update the configuration in `app/config.py` to support MCP endpoints.

**Status: Completed**

The configuration has been updated to support MCP endpoints with both JSON format and individual environment variable configuration options. The implementation includes the following features:

- `McpEndpoint` and `McpConfig` classes for structured configuration
- Support for loading endpoints from environment variables
- Type safety and validation of endpoint configurations
- Integration with the main Settings class

```python
# From app/config.py
from typing import List, Optional, Dict
from pydantic_settings import BaseSettings

class McpEndpoint(BaseSettings):
    """MCP endpoint configuration"""
    name: str
    endpoint: str
    type: str

class McpConfig(BaseSettings):
    """MCP configuration - for internal service-to-service communication only"""
    # Flag to explicitly indicate that MCP is for internal use only
    internal_only: bool = True

    # List of MCP endpoints (internal services)
    endpoints: List[Dict[str, str]] = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Load MCP endpoints from environment variables
        mcp_endpoints_json = os.environ.get("MCP_ENDPOINTS")
        if mcp_endpoints_json:
            import json
            try:
                self.endpoints = json.loads(mcp_endpoints_json)
            except json.JSONDecodeError:
                pass

        # Add individual MCP endpoints
        # Format: MCP_ENDPOINT_name=endpoint_url|type
        for key, value in os.environ.items():
            if key.startswith("MCP_ENDPOINT_"):
                name = key.replace("MCP_ENDPOINT_", "")
                if "|" in value:
                    endpoint, type_ = value.split("|", 1)
                    self.endpoints.append({"name": name, "endpoint": endpoint, "type": type_})

class Settings(BaseSettings):
    """Main application settings"""
    # Other settings...
    mcp: McpConfig = McpConfig()

    # Other configuration...
```

Example environment variable configuration:

```
# MCP endpoint configuration (JSON format)
MCP_ENDPOINTS='[
  {"name":"code_assistant", "endpoint":"http://localhost:5001/mcp", "type":"code_assistant"},
  {"name":"research", "endpoint":"http://localhost:5002/mcp", "type":"research"}
]'

# Alternative individual endpoint configuration
# MCP_ENDPOINT_CODE_ASSISTANT="http://localhost:5001/mcp|code_assistant"
# MCP_ENDPOINT_RESEARCH="http://localhost:5002/mcp|research"
```

### 3. Update Application Lifecycle ✅

Update the application lifecycle in `app/main.py` to initialize and manage the Integration Hub.

**Status: Completed**

The application lifecycle has been updated to initialize the Integration Hub during application startup and clean it up during shutdown. The implementation includes:

- Using the `lifespan` context manager pattern for the FastAPI application
- Initializing the Integration Hub alongside other core components
- Error handling during initialization
- Proper cleanup during application shutdown

```python
# From app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events handler for FastAPI
    - Startup: Connect to database, cache, initialize components
    - Shutdown: Cleanup resources
    """
    # Startup
    logger.info("Starting Cortex Core")

    # Connect to database
    await db.connect()

    # Connect to Redis
    await connect_redis()

    # Initialize and store event system in app state
    from app.components.event_system import get_event_system
    app.state.event_system = get_event_system()
    logger.info("Event System initialized")

    # Initialize SSE service
    try:
        # Use the new modular SSE service
        from app.components.sse import get_sse_service
        app.state.sse_service = get_sse_service()
        await app.state.sse_service.initialize()
        logger.info("SSE Service initialized")
    except Exception as e:
        logger.error(f"Error initializing SSE service: {e}")

    # Initialize Integration Hub for MCP connections
    try:
        from app.components.integration_hub import get_integration_hub
        app.state.integration_hub = get_integration_hub()
        await app.state.integration_hub.startup()
        logger.info("Integration Hub initialized")
    except Exception as e:
        logger.error(f"Error initializing Integration Hub: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Cortex Core")

    # Clean up Integration Hub
    try:
        if hasattr(app.state, "integration_hub"):
            await app.state.integration_hub.shutdown()
            logger.info("Integration Hub cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up Integration Hub: {e}")

    # Clean up other components
    # ...

# Create FastAPI application with lifespan
app = FastAPI(
    title="Cortex Core",
    description="Central orchestration engine for the Cortex Platform",
    version="0.1.0",
    lifespan=lifespan,
)
```

The implementation uses a singleton pattern for the Integration Hub, eliminating the need for a separate dependency function. The singleton getter function is provided directly by the module:

```python
# From app/components/integration_hub.py
# Singleton instance
_integration_hub: Optional[IntegrationHub] = None

def get_integration_hub() -> IntegrationHub:
    """Get the singleton IntegrationHub instance"""
    global _integration_hub
    if _integration_hub is None:
        _integration_hub = IntegrationHub()
    return _integration_hub
```

### 4. Add API Routes ✅

Create API endpoints for interacting with MCP services.

**Status: Completed**

API endpoints for MCP integration have been implemented in `app/api/integrations.py` with the following features:

- Consistent error handling for different types of errors
- Authentication requirements for all endpoints
- Clean API design following RESTful principles
- Type-checked request and response models

```python
# From app/api/integrations.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel

from app.components.integration_hub import IntegrationHub, get_integration_hub
from app.exceptions import ServiceError
from app.api.auth import get_current_user


router = APIRouter(prefix="/experts")


class ToolCall(BaseModel):
    """Request model for calling a tool on a domain expert"""
    arguments: Dict[str, Any]


@router.get("/", response_model=List[str])
async def list_experts(
    integration_hub: IntegrationHub = Depends(get_integration_hub),
    _user = Depends(get_current_user)
):
    """
    List all available domain experts
    """
    try:
        return await integration_hub.list_experts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list experts: {str(e)}")


@router.get("/{expert_name}/tools", response_model=Dict[str, Any])
async def list_expert_tools(
    expert_name: str,
    integration_hub: IntegrationHub = Depends(get_integration_hub),
    _user = Depends(get_current_user)
):
    """
    List all tools available from a specific domain expert
    """
    try:
        return await integration_hub.list_expert_tools(expert_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@router.post("/{expert_name}/tools/{tool_name}", response_model=Dict[str, Any])
async def invoke_expert_tool(
    expert_name: str,
    tool_name: str,
    tool_call: ToolCall,
    integration_hub: IntegrationHub = Depends(get_integration_hub),
    _user = Depends(get_current_user)
):
    """
    Invoke a tool on a specific domain expert
    """
    try:
        return await integration_hub.invoke_expert_tool(
            expert_name=expert_name,
            tool_name=tool_name,
            arguments=tool_call.arguments
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invoke tool: {str(e)}")


@router.get("/{expert_name}/resources/{uri:path}", response_model=Dict[str, Any])
async def read_expert_resource(
    expert_name: str,
    uri: str,
    integration_hub: IntegrationHub = Depends(get_integration_hub),
    _user = Depends(get_current_user)
):
    """
    Read a resource from a specific domain expert
    """
    try:
        return await integration_hub.read_expert_resource(
            expert_name=expert_name,
            uri=uri
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read resource: {str(e)}")
```

The router is included in `app/main.py`:

```python
# From app/main.py
# Import routers
from app.api import auth, sse, workspaces, conversations, monitoring, integrations

# Include routers
app.include_router(integrations.router, prefix="/integrations", tags=["Integrations"])
```

**Notable differences from guide:**

1. The implementation uses a model for tool call arguments instead of directly getting JSON
2. The API endpoints return structured JSON responses, not raw content/MIME responses
3. The current implementation doesn't include event system integration (marked as a pending feature in step 5)
4. Authentication is required for all endpoints via `get_current_user` dependency

### 5. Implement Event System Integration ❌

Define MCP-specific event types for the event system.

**Status: Not Implemented**

The event system integration for MCP has not yet been implemented. The current codebase doesn't include the following features that would be part of a complete implementation:

1. MCP-specific event types in the event system
2. Event publication for MCP-related actions (connection, tool execution, etc.)
3. Integration of the event system with the API routes for MCP tool execution

The planned implementation would involve adding MCP-related event types:

```python
# To be added to app/components/event_system.py or where event types are defined

# MCP-related event types
MCP_EVENT_TYPES = [
    "mcp.connection.established",  # When a connection to an MCP endpoint is established
    "mcp.connection.failed",       # When a connection attempt fails
    "mcp.connection.closed",       # When a connection is closed
    "mcp.tool.execution.started",  # When a tool execution starts
    "mcp.tool.execution.completed", # When a tool execution completes
    "mcp.tool.execution.failed",   # When a tool execution fails
]
```

And updating the API routes to publish events:

```python
# Example of event integration in API routes (not yet implemented)
@router.post("/{expert_name}/tools/{tool_name}", response_model=Dict[str, Any])
async def invoke_expert_tool(
    expert_name: str,
    tool_name: str,
    tool_call: ToolCall,
    request: Request,
    integration_hub: IntegrationHub = Depends(get_integration_hub),
    _user = Depends(get_current_user)
):
    """
    Invoke a tool on a specific domain expert
    """
    try:
        # Extract correlation ID if present in headers
        correlation_id = request.headers.get("X-Correlation-ID")

        # Publish event before execution
        await request.app.state.event_system.publish(
            event_type="mcp.tool.execution.started",
            data={
                "expert": expert_name,
                "tool": tool_name,
                "arguments": tool_call.arguments,
                "correlation_id": correlation_id
            },
            source="integration_hub"
        )

        # Execute the tool
        result = await integration_hub.invoke_expert_tool(
            expert_name=expert_name,
            tool_name=tool_name,
            arguments=tool_call.arguments
        )

        # Publish success event
        await request.app.state.event_system.publish(
            event_type="mcp.tool.execution.completed",
            data={
                "expert": expert_name,
                "tool": tool_name,
                "correlation_id": correlation_id
            },
            source="integration_hub"
        )

        return result
    except Exception as e:
        # Publish failure event
        await request.app.state.event_system.publish(
            event_type="mcp.tool.execution.failed",
            data={
                "expert": expert_name,
                "tool": tool_name,
                "error": str(e),
                "correlation_id": correlation_id
            },
            source="integration_hub"
        )
        raise  # Re-raise the appropriate exception
```

**Implementation note:** This feature will be completed in a future update to enable observability and monitoring of MCP operations.

### 6. Update Dependencies ✅

Update package dependencies to include the MCP SDK.

**Status: Completed**

The codebase has been updated to handle MCP SDK dependencies with graceful fallbacks for when the library isn't available. The implementation includes:

1. Conditional imports for MCP in the Integration Hub
2. Stub implementation for the ClientSession for testing when MCP isn't available
3. Error handling for missing dependencies

```python
# From app/components/integration_hub.py
# Import libraries for MCP when available
try:
    from mcp.client.session import ClientSession  # type: ignore
    from mcp.client.sse import sse_client  # type: ignore
except ImportError:
    # Define a stub ClientSession for when MCP isn't available
    class ClientSession:  # type: ignore
        """Stub implementation of ClientSession for testing and type checking"""

        def __init__(self, read_stream=None, write_stream=None):
            """Initialize with optional streams"""
            pass

        async def initialize(self):
            """Initialize the session"""
            return {"version": "stub-1.0.0", "capabilities": {}}

        async def list_tools(self):
            """List available tools"""
            return {"tools": []}

        async def call_tool(self, name, arguments):
            """Call a tool"""
            return {"result": "success"}

        async def read_resource(self, uri):
            """Read a resource"""
            return {"content": "test"}

        async def shutdown(self):
            """Shut down the session"""
            pass
```

**Note:** While the current implementation has fallbacks for testing without the MCP library, in a production environment the MCP SDK should be properly installed. The package management configuration can be updated in `pyproject.toml`:

```toml
# Dependencies in pyproject.toml (recommended for production use)
[tool.poetry.dependencies]
python = "^3.8"
# ... other dependencies ...
mcp = "^0.1.0"

[tool.poetry.extras]
cli = ["mcp[cli]"]
```

Installation command:

```bash
uv pip install -e .
```

## Domain Expert Implementation ❌

Domain Expert services should implement MCP servers using the FastMCP API.

**Status: Not Implemented**

No Domain Expert services have been implemented yet. The infrastructure for connecting to Domain Experts is in place via the Integration Hub, but the actual Domain Expert implementations are still pending.

Here's a template for creating a Domain Expert service using the FastMCP API from the Python SDK:

```python
# domain_expert_service.py
from mcp.server.fastmcp import FastMCP, Context
from typing import Dict, Any, AsyncIterator
from contextlib import asynccontextmanager

# Create a typed context for lifespan
class ExpertContext:
    def __init__(self, db_connection):
        self.db = db_connection

# Create a lifespan manager for setup/teardown
@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[ExpertContext]:
    # Setup
    db_connection = await setup_database()
    try:
        yield ExpertContext(db_connection)
    finally:
        # Cleanup
        await db_connection.close()

# Create the FastMCP server with lifespan
mcp = FastMCP("Domain Expert Name", lifespan=lifespan)

@mcp.tool()
async def example_tool(parameter: str, ctx: Context) -> Dict[str, Any]:
    """Example tool description"""
    # Access lifespan context
    db = ctx.request_context.lifespan_context.db

    # Show progress
    ctx.info(f"Processing: {parameter}")

    # Implement tool logic
    result = "Example result"

    return {
        "content": [
            {
                "type": "text",
                "text": result
            }
        ]
    }

@mcp.resource("example://{id}")
def get_example(id: str) -> str:
    """Get example data"""
    return f"Example data for {id}"

@mcp.prompt()
def example_prompt(parameter: str) -> str:
    """Example prompt template"""
    return f"Please process this parameter: {parameter}"

# Run the server
if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=5001)
```

**Implementation plan:** Domain Expert services will be developed as separate microservices that implement MCP servers. These will include specialized services like:

1. Code Assistant - For code-related tasks
2. Deep Research - For in-depth research capabilities
3. Data Analysis - For data processing and visualization
4. Document Processing - For document understanding and manipulation

Each Domain Expert will implement the necessary tools, resources, and prompts relevant to its specific domain of expertise.

## Testing ✅

### Integration Hub Testing

**Status: Completed**

Comprehensive tests for the Integration Hub component have been implemented in `tests/components/test_integration_hub.py`. The test suite includes:

1. Tests for both `CortexMcpClient` and `IntegrationHub` classes
2. Mocking of MCP dependencies and network interactions
3. Testing of error handling and edge cases
4. Circuit breaker pattern testing

Key features of the implemented tests:

```python
# From tests/components/test_integration_hub.py
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import json

from app.components.integration_hub import (
    IntegrationHub,
    CortexMcpClient,
    get_integration_hub
)


class TestCortexMcpClient:
    """Test suite for the CortexMcpClient class"""

    @pytest.fixture
    def mock_mcp_client(self):
        """Create a mock for the MCP client"""
        mock_client = AsyncMock()
        # Setup mock methods...
        return mock_client

    @pytest.mark.asyncio
    async def test_connect(self, mock_mcp_client):
        """Test connection initialization"""
        # Test connection logic...

    @pytest.mark.asyncio
    async def test_list_tools(self, mock_mcp_client):
        """Test listing tools"""
        # Test list_tools method...

    @pytest.mark.asyncio
    async def test_call_tool(self, mock_mcp_client):
        """Test calling a tool"""
        # Test call_tool method...

    @pytest.mark.asyncio
    async def test_read_resource(self, mock_mcp_client):
        """Test reading a resource"""
        # Test read_resource method...

    @pytest.mark.asyncio
    async def test_close(self, mock_mcp_client):
        """Test closing the connection"""
        # Test connection closing...

    @pytest.mark.asyncio
    async def test_connect_error_handling(self):
        """Test error handling during connection"""
        # Test error handling...


class TestIntegrationHub:
    """Test suite for the IntegrationHub class"""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with test MCP endpoints"""
        # Setup mock settings...

    @pytest.fixture
    def mock_client(self):
        """Create a mock for the CortexMcpClient"""
        # Setup mock client...

    @pytest.mark.asyncio
    async def test_startup(self, mock_settings, mock_client):
        """Test startup initializes connections to all endpoints"""
        # Test startup logic...

    @pytest.mark.asyncio
    async def test_shutdown(self, mock_settings, mock_client):
        """Test shutdown closes all connections"""
        # Test shutdown logic...

    @pytest.mark.asyncio
    async def test_list_experts(self, mock_settings):
        """Test listing available experts"""
        # Test list_experts method...

    @pytest.mark.asyncio
    async def test_list_expert_tools(self, mock_settings, mock_client):
        """Test listing tools for a specific expert"""
        # Test list_expert_tools method...

    @pytest.mark.asyncio
    async def test_list_expert_tools_unknown_expert(self, mock_settings):
        """Test listing tools for an unknown expert"""
        # Test behavior with unknown expert...

    @pytest.mark.asyncio
    async def test_invoke_expert_tool(self, mock_settings, mock_client):
        """Test invoking a tool on a specific expert"""
        # Test invoke_expert_tool method...

    @pytest.mark.asyncio
    async def test_read_expert_resource(self, mock_settings, mock_client):
        """Test reading a resource from a specific expert"""
        # Test read_expert_resource method...


def test_get_integration_hub():
    """Test the singleton getter function"""
    # Test singleton pattern...
```

### API Route Testing

Currently, there are no specific tests for the MCP API routes in the test suite. While comprehensive tests exist for the Integration Hub component itself, the API layer tests for MCP integrations should be added in a future update.

Recommended tests to be added for the API routes:

```python
# Suggested implementation for tests/api/test_integrations.py
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def mock_integration_hub():
    """Mock the Integration Hub"""
    with patch("app.components.integration_hub.get_integration_hub") as mock_get_hub:
        mock_hub = AsyncMock()
        # Mock methods...
        yield mock_hub

def test_list_experts(mock_integration_hub):
    """Test listing domain experts endpoint"""
    # Test list_experts endpoint...

def test_list_expert_tools(mock_integration_hub):
    """Test listing tools endpoint"""
    # Test list_expert_tools endpoint...

def test_invoke_expert_tool(mock_integration_hub):
    """Test invoking a tool endpoint"""
    # Test invoke_expert_tool endpoint...

def test_invoke_expert_tool_unknown_expert(mock_integration_hub):
    """Test behavior when expert is not found"""
    # Test error handling...

def test_read_expert_resource(mock_integration_hub):
    """Test reading a resource endpoint"""
    # Test read_expert_resource endpoint...
```

## Troubleshooting

### Connection Issues

If you encounter problems connecting to MCP endpoints:

1. **Check Endpoint URL**: Verify the endpoint URL is correct and accessible

   ```bash
   curl -v http://localhost:5001/mcp
   ```

2. **Transport Compatibility**: Ensure the endpoint supports the SSE transport

   ```python
   # Domain expert must be configured with SSE transport
   mcp.run(transport="sse", host="0.0.0.0", port=5001)
   ```

3. **Authentication**: Verify API keys are correctly configured if required

   ```
   # Check environment variables or .env file
   MCP_ENDPOINTS='[{"name":"expert", "endpoint":"http://localhost:5001/mcp", "type":"expert", "api_key":"your-key"}]'
   ```

4. **Firewall/Network**: Check for network restrictions between services

### Tool Execution Errors

For issues with tool execution:

1. **Tool Exists**: Verify the tool exists on the domain expert

   ```bash
   # List tools on the expert
   curl http://localhost:4000/integrations/experts/expert_name/tools
   ```

2. **Parameter Validation**: Check parameter types match the tool's schema

   ```python
   # Domain expert tool definition
   @mcp.tool()
   def example_tool(parameter: str) -> Dict[str, Any]:
       # Parameter type must be string
   ```

3. **Error Handling**: Look for detailed error messages in the response or logs

### General Debugging

1. **Logs**: Check the logs for detailed error messages

   ```bash
   tail -f logs/cortex.log
   ```

2. **Circuit Breaker**: Check if the circuit breaker has tripped for an endpoint

   ```python
   # Get the current state of a circuit breaker
   breaker = integration_hub.circuit_breakers["expert_name"]
   print(f"Circuit state: {breaker.state}, Failure count: {breaker.failure_count}")
   ```

3. **MCP Inspector**: Use the MCP Inspector to test connections directly (when available)
   ```bash
   mcp inspect http://localhost:5001/mcp
   ```

## Implementation Progress Summary

Here's a summary of the current MCP implementation status:

| Component                    | Status       | Notes                                                |
| ---------------------------- | ------------ | ---------------------------------------------------- |
| Integration Hub              | ✅ Completed | Enhanced with circuit breaker and singleton pattern  |
| Configuration                | ✅ Completed | Supports both JSON and individual endpoint config    |
| Application Lifecycle        | ✅ Completed | Proper startup/shutdown with error handling          |
| API Routes                   | ✅ Completed | Authentication, error handling, and clean API design |
| Event System Integration     | ❌ Pending   | Event publication for MCP operations                 |
| Dependencies                 | ✅ Completed | Graceful fallbacks for testing without MCP           |
| Domain Expert Implementation | ❌ Pending   | Services will be separate microservices              |
| Testing                      | ✅ Completed | Comprehensive tests for Integration Hub              |

This guide provides a comprehensive foundation for implementing MCP integration in the Cortex Core project. The core infrastructure for connecting to Domain Expert services is in place, but the actual Domain Expert implementations and some enhanced features like event system integration are still pending.
