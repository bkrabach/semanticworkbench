# Server-Sent Events (SSE) Architecture

## Overview

The Cortex Core SSE implementation provides real-time event streaming to clients using a clean, modular architecture. This system enables clients to receive live updates for conversations, workspaces, and user-specific events.

## Core Components

The SSE architecture consists of the following key components:

1. **SSE Service** (`app/services/sse_service.py`):
   - Central service that coordinates all SSE functionality
   - Handles authentication and access control
   - Creates connection managers for handling client connections

2. **Connection Manager** (`app/components/sse/starlette_manager.py`):
   - Manages the lifecycle of SSE connections using global state
   - Handles connection registration, removal, and clean-up
   - Provides efficient queuing and event delivery
   - Ensures consistent connection tracking across service instances

3. **Authentication** (`app/components/sse/auth.py`):
   - Contains authentication-related models and functions
   - Provides validation methods for SSE connections
   - Supports resource access verification

4. **Event Models** (`app/components/sse/models.py`):
   - Defines data types and models for the SSE module
   - Includes SSEConnectionStats, SSEEvent, and other models
   - Supports typed event handling

Each component is designed to be modular, making the system easier to maintain and extend over time.

## API Endpoints

The SSE API provides a clean, unified endpoint pattern:

- `GET /v1/{channel_type}/{resource_id}` - Subscribe to events for a specific resource
- `GET /v1/stats` - Get statistics about active connections

See the AsyncAPI documentation (`docs/api/asyncapi.yaml`) for detailed specification.

## Event Types

The system supports the following common event types:

- `connect` - Initial connection established
- `heartbeat` - Periodic heartbeat to keep connection alive
- `message_received` - New message received in a conversation
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

eventSource.addEventListener("error", (e) => {
  console.error("SSE error", e);
  eventSource.close();
  // Implement reconnection logic with backoff
});
```

## Security Considerations

- All SSE endpoints require authentication
- Resource access is verified for each connection
- Connections are properly cleaned up when clients disconnect
- Heartbeat mechanism ensures stale connections are detected

## Connection Management

The SSE implementation uses a shared-state pattern to ensure connections are properly tracked across multiple service instances:

- Global connection data structures are used to track all active connections
- All instances of the SSE Manager share the same connection tracking state
- Connection IDs are generated as UUIDs to ensure uniqueness
- Message delivery follows multiple paths to ensure reliability:
  1. Direct delivery to connections via the SSE manager
  2. Event system publishing for cross-component coordination

This approach ensures that even when services are created through dependency injection, they maintain a consistent view of active connections.