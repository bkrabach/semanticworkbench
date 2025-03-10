# ADR-003: SSE Implementation with sse-starlette

## Status

Implemented

## Context

Server-Sent Events (SSE) are a critical feature of the Cortex Core platform, enabling real-time updates to client applications. Our initial SSE implementation was built as a custom solution directly on top of FastAPI/Starlette's async response handling.

However, this custom implementation encountered several significant issues:

1. **Connection Instability**: Connections would register but immediately disappear from the connection registry
2. **Resource Management**: Background tasks were prematurely cleaning up connections
3. **State Management**: Connection state wasn't properly preserved across async contexts
4. **Error Handling**: No robust reconnection strategy existed

These issues manifested in client applications as:
- Connections dropping unexpectedly
- Missed events
- Client-side reconnection storms
- Inconsistent event delivery

The problems were particularly challenging to debug because:
- SSE connection issues are often intermittent
- Testing SSE endpoints is difficult due to their long-lived nature
- Local development environments might behave differently than production

We needed a more robust, production-ready implementation that would solve these issues while maintaining compatibility with our domain-driven architecture.

## Decision

After evaluating several options, we've decided to adopt the `sse-starlette` library for our SSE implementation, with a carefully designed abstraction layer to maintain our architectural boundaries:

1. **Replace Custom SSE Implementation**: Use the `sse-starlette` library instead of our custom solution
2. **Create Domain-Compatible Wrapper**: Implement `SSEStarletteManager` that maintains compatibility with our domain models
3. **Keep Connection State Separate**: Store connection queues separately from domain models to maintain architectural boundaries
4. **Maintain Unified API**: Keep the same API contracts for SSE endpoints to avoid client changes

The implementation strategy includes:
- Adding the `sse-starlette` library to our dependencies
- Creating a new `SSEStarletteManager` class that implements the same interface as our existing manager
- Updating the SSE service to use this new manager
- Ensuring proper domain model handling throughout

## Consequences

### Positive

1. **Improved Connection Stability**: The `sse-starlette` library handles connection lifecycle properly
2. **Better Resource Management**: Connections are only cleaned up when clients actually disconnect
3. **Safer State Management**: Connection state is properly preserved
4. **Enhanced Error Handling**: Better error reporting and logging
5. **Reduced Custom Code**: Less custom code to maintain
6. **Maintained Architecture**: Domain-driven design principles are preserved

### Negative

1. **New Dependency**: Added a new external dependency to the project
2. **Learning Curve**: Team needs to understand how `sse-starlette` works
3. **Implementation Complexity**: The wrapper adds some complexity to maintain domain model separation
4. **Testing Challenges**: SSE endpoints remain complex to test properly

## Implementation

The core implementation pattern is:

1. **Connection State Separation**:
   ```python
   class SSEStarletteManager:
       def __init__(self):
           # Store domain models
           self.connections = {
               "global": [],
               "user": collections.defaultdict(list),
               "workspace": collections.defaultdict(list),
               "conversation": collections.defaultdict(list)
           }
           
           # Store technical implementation details separately
           self.connection_queues = {}
   ```

2. **Domain Model Safety**:
   ```python
   async def register_connection(self, channel_type, resource_id, user_id):
       connection_id = str(uuid.uuid4())
       
       # Create the queue for this connection
       queue: asyncio.Queue = asyncio.Queue()
       
       # Create domain model
       connection = SSEConnection(
           id=connection_id,
           channel_type=channel_type,
           resource_id=resource_id,
           user_id=user_id,
           connected_at=datetime.now(timezone.utc),
           last_active_at=datetime.now(timezone.utc)
       )
       
       # Store queue separately from domain model
       self.connection_queues[connection_id] = queue
       
       # Store domain model in appropriate collection
       if channel_type == "global":
           self.connections["global"].append(connection)
       else:
           self.connections[channel_type][resource_id].append(connection)
           
       return queue, connection_id
   ```

3. **sse-starlette Integration**:
   ```python
   async def create_sse_response(self, channel_type, resource_id, user_id, request):
       # Register connection using our domain model approach
       queue, connection_id = await self.register_connection(
           channel_type, resource_id, user_id
       )
       
       # Create event generator
       generator = self.event_generator(
           channel_type, resource_id, user_id, connection_id, request
       )
       
       # Return sse-starlette's EventSourceResponse
       return EventSourceResponse(
           generator,
           media_type="text/event-stream",
           headers={
               "Cache-Control": "no-cache",
               "Connection": "keep-alive"
           }
       )
   ```

## Implementation Files

The SSE implementation is spread across several files:

1. **SSE Package Structure**:
   - `/app/components/sse/__init__.py` - Package initialization
   - `/app/components/sse/auth.py` - Authentication for SSE connections
   - `/app/components/sse/events.py` - Event definition and handling
   - `/app/components/sse/manager.py` - Base SSE manager interface
   - `/app/components/sse/models.py` - Domain models for SSE
   - `/app/components/sse/starlette_manager.py` - Starlette-specific implementation

