# Cortex Core Client API Reference

_Date: 2025-03-07_

A concise technical reference for the Cortex Core API endpoints, data structures, and integration patterns, focused on client application development.

> **Note:** This document is a client-focused summary of the [complete API Reference](API_REFERENCE.md). It focuses on practical implementation guidance for client developers.

## Quick Start

### Base URL

```
http://localhost:8000
```

### Authentication

All endpoints require a bearer token in the Authorization header:

```
Authorization: Bearer <your-token>
```

### Basic Flow

1. Create a conversation
2. Connect to the SSE endpoint for real-time updates
3. Send a user message
4. Receive the AI's response via SSE
5. Continue the conversation with additional messages

## API Endpoints

| Endpoint                           | Method | Description                     | Auth Required |
| ---------------------------------- | ------ | ------------------------------- | ------------- |
| `/api/validate-session`            | GET    | Validate a session token        | Yes           |
| `/api/conversations`               | GET    | List conversations              | Yes           |
| `/api/conversations`               | POST   | Create a new conversation       | Yes           |
| `/api/conversations/{id}`          | GET    | Get a specific conversation     | Yes           |
| `/api/conversations/{id}`          | DELETE | Delete a conversation           | Yes           |
| `/api/conversations/{id}/messages` | GET    | List messages in a conversation | Yes           |
| `/api/conversations/{id}/messages` | POST   | Send a message                  | Yes           |
| `/api/sse/conversations/{id}`      | GET    | Establish an SSE connection     | Yes           |

## Data Models

### Conversation

```json
{
  "id": "string",
  "user_id": "string",
  "title": "string",
  "created_at": "string (ISO datetime)",
  "updated_at": "string (ISO datetime)",
  "metadata": {},
  "messages": []
}
```

### Message

```json
{
  "id": "string",
  "conversation_id": "string",
  "role": "user | assistant | system | tool",
  "content": "string",
  "created_at": "string (ISO datetime)",
  "metadata": {},
  "tool_calls": [],
  "is_complete": true
}
```

### Message Roles

- `user`: Messages from the end user
- `assistant`: Messages from the AI assistant
- `system`: System messages that provide context or instructions
- `tool`: Results from tool executions

## Request/Response Examples

### Create a Conversation

Request:

```http
POST /api/conversations
Authorization: Bearer <your-token>
Content-Type: application/json

{
  "title": "New Conversation"
}
```

Response:

```json
{
  "conversation": {
    "id": "conversation-id",
    "user_id": "user-id",
    "title": "New Conversation",
    "created_at": "2025-03-06T21:10:00Z",
    "updated_at": "2025-03-06T21:10:00Z",
    "metadata": {},
    "messages": []
  }
}
```

### Send a Message

Request:

```http
POST /api/conversations/{conversation_id}/messages
Authorization: Bearer <your-token>
Content-Type: application/json

{
  "content": "Hello, AI!",
  "role": "user"
}
```

Response:

```json
{
  "message": {
    "id": "message-id",
    "conversation_id": "conversation-id",
    "role": "user",
    "content": "Hello, AI!",
    "created_at": "2025-03-06T21:10:00Z",
    "metadata": {
      "user_id": "user-id"
    },
    "tool_calls": [],
    "is_complete": true
  }
}
```

## Server-Sent Events (SSE)

SSE is used for real-time updates, particularly for receiving assistant responses.

### Connect to SSE

```http
GET /api/sse/conversations/{conversation_id}
Authorization: Bearer <your-token>
```

### SSE Event Types

| Event Type                 | Description                                            |
| -------------------------- | ------------------------------------------------------ |
| `message_created`          | A new message has been created                         |
| `message_updated`          | A message has been updated (e.g., streaming responses) |
| `message_deleted`          | A message has been deleted                             |
| `conversation_updated`     | Conversation metadata has been updated                 |
| `tool_execution_started`   | A tool execution has begun                             |
| `tool_execution_completed` | A tool execution has completed                         |
| `tool_execution_failed`    | A tool execution has failed                            |

### SSE Data Format

```
event: message_created
data: {"id":"msg-id","conversation_id":"conv-id","role":"assistant","content":"Hello!","created_at":"2025-03-06T21:10:05Z","metadata":{},"tool_calls":[],"is_complete":true}
```

## Implementation Notes

1. **Always listen for SSE events** when interacting with conversations. AI responses are streamed via SSE, not returned directly from API calls.

2. **Handle partial messages**: Messages may have `is_complete: false` during streaming.

3. **Token validation**: Periodically validate your token using the `/api/validate-session` endpoint.

4. **Reconnect SSE on disconnect**: Implement reconnection logic if the SSE connection is lost.

5. **Error handling**: All endpoints return standard HTTP status codes and error responses:
   ```json
   {
     "detail": "Error message",
     "code": "optional_error_code"
   }
   ```

## Client Dependencies

For JavaScript/TypeScript clients:

- `fetch` API (or `axios`)
- `EventSource` for SSE (or a polyfill)

For Python clients:

- `requests`
- `sseclient-py` for SSE
- `threading` for SSE background processing

## Testing Your Implementation

1. Create a new conversation
2. Connect to the SSE endpoint
3. Send a simple message like "Hello"
4. Verify you receive the assistant's response via SSE
5. Test error handling by sending malformed requests
6. Verify reconnection works if the SSE connection is dropped

For comprehensive client implementation examples, see [CLIENT_INTEGRATION_GUIDE.md](CLIENT_INTEGRATION_GUIDE.md).
