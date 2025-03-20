# Cortex Core Client Integration Guide

This document provides guidance for developers building client applications that integrate with Cortex Core. It covers authentication, input/output communication, and best practices.

## Overview

Cortex Core provides a clean, simple API for communication between input clients (which send data) and output clients (which receive processed data). The system is designed to be easy to integrate with while maintaining proper data isolation between users.

## Integration Architecture

```mermaid
flowchart LR
    InputClient["Input Client"] -->|HTTP POST| CortexCore["Cortex Core"]
    CortexCore -->|SSE GET| OutputClient["Output Client"]

    style InputClient stroke:#f9f,stroke-width:4px
    style CortexCore stroke:#bbf,stroke-width:4px
    style OutputClient stroke:#bfb,stroke-width:4px
```

- **Input Clients**: Send data to Cortex Core via HTTP POST
- **Output Clients**: Receive data from Cortex Core via Server-Sent Events (SSE)
- **Authentication**: Both use JWT tokens for authentication

## Authentication

### Obtaining a JWT Token

1. Make a POST request to the `/auth/login` endpoint:

```http
POST /auth/login
Content-Type: application/json

{
  "username": "example@example.com",
  "password": "password123"
}
```

2. The response will contain a JWT token:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

3. Include this token in all subsequent requests:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Verification

You can verify your token is valid by making a GET request to `/auth/verify`:

```http
GET /auth/verify
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

The response will contain your user information:

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Example User",
  "email": "example@example.com"
}
```

### Token Lifecycle

- Tokens are valid for 24 hours by default
- There is no token refresh mechanism in Phase 1
- When a token expires, you'll need to obtain a new one

## Input Client Integration

Input clients send data to Cortex Core via HTTP POST requests.

### Sending Input

1. Make a POST request to the `/input` endpoint:

```http
POST /input
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{
  "content": "Hello, Cortex!",
  "conversation_id": "850e8400-e29b-41d4-a716-446655440333",
  "metadata": {
    "client_id": "web-chat-client",
    "client_version": "1.0.0"
  }
}
```

2. The response will confirm receipt:

```json
{
  "status": "received"
}
```

### Input Request Format

The input request must include:

- `content`: The message content (required, string)
- `conversation_id`: The ID of the conversation (required, UUID string)
- `metadata`: Optional metadata about the client (object)

### Error Handling

Handle these potential error responses:

- `401 Unauthorized`: Invalid or expired token
- `422 Unprocessable Entity`: Invalid request format
- `500 Internal Server Error`: Server-side error

### JavaScript Example

```javascript
async function sendInput(content, conversationId, token) {
  try {
    const response = await fetch("http://localhost:8000/input", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        content,
        conversation_id: conversationId,
        metadata: {
          client_id: "web-chat-client",
          client_version: "1.0.0",
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to send input:", error);
    throw error;
  }
}
```

### Python Example

```python
import requests

def send_input(content, conversation_id, token):
    try:
        response = requests.post(
            'http://localhost:8000/input',
            json={
                'content': content,
                'conversation_id': conversation_id,
                'metadata': {
                    'client_id': 'python-client',
                    'client_version': '1.0.0'
                }
            },
            headers={
                'Authorization': f'Bearer {token}'
            }
        )

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending input: {e}")
        raise
```

## Output Client Integration

Output clients receive data from Cortex Core via Server-Sent Events (SSE).

### Connecting to the SSE Stream

1. Make a GET request to the `/output/stream` endpoint:

```http
GET /output/stream
Accept: text/event-stream
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

2. The response will be a stream of SSE events:

```
data: {"type": "output", "content": "Hello, user!", "user_id": "550e8400-e29b-41d4-a716-446655440000", "timestamp": "2025-03-20T10:16:00Z"}

