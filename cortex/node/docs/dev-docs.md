# Cortex Core Developer Documentation

## Overview

Cortex Core is a central AI orchestration system that coordinates interactions between users, memory systems, domain expert entities, and external integrations. This document provides guidance for developers building clients that interact with the Cortex Core API.

## Getting Started

### Prerequisites

- Node.js 18+ for client development
- API base URL for your Cortex Core instance (default: `http://localhost:4000`)

### Authentication

All API interactions (except authentication endpoints) require a valid JWT token.

#### Login

**Endpoint**: `POST /auth/login`

**Request Body**:

```json
{
  "type": "password",
  "identifier": "user@example.com",
  "secret": "userpassword"
}
```

**Response**:

```json
{
  "token": "jwt-token-string",
  "userId": "user-id-string",
  "expiresAt": "2023-04-01T12:00:00Z"
}
```

**Authentication Header**: Include the token in all subsequent requests:

```
Authorization: Bearer jwt-token-string
```

> **Development Note**: When using a development environment, a test user with email `test@example.com` and password `password` will be automatically created on first login attempt.

## Core Concepts

Cortex Core organizes data in a hierarchical structure:

- **User**: A user account that owns workspaces
- **Workspace**: A container for related conversations and context
- **Conversation**: A thread of interactions within a workspace
- **Entry**: An individual message within a conversation

## API Reference

### Workspaces

#### List Workspaces

**Endpoint**: `GET /workspaces`

**Response**:

```json
{
  "workspaces": [
    {
      "id": "workspace-id",
      "userId": "user-id",
      "name": "Workspace Name",
      "createdAt": "2023-03-15T10:30:00Z",
      "lastActiveAt": "2023-03-16T14:20:00Z",
      "config": {
        "defaultModality": "chat",
        "sharingEnabled": false,
        "retentionDays": 90
      },
      "metadata": {}
    }
  ]
}
```

#### Create Workspace

**Endpoint**: `POST /workspaces`

**Request Body**:

```json
{
  "name": "New Workspace",
  "config": {
    "defaultModality": "chat",
    "sharingEnabled": false,
    "retentionDays": 90
  }
}
```

**Response**: Same as a single workspace object.

#### Get Workspace

**Endpoint**: `GET /workspaces/{id}`

**Response**: A single workspace object.

### Conversations

#### List Conversations

**Endpoint**: `GET /workspaces/{workspaceId}/conversations`

**Query Parameters**:

- `modality` (optional): Filter by modality (e.g., "chat")
- `fromDate` (optional): ISO date string
- `toDate` (optional): ISO date string
- `search` (optional): Search term for titles and metadata

**Response**:

```json
{
  "conversations": [
    {
      "id": "conversation-id",
      "workspaceId": "workspace-id",
      "modality": "chat",
      "title": "Conversation Title",
      "createdAt": "2023-03-15T10:30:00Z",
      "lastActiveAt": "2023-03-16T14:20:00Z",
      "entries": [],
      "metadata": {}
    }
  ]
}
```

#### Create Conversation

**Endpoint**: `POST /workspaces/{workspaceId}/conversations`

**Request Body**:

```json
{
  "modality": "chat",
  "title": "New Conversation"
}
```

**Response**: A single conversation object.

#### Get Conversation

**Endpoint**: `GET /conversations/{id}`

**Response**: A single conversation object with entries.

#### Add Message

**Endpoint**: `POST /conversations/{id}/messages`

**Request Body**:

```json
{
  "content": "Hello, Cortex!",
  "type": "user",
  "metadata": {} // Optional
}
```

**Response**:

```json
{
  "entry": {
    "id": "entry-id",
    "type": "user",
    "content": "Hello, Cortex!",
    "timestamp": "2023-03-16T14:20:00Z",
    "metadata": {}
  }
}
```

> **Note**: When a user message is sent, the system will automatically process it and respond with an assistant message. This response will be delivered through the real-time channel (Socket.IO).

## Real-time Updates

Cortex Core provides real-time updates through Socket.IO.

### Connecting

```javascript
const socket = io("http://localhost:4000", {
  auth: {
    token: "jwt-token-string",
  },
});

socket.on("connect", () => {
  console.log("Connected to Cortex Core");
});

socket.on("error", (error) => {
  console.error("Socket error:", error);
});
```

### Conversation Updates

