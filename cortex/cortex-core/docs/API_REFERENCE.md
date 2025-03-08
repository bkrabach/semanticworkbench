# API Reference

This document details the API endpoints available in Cortex Core.

> **⚠️ Implementation Notes**: This document describes the current state of API implementation. Some endpoints may be documented but not fully implemented yet. The prefix `/api/v1` is not currently implemented for most endpoints (except SSE endpoints which use `/v1`).

## Authentication API

### Login

Authenticate a user and create a session token.

**Endpoint**: `POST /auth/login`

**Request Body**:

```json
{
  "type": "password", // "password", "api_key", "oauth", "msal"
  "identifier": "email@example.com",
  "secret": "password"
}
```

**Response**:

```json
{
  "success": true,
  "user_id": "user-uuid",
  "token": "jwt-token",
  "expires_at": "2023-12-31T23:59:59Z"
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid credentials
- `400 Bad Request`: Invalid request format

### Refresh Token (Not Implemented)

Refresh an authentication token.

**Endpoint**: `POST /auth/refresh`

**Authentication**: Bearer token

> ⚠️ Note: This endpoint returns a 501 Not Implemented status.

**Response**:

```json
{
  "success": true,
  "token": "new-jwt-token",
  "expires_at": "2023-12-31T23:59:59Z"
}
```

### Logout

Log out and invalidate token.

**Endpoint**: `POST /auth/logout`

**Authentication**: Bearer token

> ⚠️ Note: Currently, this endpoint returns a success message but does not fully invalidate tokens.

**Response**:

```json
{
  "message": "Logged out successfully"
}
```

### Generate API Key (Partial Implementation)

Generate an API key for programmatic access.

**Endpoint**: `POST /auth/key/generate`

**Authentication**: Bearer token

> ⚠️ Note: API key authentication is not fully implemented yet.

**Request Body**:

```json
{
  "scopes": ["*"],
  "expiry_days": 30
}
```

**Response**:

```json
{
  "key": "api-key",
  "expires_at": "2023-12-31T23:59:59Z"
}
```

## Workspace API

### List Workspaces

List workspaces for the current user.

**Endpoint**: `GET /workspaces`

**Authentication**: Bearer token

**Response**:

```json
{
  "workspaces": [
    {
      "id": "workspace-uuid",
      "name": "Project X",
      "created_at": "2023-01-01T00:00:00Z",
      "last_active_at": "2023-01-10T15:30:00Z"
    }
  ]
}
```

> ⚠️ Note: The response format uses `created_at` and `last_active_at` rather than the `created_at_utc` and `last_active_at_utc` mentioned in older documentation.

### Create Workspace

Create a new workspace.

**Endpoint**: `POST /workspaces`

**Authentication**: Bearer token

**Request Body**:

```json
{
  "name": "New Project",
  "config": {
    "default_modality": "chat"
  }
}
```

**Response**:

```json
{
  "id": "new-workspace-uuid",
  "name": "New Project",
  "created_at": "2023-01-15T00:00:00Z"
}
```

### Get Workspace (Not Implemented)

Get details of a specific workspace.

**Endpoint**: `GET /workspaces/{id}`

> ⚠️ Note: This endpoint is not currently implemented.

### Update Workspace (Not Implemented)

Update a workspace.

**Endpoint**: `PUT /workspaces/{id}`

> ⚠️ Note: This endpoint is not currently implemented.

### Delete Workspace (Not Implemented)

Delete a workspace.

**Endpoint**: `DELETE /workspaces/{id}`

> ⚠️ Note: This endpoint is not currently implemented.

## Conversation API

### List Conversations

List conversations in a workspace.

**Endpoint**: `GET /workspaces/{id}/conversations`

**Authentication**: Bearer token

**Parameters**:

- `id` (path): Workspace ID

**Response**:

```json
{
  "conversations": [
    {
      "id": "conversation-uuid",
      "title": "Chat with AI",
      "modality": "chat",
      "created_at": "2023-01-15T10:00:00Z",
      "last_active_at": "2023-01-15T11:30:00Z"
    }
  ]
}
```

### Create Conversation

Create a new conversation.

**Endpoint**: `POST /workspaces/{id}/conversations`

**Authentication**: Bearer token

**Parameters**:

- `id` (path): Workspace ID

**Request Body**:

```json
{
  "title": "New Discussion",
  "modality": "chat"
}
```

**Response**:

```json
{
  "id": "new-conversation-uuid",
  "title": "New Discussion",
  "modality": "chat",
  "created_at": "2023-01-15T12:00:00Z"
}
```

### Get Conversation

Get details of a specific conversation.

**Endpoint**: `GET /conversations/{id}`

**Authentication**: Bearer token

**Parameters**:

- `id` (path): Conversation ID

**Response**:

```json
{
  "id": "conversation-uuid",
  "title": "Chat with AI",
  "modality": "chat",
  "created_at": "2023-01-15T10:00:00Z",
  "last_active_at": "2023-01-15T11:30:00Z",
  "workspace_id": "workspace-uuid"
}
```

### Update Conversation

Update a conversation.

**Endpoint**: `PATCH /conversations/{id}`

> ⚠️ Note: The current implementation uses PATCH instead of the PUT method mentioned in older documentation.

**Authentication**: Bearer token

**Parameters**:

- `id` (path): Conversation ID

**Request Body**:

```json
{
  "title": "Updated Discussion Name"
}
```

**Response**:

```json
{
  "id": "conversation-uuid",
  "title": "Updated Discussion Name",
  "modality": "chat",
  "updated_at": "2023-01-16T12:00:00Z"
}
```

### Delete Conversation

Delete a conversation.

**Endpoint**: `DELETE /conversations/{id}`

**Authentication**: Bearer token

**Parameters**:

- `id` (path): Conversation ID

**Response**:

```json
{
  "message": "Conversation deleted successfully"
}
```

### Add Message to Conversation

Add a message to a conversation.

**Endpoint**: `POST /conversations/{id}/messages`

**Authentication**: Bearer token

**Parameters**:

- `id` (path): Conversation ID

**Request Body**:

```json
{
  "content": "Hello, how can you help me today?",
  "role": "user",
  "metadata": {}
}
```

**Response**:

```json
{
  "id": "message-uuid",
  "content": "Hello, how can you help me today?",
  "role": "user",
  "created_at": "2023-01-15T12:05:00Z"
}
```

### Stream Messages (Partial Implementation)

Send a message and receive a streaming response.

**Endpoint**: `POST /conversations/{id}/messages/stream`

**Authentication**: Bearer token

> ⚠️ Note: This endpoint currently returns a placeholder response instructing clients to listen for events via the SSE endpoints.

**Parameters**:

- `id` (path): Conversation ID

**Request Body**:

```json
{
  "content": "Hello, how can you help me today?",
  "role": "user",
  "metadata": {}
}
```

**Response**:

```json
{
  "message": "Stream initiated. Listen to the SSE endpoint for real-time updates.",
  "conversation_id": "conversation-uuid"
}
```

### Get Conversation Messages

Get messages in a conversation.

**Endpoint**: `GET /conversations/{id}/messages`

**Authentication**: Bearer token

**Parameters**:

- `id` (path): Conversation ID

**Response**:

```json
{
  "messages": [
    {
      "id": "message-uuid-1",
      "content": "Hello, how can you help me today?",
      "role": "user",
      "created_at": "2023-01-15T12:05:00Z"
    },
    {
      "id": "message-uuid-2",
      "content": "I'm here to assist you with any questions or tasks you have. What would you like to work on today?",
      "role": "assistant",
      "created_at": "2023-01-15T12:05:05Z"
    }
  ]
}
```

## Events API

Cortex Core uses Server-Sent Events (SSE) for real-time updates to clients. The Events API provides a unified endpoint pattern for all event types using a clean, modular architecture.

### Unified Events Endpoint

**Endpoint**: `GET /v1/{channel_type}/{resource_id}`

**Authentication**: Query parameter token

**Parameters**:

- `channel_type` (path): Type of events to subscribe to (one of: `global`, `user`, `workspace`, `conversation`)
- `resource_id` (path): ID of the resource to subscribe to (not required for global events)
- `token` (query): Authentication token

**Response**: Server-Sent Events stream with the following common event types:

- `connect`: Sent when the connection is established
- `heartbeat`: Periodic heartbeat to keep the connection alive (every 30 seconds)

**Error Responses**:

- `400 Bad Request`: Invalid channel type
- `401 Unauthorized`: Invalid token
- `403 Forbidden`: Not authorized to access the requested resource

### Channel-Specific Events

Depending on the channel type, you will receive different specialized events:

#### Global Channel (`/v1/global`)

> ⚠️ Note: The implementation uses `/v1/global` rather than `/v1/global/global` mentioned in older documentation.

- `notification`: General system notifications
- `system_update`: System update information

Example events:

```
event: connect
data: {"connected": true}