data: {"type": "typing", "is_typing": true, "user_id": "550e8400-e29b-41d4-a716-446655440000", "timestamp": "2025-03-20T10:16:00Z"}
```

### Event Types

The SSE stream includes these event types:

- `input`: Input received from a client
- `output`: Output to be displayed to the user
- `typing`: Typing indicator status
- `heartbeat`: Connection keepalive (sent every 30 seconds)
- `error`: Error notification

### Handling SSE Connections

When implementing an SSE client:

1. Use appropriate SSE libraries for your platform
2. Implement reconnection logic (browsers handle this automatically)
3. Handle JSON parsing of event data
4. Filter events by type based on your needs
5. Keep the connection open for real-time updates

### JavaScript Example

```javascript
function connectToOutputStream(token, onEvent) {
  const eventSource = new EventSource("/output/stream", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onEvent(data);
    } catch (error) {
      console.error("Error parsing SSE event:", error);
    }
  };

  eventSource.onerror = (error) => {
    console.error("SSE connection error:", error);
    // Implement reconnection logic if needed
    // Browsers automatically try to reconnect
    setTimeout(() => eventSource.close(), 3000);
  };

  return {
    close: () => eventSource.close(),
  };
}

// Usage
const connection = connectToOutputStream(token, (event) => {
  switch (event.type) {
    case "output":
      console.log("Received output:", event.content);
      break;
    case "typing":
      console.log("Typing status:", event.is_typing);
      break;
    case "heartbeat":
      console.log("Heartbeat received");
      break;
  }
});

// Later, close the connection
connection.close();
```

### Python Example

```python
import json
import sseclient
import requests

def connect_to_output_stream(token, on_event):
    """Connect to the SSE output stream and call on_event for each event."""
    session = requests.Session()
    session.headers.update({
        'Accept': 'text/event-stream',
        'Authorization': f'Bearer {token}'
    })

    try:
        response = session.get('http://localhost:8000/output/stream', stream=True)
        response.raise_for_status()

        client = sseclient.SSEClient(response)
        for event in client.events():
            try:
                data = json.loads(event.data)
                on_event(data)
            except json.JSONDecodeError as e:
                print(f"Error parsing SSE event: {e}")
    except requests.exceptions.RequestException as e:
        print(f"SSE connection error: {e}")
    finally:
        session.close()

# Usage
def handle_event(event):
    event_type = event.get('type')
    if event_type == 'output':
        print(f"Received output: {event.get('content')}")
    elif event_type == 'typing':
        print(f"Typing status: {event.get('is_typing')}")
    elif event_type == 'heartbeat':
        print("Heartbeat received")

# Start in a separate thread or async task
import threading
thread = threading.Thread(
    target=connect_to_output_stream,
    args=(token, handle_event),
    daemon=True
)
thread.start()
```

## Workspace and Conversation Management

Before sending and receiving messages, you need to create workspaces and conversations.

### Creating a Workspace

```http
POST /config/workspace
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{
  "name": "My Workspace",
  "description": "A workspace for my project"
}
```

Response:

```json
{
  "id": "950e8400-e29b-41d4-a716-446655440444",
  "name": "My Workspace",
  "description": "A workspace for my project",
  "owner_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {}
}
```

### Listing Workspaces

```http
GET /config/workspace
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Response:

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

### Creating a Conversation

```http
POST /config/conversation
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{
  "workspace_id": "950e8400-e29b-41d4-a716-446655440444",
  "topic": "General Discussion"
}
```

Response:

```json
{
  "id": "850e8400-e29b-41d4-a716-446655440333",
  "workspace_id": "950e8400-e29b-41d4-a716-446655440444",
  "topic": "General Discussion",
  "participant_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "metadata": {}
}
```

### Listing Conversations

```http
GET /config/conversation?workspace_id=950e8400-e29b-41d4-a716-446655440444
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Response:

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

## End-to-End Example

Here's an end-to-end example that ties everything together:

```javascript
// 1. Authenticate
async function authenticate(username, password) {
  const response = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) throw new Error("Authentication failed");
  const data = await response.json();
  return data.access_token;
}

// 2. Create a workspace
async function createWorkspace(token, name, description) {
  const response = await fetch("/config/workspace", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ name, description }),
  });

  if (!response.ok) throw new Error("Failed to create workspace");
  return await response.json();
}

// 3. Create a conversation
async function createConversation(token, workspaceId, topic) {
  const response = await fetch("/config/conversation", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ workspace_id: workspaceId, topic }),
  });

  if (!response.ok) throw new Error("Failed to create conversation");
  return await response.json();
}

// 4. Connect to the output stream
function connectToOutputStream(token, onEvent) {
  const eventSource = new EventSource("/output/stream", {
    headers: { Authorization: `Bearer ${token}` },
  });

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onEvent(data);
  };

  return { close: () => eventSource.close() };
}