2. **Core Implementation**:
   - `/app/components/sse/starlette_manager.py` contains the `SSEStarletteManager` class that implements the sse-starlette integration.
   - `/app/services/sse_service.py` contains the service layer that coordinates SSE functionality.

3. **API Endpoints**:
   - `/app/api/sse.py` defines all the SSE endpoints using FastAPI.

4. **Domain Models**:
   - `/app/models/domain/sse.py` contains the domain models for SSE connections and events.

## Testing Implementation

SSE testing is implemented in:

- `/tests/components/test_sse_module.py` - Unit tests for the SSE components
- `/tests/api/test_sse.py` - API tests for the SSE endpoints
- `/tests/api/test_sse_integration.py` - Integration tests with client simulation

The testing strategy uses mock responses to avoid hanging during tests:

```python
class MockSSEResponse:
    def __init__(self):
        self.status_code = 200
        self.headers = {"content-type": "text/event-stream"}
    
    def close(self):
        pass
```

## Alternatives Considered

### Keep and Fix Custom Implementation

We considered fixing our custom SSE implementation. The benefits would have been:
- No new dependencies
- Complete control over implementation details
- No need to learn a new library

We rejected this approach because:
- The issues were deep and complex, involving subtle async behaviors
- Other libraries have already solved these problems
- Maintaining a custom implementation would be an ongoing burden
- We weren't adding unique value by solving these standard problems ourselves

### Use WebSockets Instead of SSE

We considered switching from SSE to WebSockets, which would have offered:
- Bi-directional communication
- More standardized implementation in FastAPI
- Different connection management patterns

We rejected this approach because:
- SSE is simpler for the one-way communication pattern we need
- Client implementations are often simpler with SSE
- The change would require significant client-side changes
- Our event model fits the SSE pattern well

### Server-Side Polling Solution

We considered replacing real-time updates with a polling mechanism, which would have:
- Simplified the server implementation
- Avoided connection management issues
- Been more compatible with certain proxy/firewall configurations

We rejected this approach because:
- It would increase latency for updates
- It would create more load on the server
- Real-time updates were a key requirement
- It would be a step backward in capabilities

## References

- [sse-starlette documentation](https://github.com/sysid/sse-starlette)
- [MDN Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [FastAPI Streaming Response](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [SSE.md](../SSE.md) - Main SSE documentation

## Update: Shared Connection State

After implementing the initial solution, we encountered an issue where connections were being properly established but not consistently tracked across different service instances. This occurred because FastAPI's dependency injection system creates new service instances for each request, leading to fragmented connection tracking.

### Problem

- Each SSE service instance maintained its own connection tracking state
- When a client connected via one instance, other instances wouldn't see the connection
- Messages sent via different service instances would fail with "No active connections" errors
- Router components couldn't reliably deliver messages to clients

### Solution

We implemented a shared-state pattern for connection tracking in `/app/components/sse/starlette_manager.py`:

1. **Global Connection Structures**:
   ```python
   # Global singleton structures for connection tracking
   _global_connections = {
       "global": {"global": []},
       "user": {},
       "workspace": {},
       "conversation": {}
   }
   
   # Global event callbacks and queue tracking
   _global_event_callbacks = {...}
   _global_connection_queues = {}
   ```

2. **Instance Sharing**:
   ```python
   def __init__(self):
       # Use global connection structures for shared state
       global _global_connections, _global_event_callbacks, _global_connection_queues
       
       # Store connection objects by type and resource
       self.connections = _global_connections
       self.event_callbacks = _global_event_callbacks
       self.connection_queues = _global_connection_queues
   ```

3. **Multi-Path Message Delivery** in `/app/components/cortex_router.py`:
   ```python
   async def send_message_to_client(self, conversation_id, message_id, content, role, metadata):
       # First publish through the event system
       await event_system.publish(
           f"conversation.message_received",
           payload,
           source="cortex_router"
       )
       
       # Also try direct SSE path for active connections
       await sse_service.connection_manager.send_event(
           "conversation",
           conversation_id,
           "message_received",
           payload,
           republish=False  # Already published through event system
       )
   ```

This approach ensures that all SSE manager instances share the same connection state, allowing any service instance to see all active connections and deliver messages regardless of which instance created the connection.

## Implementation Learnings

Since implementing this solution, we've learned several important lessons:

1. **Connection Cleanup**: Proper cleanup on client disconnect is critical for avoiding resource leaks
2. **Heartbeat Events**: Regular heartbeat events help keep connections alive through proxies
3. **Error Recovery**: Implementing client-side reconnection logic improves reliability
4. **Connection Monitoring**: Adding connection monitoring dashboards helps track system health
5. **Testing Strategy**: Specialized testing approaches for streaming endpoints are necessary

These learnings have been incorporated into our [SSE.md](../SSE.md) documentation to guide future development.