event: notification
data: {"message": "New platform feature available", "timestamp": "2023-01-15T12:00:00Z"}

event: heartbeat
data: {"timestamp": "2023-01-15T12:00:30Z"}
```

#### User Channel (`/v1/user/{user_id}`)

- `notification`: User-specific notifications
- `preference_update`: User preference changes

Example events:

```
event: connect
data: {"connected": true}

event: notification
data: {"message": "You have a new message", "timestamp": "2023-01-15T12:00:00Z"}

event: heartbeat
data: {"timestamp": "2023-01-15T12:00:30Z"}
```

#### Workspace Channel (`/v1/workspace/{workspace_id}`)

- `workspace_update`: Workspace metadata updates
- `conversation_created`: New conversation in the workspace
- `conversation_deleted`: Conversation deleted from workspace

Example events:

```
event: connect
data: {"connected": true}

event: conversation_created
data: {"id": "conversation-uuid", "title": "New Chat", "modality": "chat", "created_at": "2023-01-15T12:00:00Z"}

event: heartbeat
data: {"timestamp": "2023-01-15T12:00:30Z"}
```

#### Conversation Channel (`/v1/conversation/{conversation_id}`)

- `message_received`: New message in the conversation
- `status_update`: Status updates (like typing indicators)
- `conversation_update`: Conversation metadata updates

Example events:

```
event: connect
data: {"connected": true}

