# Configuration API Specification

## Overview

This document provides a comprehensive specification for the Configuration API endpoints added in Phase 2 of the Cortex Core platform. These endpoints enable management of workspaces and conversations, allowing clients to organize messages into appropriate contexts with persistence across application restarts.

The Configuration API follows RESTful principles and provides consistent patterns for authentication, error handling, and pagination. All endpoints require authentication and enforce user-based access control to ensure data partitioning.

## Table of Contents

1. [Authentication](#authentication)
2. [Common Patterns](#common-patterns)
3. [API Versioning](#api-versioning)
4. [Workspace Endpoints](#workspace-endpoints)
   - [Create Workspace](#create-workspace)
   - [List Workspaces](#list-workspaces)
   - [Get Workspace](#get-workspace)
   - [Update Workspace](#update-workspace)
   - [Delete Workspace](#delete-workspace)
5. [Conversation Endpoints](#conversation-endpoints)
   - [Create Conversation](#create-conversation)
   - [List Conversations](#list-conversations)
   - [Get Conversation](#get-conversation)
   - [Update Conversation](#update-conversation)
   - [Delete Conversation](#delete-conversation)
6. [Error Handling](#error-handling)
7. [Pagination](#pagination)
8. [Usage Examples](#usage-examples)

## Authentication

All Configuration API endpoints require authentication via JWT bearer token in the Authorization header.

**Header Syntax:**

```
Authorization: Bearer {token}
```

**Token Acquisition:**

Tokens are obtained from the `/auth/login` endpoint from Phase 1. See the Authentication section in the API documentation for details.

**Access Control:**

- Users can only access their own workspaces and conversations
- Workspace owners have full control over their workspaces and all conversations within them
- Conversation participants can view and update conversations, but not delete them
- Only workspace owners can delete conversations

## Common Patterns

### Resource Identifiers

All resources (workspaces, conversations) are identified by UUID strings in the format:

```
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### Resource Representation

Resources use JSON for request/response bodies with consistent field naming:

- Resource IDs are represented as `id`
- Timestamps use ISO 8601 format (`YYYY-MM-DDTHH:MM:SSZ`)
- All resources include a `metadata` field for extensibility

### Success Responses

Successful operations return:

- Appropriate HTTP status code (`200`, `201`, etc.)
- JSON response body with resource data
- Consistent field names across endpoints

### Error Responses

Error responses follow a consistent format:

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

## API Versioning

The Configuration API endpoints are part of the base API and do not include a version in the URL path. All endpoints are prefixed with `/config/`.

Future breaking changes will be communicated and may introduce versioned endpoints.

## Workspace Endpoints

Workspaces are top-level containers that group related conversations and provide organizational structure.

### Create Workspace

Creates a new workspace.

**URL**: `/config/workspace`

**Method**: `POST`

**Auth Required**: Yes (JWT Bearer Token)

**Content-Type**: `application/json`

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

**Request Fields**:

| Field         | Type   | Required | Description                       | Constraints                |
| ------------- | ------ | -------- | --------------------------------- | -------------------------- |
| `name`        | String | Yes      | Name of the workspace             | 1-100 characters           |
| `description` | String | Yes      | Description of the workspace      | 1-500 characters           |
| `metadata`    | Object | No       | Additional data (key-value pairs) | Optional, defaults to `{}` |

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

- **Code**: 409 Conflict
- **Content**:

```json
{
  "error": {
    "code": "conflict",
    "message": "Workspace with this name already exists"
  }
}
```

**Notes**:

- The `owner_id` is automatically set to the ID of the authenticated user
- `metadata` is optional and can contain arbitrary JSON data for client use
- The `id` is automatically generated as a UUID
- A workspace can have multiple conversations but belongs to a single owner

### List Workspaces

Retrieves all workspaces owned by the authenticated user.

**URL**: `/config/workspace`

**Method**: `GET`

**Auth Required**: Yes (JWT Bearer Token)

**Query Parameters**:

| Parameter | Type    | Required | Description                            | Default | Constraints   |
| --------- | ------- | -------- | -------------------------------------- | ------- | ------------- |
| `limit`   | Integer | No       | Maximum number of workspaces to return | 100     | Range: 1-1000 |
| `offset`  | Integer | No       | Offset for pagination                  | 0       | Minimum: 0    |

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
      "name": "Project Y",
      "description": "Workspace for Project Y research",
      "owner_id": "550e8400-e29b-41d4-a716-446655440000",
      "metadata": {
        "icon": "research",
        "color": "#f54242"
      }
    }
  ],
  "total": 2
}
```

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

**Notes**:

- Only workspaces owned by the authenticated user are returned
- Results are paginated, controlled by `limit` and `offset` parameters
- The `total` field indicates the total number of workspaces owned by the user

### Get Workspace

Retrieves a specific workspace by ID.

**URL**: `/config/workspace/{id}`

**Method**: `GET`

**Auth Required**: Yes (JWT Bearer Token)

**URL Parameters**:

| Parameter | Type   | Required | Description  |
| --------- | ------ | -------- | ------------ |
| `id`      | String | Yes      | Workspace ID |

**Success Response**:

- **Code**: 200 OK
- **Content**:

```json
{
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

- **Code**: 403 Forbidden
- **Content**:

```json
{
  "error": {
    "code": "forbidden",
    "message": "Access denied to workspace"
  }
}
```

- **Code**: 404 Not Found
- **Content**:

```json
{
  "error": {
    "code": "not_found",
    "message": "Workspace not found"
  }
}
```

**Notes**:

- Only the workspace owner can access the workspace
- The `id` in the URL must be a valid UUID

### Update Workspace

Updates an existing workspace.

**URL**: `/config/workspace/{id}`

**Method**: `PUT`

**Auth Required**: Yes (JWT Bearer Token)

**URL Parameters**:

| Parameter | Type   | Required | Description  |
| --------- | ------ | -------- | ------------ |
| `id`      | String | Yes      | Workspace ID |

**Content-Type**: `application/json`

**Request Body**:

```json
{
  "name": "Project X (Updated)",
  "description": "Updated workspace for Project X development",
  "metadata": {
    "icon": "project-updated",
    "color": "#42f587"
  }
}
```

**Request Fields**:

| Field         | Type   | Required | Description                       | Constraints                  |
| ------------- | ------ | -------- | --------------------------------- | ---------------------------- |
| `name`        | String | No       | Name of the workspace             | 1-100 characters if provided |
| `description` | String | No       | Description of the workspace      | 1-500 characters if provided |
| `metadata`    | Object | No       | Additional data (key-value pairs) | Optional                     |

**Success Response**:

- **Code**: 200 OK
- **Content**:

```json
{
  "status": "workspace updated",
  "workspace": {
    "id": "650e8400-e29b-41d4-a716-446655440111",
    "name": "Project X (Updated)",
    "description": "Updated workspace for Project X development",
    "owner_id": "550e8400-e29b-41d4-a716-446655440000",
    "metadata": {
      "icon": "project-updated",
      "color": "#42f587"
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
      "name": "Length must be 1-100 characters"
    }
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

- **Code**: 403 Forbidden
- **Content**:

```json
{
  "error": {
    "code": "forbidden",
    "message": "Access denied to workspace"
  }
}
```

- **Code**: 404 Not Found
- **Content**:

```json
{
  "error": {
    "code": "not_found",
    "message": "Workspace not found"
  }
}
```

**Notes**:

- Only the workspace owner can update the workspace
- Fields that are not provided remain unchanged
- For `metadata`, the provided values are merged with existing metadata rather than replacing it entirely

### Delete Workspace

Deletes a workspace and all its contents (conversations and messages).

**URL**: `/config/workspace/{id}`

**Method**: `DELETE`

**Auth Required**: Yes (JWT Bearer Token)

**URL Parameters**:

| Parameter | Type   | Required | Description  |
| --------- | ------ | -------- | ------------ |
| `id`      | String | Yes      | Workspace ID |

**Success Response**:

- **Code**: 200 OK
- **Content**:

```json
{
  "status": "workspace deleted",
  "success": true
}
```

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

- **Code**: 403 Forbidden
- **Content**:

```json
{
  "error": {
    "code": "forbidden",
    "message": "Access denied to workspace"
  }
}
```

- **Code**: 404 Not Found
- **Content**:

```json
{
  "error": {
    "code": "not_found",
    "message": "Workspace not found"
  }
}
```

**Notes**:

- Only the workspace owner can delete the workspace
- Deleting a workspace also deletes all conversations and messages within it
- This operation cannot be undone
- The deletion happens in a single transaction to ensure consistency

## Conversation Endpoints

Conversations are groupings of messages within a workspace.

### Create Conversation

Creates a new conversation within a workspace.

**URL**: `/config/conversation`

**Method**: `POST`

**Auth Required**: Yes (JWT Bearer Token)

**Content-Type**: `application/json`

**Request Body**:

```json
{
  "workspace_id": "650e8400-e29b-41d4-a716-446655440111",
  "topic": "Backend Development",
  "participant_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440111"
  ],
  "metadata": {
    "icon": "code",
    "priority": "high"
  }
}
```

**Request Fields**:

| Field             | Type     | Required | Description                       | Constraints                       |
| ----------------- | -------- | -------- | --------------------------------- | --------------------------------- |
| `workspace_id`    | String   | Yes      | ID of the parent workspace        | Valid workspace ID                |
| `topic`           | String   | Yes      | Topic of the conversation         | 1-200 characters                  |
| `participant_ids` | String[] | No       | List of participant user IDs      | Optional, array of valid user IDs |
| `metadata`        | Object   | No       | Additional data (key-value pairs) | Optional, defaults to `{}`        |

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
    "participant_ids": [
      "550e8400-e29b-41d4-a716-446655440000",
      "660e8400-e29b-41d4-a716-446655440111"
    ],
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

- **Code**: 403 Forbidden
- **Content**:

```json
{
  "error": {
    "code": "forbidden",
    "message": "Access denied to workspace"
  }
}
```

- **Code**: 404 Not Found
- **Content**:

```json
{
  "error": {
    "code": "not_found",
    "message": "Workspace not found"
  }
}
```

**Notes**:

- The authenticated user must be the owner of the specified workspace
- The authenticated user is automatically added to the `participant_ids` list if not included
- The `id` is automatically generated as a UUID
- `metadata` is optional and can contain arbitrary JSON data for client use

### List Conversations

Retrieves all conversations within a workspace.

**URL**: `/config/conversation`

**Method**: `GET`

**Auth Required**: Yes (JWT Bearer Token)

**Query Parameters**:

| Parameter      | Type    | Required | Description                               | Default | Constraints   |
| -------------- | ------- | -------- | ----------------------------------------- | ------- | ------------- |
| `workspace_id` | String  | Yes      | ID of the workspace                       | N/A     | Valid UUID    |
| `limit`        | Integer | No       | Maximum number of conversations to return | 100     | Range: 1-1000 |
| `offset`       | Integer | No       | Offset for pagination                     | 0       | Minimum: 0    |

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
      "participant_ids": [
        "550e8400-e29b-41d4-a716-446655440000",
        "660e8400-e29b-41d4-a716-446655440111"
      ],
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

- **Code**: 403 Forbidden
- **Content**:

```json
{
  "error": {
    "code": "forbidden",
    "message": "Access denied to workspace"
  }
}
```

- **Code**: 404 Not Found
- **Content**:

```json
{
  "error": {
    "code": "not_found",
    "message": "Workspace not found"
  }
}
```

**Notes**:

- The authenticated user must be the owner of the specified workspace
- Results are paginated, controlled by `limit` and `offset` parameters
- The `total` field indicates the total number of conversations in the workspace
- The `workspace_id` query parameter is required

### Get Conversation

Retrieves a specific conversation by ID.

**URL**: `/config/conversation/{id}`

**Method**: `GET`

**Auth Required**: Yes (JWT Bearer Token)

**URL Parameters**:

| Parameter | Type   | Required | Description     |
| --------- | ------ | -------- | --------------- |
| `id`      | String | Yes      | Conversation ID |

**Success Response**:

- **Code**: 200 OK
- **Content**:

```json
{
  "conversation": {
    "id": "850e8400-e29b-41d4-a716-446655440333",
    "workspace_id": "650e8400-e29b-41d4-a716-446655440111",
    "topic": "Backend Development",
    "participant_ids": [
      "550e8400-e29b-41d4-a716-446655440000",
      "660e8400-e29b-41d4-a716-446655440111"
    ],
    "metadata": {
      "icon": "code",
      "priority": "high"
    }
  }
}
```

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

- **Code**: 403 Forbidden
- **Content**:

```json
{
  "error": {
    "code": "forbidden",
    "message": "Access denied to conversation"
  }
}
```

- **Code**: 404 Not Found
- **Content**:

```json
{
  "error": {
    "code": "not_found",
    "message": "Conversation not found"
  }
}
```

**Notes**:

- Access is granted if the authenticated user is either:
  - The owner of the workspace that contains the conversation
  - A participant in the conversation
- The `id` in the URL must be a valid UUID

### Update Conversation

Updates an existing conversation.

**URL**: `/config/conversation/{id}`

**Method**: `PUT`

**Auth Required**: Yes (JWT Bearer Token)

**URL Parameters**:

| Parameter | Type   | Required | Description     |
| --------- | ------ | -------- | --------------- |
| `id`      | String | Yes      | Conversation ID |

**Content-Type**: `application/json`

**Request Body**:

```json
{
  "topic": "Backend Development (Updated)",
  "participant_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440111",
    "770e8400-e29b-41d4-a716-446655440222"
  ],
  "metadata": {
    "icon": "code-updated",
    "priority": "critical"
  }
}
```

**Request Fields**:

| Field             | Type     | Required | Description                       | Constraints                         |
| ----------------- | -------- | -------- | --------------------------------- | ----------------------------------- |
| `topic`           | String   | No       | Topic of the conversation         | 1-200 characters if provided        |
| `participant_ids` | String[] | No       | List of participant user IDs      | Array of valid user IDs if provided |
| `metadata`        | Object   | No       | Additional data (key-value pairs) | Optional                            |

**Success Response**:

- **Code**: 200 OK
- **Content**:

```json
{
  "status": "conversation updated",
  "conversation": {
    "id": "850e8400-e29b-41d4-a716-446655440333",
    "workspace_id": "650e8400-e29b-41d4-a716-446655440111",
    "topic": "Backend Development (Updated)",
    "participant_ids": [
      "550e8400-e29b-41d4-a716-446655440000",
      "660e8400-e29b-41d4-a716-446655440111",
      "770e8400-e29b-41d4-a716-446655440222"
    ],
    "metadata": {
      "icon": "code-updated",
      "priority": "critical"
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
      "topic": "Length must be 1-200 characters"
    }
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

- **Code**: 403 Forbidden
- **Content**:

```json
{
  "error": {
    "code": "forbidden",
    "message": "Access denied to conversation"
  }
}
```

- **Code**: 404 Not Found
- **Content**:

```json
{
  "error": {
    "code": "not_found",
    "message": "Conversation not found"
  }
}
```

**Notes**:

- Access is granted if the authenticated user is either:
  - The owner of the workspace that contains the conversation
  - A participant in the conversation
- The authenticated user is automatically added to the `participant_ids` list if not included
- Fields that are not provided remain unchanged
- For `metadata`, the provided values are merged with existing metadata rather than replacing it entirely
- The `workspace_id` cannot be changed

### Delete Conversation

Deletes a conversation and all its messages.

**URL**: `/config/conversation/{id}`

**Method**: `DELETE`

**Auth Required**: Yes (JWT Bearer Token)

**URL Parameters**:

| Parameter | Type   | Required | Description     |
| --------- | ------ | -------- | --------------- |
| `id`      | String | Yes      | Conversation ID |

**Success Response**:

- **Code**: 200 OK
- **Content**:

```json
{
  "status": "conversation deleted",
  "success": true
}
```

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

- **Code**: 403 Forbidden
- **Content**:

```json
{
  "error": {
    "code": "forbidden",
    "message": "Access denied: only workspace owner can delete conversations"
  }
}
```

- **Code**: 404 Not Found
- **Content**:

```json
{
  "error": {
    "code": "not_found",
    "message": "Conversation not found"
  }
}
```

**Notes**:

- Only the workspace owner can delete conversations
- Deleting a conversation also deletes all messages within it
- This operation cannot be undone
- The deletion happens in a single transaction to ensure consistency

## Error Handling

The Configuration API uses a consistent error response format across all endpoints. Error responses include:

1. An appropriate HTTP status code
2. A JSON response body with error details

### Common Error Response Format

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

| Status Code | Error Code            | Description                        |
| ----------- | --------------------- | ---------------------------------- |
| 400         | `validation_error`    | Request data validation failed     |
| 400         | `missing_parameter`   | Required parameter is missing      |
| 401         | `unauthorized`        | Authentication required or invalid |
| 403         | `forbidden`           | Permission denied                  |
| 404         | `not_found`           | Resource not found                 |
| 409         | `conflict`            | Resource already exists            |
| 500         | `internal_error`      | Server error                       |
| 503         | `service_unavailable` | Database or service unavailable    |

### Validation Errors

Validation errors include a `details` object that contains field-specific errors:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid request data",
    "details": {
      "name": "Field is required",
      "description": "Length must be 1-500 characters"
    }
  }
}
```

## Pagination

List endpoints support pagination through `limit` and `offset` query parameters.

### Pagination Parameters

| Parameter | Type    | Description                           | Default | Constraints   |
| --------- | ------- | ------------------------------------- | ------- | ------------- |
| `limit`   | Integer | Maximum number of items to return     | 100     | Range: 1-1000 |
| `offset`  | Integer | Offset for pagination (items to skip) | 0       | Minimum: 0    |

### Pagination Response

Paginated responses include a `total` field that indicates the total number of items available:

```json
{
  "workspaces": [...],
  "total": 42
}
```

### Calculating Total Pages

To calculate the total number of pages:

```
total_pages = Math.ceil(total / limit)
```

### Calculating Current Page

To calculate the current page number (0-based):

```
current_page = Math.floor(offset / limit)
```

## Usage Examples

### Creating and Managing Workspaces (cURL)

#### Create a Workspace

```bash
curl -X POST "http://localhost:8000/config/workspace" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Project X",
    "description": "Workspace for Project X development",
    "metadata": {
      "icon": "project",
      "color": "#4287f5"
    }
  }'
```

#### List Workspaces

```bash
curl -X GET "http://localhost:8000/config/workspace?limit=10&offset=0" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Get a Workspace

```bash
curl -X GET "http://localhost:8000/config/workspace/650e8400-e29b-41d4-a716-446655440111" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Update a Workspace

```bash
curl -X PUT "http://localhost:8000/config/workspace/650e8400-e29b-41d4-a716-446655440111" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Project X (Updated)",
    "description": "Updated workspace for Project X development",
    "metadata": {
      "icon": "project-updated",
      "color": "#42f587"
    }
  }'
```

#### Delete a Workspace

```bash
curl -X DELETE "http://localhost:8000/config/workspace/650e8400-e29b-41d4-a716-446655440111" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Creating and Managing Conversations (cURL)

#### Create a Conversation

```bash
curl -X POST "http://localhost:8000/config/conversation" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "650e8400-e29b-41d4-a716-446655440111",
    "topic": "Backend Development",
    "participant_ids": ["550e8400-e29b-41d4-a716-446655440000", "660e8400-e29b-41d4-a716-446655440111"],
    "metadata": {
      "icon": "code",
      "priority": "high"
    }
  }'
```

#### List Conversations

```bash
curl -X GET "http://localhost:8000/config/conversation?workspace_id=650e8400-e29b-41d4-a716-446655440111&limit=10&offset=0" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Get a Conversation

```bash
curl -X GET "http://localhost:8000/config/conversation/850e8400-e29b-41d4-a716-446655440333" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Update a Conversation

```bash
curl -X PUT "http://localhost:8000/config/conversation/850e8400-e29b-41d4-a716-446655440333" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Backend Development (Updated)",
    "participant_ids": ["550e8400-e29b-41d4-a716-446655440000", "660e8400-e29b-41d4-a716-446655440111", "770e8400-e29b-41d4-a716-446655440222"],
    "metadata": {
      "icon": "code-updated",
      "priority": "critical"
    }
  }'
```

#### Delete a Conversation

```bash
curl -X DELETE "http://localhost:8000/config/conversation/850e8400-e29b-41d4-a716-446655440333" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Python Client Examples

#### Workspace Management

```python
import requests
import json

# Base URL and authentication
base_url = "http://localhost:8000"
headers = {
    "Authorization": f"Bearer {your_jwt_token}",
    "Content-Type": "application/json"
}

# Create a workspace
def create_workspace(name, description, metadata=None):
    url = f"{base_url}/config/workspace"
    payload = {
        "name": name,
        "description": description,
        "metadata": metadata or {}
    }
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        return response.json()["workspace"]
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# List workspaces
def list_workspaces(limit=100, offset=0):
    url = f"{base_url}/config/workspace?limit={limit}&offset={offset}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# Get a workspace
def get_workspace(workspace_id):
    url = f"{base_url}/config/workspace/{workspace_id}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()["workspace"]
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# Update a workspace
def update_workspace(workspace_id, name=None, description=None, metadata=None):
    url = f"{base_url}/config/workspace/{workspace_id}"
    payload = {}

    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if metadata is not None:
        payload["metadata"] = metadata

    response = requests.put(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["workspace"]
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# Delete a workspace
def delete_workspace(workspace_id):
    url = f"{base_url}/config/workspace/{workspace_id}"
    response = requests.delete(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# Example usage
if __name__ == "__main__":
    # Create a workspace
    workspace = create_workspace(
        name="Project X",
        description="Workspace for Project X development",
        metadata={"icon": "project", "color": "#4287f5"}
    )

    if workspace:
        workspace_id = workspace["id"]
        print(f"Created workspace: {workspace_id}")

        # List workspaces
        workspaces = list_workspaces()
        print(f"Total workspaces: {workspaces['total']}")

        # Update the workspace
        updated_workspace = update_workspace(
            workspace_id,
            name="Project X (Updated)",
            metadata={"icon": "project-updated", "color": "#42f587"}
        )
        print(f"Updated workspace: {updated_workspace['name']}")

        # Delete the workspace
        delete_result = delete_workspace(workspace_id)
        print(f"Workspace deleted: {delete_result['success']}")
```

#### Conversation Management

```python
import requests
import json

# Base URL and authentication
base_url = "http://localhost:8000"
headers = {
    "Authorization": f"Bearer {your_jwt_token}",
    "Content-Type": "application/json"
}

# Create a conversation
def create_conversation(workspace_id, topic, participant_ids=None, metadata=None):
    url = f"{base_url}/config/conversation"
    payload = {
        "workspace_id": workspace_id,
        "topic": topic,
        "participant_ids": participant_ids or [],
        "metadata": metadata or {}
    }
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        return response.json()["conversation"]
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# List conversations
def list_conversations(workspace_id, limit=100, offset=0):
    url = f"{base_url}/config/conversation?workspace_id={workspace_id}&limit={limit}&offset={offset}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# Get a conversation
def get_conversation(conversation_id):
    url = f"{base_url}/config/conversation/{conversation_id}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()["conversation"]
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# Update a conversation
def update_conversation(conversation_id, topic=None, participant_ids=None, metadata=None):
    url = f"{base_url}/config/conversation/{conversation_id}"
    payload = {}

    if topic is not None:
        payload["topic"] = topic
    if participant_ids is not None:
        payload["participant_ids"] = participant_ids
    if metadata is not None:
        payload["metadata"] = metadata

    response = requests.put(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["conversation"]
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# Delete a conversation
def delete_conversation(conversation_id):
    url = f"{base_url}/config/conversation/{conversation_id}"
    response = requests.delete(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# Example usage
if __name__ == "__main__":
    # Assume we already have a workspace
    workspace_id = "650e8400-e29b-41d4-a716-446655440111"

    # Create a conversation
    conversation = create_conversation(
        workspace_id=workspace_id,
        topic="Backend Development",
        participant_ids=["550e8400-e29b-41d4-a716-446655440000"],
        metadata={"icon": "code", "priority": "high"}
    )

    if conversation:
        conversation_id = conversation["id"]
        print(f"Created conversation: {conversation_id}")

        # List conversations
        conversations = list_conversations(workspace_id)
        print(f"Total conversations: {conversations['total']}")

        # Update the conversation
        updated_conversation = update_conversation(
            conversation_id,
            topic="Backend Development (Updated)",
            metadata={"icon": "code-updated", "priority": "critical"}
        )
        print(f"Updated conversation: {updated_conversation['topic']}")

        # Delete the conversation
        delete_result = delete_conversation(conversation_id)
        print(f"Conversation deleted: {delete_result['success']}")
```

These examples demonstrate basic usage of the Configuration API endpoints. Clients should implement proper error handling, authentication token management, and retry logic for production use.