// 5. Send input
async function sendInput(token, content, conversationId) {
  const response = await fetch("/input", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      content,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok) throw new Error("Failed to send input");
  return await response.json();
}

// Put it all together
async function main() {
  try {
    // Authenticate
    const token = await authenticate("user@example.com", "password123");

    // Create workspace
    const workspace = await createWorkspace(
      token,
      "My Workspace",
      "A test workspace"
    );
    console.log("Created workspace:", workspace);

    // Create conversation
    const conversation = await createConversation(
      token,
      workspace.id,
      "Test Conversation"
    );
    console.log("Created conversation:", conversation);

    // Connect to output stream
    const connection = connectToOutputStream(token, (event) => {
      console.log("Received event:", event);
    });

    // Send input
    const result = await sendInput(token, "Hello, Cortex!", conversation.id);
    console.log("Input sent:", result);

    // Later, close connection
    // connection.close();
  } catch (error) {
    console.error("Error:", error);
  }
}

main();
```

## Best Practices

### Authentication

1. **Store tokens securely**: Use secure storage mechanisms appropriate for your platform
2. **Handle token expiration**: Detect 401 responses and reauthenticate when needed
3. **Protect tokens**: Never expose tokens in URLs or client-side code

### Input Client

1. **Validate input locally**: Validate data before sending to reduce server errors
2. **Handle errors gracefully**: Provide clear feedback for authentication and validation errors
3. **Include appropriate metadata**: Add client ID and version to help with debugging
4. **Implement retries**: Add retries with backoff for transient failures

### Output Client

1. **Implement reconnection logic**: Handle connection drops appropriately
2. **Process events asynchronously**: Don't block the event processing thread
3. **Filter events by type**: Process only the event types your client needs
4. **Handle heartbeats**: Use heartbeats to detect connection health
5. **Properly close connections**: Close SSE connections when no longer needed

### General

1. **Use UUIDs for IDs**: Always use proper UUIDs for workspace and conversation IDs
2. **Respect rate limits**: Implement appropriate backoff when rate limits are hit
3. **Check conversation access**: Verify a user has access to a conversation before using it
4. **Log correlation IDs**: Use event IDs or timestamps for correlating events
5. **Implement proper error handling**: Provide clear error messages to users

## Troubleshooting

### Common Issues

1. **401 Unauthorized**

   - Check that the token is valid and not expired
   - Ensure the token is correctly formatted in the Authorization header
   - Try re-authenticating to get a new token

2. **SSE Connection Drops**

   - Implement reconnection logic with exponential backoff
   - Check network stability
   - Verify the server is still running

3. **Events Not Received**

   - Verify you're using the correct user_id
   - Check that the conversation exists and is accessible to the user
   - Ensure the SSE connection is established correctly

4. **Invalid Request Format**
   - Double-check the request format against the API documentation
   - Ensure all required fields are included
   - Validate UUIDs are properly formatted

### Debugging Tips

1. **Enable Verbose Logging**

   - Log all API requests and responses
   - Record SSE events for debugging
   - Track event timing for performance issues

2. **Use API Inspection Tools**

   - Browser DevTools Network tab
   - Tools like Postman or Insomnia
   - Network packet analyzers if needed

3. **Test in Isolation**
   - Test authentication separately
   - Verify SSE connection works independently
   - Test input sending with curl

## Future Enhancements

In future phases, the API will be enhanced with:

1. **Persistent Storage**: Data will persist across server restarts
2. **Azure B2C Integration**: Production authentication with Azure B2C
3. **Token Refresh**: Mechanism to refresh tokens without reauthentication
4. **Rate Limiting**: Appropriate rate limits with headers
5. **WebSockets Option**: Alternative to SSE for some clients
6. **Event Acknowledgment**: Confirming event receipt
7. **MCP Protocol Support**: Advanced service communication

## Support

For issues or questions about integrating with Cortex Core:

1. Check the API documentation
2. Run tests with the provided examples
3. Contact the development team for assistance

## Conclusion

This guide should provide everything you need to successfully integrate clients with Cortex Core. The API is designed to be simple and consistent, making integration straightforward across different platforms and languages.