event: status_update
data: {"status": "typing", "role": "assistant", "timestamp": "2023-01-15T12:00:00Z"}

event: message_received
data: {"id": "message-uuid", "content": "Hello there!", "role": "assistant", "created_at": "2023-01-15T12:00:05Z"}

event: heartbeat
data: {"timestamp": "2023-01-15T12:00:30Z"}
```

### Connection Statistics

Get statistics about active SSE connections.

**Endpoint**: `GET /v1/stats`

**Authentication**: Bearer token

**Response**:

```json
{
  "global": 5,
  "channels": {
    "user": {
      "user-id-1": 1,
      "user-id-2": 2
    },
    "workspace": {
      "workspace-id-1": 3
    },
    "conversation": {
      "conversation-id-1": 2,
      "conversation-id-2": 1
    }
  },
  "total": 14
}
```

## Monitoring API

### Event System Statistics

Get statistics about the event system.

**Endpoint**: `GET /monitoring/events/stats`

**Authentication**: Bearer token

**Response**:

```json
{
  "events_published": 100,
  "events_delivered": 95,
  "subscriber_count": 5,
  "event_types": {
    "conversation.message.created": 50,
    "user.session.started": 30,
    "system.component.initialized": 20
  },
  "errors": 2,
  "uptime_seconds": 3600,
  "events_per_second": 0.028
}
```

## Health Check API

### Health Check

Check the health of the service.

**Endpoint**: `GET /health`

**Response**:

```json
{
  "status": "ok"
}
```

## API Authentication

All authenticated endpoints require a valid JWT token in the Authorization header:

```
Authorization: Bearer <token>
```

Tokens are obtained through the login endpoint or by generating an API key.

## Error Handling

All error responses follow a standard format:

```json
{
  "detail": "Error message describing the issue"
}
```

Common HTTP status codes:

- `400 Bad Request`: Invalid request format or parameters
- `401 Unauthorized`: Authentication required or invalid credentials
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side error
- `501 Not Implemented`: The feature is not implemented yet

## Timestamp Format Notes

The current implementation uses timestamps with the following formats:
- `created_at` (without the `_utc` suffix mentioned in older documentation)
- `last_active_at` (without the `_utc` suffix)
- `updated_at` (without the `_utc` suffix)

All timestamps are provided in ISO 8601 format with UTC timezone (indicated by the 'Z' suffix, e.g., `2023-01-15T12:00:00Z`).