```javascript
// Join a conversation room to receive updates
socket.emit("join-conversation", "conversation-id");

// Listen for new messages
socket.on("message", (message) => {
  console.log("Received message:", message);
  // message = { type, content, timestamp, metadata }
});

// Leave a conversation room
socket.emit("leave-conversation", "conversation-id");
```

## MCP (Model Context Protocol) Integration

The MCP protocol enables two-way communication between Cortex Core and external tools.

### Configuration

MCP endpoints can be configured in several ways:

1. **Environment Variables**:

   ```
   # JSON array of endpoints
   MCP_ENDPOINTS=[{"name":"vscode","endpoint":"http://localhost:5000","type":"vscode"}]

   # OR individual endpoints
   MCP_ENDPOINT_VSCODE=http://localhost:5000|vscode
   ```

2. **In code** via `config.ts`:
   ```typescript
   mcp: {
     endpoints: [
       { name: "vscode", endpoint: "http://localhost:5000", type: "vscode" },
     ];
   }
   ```

### MCP API Endpoints

#### List MCP Integrations

**Endpoint**: `GET /mcp/integrations`

**Response**:

```json
{
  "integrations": [
    {
      "id": "integration-id",
      "name": "vscode",
      "type": "vscode",
      "connectionDetails": {
        "protocol": "mcp",
        "endpoint": "http://localhost:5000"
      },
      "capabilities": [],
      "status": "connected",
      "lastActive": "2023-03-16T14:20:00Z"
    }
  ]
}
```

#### Send MCP Message

**Endpoint**: `POST /mcp?integration={integrationId}`

**Request Body**: Any valid MCP message

**Response**: The response from the integration

#### Connect to MCP Events

**Endpoint**: `GET /mcp/events?integration={integrationId}`

This is a Server-Sent Events (SSE) endpoint that provides real-time updates from MCP integrations.

```javascript
const eventSource = new EventSource(
  `${API_URL}/mcp/events?integration=${integrationId}`,
  {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  }
);

eventSource.addEventListener("connection", (event) => {
  const data = JSON.parse(event.data);
  console.log("MCP connection established:", data);
});

eventSource.addEventListener("integration-event", (event) => {
  const data = JSON.parse(event.data);
  console.log("MCP event:", data);
});

eventSource.onerror = (error) => {
  console.error("SSE error:", error);
  eventSource.close();
};
```

## Building a Client Application

### Recommended Flow

1. **Authentication**:

   - Login and obtain a JWT token
   - Store token securely for subsequent requests

2. **Workspace Management**:

   - List available workspaces
   - Create a new workspace if needed
   - Select a workspace for the session

3. **Conversation Management**:

   - List conversations in the selected workspace
   - Create a new conversation or select an existing one
   - Load conversation history

4. **Interaction**:

   - Connect to real-time updates via Socket.IO
   - Send user messages and receive assistant responses
   - Display messages and handle updates

5. **Integration**:
   - List available MCP integrations
   - Connect to relevant integrations
   - Exchange messages with integrations

### Best Practices

1. **Authentication**:

   - Handle token expiration gracefully
   - Store tokens securely (not in localStorage for production)
   - Implement refresh token flow if applicable

2. **Error Handling**:

   - Implement consistent error handling for all API calls
   - Provide meaningful feedback to users
   - Retry transient failures with exponential backoff

3. **Real-time Updates**:

   - Implement reconnection logic for WebSocket connections
   - Handle temporary disconnections without losing context
   - Buffer messages during disconnections

4. **Performance**:

   - Cache workspace and conversation data when appropriate
   - Implement pagination for large datasets
   - Use background fetching for non-critical data

5. **User Experience**:
   - Show loading indicators for long-running operations
   - Provide immediate feedback for user actions
   - Implement optimistic updates for a smoother experience

## Troubleshooting

### Common Issues

1. **Authentication Failures**:

   - Ensure credentials are correct
   - Check if the token has expired
   - Verify the token is being sent correctly in the Authorization header

2. **API Connection Issues**:

   - Verify the API base URL is correct
   - Check network connectivity
   - Ensure CORS is properly configured if applicable

3. **WebSocket Disconnections**:
   - Implement reconnection logic
   - Check for network issues or proxies
   - Verify authentication is maintained

### Logging

Enable detailed logging in your client to help troubleshoot issues:

```javascript
// Enable verbose logging
const enableDebugLogging = true;

function log(level, message, data) {
  if (enableDebugLogging || level === "error") {
    console[level](`[Cortex] ${message}`, data);
  }
}

// Example usage
log("info", "Connecting to Cortex API");
log("error", "Authentication failed", error);
```
