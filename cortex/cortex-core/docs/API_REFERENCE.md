# API Reference

This document details the API endpoints available in Cortex Core.

> **Note on Timestamps**: All timestamps in API responses are provided in ISO 8601 format with UTC timezone (indicated by the 'Z' suffix, e.g., `2023-01-15T12:00:00Z`). Timestamps are consistently provided with the `*_utc` suffix (e.g., `created_at_utc`) to clearly indicate their timezone. Client applications should convert these UTC timestamps to local time for display.

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
  "expires_at": "2023-12-31T23:59:59Z"  // ISO 8601 format with 'Z' indicating UTC timezone
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid credentials
- `400 Bad Request`: Invalid request format

### Refresh Token

Refresh an authentication token.

**Endpoint**: `POST /auth/refresh`

**Authentication**: Bearer token

**Response**:

```json
{
  "success": true,
  "token": "new-jwt-token",
  "expires_at": "2023-12-31T23:59:59Z"  // ISO 8601 format with 'Z' indicating UTC timezone
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token
- `400 Bad Request`: Invalid request format

### Logout

Log out and invalidate token.

**Endpoint**: `POST /auth/logout`

**Authentication**: Bearer token

**Response**:

```json
{
  "message": "Logged out successfully"
}
```

### Generate API Key

Generate an API key for programmatic access.

**Endpoint**: `POST /auth/key/generate`

**Authentication**: Bearer token

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
  "expires_at": "2023-12-31T23:59:59Z"  // ISO 8601 format with 'Z' indicating UTC timezone
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token
- `400 Bad Request`: Invalid request format

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
      "created_at_utc": "2023-01-01T00:00:00Z",
      "last_active_at_utc": "2023-01-10T15:30:00Z"
    }
  ]
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token

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
  "created_at_utc": "2023-01-15T00:00:00Z"
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token
- `400 Bad Request`: Invalid request format

### Get Workspace

Get details of a specific workspace.

**Endpoint**: `GET /workspaces/{id}`

**Authentication**: Bearer token

**Parameters**:

- `id` (path): Workspace ID

**Response**:

```json
{
  "id": "workspace-uuid",
  "name": "Project X",
  "created_at_utc": "2023-01-01T00:00:00Z",
  "last_active_at_utc": "2023-01-10T15:30:00Z",
  "config": {
    "default_modality": "chat"
  },
  "meta_data": {}
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token
- `404 Not Found`: Workspace not found

### Update Workspace

Update a workspace.

**Endpoint**: `PUT /workspaces/{id}`

**Authentication**: Bearer token

**Parameters**:

- `id` (path): Workspace ID

**Request Body**:

```json
{
  "name": "Updated Project Name",
  "config": {
    "default_modality": "voice"
  }
}
```

**Response**:

```json
{
  "id": "workspace-uuid",
  "name": "Updated Project Name",
  "updated_at_utc": "2023-01-16T12:00:00Z"
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token
- `404 Not Found`: Workspace not found
- `400 Bad Request`: Invalid request format

### Delete Workspace

Delete a workspace.

**Endpoint**: `DELETE /workspaces/{id}`

**Authentication**: Bearer token

**Parameters**:

- `id` (path): Workspace ID

**Response**:

```json
{
  "message": "Workspace deleted successfully"
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token
- `404 Not Found`: Workspace not found

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
      "created_at_utc": "2023-01-15T10:00:00Z",
      "last_active_at_utc": "2023-01-15T11:30:00Z"
    }
  ]
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token
- `404 Not Found`: Workspace not found

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
  "created_at_utc": "2023-01-15T12:00:00Z"
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token
- `404 Not Found`: Workspace not found
- `400 Bad Request`: Invalid request format

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
  "created_at_utc": "2023-01-15T10:00:00Z",
  "last_active_at_utc": "2023-01-15T11:30:00Z",
  "workspace_id": "workspace-uuid",
  "meta_data": {}
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token
- `404 Not Found`: Conversation not found

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
  "created_at_utc": "2023-01-15T12:05:00Z"  // ISO 8601 format with 'Z' indicating UTC timezone
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token
- `404 Not Found`: Conversation not found
- `400 Bad Request`: Invalid request format

### Stream Messages

Send a message and receive a streaming response.

**Endpoint**: `POST /conversations/{id}/messages/stream`

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
Server-Sent Events stream with chunks of the response in the following format:

```json
{
  "id": "response-uuid",
  "created": 1689956912,
  "model": "model-name",
  "choices": [
    {
      "delta": {
        "content": "chunk of text"
      },
      "index": 0
    }
  ]
}
```

Final chunk includes finish reason:

```json
{
  "id": "response-uuid",
  "created": 1689956912,
  "model": "model-name",
  "choices": [
    {
      "delta": {},
      "finish_reason": "stop",
      "index": 0
    }
  ]
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token
- `404 Not Found`: Conversation not found
- `400 Bad Request`: Invalid request format

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
      "created_at_utc": "2023-01-15T12:05:00Z"
    },
    {
      "id": "message-uuid-2",
      "content": "I'm here to assist you with any questions or tasks you have. What would you like to work on today?",
      "role": "assistant",
      "created_at_utc": "2023-01-15T12:05:05Z"
    }
  ]
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token
- `404 Not Found`: Conversation not found

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

#### Global Channel (`/v1/global/global`)

- `notification`: General system notifications
- `system_update`: System update information

Example events:

```
event: connect
data: {"connected": true}

event: notification
data: {"message": "New platform feature available", "timestamp_utc": "2023-01-15T12:00:00Z"}

event: heartbeat
data: {"timestamp_utc": "2023-01-15T12:00:30Z"}
```

#### User Channel (`/v1/user/{user_id}`)

- `notification`: User-specific notifications
- `preference_update`: User preference changes

Example events:

```
event: connect
data: {"connected": true}

event: notification
data: {"message": "You have a new message", "timestamp_utc": "2023-01-15T12:00:00Z"}

event: heartbeat
data: {"timestamp_utc": "2023-01-15T12:00:30Z"}
```

#### Workspace Channel (`/v1/workspace/{workspace_id}`)

- `workspace_update`: Workspace metadata updates
- `conversation_created`: New conversation in the workspace
- `conversation_deleted`: Conversation deleted from workspace
- `member_joined`: New member joined the workspace
- `member_left`: Member left the workspace

Example events:

```
event: connect
data: {"connected": true}

event: conversation_created
data: {"id": "conversation-uuid", "title": "New Chat", "modality": "chat", "created_at_utc": "2023-01-15T12:00:00Z"}

event: heartbeat
data: {"timestamp_utc": "2023-01-15T12:00:30Z"}
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
data: {"status": "typing", "role": "assistant", "timestamp_utc": "2023-01-15T12:00:00Z"}

event: message_received
data: {"id": "message-uuid", "content": "Hello there!", "role": "assistant", "created_at_utc": "2023-01-15T12:00:05Z"}

event: heartbeat
data: {"timestamp_utc": "2023-01-15T12:00:30Z"}
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

**Error Responses**:

- `401 Unauthorized`: Invalid or expired token

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

## Rate Limiting

API endpoints are rate-limited to prevent abuse. Current limits:

- Authentication endpoints: 10 requests per minute
- All other endpoints: 100 requests per minute

Exceeding these limits will result in a `429 Too Many Requests` response.

## API Versioning

The API version is included in the URL path:

```
/api/v1/workspaces
```

The current version is v1.

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
