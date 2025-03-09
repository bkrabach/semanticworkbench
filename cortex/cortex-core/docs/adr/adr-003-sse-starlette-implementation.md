# ADR-003: SSE Implementation with sse-starlette

## Status

Accepted

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
- [Fastapi Streaming Response](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [SSE improvements document](../SSE_IMPROVEMENTS.md)