# Cortex Core API Reference

This document provides detailed information about the API endpoints available in Cortex Core as implemented in Phase 2.

## Base URL

All endpoints are relative to the base URL:

```
http://localhost:8000
```

For production deployments, this will be replaced with the appropriate domain.

## Authentication

All endpoints except `/auth/login` require authentication using JWT tokens.

### Token Format

Tokens must be included in the `Authorization` header with the `Bearer` scheme:

```
Authorization: Bearer <token>
```

Tokens include the following claims:
- `sub`: Subject (user email)
- `oid`: Object ID (user ID from Azure B2C, or locally generated)
- `name`: User's display name
- `email`: User's email address
- `exp`: Expiration timestamp
- `iat`: Issued at timestamp

## API Endpoints

### Authentication

#### Login

```
POST /auth/login
```

Authenticates a user and returns a JWT token.

**Request Body:**
```json
{
  "username": "example@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Status Codes:**
- `200 OK`: Successful authentication
- `401 Unauthorized`: Invalid credentials

#### Verify Token

```
GET /auth/verify
```

Verifies a JWT token and returns the user information.

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Example User",
  "email": "example@example.com"
}
```

**Status Codes:**
- `200 OK`: Valid token
- `401 Unauthorized`: Invalid token

### Input

#### Send Input

```
POST /input
```

Sends input data to the system.

**Request Body:**
```json
{
  "content": "Hello, Cortex!",
  "conversation_id": "850e8400-e29b-41d4-a716-446655440333", // Required
  "metadata": {
    "client_id": "web-chat-client",
    "client_version": "1.0.0"
  }
}
```

**Response:**
```json
{
  "status": "received"
}
```

**Status Codes:**
- `200 OK`: Input received and processed
- `401 Unauthorized`: Invalid token
- `422 Unprocessable Entity`: Invalid request body

### Output

#### Stream Output

```
GET /output/stream
```

Establishes a Server-Sent Events (SSE) connection for receiving output events.

**Response:**
Server-Sent Events stream with the following event format:

```
data: {"type": "output", "content": "Hello, user!", "user_id": "550e8400-e29b-41d4-a716-446655440000", "timestamp": "2025-03-20T10:16:00Z"}

data: {"type": "typing", "is_typing": true, "user_id": "550e8400-e29b-41d4-a716-446655440000", "timestamp": "2025-03-20T10:16:00Z"}
```

**Common Event Types:**
- `input`: Input received from a client
- `output`: Output to be displayed to the user
- `typing`: Typing indicator status
- `heartbeat`: Connection keepalive (sent every 30 seconds)
- `error`: Error notification

**Status Codes:**
- `200 OK`: Connection established
- `401 Unauthorized`: Invalid token

### Configuration

#### Create Workspace

```
POST /config/workspace
```

Creates a new workspace.

**Request Body:**
```json
{
  "name": "My Workspace",
  "description": "A workspace for my project"
}
```

**Response:**
```json
{
  "id": "950e8400-e29b-41d4-a716-446655440444",
  "name": "My Workspace",
  "description": "A workspace for my project",
  "owner_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {}
}
```

**Status Codes:**
- `200 OK`: Workspace created
- `401 Unauthorized`: Invalid token
- `422 Unprocessable Entity`: Invalid request body

#### List Workspaces

```
GET /config/workspace
```

Lists all workspaces owned by the authenticated user.

**Response:**
```json
{
  "workspaces": [
    {
      "id": "950e8400-e29b-41d4-a716-446655440444",
      "name": "My Workspace",
      "description": "A workspace for my project",
      "owner_id": "550e8400-e29b-41d4-a716-446655440000",
      "metadata": {}
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Workspaces retrieved
- `401 Unauthorized`: Invalid token

#### Create Conversation

```
POST /config/conversation
```

Creates a new conversation in a workspace.

**Request Body:**
```json
{
  "workspace_id": "950e8400-e29b-41d4-a716-446655440444",
  "topic": "General Discussion"
}
```

**Response:**
```json
{
  "id": "850e8400-e29b-41d4-a716-446655440333",
  "workspace_id": "950e8400-e29b-41d4-a716-446655440444",
  "topic": "General Discussion",
  "participant_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "metadata": {}
}
```

**Status Codes:**
- `200 OK`: Conversation created
- `401 Unauthorized`: Invalid token
- `404 Not Found`: Workspace not found
- `422 Unprocessable Entity`: Invalid request body

#### List Conversations

```
GET /config/conversation?workspace_id=950e8400-e29b-41d4-a716-446655440444
```

Lists all conversations in a workspace.

**Query Parameters:**
- `workspace_id`: ID of the workspace

**Response:**
```json
{
  "conversations": [
    {
      "id": "850e8400-e29b-41d4-a716-446655440333",
      "workspace_id": "950e8400-e29b-41d4-a716-446655440444",
      "topic": "General Discussion",
      "participant_ids": ["550e8400-e29b-41d4-a716-446655440000"],
      "metadata": {}
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Conversations retrieved
- `401 Unauthorized`: Invalid token
- `404 Not Found`: Workspace not found

## Error Responses

All error responses follow a consistent format:

```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable error message",
    "details": {
      // Additional error-specific details
    }
  },
  "request_id": "unique-request-identifier"
}
```

For validation errors, the response includes more detailed information:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Validation error in request data",
    "status_code": 422,
    "details": {
      "validation_errors": [
        {
          "loc": ["body", "conversation_id"],
          "msg": "field required",
          "type": "value_error.missing"
        }
      ]
    }
  },
  "request_id": "unique-request-identifier"
}
```

## Rate Limiting

In Phase 2, no rate limiting is implemented. Future phases will add appropriate rate limiting headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1616239022
```

## CORS

Cross-Origin Resource Sharing (CORS) is enabled for development with configurable allowed origins. By default, all origins are allowed in development mode.

## Client Implementation Notes

### Server-Sent Events (SSE)

When implementing an SSE client:

1. Connect to the `/output/stream` endpoint with the JWT token in the Authorization header
2. Listen for events and parse the JSON data
3. Filter events by type if needed
4. Implement reconnection logic (browsers handle this automatically)
5. Handle heartbeat events (sent every 30 seconds)

Example JavaScript client:

```javascript
const eventSource = new EventSource('/output/stream', {
  headers: {
    'Authorization': 'Bearer your-jwt-token'
  }
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'output':
      console.log('Received output:', data.content);
      break;
    case 'typing':
      console.log('Typing status:', data.is_typing);
      break;
    case 'heartbeat':
      console.log('Heartbeat received');
      break;
  }
};

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  // Implement custom reconnection logic if needed
};
```

### Input Handling

When sending input:

1. Include the JWT token in the Authorization header
2. Format the request body according to the API specification
3. Handle error responses appropriately

Example JavaScript client:

```javascript
async function sendInput(content, conversationId) {
  // Ensure conversation ID is provided
  if (!conversationId) {
    throw new Error('Conversation ID is required');
  }
  
  try {
    const response = await fetch('/input', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer your-jwt-token'
      },
      body: JSON.stringify({
        content,
        conversation_id: conversationId,
        metadata: {
          client_id: 'web-chat-client',
          client_version: '1.0.0'
        }
      })
    });
    
    if (!response.ok) {
      throw new Error(`Error sending input: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Failed to send input:', error);
    throw error;
  }
}
```