# MCP Implementation Guide for Simplified Cortex

This document outlines the key requirements and implementation approach for the Model Context Protocol (MCP) in our simplified Cortex design. MCP is a critical component for service-to-service communication within the system.

## Core MCP Requirements

1. **Communication Protocol**: MCP will be used for all backend service-to-service communication, including:
   - Domain Expert services (e.g., Code Assistant, Deep Research)
   - Memory System access
   - Specialized AI services

2. **Transport Protocol**: Server-Sent Events (SSE) will be used as the underlying transport protocol for MCP.

3. **Usage Scope**: MCP is strictly for internal service communication, not for client-facing APIs.

## Simplified MCP Client Implementation

While retaining the core MCP functionality, we can simplify the current implementation:

### Simplified Connection Management

```python
class SimplifiedMcpClient:
    """Streamlined MCP client implementation"""
    
    def __init__(self, endpoint: str, service_name: str):
        self.endpoint = endpoint
        self.service_name = service_name
        self.client = None
        self._state = "disconnected"
        self._health_check_task = None
        
    async def connect(self) -> None:
        """Connect to MCP server with simplified error handling"""
        # If already connected, return
        if self._state == "connected" and self.client is not None:
            return
            
        self._state = "connecting"
        
        try:
            # Create SSE client
            async with sse_client(self.endpoint) as (read_stream, write_stream):
                # Create client session
                self.client = ClientSession(read_stream, write_stream)
                
                # Initialize with reasonable timeout
                server_info = await asyncio.wait_for(self.client.initialize(), timeout=10.0)
                
                # Update state
                self._state = "connected"
                self._server_info = server_info
                
                # Start background health check
                self._start_health_check()
                
                # Keep connection open until explicitly closed
                await self._connection_maintainer()
                
        except Exception as e:
            self._state = "error"
            self.client = None
            raise
            
    async def close(self) -> None:
        """Close the MCP connection"""
        # Cancel health check
        if self._health_check_task:
            self._health_check_task.cancel()
            
        # Change state and clear client
        self._state = "disconnected"
        self.client = None
```

### Core Operations

```python
class SimplifiedMcpClient:
    # ... (initialization and connection code) ...
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools from the MCP server"""
        if not self.client or self._state != "connected":
            await self.connect()
            
        try:
            result = await asyncio.wait_for(self.client.list_tools(), timeout=5.0)
            return self._normalize_result(result)
        except Exception as e:
            logger.error(f"Error listing tools: {str(e)}")
            return {"tools": [], "error": str(e)}
            
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        if not self.client or self._state != "connected":
            await self.connect()
            
        try:
            result = await self.client.call_tool(name=name, arguments=arguments)
            return self._normalize_result(result)
        except Exception as e:
            logger.error(f"Error calling tool {name}: {str(e)}")
            raise
            
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the MCP server"""
        if not self.client or self._state != "connected":
            await self.connect()
            
        try:
            uri_param = AnyUrl(uri) if isinstance(uri, str) else uri
            result = await self.client.read_resource(uri=uri_param)
            # Process result...
            return {"content": [...]}
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {str(e)}")
            raise
```

### Simplified Error Handling

The current implementation has extensive error handling that adds significant complexity. We can simplify while keeping the essential error recovery:

```python
async def _health_check_loop(self) -> None:
    """Simplified health check loop"""
    try:
        while True:
            # Basic interval with minor jitter
            await asyncio.sleep(30 + random.uniform(-3, 3))
            
            if self._state != "connected" or not self.client:
                continue
                
            try:
                # Simple health check
                await asyncio.wait_for(self.client.list_tools(), timeout=5.0)
                logger.debug(f"Health check passed for {self.service_name}")
            except Exception as e:
                logger.warning(f"Health check failed: {str(e)}")
                # Simple reconnection logic
                self._state = "reconnecting"
                self.client = None
                asyncio.create_task(self.connect())
                
    except asyncio.CancelledError:
        logger.debug("Health check cancelled")
```

## Integration Hub Simplification

The Integration Hub can also be simplified while maintaining its core functionality:

```python
class SimplifiedIntegrationHub:
    """Manages connections to Domain Experts and other services via MCP"""
    
    def __init__(self, endpoints: List[Dict[str, str]]):
        self.endpoints = endpoints
        self.clients = {}  # name -> client mapping
        
    async def startup(self) -> None:
        """Initialize clients but don't wait for connections"""
        for endpoint in self.endpoints:
            name = endpoint["name"]
            url = endpoint["endpoint"]
            self.clients[name] = SimplifiedMcpClient(url, name)
            # Initialize in background without waiting
            asyncio.create_task(self.clients[name].connect())
            
    async def list_experts(self) -> List[str]:
        """List all available experts"""
        return list(self.clients.keys())
        
    async def list_expert_tools(self, expert_name: str) -> Dict[str, Any]:
        """List tools available from a specific expert"""
        if expert_name not in self.clients:
            raise ValueError(f"Unknown expert: {expert_name}")
            
        client = self.clients[expert_name]
        return await client.list_tools()
        
    async def invoke_expert_tool(
        self, expert_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invoke a tool on a specific expert"""
        if expert_name not in self.clients:
            raise ValueError(f"Unknown expert: {expert_name}")
            
        client = self.clients[expert_name]
        return await client.call_tool(name=tool_name, arguments=arguments)
```

## MCP Server Side Implementation

For domain expert and memory system services, we'll use the FastMCP API to implement MCP servers:

```python
from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(mcp: FastMCP):
    """Setup and cleanup domain expert resources"""
    # Setup resources
    print("Starting domain expert...")
    resources = {}  # Initialize resources
    
    try:
        yield resources  # Server runs with these resources
    finally:
        # Cleanup resources
        print("Shutting down domain expert...")

# Create the MCP server
mcp = FastMCP(
    name="MemorySystem",
    description="MCP-based memory system service",
    lifespan=lifespan
)

@mcp.tool()
async def store_memory(
    workspace_id: str,
    memory_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Store a memory item in the specified workspace"""
    # Implementation...
    return {"memory_id": "..."}

@mcp.tool()
async def retrieve_memory(
    workspace_id: str,
    query: Optional[str] = None,
    memory_type: Optional[str] = None,
    metadata_filter: Optional[Dict[str, Any]] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """Retrieve memory items matching criteria"""
    # Implementation...
    return {"memories": [...]}
```

## Key Simplifications from Original Implementation

1. **Connection Management**: Streamlined connection logic with clearer responsibility boundaries
2. **Error Handling**: Reduced error handling complexity while maintaining resilience
3. **Health Checking**: Simplified health check mechanism with basic reconnection
4. **Resource Management**: Clearer lifecycle management for MCP resources
5. **Retry Logic**: Simplified retry mechanisms for failed operations
6. **Type Handling**: Reduced complexity in type conversion and normalization
7. **Logging**: More focused logging with less verbosity

## Implementation Guidelines

1. **Use Standard Patterns**: Follow the MCP SDK standards without excessive customization
2. **Fail Fast**: Detect connection issues early and provide clear error messages
3. **Reconnect Automatically**: Implement simple reconnection logic for resilience
4. **Leverage FastMCP**: Use FastMCP API for server-side implementations
5. **Improve Testability**: Design with testing in mind, enable mocking of MCP connections
6. **Minimize Dependencies**: Reduce dependencies between MCP clients and other components

## Next Steps

1. Implement the simplified MCP client with core functionality
2. Create the Integration Hub with streamlined connection management
3. Build domain expert frameworks using FastMCP
4. Develop MCP-based memory system service
5. Create comprehensive tests for MCP client and server implementations