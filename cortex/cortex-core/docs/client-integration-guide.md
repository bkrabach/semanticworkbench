# Cortex Core Client Integration Guide

This guide provides comprehensive documentation for developers building client applications that interface with the Cortex Core API. The document outlines all necessary endpoints, authentication methods, data structures, and real-time communication patterns required to build a fully functional client.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Conversation Management](#conversation-management)
4. [Message Handling](#message-handling)
5. [Real-time Updates with SSE](#real-time-updates-with-sse)
6. [Error Handling](#error-handling)
7. [Complete API Reference](#complete-api-reference)
8. [Client Implementation Examples](#client-implementation-examples)

## Overview

Cortex Core provides a RESTful API for managing AI-powered conversations. Clients can:

- Create and manage conversations
- Send messages and receive AI responses
- Subscribe to real-time updates via Server-Sent Events (SSE)
- Handle conversation context and history

The API follows RESTful principles with JSON as the primary data format.

## Authentication

### Authentication Flow

Cortex Core uses bearer token authentication. All API requests (except for token validation) must include an `Authorization` header with a valid bearer token.

```
Authorization: Bearer <your-token>
```

### Validating Sessions

To validate a session token:

```
GET /api/validate-session
Authorization: Bearer <your-token>
```

#### Response

```json
{
  "valid": true,
  "user": {
    "id": "user-id",
    "name": "User Name"
  }
}
```

If the token is invalid:

```json
{
  "valid": false,
  "user": null
}
```

## Conversation Management

### List Conversations

Retrieves all conversations for the authenticated user.

```
GET /api/conversations?limit=10&offset=0&sort_by=updated_at&sort_order=desc
Authorization: Bearer <your-token>
```

#### Query Parameters

- `limit` (optional): Maximum number of conversations to return (default: 10)
- `offset` (optional): Number of conversations to skip (for pagination) (default: 0)
- `sort_by` (optional): Field to sort by (`created_at`, `updated_at`, `title`) (default: `updated_at`)
- `sort_order` (optional): Sort order (`asc`, `desc`) (default: `desc`)

#### Response

```json
{
  "conversations": [
    {
      "id": "conversation-id",
      "user_id": "user-id",
      "title": "Conversation Title",
      "created_at": "2025-03-06T21:00:00Z",
      "updated_at": "2025-03-06T21:05:00Z",
      "metadata": {},
      "messages": []
    }
  ],
  "total": 10
}
```

### Create a New Conversation

```
POST /api/conversations
Authorization: Bearer <your-token>
Content-Type: application/json

{
  "title": "New Conversation"
}
```

#### Response

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

### Get a Specific Conversation

```
GET /api/conversations/{conversation_id}
Authorization: Bearer <your-token>
```

#### Response

```json
{
  "conversation": {
    "id": "conversation-id",
    "user_id": "user-id",
    "title": "Conversation Title",
    "created_at": "2025-03-06T21:00:00Z",
    "updated_at": "2025-03-06T21:05:00Z",
    "metadata": {},
    "messages": [
      {
        "id": "message-id",
        "conversation_id": "conversation-id",
        "role": "user",
        "content": "Hello, AI!",
        "created_at": "2025-03-06T21:01:00Z",
        "metadata": {},
        "tool_calls": [],
        "is_complete": true
      },
      {
        "id": "message-id-2",
        "conversation_id": "conversation-id",
        "role": "assistant",
        "content": "Hello! How can I help you today?",
        "created_at": "2025-03-06T21:02:00Z",
        "metadata": {},
        "tool_calls": [],
        "is_complete": true
      }
    ]
  }
}
```

### Delete a Conversation

```
DELETE /api/conversations/{conversation_id}
Authorization: Bearer <your-token>
```

#### Response

```json
{
  "success": true
}
```

## Message Handling

### List Messages in a Conversation

```
GET /api/conversations/{conversation_id}/messages?limit=50&offset=0
Authorization: Bearer <your-token>
```

#### Query Parameters

- `limit` (optional): Maximum number of messages to return (default: 50)
- `offset` (optional): Number of messages to skip (for pagination) (default: 0)
- `before_id` (optional): Return messages before this message ID
- `after_id` (optional): Return messages after this message ID

#### Response

```json
{
  "messages": [
    {
      "id": "message-id",
      "conversation_id": "conversation-id",
      "role": "user",
      "content": "Hello, AI!",
      "created_at": "2025-03-06T21:01:00Z",
      "metadata": {},
      "tool_calls": [],
      "is_complete": true
    },
    {
      "id": "message-id-2",
      "conversation_id": "conversation-id",
      "role": "assistant",
      "content": "Hello! How can I help you today?",
      "created_at": "2025-03-06T21:02:00Z",
      "metadata": {},
      "tool_calls": [],
      "is_complete": true
    }
  ],
  "total": 2
}
```

### Send a Message

```
POST /api/conversations/{conversation_id}/messages
Authorization: Bearer <your-token>
Content-Type: application/json

{
  "content": "Hello, AI!",
  "role": "user"
}
```

#### Response

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

**Note:** When you send a user message, the system automatically processes it and generates an assistant response. This response is not included in the immediate API response. Instead, you should use Server-Sent Events (SSE) to receive the assistant's response in real-time.

## Real-time Updates with SSE

Cortex Core uses Server-Sent Events (SSE) to provide real-time updates for conversations. This is particularly important for receiving assistant responses and status updates.

### Establishing an SSE Connection

```
GET /api/sse/conversations/{conversation_id}
Authorization: Bearer <your-token>
```

The server will establish an SSE connection and send events in the following format:

```
event: message_created
data: {"id":"message-id","conversation_id":"conversation-id","role":"assistant","content":"I'm thinking...","created_at":"2025-03-06T21:10:05Z","metadata":{},"tool_calls":[],"is_complete":false}

event: message_updated
data: {"id":"message-id","conversation_id":"conversation-id","role":"assistant","content":"Hello! How can I help you today?","created_at":"2025-03-06T21:10:05Z","metadata":{},"tool_calls":[],"is_complete":true}
```

### SSE Event Types

- `message_created`: A new message has been created
- `message_updated`: An existing message has been updated (e.g., when streaming a response)
- `message_deleted`: A message has been deleted
- `conversation_updated`: The conversation metadata has been updated
- `tool_execution_started`: A tool execution has begun
- `tool_execution_completed`: A tool execution has completed
- `tool_execution_failed`: A tool execution has failed

### Handling SSE in Clients

Here's a JavaScript example for handling SSE connections:

```javascript
function connectToSSE(conversationId, token) {
  const eventSource = new EventSource(
    `/api/sse/conversations/${conversationId}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  eventSource.addEventListener("message_created", (event) => {
    const message = JSON.parse(event.data);
    console.log("New message:", message);
    // Update UI with new message
  });

  eventSource.addEventListener("message_updated", (event) => {
    const message = JSON.parse(event.data);
    console.log("Updated message:", message);
    // Update UI with updated message content
  });

  eventSource.addEventListener("error", (error) => {
    console.error("SSE error:", error);
    eventSource.close();
    // Implement reconnection logic here
  });

  return eventSource;
}
```

## Error Handling

The API uses standard HTTP status codes for error responses:

- `400 Bad Request`: The request was invalid
- `401 Unauthorized`: Authentication is required or failed
- `403 Forbidden`: The user doesn't have permission for the requested operation
- `404 Not Found`: The requested resource doesn't exist
- `500 Internal Server Error`: An unexpected server error occurred

Error responses follow this format:

```json
{
  "detail": "Error message",
  "code": "optional_error_code"
}
```

## Complete API Reference

| Endpoint                                        | Method | Description                     |
| ----------------------------------------------- | ------ | ------------------------------- |
| `/api/validate-session`                         | GET    | Validate a session token        |
| `/api/conversations`                            | GET    | List conversations              |
| `/api/conversations`                            | POST   | Create a new conversation       |
| `/api/conversations/{conversation_id}`          | GET    | Get a specific conversation     |
| `/api/conversations/{conversation_id}`          | DELETE | Delete a conversation           |
| `/api/conversations/{conversation_id}/messages` | GET    | List messages in a conversation |
| `/api/conversations/{conversation_id}/messages` | POST   | Send a message                  |
| `/api/sse/conversations/{conversation_id}`      | GET    | Establish an SSE connection     |

## Client Implementation Examples

### JavaScript/TypeScript Client

Here's a simple JavaScript client implementation using the fetch API and EventSource for SSE:

```javascript
class CortexClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.token = token;
    this.sseConnections = {};
  }

  async request(endpoint, method = "GET", body = null) {
    const headers = {
      Authorization: `Bearer ${this.token}`,
      "Content-Type": "application/json",
    };

    const options = {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    };

    const response = await fetch(`${this.baseUrl}${endpoint}`, options);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Unknown error");
    }

    return response.json();
  }

  // Authentication
  async validateSession() {
    return this.request("/api/validate-session");
  }

  // Conversations
  async listConversations(
    limit = 10,
    offset = 0,
    sortBy = "updated_at",
    sortOrder = "desc"
  ) {
    return this.request(
      `/api/conversations?limit=${limit}&offset=${offset}&sort_by=${sortBy}&sort_order=${sortOrder}`
    );
  }

  async createConversation(title = "New Conversation") {
    return this.request("/api/conversations", "POST", { title });
  }

  async getConversation(conversationId) {
    return this.request(`/api/conversations/${conversationId}`);
  }

  async deleteConversation(conversationId) {
    return this.request(`/api/conversations/${conversationId}`, "DELETE");
  }

  // Messages
  async listMessages(conversationId, limit = 50, offset = 0) {
    return this.request(
      `/api/conversations/${conversationId}/messages?limit=${limit}&offset=${offset}`
    );
  }

  async sendMessage(conversationId, content) {
    return this.request(
      `/api/conversations/${conversationId}/messages`,
      "POST",
      {
        content,
        role: "user",
      }
    );
  }

  // Server-Sent Events
  connectToSSE(conversationId, callbacks = {}) {
    const eventSource = new EventSource(
      `${this.baseUrl}/api/sse/conversations/${conversationId}`,
      {
        headers: {
          Authorization: `Bearer ${this.token}`,
        },
      }
    );

    // Set up event listeners
    eventSource.addEventListener("message_created", (event) => {
      if (callbacks.onMessageCreated) {
        callbacks.onMessageCreated(JSON.parse(event.data));
      }
    });

    eventSource.addEventListener("message_updated", (event) => {
      if (callbacks.onMessageUpdated) {
        callbacks.onMessageUpdated(JSON.parse(event.data));
      }
    });

    eventSource.addEventListener("error", (error) => {
      if (callbacks.onError) {
        callbacks.onError(error);
      }
      eventSource.close();
    });

    this.sseConnections[conversationId] = eventSource;
    return eventSource;
  }

  disconnectSSE(conversationId) {
    if (this.sseConnections[conversationId]) {
      this.sseConnections[conversationId].close();
      delete this.sseConnections[conversationId];
    }
  }

  disconnectAllSSE() {
    Object.values(this.sseConnections).forEach((connection) =>
      connection.close()
    );
    this.sseConnections = {};
  }
}

// Usage example
async function example() {
  const client = new CortexClient("http://localhost:8000", "your-token-here");

  // Create a new conversation
  const { conversation } = await client.createConversation("My New Chat");
  console.log("Created conversation:", conversation);

  // Connect to SSE for real-time updates
  client.connectToSSE(conversation.id, {
    onMessageCreated: (message) => console.log("New message:", message),
    onMessageUpdated: (message) => console.log("Updated message:", message),
    onError: (error) => console.error("SSE error:", error),
  });

  // Send a message
  await client.sendMessage(conversation.id, "Hello, AI!");
  console.log("Message sent");

  // The AI's response will come through the SSE connection
}
```

### Python Client

Here's a Python client implementation using the `requests` and `sseclient` libraries:

```python
import requests
import json
import sseclient
import threading

class CortexClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token
        self.sse_threads = {}
        self.sse_running = {}

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def request(self, endpoint, method='GET', data=None):
        url = f"{self.base_url}{endpoint}"
        headers = self._headers()

        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if not response.ok:
            try:
                error = response.json()
                detail = error.get('detail', 'Unknown error')
            except:
                detail = response.text or 'Unknown error'

            raise Exception(f"API Error ({response.status_code}): {detail}")

        return response.json()

    # Authentication
    def validate_session(self):
        return self.request('/api/validate-session')

    # Conversations
    def list_conversations(self, limit=10, offset=0, sort_by='updated_at', sort_order='desc'):
        return self.request(f'/api/conversations?limit={limit}&offset={offset}&sort_by={sort_by}&sort_order={sort_order}')

    def create_conversation(self, title='New Conversation'):
        return self.request('/api/conversations', method='POST', data={'title': title})

    def get_conversation(self, conversation_id):
        return self.request(f'/api/conversations/{conversation_id}')

    def delete_conversation(self, conversation_id):
        return self.request(f'/api/conversations/{conversation_id}', method='DELETE')

    # Messages
    def list_messages(self, conversation_id, limit=50, offset=0):
        return self.request(f'/api/conversations/{conversation_id}/messages?limit={limit}&offset={offset}')

    def send_message(self, conversation_id, content):
        return self.request(
            f'/api/conversations/{conversation_id}/messages',
            method='POST',
            data={'content': content, 'role': 'user'}
        )

    # Server-Sent Events
    def _sse_listener(self, conversation_id, callbacks):
        headers = self._headers()
        url = f"{self.base_url}/api/sse/conversations/{conversation_id}"

        self.sse_running[conversation_id] = True

        try:
            response = requests.get(url, headers=headers, stream=True)
            client = sseclient.SSEClient(response)

            for event in client.events():
                if not self.sse_running.get(conversation_id, False):
                    break

                event_type = event.event
                data = json.loads(event.data)

                if event_type == 'message_created' and 'onMessageCreated' in callbacks:
                    callbacks['onMessageCreated'](data)
                elif event_type == 'message_updated' and 'onMessageUpdated' in callbacks:
                    callbacks['onMessageUpdated'](data)
        except Exception as e:
            if 'onError' in callbacks:
                callbacks['onError'](str(e))
        finally:
            self.sse_running[conversation_id] = False

    def connect_to_sse(self, conversation_id, callbacks=None):
        if callbacks is None:
            callbacks = {}

        if conversation_id in self.sse_threads and self.sse_running.get(conversation_id, False):
            return

        thread = threading.Thread(
            target=self._sse_listener,
            args=(conversation_id, callbacks),
            daemon=True
        )

        self.sse_threads[conversation_id] = thread
        thread.start()

    def disconnect_sse(self, conversation_id):
        self.sse_running[conversation_id] = False
        if conversation_id in self.sse_threads:
            # Thread will exit on next event or timeout
            if self.sse_threads[conversation_id].is_alive():
                self.sse_threads[conversation_id].join(timeout=1.0)
            del self.sse_threads[conversation_id]

    def disconnect_all_sse(self):
        for conversation_id in list(self.sse_threads.keys()):
            self.disconnect_sse(conversation_id)

# Usage example
def example():
    client = CortexClient('http://localhost:8000', 'your-token-here')

    # Create a new conversation
    result = client.create_conversation('My Python Chat')
    conversation = result['conversation']
    print(f"Created conversation: {conversation['id']}")

    # Define callbacks for SSE events
    def on_message_created(message):
        print(f"New message: {message['role']}: {message['content']}")

    def on_message_updated(message):
        print(f"Updated message: {message['role']}: {message['content']}")

    def on_error(error):
        print(f"SSE error: {error}")

    # Connect to SSE
    client.connect_to_sse(conversation['id'], {
        'onMessageCreated': on_message_created,
        'onMessageUpdated': on_message_updated,
        'onError': on_error
    })

    # Send a message
    client.send_message(conversation['id'], 'Hello from Python!')

    # Wait for responses (in a real application you'd handle this differently)
    import time
    time.sleep(10)

    # Disconnect
    client.disconnect_all_sse()

if __name__ == "__main__":
    example()
```

These examples provide a foundation for building clients that interact with the Cortex Core API. Adapt and extend them based on your specific requirements and the programming language you're using.
