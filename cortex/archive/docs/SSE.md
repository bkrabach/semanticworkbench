# Server-Sent Events (SSE) Architecture

## Overview

The Cortex Core SSE implementation provides real-time event streaming to clients using a clean, modular architecture. This system enables clients to receive live updates for conversations, workspaces, and user-specific events.

The implementation uses the `sse-starlette` library to ensure robust connection handling, proper resource management, and consistent state tracking across multiple service instances.

## Core Components

The SSE architecture consists of the following key components:

1. **SSE Service** (`app/services/sse_service.py`):
   - Central service that coordinates all SSE functionality
   - Handles authentication and access control
   - Creates connection managers for handling client connections
   - Follows the domain-driven repository pattern

2. **Connection Manager** (`app/components/sse/starlette_manager.py`):
   - Manages the lifecycle of SSE connections using global state
   - Handles connection registration, removal, and clean-up
   - Provides efficient queuing and event delivery
   - Ensures consistent connection tracking across service instances
   - Uses the `sse-starlette` library for robust connection handling

3. **Authentication** (`app/components/sse/auth.py`):
   - Contains authentication-related models and functions
   - Provides validation methods for SSE connections
   - Supports resource access verification

4. **Event Models** (`app/components/sse/models.py`):
   - Defines data types and models for the SSE module
   - Includes SSEConnectionStats, SSEEvent, and other models
   - Supports typed event handling

## Current Implementation

The current SSE implementation has been redesigned to address several critical issues that were present in earlier versions:

1. **Connection Stability**: Using `sse-starlette` ensures connections remain active and don't immediately disappear
2. **Resource Management**: Proper cleanup only when clients actually disconnect
3. **State Management**: Connection state is properly preserved across async contexts
4. **Error Handling**: Robust error handling and reconnection strategies

### Connection Management

The SSE implementation uses a shared-state pattern to ensure connections are properly tracked across multiple service instances:

- Global connection data structures track all active connections
- All instances of the SSE Manager share the same connection tracking state
- Connection IDs are generated as UUIDs to ensure uniqueness
- Message delivery follows multiple paths to ensure reliability:
  1. Direct delivery to connections via the SSE manager
  2. Event system publishing for cross-component coordination

```python
# Global connection structures
_global_connections = {
    "global": {"global": []},
    "user": {},
    "workspace": {},
    "conversation": {}
}

# Connection manager implementation
class SSEStarletteManager:
    def __init__(self):
        global _global_connections
        # Use global structures for shared state
        self.connections = _global_connections
```

## API Endpoints

The SSE API provides a clean, unified endpoint pattern:

- `GET /v1/{channel_type}/{resource_id}` - Subscribe to events for a specific resource
- `GET /v1/stats` - Get statistics about active connections

The system supports these channel types:
- `global` - System-wide events
- `user` - User-specific events
- `workspace` - Workspace-specific events
- `conversation` - Conversation-specific events

Example endpoints:
- `/v1/global/global?token=xyz` - Global system events
- `/v1/user/123?token=xyz` - Events for user 123
- `/v1/workspace/456?token=xyz` - Events for workspace 456
- `/v1/conversation/789?token=xyz` - Events for conversation 789

See the AsyncAPI documentation (`docs/api/asyncapi.yaml`) for detailed specification.

## Event Types

The system supports the following common event types:

- `connect` - Initial connection established
- `connection_confirmed` - Connection confirmation
- `heartbeat` - Periodic heartbeat to keep connection alive
- `message_received` - New message received in a conversation
- `typing_indicator` - Typing status updates
- `status_update` - Status update for a conversation or workspace

Custom event types can be added as needed for specific features.

## Client Integration

To connect to an SSE endpoint, clients should:

1. Obtain an authentication token
2. Connect to the appropriate endpoint
3. Parse SSE events in the format `event: {event_type}\ndata: {json_data}\n\n`
4. Handle reconnection with appropriate backoff strategy

Example JavaScript client:

```javascript
const token = "your_auth_token";
const conversationId = "123456";
const eventSource = new EventSource(`/v1/conversation/${conversationId}?token=${token}`);

eventSource.addEventListener("connect", (e) => {
  console.log("Connected to SSE stream", JSON.parse(e.data));
});

eventSource.addEventListener("message_received", (e) => {
  const message = JSON.parse(e.data);
  console.log("New message:", message);
  // Update UI with message
});

eventSource.addEventListener("typing_indicator", (e) => {
  const data = JSON.parse(e.data);
  console.log("Typing status:", data.isTyping);
  // Update UI with typing indicator
});

eventSource.addEventListener("error", (e) => {
  console.error("SSE error", e);
  eventSource.close();
  // Implement reconnection logic with backoff
});
```

