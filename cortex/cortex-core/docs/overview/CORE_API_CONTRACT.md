# Cortex Core API Contract

This document defines the API contract for the Cortex Core service. It covers all endpoints, request/response formats, authentication, and error handling standards. This contract serves as the definitive reference for client integration.

## API Overview

The Cortex Core API is organized into four main sections:

1. **Authentication**: Endpoints for login, token verification, and user management
2. **Input**: Endpoint for receiving input from dumb clients
3. **Output**: Endpoint for streaming output via Server-Sent Events (SSE)
4. **Configuration**: Endpoints for managing workspaces and conversations

All endpoints use JSON for request/response payloads unless otherwise specified. All endpoints except `/auth/login` require authentication via JWT bearer token in the Authorization header.

## Base URL

- Development: `http://localhost:8000`
- Production: `https://cortex-core.example.com`

## Authentication

### Login

Authenticates a user and returns a JWT token.

- **URL**: `/auth/login`
- **Method**: `POST`
- **Auth Required**: No
- **Content-Type**: `application/json`

**Request Body**:

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Success Response**:

- **Code**: 200 OK
- **Content**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "claims": {
    "oid": "550e8400-e29b-41d4-a716-446655440000",
    "name": "John Doe",
    "email": "user@example.com"
  }
}
```

**Error Responses**:

- **Code**: 401 Unauthorized
- **Content**:

```json
{
  "error": {
    "code": "invalid_credentials",
    "message": "Invalid email or password"
  }
}
```

### Token Verification

Verifies a JWT token and returns user information.

- **URL**: `/auth/verify`
- **Method**: `GET`
- **Auth Required**: Yes (JWT Bearer Token)
- **Headers**:
  - `Authorization: Bearer {token}`

**Success Response**:

- **Code**: 200 OK
- **Content**:

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "John Doe",
  "email": "user@example.com"
}
```

**Error Responses**:

- **Code**: 401 Unauthorized
- **Content**:

```json
{
  "error": {
    "code": "invalid_token",
    "message": "Invalid or expired token"
  }
}
```

## Input Endpoint

### Submit Input

Submits input data to the Cortex Core.

- **URL**: `/input`
- **Method**: `POST`
- **Auth Required**: Yes (JWT Bearer Token)
- **Headers**:
  - `Authorization: Bearer {token}`
  - `Content-Type: application/json`

**Request Body**:

The request body can contain any JSON object. The structure is flexible to accommodate different input types. Here's an example for text input:

```json
{
  "message": "Hello, Cortex!",
  "timestamp": "2025-03-20T10:15:30Z",
  "metadata": {
    "client_id": "web-chat-client",
    "client_version": "1.0.0"
  }
}
```

**Success Response**:

- **Code**: 200 OK
- **Content**:

```json
{
  "status": "received",
  "data": {
    "message": "Hello, Cortex!",
    "timestamp": "2025-03-20T10:15:30Z",
    "metadata": {
      "client_id": "web-chat-client",
      "client_version": "1.0.0"
    }
  }
}
```

**Error Responses**:

- **Code**: 400 Bad Request
- **Content**:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Invalid JSON payload"
  }
}
```

- **Code**: 401 Unauthorized
- **Content**:

```json
{
  "error": {
    "code": "unauthorized",
    "message": "Authentication required"
  }
}
```

## Output Streaming Endpoint

### Output Stream

Establishes a Server-Sent Events (SSE) connection to receive output events.

- **URL**: `/output/stream`
- **Method**: `GET`
- **Auth Required**: Yes (JWT Bearer Token)
- **Headers**:
  - `Authorization: Bearer {token}`
  - `Accept: text/event-stream`

**Success Response**:

- **Code**: 200 OK
- **Content-Type**: `text/event-stream`
- **Content Format**:

```
data: {"type": "output", "content": "Hello, user!", "user_id": "550e8400-e29b-41d4-a716-446655440000", "timestamp": "2025-03-20T10:16:00Z"}

