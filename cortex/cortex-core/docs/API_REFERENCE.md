# Cortex Core API Reference

_Date: 2025-03-07_

This document provides a detailed reference for the Cortex Core REST API endpoints. This reference reflects the current implementation of the API as of the document date.

> **Note:** This API reference documents the currently implemented endpoints. For information about the implementation status and future plans, see the [Implementation Status](IMPLEMENTATION_STATUS.md) document.

## Authentication

### Login
```
POST /api/login
```

Authenticates a user and creates a new session.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "session_id": "string",
  "user": {
    "id": "string",
    "username": "string",
    "display_name": "string"
  }
}
```

**Status Codes:**
- 200: Success
- 401: Invalid credentials

### Validate Session
```
GET /api/validate-session
```

Validates an existing session token.

**Headers:**
- `Authorization`: Bearer \<session_id\>

**Response:**
```json
{
  "valid": true,
  "user": {
    "id": "string",
    "username": "string",
    "display_name": "string"
  }
}
```

**Status Codes:**
- 200: Success
- 401: Invalid session

### Logout
```
POST /api/logout
```

Ends a user session.

**Headers:**
- `Authorization`: Bearer \<session_id\>

**Response:**
```json
{
  "success": true
}
```

**Status Codes:**
- 200: Success
- 401: Invalid session

## Conversations

### List Conversations
```
GET /api/conversations
```

Retrieves a list of conversations for the authenticated user.

**Headers:**
- `Authorization`: Bearer \<session_id\>

**Response:**
```json
{
  "conversations": [
    {
      "id": "string",
      "title": "string",
      "created_at": "string (ISO datetime)",
      "updated_at": "string (ISO datetime)"
    }
  ]
}
```

**Status Codes:**
- 200: Success
- 401: Unauthorized

### Create Conversation
```
POST /api/conversations
```

Creates a new conversation.

**Headers:**
- `Authorization`: Bearer \<session_id\>

**Request Body:**
```json
{
  "title": "string (optional)"
}
```

**Response:**
```json
{
  "id": "string",
  "title": "string",
  "created_at": "string (ISO datetime)",
  "updated_at": "string (ISO datetime)"
}
```

**Status Codes:**
- 201: Created
- 401: Unauthorized
- 422: Validation Error

### Get Conversation
```
GET /api/conversations/{conversation_id}
```

Retrieves details for a specific conversation.

**Headers:**
- `Authorization`: Bearer \<session_id\>

**Parameters:**
- `conversation_id`: ID of the conversation

**Response:**
```json
{
  "id": "string",
  "title": "string",
  "created_at": "string (ISO datetime)",
  "updated_at": "string (ISO datetime)",
  "messages_count": "integer"
}
```

**Status Codes:**
- 200: Success
- 401: Unauthorized
- 404: Conversation not found

### Update Conversation
```
PUT /api/conversations/{conversation_id}
```

Updates an existing conversation.

**Headers:**
- `Authorization`: Bearer \<session_id\>

**Parameters:**
- `conversation_id`: ID of the conversation

**Request Body:**
```json
{
  "title": "string"
}
```

**Response:**
```json
{
  "id": "string",
  "title": "string",
  "created_at": "string (ISO datetime)",
  "updated_at": "string (ISO datetime)"
}
```

**Status Codes:**
- 200: Success
- 401: Unauthorized
- 404: Conversation not found
- 422: Validation Error

### Delete Conversation
```
DELETE /api/conversations/{conversation_id}
```

Deletes a conversation.

**Headers:**
- `Authorization`: Bearer \<session_id\>

**Parameters:**
- `conversation_id`: ID of the conversation

**Response:**
```json
{
  "success": true
}
```

**Status Codes:**
- 200: Success
- 401: Unauthorized
- 404: Conversation not found

## Messages

### List Messages
```
GET /api/conversations/{conversation_id}/messages
```

Retrieves messages for a specific conversation.

**Headers:**
- `Authorization`: Bearer \<session_id\>

**Parameters:**
- `conversation_id`: ID of the conversation

**Query Parameters:**
- `limit`: Maximum number of messages to return (default: 50)
- `offset`: Number of messages to skip (default: 0)

**Response:**
```json
{
  "messages": [
    {
      "id": "string",
      "conversation_id": "string",
      "role": "string (user|assistant|system|tool)",
      "content": "string",
      "created_at": "string (ISO datetime)",
      "tool_calls": [
        {
          "id": "string",
          "name": "string",
          "arguments": {},
          "result": "string (optional)"
        }
      ]
    }
  ],
  "total": "integer",
  "offset": "integer",
  "limit": "integer"
}
```

**Status Codes:**
- 200: Success
- 401: Unauthorized
- 404: Conversation not found

### Create Message
```
POST /api/conversations/{conversation_id}/messages
```

Adds a new message to a conversation and gets the assistant's response.

**Headers:**
- `Authorization`: Bearer \<session_id\>

**Parameters:**
- `conversation_id`: ID of the conversation

**Request Body:**
```json
{
  "content": "string",
  "role": "string (defaults to 'user')"
}
```

**Response:**
```json
{
  "id": "string",
  "conversation_id": "string",
  "role": "string",
  "content": "string",
  "created_at": "string (ISO datetime)"
}
```

**Status Codes:**
- 201: Created
- 401: Unauthorized
- 404: Conversation not found
- 422: Validation Error

## Real-time Updates

### SSE Connection
```
GET /api/sse/conversations/{conversation_id}
```

Establishes a Server-Sent Events (SSE) connection for real-time updates.

**Headers:**
- `Authorization`: Bearer \<session_id\>

**Parameters:**
- `conversation_id`: ID of the conversation

**Events:**
- `message_created`: When a new message is added
- `message_updated`: When a message is updated (e.g., during streaming)
- `conversation_updated`: When conversation metadata is updated
- `tool_execution_started`: When a tool execution begins
- `tool_execution_completed`: When a tool execution completes
- `tool_execution_failed`: When a tool execution fails

**Event Data Format:**
```
event: message_created
data: {"id":"msg-id","conversation_id":"conv-id","role":"assistant","content":"Hello!","created_at":"2025-03-06T21:10:05Z","metadata":{},"tool_calls":[],"is_complete":true}
```

**Status Codes:**
- 200: Success with established SSE connection
- 401: Unauthorized
- 404: Conversation not found

## MCP Tools

### List Available Tools
```
GET /api/tools
```

Retrieves a list of available tools from registered MCP servers.

**Headers:**
- `Authorization`: Bearer \<session_id\>

**Response:**
```json
{
  "tools": [
    {
      "id": "string",
      "name": "string",
      "description": "string",
      "server_id": "string",
      "server_name": "string",
      "parameters": {
        "schema": {}
      }
    }
  ]
}
```

**Status Codes:**
- 200: Success
- 401: Unauthorized

## Error Responses

All API endpoints may return the following error responses:

### Error Response Format
```json
{
  "detail": [
    {
      "loc": ["string (path to error)"],
      "msg": "string (error message)",
      "type": "string (error type)"
    }
  ]
}
```

### Authentication Error
```json
{
  "detail": "string (error message)"
}
```

### Not Found Error
```json
{
  "detail": "string (error message)"
}
```

### Server Error
```json
{
  "detail": "Internal server error"
}
```