## Security Considerations

- All SSE endpoints require authentication via JWT tokens
- Resource access is verified for each connection
- Connections are properly cleaned up when clients disconnect
- Heartbeat mechanisms ensure stale connections are detected
- Token refresh mechanisms are recommended for long-lived connections

## Server Implementation

### SSE Service

The SSE service (`app/services/sse_service.py`) orchestrates the SSE functionality:

```python
class SSEService:
    """Server-Sent Events service."""

    def __init__(self, db_session: Session, repository: ResourceAccessRepository):
        self.db = db_session
        self.repository = repository
        self.connection_manager = SSEStarletteManager()
        self.event_subscriber = SSEEventSubscriber(get_event_system(), self.connection_manager)

    async def create_sse_stream(self, channel_type: str, resource_id: str, token: str, request):
        """Create an SSE stream for a specific channel type and resource."""
        # Authenticate user
        user_info = await self.authenticate_token(token)
        
        # Verify resource access
        if channel_type != "global":
            has_access = await self.verify_resource_access(user_info, channel_type, resource_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="Not authorized")
        
        # Create SSE response
        return await self.connection_manager.create_sse_response(
            channel_type=channel_type,
            resource_id=resource_id,
            user_id=user_info.id,
            request=request
        )
```

### Connection Manager

The connection manager (`app/components/sse/starlette_manager.py`) handles the lifecycle of SSE connections:

```python
class SSEStarletteManager:
    """SSE connection manager using sse-starlette"""

    def __init__(self):
        # Use global connection structures for shared state
        global _global_connections, _global_connection_queues
        self.connections = _global_connections
        self.connection_queues = _global_connection_queues

    async def create_sse_response(self, channel_type, resource_id, user_id, request):
        """Create an SSE response"""
        # Register connection
        queue, connection_id = await self.register_connection(
            channel_type, resource_id, user_id
        )
        
        # Create event generator
        event_generator = self.generate_sse_events(queue)
        
        # Return SSE response
        return EventSourceResponse(
            event_generator,
            media_type="text/event-stream"
        )
```

## Deployment Considerations

When deploying the SSE system in production, consider these recommendations:

1. **Nginx Configuration**:
   ```
   proxy_buffering off;
   proxy_read_timeout 3600s;
   ```

2. **Application Server Timeouts**: Adjust timeouts for long-lived connections:
   ```
   uvicorn app.main:app --timeout-keep-alive 300
   ```

3. **Horizontal Scaling**: For multi-instance deployments:
   - Implement a Redis backend for shared connection state
   - Use Redis Pub/Sub for event distribution

## Testing SSE

Testing SSE endpoints requires special consideration due to their long-lived nature:

```python
# Example test for SSE endpoint
def test_sse_connection(client, mock_auth):
    # Mock authentication
    mock_auth.return_value = UserInfo(id="user123", email="test@example.com")
    
    # Create a mock SSE response class
    class MockSSEResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {"content-type": "text/event-stream"}
        def close(self):
            pass
    
    # Patch the client's get method
    def mock_get(url, **kwargs):
        if url.startswith("/v1/conversation/"):
            return MockSSEResponse()
        return original_get(url, **kwargs)
    
    with patch.object(client, "get", side_effect=mock_get):
        # Test the connection
        response = client.get("/v1/conversation/123?token=xyz")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
```

## Future Enhancements

Planned improvements to the SSE system:

1. **Redis Backend**: Distributed connection tracking for multi-instance deployments
2. **Connection Limits**: Per-user and per-resource connection limits
3. **Token Refresh**: Automatic token refresh for long-lived connections
4. **Enhanced Monitoring**: Detailed metrics and diagnostics
5. **Load Testing**: Comprehensive load testing framework

## Version History

### v2.0 (Current) - SSE-Starlette Implementation
- Adopted `sse-starlette` library
- Implemented shared connection state
- Improved connection lifecycle management
- Enhanced error handling and reconnection

### v1.0 (Superseded) - Custom Implementation
- Initial implementation using FastAPI/Starlette async responses
- Had issues with connection stability and resource management

## References

- [ADR-003: SSE Implementation with sse-starlette](adr/adr-003-sse-starlette-implementation.md)
- [sse-starlette GitHub Repository](https://github.com/sysid/sse-starlette)
- [MDN Server-Sent Events Documentation](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)