data: {"type": "output", "content": "How can I help you today?", "user_id": "550e8400-e29b-41d4-a716-446655440000", "timestamp": "2025-03-20T10:16:02Z"}
```

**Event Types**:

1. **Output Event**:

   ```json
   {
     "type": "output",
     "content": "Text content to display",
     "user_id": "550e8400-e29b-41d4-a716-446655440000",
     "timestamp": "2025-03-20T10:16:00Z",
     "metadata": {}
   }
   ```

2. **Typing Indicator**:

   ```json
   {
     "type": "typing",
     "is_typing": true,
     "user_id": "550e8400-e29b-41d4-a716-446655440000",
     "timestamp": "2025-03-20T10:16:00Z"
   }
   ```

3. **Error Event**:

   ```json
   {
     "type": "error",
     "message": "Error processing request",
     "user_id": "550e8400-e29b-41d4-a716-446655440000",
     "timestamp": "2025-03-20T10:16:00Z"
   }
   ```

4. **Heartbeat**:
   ```json
   {
     "type": "heartbeat",
     "timestamp": "2025-03-20T10:16:30Z"
   }
   ```

**Connection Handling**:

1. Clients should handle reconnection if the connection is lost
2. The server sends a heartbeat event every 30 seconds
3. If no heartbeat is received for 90 seconds, clients should attempt to reconnect
4. Events are filtered server-side to include only those for the authenticated user

**Error Responses**:

- **Code**: 401 Unauthorized
- **Content**:

```json
{
  "error": {
    "code": "unauthorized",
    "message": "Authentication required"
  }
}
```

## Configuration Endpoints

### Create Workspace

Creates a new workspace.

- **URL**: `/config/workspace`
- **Method**: `POST`
- **Auth Required**: Yes (JWT Bearer Token)
- **Headers**:
  - `Authorization: Bearer {token}`
  - `Content-Type: application/json`

**Request Body**:

```json
{
  "name": "Project X",
  "description": "Workspace for Project X development",
  "metadata": {
    "icon": "project",
    "color": "#4287f5"
  }
}
```

**Success Response**:

- **Code**: 201 Created
- **Content**:

```json
{
  "status": "workspace created",
  "workspace": {
    "id": "650e8400-e29b-41d4-a716-446655440111",
    "name": "Project X",
    "description": "Workspace for Project X development",
    "owner_id": "550e8400-e29b-41d4-a716-446655440000",
    "metadata": {
      "icon": "project",
      "color": "#4287f5"
    }
  }
}
```

**Error Responses**:

- **Code**: 400 Bad Request
- **Content**:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid workspace data",
    "details": {
      "name": "Field is required"
    }
  }
}
```

### List Workspaces

Retrieves all workspaces owned by the authenticated user.

- **URL**: `/config/workspace`
- **Method**: `GET`
- **Auth Required**: Yes (JWT Bearer Token)
- **Headers**:
  - `Authorization: Bearer {token}`

**Query Parameters**:

- `limit` (optional): Maximum number of workspaces to return
- `offset` (optional): Offset for pagination

**Success Response**:

- **Code**: 200 OK
- **Content**:

```json
{
  "workspaces": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440111",
      "name": "Project X",
      "description": "Workspace for Project X development",
      "owner_id": "550e8400-e29b-41d4-a716-446655440000",
      "metadata": {
        "icon": "project",
        "color": "#4287f5"
      }
    },
    {
      "id": "750e8400-e29b-41d4-a716-446655440222",
      "name": "Research",
      "description": "Research workspace",
      "owner_id": "550e8400-e29b-41d4-a716-446655440000",
      "metadata": {
        "icon": "books",
        "color": "#42f56f"
      }
    }
  ],
  "total": 2
}
```

### Create Conversation

Creates a new conversation within a workspace.

- **URL**: `/config/conversation`
- **Method**: `POST`
- **Auth Required**: Yes (JWT Bearer Token)
- **Headers**:
  - `Authorization: Bearer {token}`
  - `Content-Type: application/json`

**Request Body**:

```json
{
  "workspace_id": "650e8400-e29b-41d4-a716-446655440111",
  "topic": "Backend Development",
  "participant_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "metadata": {
    "icon": "code",
    "priority": "high"
  }
}
```

**Success Response**:

- **Code**: 201 Created
- **Content**:

```json
{
  "status": "conversation created",
  "conversation": {
    "id": "850e8400-e29b-41d4-a716-446655440333",
    "workspace_id": "650e8400-e29b-41d4-a716-446655440111",
    "topic": "Backend Development",
    "participant_ids": ["550e8400-e29b-41d4-a716-446655440000"],
    "metadata": {
      "icon": "code",
      "priority": "high"
    }
  }
}
```

**Error Responses**:

- **Code**: 400 Bad Request
- **Content**:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid conversation data",
    "details": {
      "workspace_id": "Field is required"
    }
  }
}
```

- **Code**: 404 Not Found
- **Content**:

```json
{
  "error": {
    "code": "workspace_not_found",
    "message": "Workspace not found"
  }
}
```

### List Conversations

Retrieves all conversations within a workspace.

- **URL**: `/config/conversation`
- **Method**: `GET`
- **Auth Required**: Yes (JWT Bearer Token)
- **Headers**:
  - `Authorization: Bearer {token}`

**Query Parameters**:

- `workspace_id` (required): ID of the workspace
- `limit` (optional): Maximum number of conversations to return
- `offset` (optional): Offset for pagination

**Success Response**:

- **Code**: 200 OK
- **Content**:

```json
{
  "conversations": [
    {
      "id": "850e8400-e29b-41d4-a716-446655440333",
      "workspace_id": "650e8400-e29b-41d4-a716-446655440111",
      "topic": "Backend Development",
      "participant_ids": ["550e8400-e29b-41d4-a716-446655440000"],
      "metadata": {
        "icon": "code",
        "priority": "high"
      }
    },
    {
      "id": "950e8400-e29b-41d4-a716-446655440444",
      "workspace_id": "650e8400-e29b-41d4-a716-446655440111",
      "topic": "Frontend Development",
      "participant_ids": ["550e8400-e29b-41d4-a716-446655440000"],
      "metadata": {
        "icon": "web",
        "priority": "medium"
      }
    }
  ],
  "total": 2
}
```

**Error Responses**:

- **Code**: 400 Bad Request
- **Content**:

```json
{
  "error": {
    "code": "missing_parameter",
    "message": "workspace_id is required"
  }
}
```

- **Code**: 404 Not Found
- **Content**:

```json
{
  "error": {
    "code": "workspace_not_found",
    "message": "Workspace not found"
  }
}
```

## Data Models

### Base Properties

All models include these base properties:

- `metadata`: Object - Optional additional data (object with string keys and any value)

### Workspace

- `id`: String - UUID of the workspace (generated by server)
- `name`: String - Name of the workspace (required, 1-100 characters)
- `description`: String - Description of the workspace (required, 1-500 characters)
- `owner_id`: String - UUID of the workspace owner (from authenticated user)

### Conversation

- `id`: String - UUID of the conversation (generated by server)
- `workspace_id`: String - UUID of the parent workspace (required)
- `topic`: String - Topic of the conversation (required, 1-200 characters)
- `participant_ids`: Array of String - UUIDs of conversation participants (at least one required)

### Message

- `id`: String - UUID of the message (generated by server)
- `conversation_id`: String - UUID of the parent conversation (required)
- `sender_id`: String - UUID of the message sender (required)
- `content`: String - Content of the message (required)
- `timestamp`: String - ISO 8601 timestamp of when the message was sent

## Error Format

All API errors follow a consistent format:

```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable error message",
    "details": {
      "field_name": "Specific error for this field"
    }
  }
}
```

### Common Error Codes

- `validation_error`: Request data validation failed
- `unauthorized`: Authentication required or invalid
- `forbidden`: Permission denied
- `not_found`: Resource not found
- `conflict`: Resource already exists
- `internal_error`: Server error

## Authentication Headers

All authenticated endpoints require the following header:

```
Authorization: Bearer {jwt_token}
```

The JWT token should be obtained from the `/auth/login` endpoint.

## Complete API Workflow Example

Here's a complete example of a typical workflow:

### 1. Authenticate User

**Request**:

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response**:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "claims": {
    "oid": "550e8400-e29b-41d4-a716-446655440000",
    "name": "John Doe",
    "email": "user@example.com"
  }
}
```

### 2. Create Workspace

**Request**:

```http
POST /config/workspace
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "name": "Project X",
  "description": "Workspace for Project X development",
  "metadata": {
    "icon": "project",
    "color": "#4287f5"
  }
}
```

**Response**:

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "status": "workspace created",
  "workspace": {
    "id": "650e8400-e29b-41d4-a716-446655440111",
    "name": "Project X",
    "description": "Workspace for Project X development",
    "owner_id": "550e8400-e29b-41d4-a716-446655440000",
    "metadata": {
      "icon": "project",
      "color": "#4287f5"
    }
  }
}
```

### 3. Create Conversation

**Request**:

```http
POST /config/conversation
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "workspace_id": "650e8400-e29b-41d4-a716-446655440111",
  "topic": "Backend Development",
  "participant_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "metadata": {
    "icon": "code",
    "priority": "high"
  }
}
```

**Response**:

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "status": "conversation created",
  "conversation": {
    "id": "850e8400-e29b-41d4-a716-446655440333",
    "workspace_id": "650e8400-e29b-41d4-a716-446655440111",
    "topic": "Backend Development",
    "participant_ids": ["550e8400-e29b-41d4-a716-446655440000"],
    "metadata": {
      "icon": "code",
      "priority": "high"
    }
  }
}
```

### 4. Connect to Output Stream

**Request**:

```http
GET /output/stream
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Accept: text/event-stream
```

**Response**:

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Transfer-Encoding: chunked

data: {"type": "heartbeat", "timestamp": "2025-03-20T10:16:30Z"}

```

### 5. Send Input

**Request**:

```http
POST /input
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "message": "Hello, Cortex!",
  "conversation_id": "850e8400-e29b-41d4-a716-446655440333",
  "timestamp": "2025-03-20T10:15:30Z",
  "metadata": {
    "client_id": "web-chat-client",
    "client_version": "1.0.0"
  }
}
```

**Response**:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "received",
  "data": {
    "message": "Hello, Cortex!",
    "conversation_id": "850e8400-e29b-41d4-a716-446655440333",
    "timestamp": "2025-03-20T10:15:30Z",
    "metadata": {
      "client_id": "web-chat-client",
      "client_version": "1.0.0"
    }
  }
}
```

### 6. Receive Output via SSE

The open SSE connection will receive events:

```
data: {"type": "typing", "is_typing": true, "user_id": "550e8400-e29b-41d4-a716-446655440000", "timestamp": "2025-03-20T10:15:31Z"}

data: {"type": "output", "content": "Hello! How can I help you with Project X today?", "user_id": "550e8400-e29b-41d4-a716-446655440000", "timestamp": "2025-03-20T10:15:32Z"}
```

## API Versioning

The API does not currently use explicit versioning in the URL path. Future breaking changes will be communicated and may introduce versioned endpoints.
