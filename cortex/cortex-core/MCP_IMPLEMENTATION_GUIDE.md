# MCP Implementation Guide

This guide provides step-by-step instructions for implementing the Model Context Protocol (MCP) integration within the Cortex Core architecture. MCP is used for internal service-to-service communication between Cortex Core and Domain Expert services.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Implementation Steps](#implementation-steps)
  - [1. Create the Integration Hub Component](#1-create-the-integration-hub-component)
  - [2. Update Configuration](#2-update-configuration)
  - [3. Update Application Lifecycle](#3-update-application-lifecycle)
  - [4. Add API Routes](#4-add-api-routes)
  - [5. Implement Event System Integration](#5-implement-event-system-integration)
  - [6. Update Dependencies](#6-update-dependencies)
- [Domain Expert Implementation](#domain-expert-implementation)
- [Testing](#testing)
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

### 1. Create the Integration Hub Component

Create a new file `app/components/integration_hub.py` that implements the Integration Hub:

```python
# app/components/integration_hub.py
from typing import Dict, Any, List, Optional, AsyncIterator
from contextlib import asynccontextmanager
import logging
from mcp.client import ClientSession
from mcp.client.sse import sse_client
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class IntegrationHub:
    """Manages connections to Domain Expert services via MCP"""
    
    def __init__(self):
        self.settings = get_settings()
        self.sessions: Dict[str, ClientSession] = {}
        
    async def startup(self):
        """Initialize connections to all configured MCP endpoints"""
        for endpoint in self.settings.mcp.endpoints:
            try:
                # Create transport for SSE connection
                read_stream, write_stream = await sse_client({
                    "url": endpoint.endpoint,
                    "headers": {"X-API-Key": endpoint.api_key} if endpoint.api_key else {}
                })
                
                # Create a client session with the streams
                session = ClientSession(read_stream, write_stream)
                
                # Initialize the session
                await session.initialize()
                
                # Store the session
                self.sessions[endpoint.name] = session
                
                logger.info(f"Connected to MCP endpoint: {endpoint.name}")
            except Exception as e:
                logger.error(f"Failed to connect to MCP endpoint {endpoint.name}: {str(e)}")
                
    async def shutdown(self):
        """Close all MCP connections"""
        for name, session in self.sessions.items():
            try:
                await session.shutdown()
                logger.info(f"Closed connection to MCP endpoint: {name}")
            except Exception as e:
                logger.error(f"Error closing MCP connection to {name}: {str(e)}")
    
    async def list_experts(self) -> List[str]:
        """List all available domain experts"""
        return list(self.sessions.keys())
    
    async def list_expert_tools(self, expert_name: str) -> Dict[str, Any]:
        """List all tools available from a specific domain expert"""
        if expert_name not in self.sessions:
            raise ValueError(f"Unknown domain expert: {expert_name}")
            
        session = self.sessions[expert_name]
        return await session.list_tools()
    
    async def invoke_expert_tool(self, expert_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool on a specific domain expert"""
        if expert_name not in self.sessions:
            raise ValueError(f"Unknown domain expert: {expert_name}")
            
        session = self.sessions[expert_name]
        return await session.call_tool(tool_name, arguments=arguments)
    
    async def read_expert_resource(self, expert_name: str, uri: str) -> tuple[bytes, str]:
        """Read a resource from a specific domain expert"""
        if expert_name not in self.sessions:
            raise ValueError(f"Unknown domain expert: {expert_name}")
            
        session = self.sessions[expert_name]
        # Per SDK, read_resource returns a tuple of (content, mime_type)
        return await session.read_resource(uri)
    
    async def list_expert_prompts(self, expert_name: str) -> Dict[str, Any]:
        """List all prompts available from a specific domain expert"""
        if expert_name not in self.sessions:
            raise ValueError(f"Unknown domain expert: {expert_name}")
            
        session = self.sessions[expert_name]
        return await session.list_prompts()
```

### 2. Update Configuration

Update the configuration in `app/config.py` to support MCP endpoints:

```python
# Add to app/config.py
from pydantic import BaseModel, BaseSettings, validator
from typing import List, Optional

class McpEndpoint(BaseModel):
    """MCP endpoint configuration"""
    name: str
    endpoint: str
    type: str
    api_key: Optional[str] = None
    timeout: Optional[int] = 30
    max_retries: Optional[int] = 3

class McpConfig(BaseSettings):
    """MCP configuration - for internal service-to-service communication only"""
    internal_only: bool = True
    endpoints: List[McpEndpoint] = []
    
    # Add validation methods
    @validator('endpoints')
    def validate_endpoints(cls, v):
        """Validate that endpoint names are unique"""
        names = [endpoint.name for endpoint in v]
        if len(names) != len(set(names)):
            raise ValueError("MCP endpoint names must be unique")
        return v

# Update the main settings class to include MCP config
class Settings(BaseSettings):
    # Existing settings...
    
    # Add MCP configuration
    mcp: McpConfig = McpConfig()
    
    class Config:
        env_file = ".env"
```

Update the `.env` file or environment variables to configure MCP endpoints:

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

### 3. Update Application Lifecycle

Update the application lifecycle in `app/main.py` to initialize and manage the Integration Hub:

```python
# Add to imports section in app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.components.integration_hub import IntegrationHub

# Update or add the lifespan function
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    logger.info("Starting application")
    
    # Initialize existing components
    # ...
    
    # Initialize Integration Hub
    integration_hub = IntegrationHub()
    await integration_hub.startup()
    app.state.integration_hub = integration_hub
    
    yield
    
    # Shutdown in reverse order
    logger.info("Shutting down application")
    
    # Close Integration Hub connections
    await app.state.integration_hub.shutdown()
    
    # Shutdown other components
    # ...

# Create FastAPI application with lifespan
app = FastAPI(lifespan=lifespan)
```

Add a dependency function to access the Integration Hub:

```python
# Add to app/dependencies.py or appropriate location
from fastapi import Request
from app.components.integration_hub import IntegrationHub

async def get_integration_hub(request: Request) -> IntegrationHub:
    """Get the Integration Hub instance"""
    return request.app.state.integration_hub
```

### 4. Add API Routes

Create API endpoints for interacting with MCP services in `app/api/integration.py`:

```python
# app/api/integration.py
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from typing import Dict, Any, List
from app.components.integration_hub import IntegrationHub
from app.dependencies import get_integration_hub

router = APIRouter()

@router.get("/experts", response_model=List[str])
async def list_experts(integration_hub: IntegrationHub = Depends(get_integration_hub)):
    """List all available domain experts"""
    return await integration_hub.list_experts()

@router.get("/experts/{expert_name}/tools")
async def list_expert_tools(
    expert_name: str,
    integration_hub: IntegrationHub = Depends(get_integration_hub)
):
    """List all tools available from a specific domain expert"""
    try:
        return await integration_hub.list_expert_tools(expert_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/experts/{expert_name}/tools/{tool_name}")
async def invoke_expert_tool(
    expert_name: str,
    tool_name: str,
    arguments: Dict[str, Any],
    request: Request,
    integration_hub: IntegrationHub = Depends(get_integration_hub)
):
    """Invoke a tool on a specific domain expert"""
    try:
        # Extract correlation ID if present in headers
        correlation_id = request.headers.get("X-Correlation-ID")
        
        # Publish event before execution
        await request.app.state.event_system.publish(
            event_type="mcp.tool.execution.started",
            data={
                "expert": expert_name,
                "tool": tool_name,
                "arguments": arguments,
                "correlation_id": correlation_id
            },
            source="integration_hub"
        )
        
        # Execute the tool
        result = await integration_hub.invoke_expert_tool(expert_name, tool_name, arguments)
        
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
    except ValueError as e:
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
        raise HTTPException(status_code=404, detail=str(e))
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
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/experts/{expert_name}/resources/{uri:path}")
async def read_expert_resource(
    expert_name: str,
    uri: str,
    integration_hub: IntegrationHub = Depends(get_integration_hub)
):
    """Read a resource from a specific domain expert"""
    try:
        content, mime_type = await integration_hub.read_expert_resource(expert_name, uri)
        return Response(content=content, media_type=mime_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/experts/{expert_name}/prompts")
async def list_expert_prompts(
    expert_name: str,
    integration_hub: IntegrationHub = Depends(get_integration_hub)
):
    """List all prompts available from a specific domain expert"""
    try:
        return await integration_hub.list_expert_prompts(expert_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

Include the integration router in `app/main.py`:

```python
# Add to app/main.py
from app.api.integration import router as integration_router

# Include the router with other routers
app.include_router(integration_router, prefix="/api/v1/integration", tags=["Integration"])
```

### 5. Implement Event System Integration

Define MCP-specific event types for the event system:

```python
# Add to app/components/event_system.py or where event types are defined

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

### 6. Update Dependencies

Update `pyproject.toml` to include the MCP SDK:

```toml
# Update dependencies in pyproject.toml
[tool.poetry.dependencies]
python = "^3.8"
# ... other dependencies ...
mcp = "^0.1.0"

[tool.poetry.dev-dependencies]
# ... dev dependencies ...

[tool.poetry.extras]
cli = ["mcp[cli]"]
```

Install the dependencies:

```bash
uv pip install -e .
```

## Domain Expert Implementation

Domain Expert services should implement MCP servers using the FastMCP API. Here's a template for creating a Domain Expert service:

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

## Testing

### Integration Hub Testing

Create tests for the Integration Hub component:

```python
# tests/components/test_integration_hub.py
import pytest
from unittest.mock import AsyncMock, patch
from app.components.integration_hub import IntegrationHub

@pytest.fixture
def mock_settings():
    """Mock the settings with test MCP endpoints"""
    with patch("app.components.integration_hub.get_settings") as mock_get_settings:
        mock_settings = AsyncMock()
        mock_settings.mcp.endpoints = [
            {"name": "test_expert", "endpoint": "http://localhost:5001/mcp", "type": "test"}
        ]
        mock_get_settings.return_value = mock_settings
        yield mock_get_settings

@pytest.fixture
async def mock_client_session():
    """Mock the MCP ClientSession"""
    with patch("app.components.integration_hub.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        
        # Mock MCP client methods
        mock_session.initialize = AsyncMock()
        mock_session.shutdown = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value={"tools": []})
        mock_session.call_tool = AsyncMock(return_value={"result": "success"})
        mock_session.read_resource = AsyncMock(return_value=(b"content", "text/plain"))
        
        yield mock_session

@pytest.fixture
async def mock_sse_client():
    """Mock the SSE client transport"""
    with patch("app.components.integration_hub.sse_client") as mock_sse:
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_sse.return_value = (mock_read, mock_write)
        yield mock_sse

@pytest.mark.asyncio
async def test_integration_hub_startup(mock_settings, mock_client_session, mock_sse_client):
    """Test Integration Hub startup and connection initialization"""
    hub = IntegrationHub()
    await hub.startup()
    
    # Verify SSE client was created with correct parameters
    mock_sse_client.assert_called_once()
    
    # Verify session was initialized
    mock_client_session.initialize.assert_called_once()
    
    # Verify session was stored
    assert "test_expert" in hub.sessions
    assert hub.sessions["test_expert"] == mock_client_session

@pytest.mark.asyncio
async def test_integration_hub_invoke_tool(mock_settings, mock_client_session, mock_sse_client):
    """Test invoking a tool through Integration Hub"""
    hub = IntegrationHub()
    await hub.startup()
    
    # Call a tool
    result = await hub.invoke_expert_tool("test_expert", "test_tool", {"param": "value"})
    
    # Verify tool was called with correct parameters
    mock_client_session.call_tool.assert_called_once_with("test_tool", arguments={"param": "value"})
    
    # Verify result
    assert result == {"result": "success"}

@pytest.mark.asyncio
async def test_integration_hub_unknown_expert(mock_settings, mock_client_session, mock_sse_client):
    """Test behavior with unknown expert"""
    hub = IntegrationHub()
    await hub.startup()
    
    # Try to call a tool on an unknown expert
    with pytest.raises(ValueError, match="Unknown domain expert: unknown"):
        await hub.invoke_expert_tool("unknown", "test_tool", {"param": "value"})
```

### API Route Testing

Create tests for the integration API endpoints:

```python
# tests/api/test_integration.py
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def mock_integration_hub():
    """Mock the Integration Hub"""
    with patch("app.dependencies.get_integration_hub") as mock_get_hub:
        mock_hub = AsyncMock()
        mock_get_hub.return_value = mock_hub
        
        # Mock methods
        mock_hub.list_experts = AsyncMock(return_value=["expert1", "expert2"])
        mock_hub.list_expert_tools = AsyncMock(return_value={"tools": []})
        mock_hub.invoke_expert_tool = AsyncMock(return_value={"result": "success"})
        
        yield mock_hub

def test_list_experts(mock_integration_hub):
    """Test listing domain experts endpoint"""
    with TestClient(app) as client:
        response = client.get("/api/v1/integration/experts")
        
        # Verify correct status code and response
        assert response.status_code == 200
        assert response.json() == ["expert1", "expert2"]
        
        # Verify method was called
        mock_integration_hub.list_experts.assert_called_once()

def test_invoke_expert_tool(mock_integration_hub):
    """Test invoking a tool endpoint"""
    with TestClient(app) as client:
        # Prepare test data
        expert = "expert1"
        tool = "test_tool"
        arguments = {"param": "value"}
        
        # Make the request
        response = client.post(
            f"/api/v1/integration/experts/{expert}/tools/{tool}",
            json=arguments
        )
        
        # Verify correct status code and response
        assert response.status_code == 200
        assert response.json() == {"result": "success"}
        
        # Verify method was called with correct parameters
        mock_integration_hub.invoke_expert_tool.assert_called_once_with(
            expert, tool, arguments
        )

def test_invoke_expert_tool_unknown_expert(mock_integration_hub):
    """Test behavior when expert is not found"""
    # Configure mock to raise ValueError
    mock_integration_hub.invoke_expert_tool.side_effect = ValueError("Unknown domain expert: unknown")
    
    with TestClient(app) as client:
        # Make the request
        response = client.post(
            "/api/v1/integration/experts/unknown/tools/test_tool",
            json={"param": "value"}
        )
        
        # Verify correct status code and error message
        assert response.status_code == 404
        assert "Unknown domain expert: unknown" in response.json()["detail"]
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
   curl http://localhost:4000/api/v1/integration/experts/expert_name/tools
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

2. **Event Monitoring**: Use the event system to monitor MCP events
   ```python
   # Subscribe to MCP events
   await event_system.subscribe("mcp.*", handle_mcp_event)
   ```

3. **MCP Inspector**: Use the MCP Inspector to test connections directly
   ```bash
   mcp inspect http://localhost:5001/mcp
   ```

This guide provides a comprehensive foundation for implementing MCP integration in the Cortex Core project. Follow these steps to enable standardized communication between Cortex Core and Domain Expert services, maintaining a clean, modular architecture with well-defined interfaces.