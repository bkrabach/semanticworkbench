# API Reference

_Version: 1.0_  
_Date: 2025-03-05_

## Overview

This document provides comprehensive reference information for the Cortex Platform APIs. These APIs enable developers to integrate with and extend the capabilities of the Cortex Platform.

## API Structure

The Cortex Platform exposes the following API categories:

1. **Core API** - Primary interface for interacting with the central AI system
2. **Domain Expert APIs** - Specialized interfaces for domain-specific capabilities
3. **Integration APIs** - Interfaces for third-party tool integration
4. **Management API** - Administrative functions for platform management

All APIs follow consistent REST patterns with JSON payloads, using OAuth 2.0 for authentication.

## Core API

### Authentication

```http
POST /v1/auth/token
```

Obtain an access token for API calls.

**Request Body:**

```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "grant_type": "client_credentials",
  "scope": "cortex.read cortex.write"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "cortex.read cortex.write"
}
```

### Conversation Management

```http
POST /v1/conversations
```

Create a new conversation.

**Request Headers:**

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "title": "Optional conversation title",
  "metadata": {
    "source": "api",
    "custom_key": "custom_value"
  }
}
```

**Response:**

```json
{
  "conversation_id": "conv_abc123",
  "title": "Optional conversation title",
  "created_at": "2025-03-05T12:00:00Z",
  "metadata": {
    "source": "api",
    "custom_key": "custom_value"
  }
}
```

```http
GET /v1/conversations
```

List conversations.

**Request Headers:**

```
Authorization: Bearer {access_token}
```

**Query Parameters:**

- `limit` (optional): Maximum number of results to return (default: 20, max: 100)
- `offset` (optional): Pagination offset (default: 0)
- `sort` (optional): Sort order (`created_at_asc`, `created_at_desc` (default))

**Response:**

```json
{
  "conversations": [
    {
      "conversation_id": "conv_abc123",
      "title": "Conversation title",
      "created_at": "2025-03-05T12:00:00Z",
      "last_message_at": "2025-03-05T12:10:00Z",
      "message_count": 10
    },
    {
      "conversation_id": "conv_def456",
      "title": "Another conversation",
      "created_at": "2025-03-04T15:30:00Z",
      "last_message_at": "2025-03-04T16:00:00Z",
      "message_count": 5
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 42
  }
}
```

```http
GET /v1/conversations/{conversation_id}
```

Get conversation details.

**Request Headers:**

```
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "conversation_id": "conv_abc123",
  "title": "Conversation title",
  "created_at": "2025-03-05T12:00:00Z",
  "last_message_at": "2025-03-05T12:10:00Z",
  "message_count": 10,
  "metadata": {
    "source": "api",
    "custom_key": "custom_value"
  }
}
```

### Message Management

```http
POST /v1/conversations/{conversation_id}/messages
```

Send a message.

**Request Headers:**

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "content": "What can you tell me about the Cortex Platform?",
  "role": "user",
  "modality": "text",
  "metadata": {
    "source": "api",
    "custom_key": "custom_value"
  }
}
```

**Response:**

```json
{
  "message_id": "msg_abc123",
  "conversation_id": "conv_abc123",
  "content": "What can you tell me about the Cortex Platform?",
  "role": "user",
  "modality": "text",
  "created_at": "2025-03-05T12:15:00Z",
  "metadata": {
    "source": "api",
    "custom_key": "custom_value"
  }
}
```

```http
GET /v1/conversations/{conversation_id}/messages
```

List messages in a conversation.

**Request Headers:**

```
Authorization: Bearer {access_token}
```

**Query Parameters:**

- `limit` (optional): Maximum number of results to return (default: 20, max: 100)
- `before` (optional): Return messages created before this message ID
- `after` (optional): Return messages created after this message ID

**Response:**

```json
{
  "messages": [
    {
      "message_id": "msg_abc123",
      "conversation_id": "conv_abc123",
      "content": "What can you tell me about the Cortex Platform?",
      "role": "user",
      "modality": "text",
      "created_at": "2025-03-05T12:15:00Z"
    },
    {
      "message_id": "msg_def456",
      "conversation_id": "conv_abc123",
      "content": "The Cortex Platform is an advanced AI assistant system that...",
      "role": "assistant",
      "modality": "text",
      "created_at": "2025-03-05T12:15:05Z"
    }
  ],
  "pagination": {
    "has_more": false
  }
}
```

### Memory Management

```http
POST /v1/memory/store
```

Store information in memory.

**Request Headers:**

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "entity_type": "document",
  "entity_id": "doc_abc123",
  "content": "This is an important document that contains information about...",
  "metadata": {
    "title": "Important Document",
    "tags": ["research", "ai", "cortex"],
    "source": "user_upload"
  }
}
```

**Response:**

```json
{
  "memory_id": "mem_abc123",
  "entity_type": "document",
  "entity_id": "doc_abc123",
  "created_at": "2025-03-05T13:00:00Z",
  "status": "stored"
}
```

```http
GET /v1/memory/retrieve
```

Retrieve information from memory.

**Request Headers:**

```
Authorization: Bearer {access_token}
```

**Query Parameters:**

- `query` (required): Search query
- `entity_type` (optional): Filter by entity type
- `limit` (optional): Maximum number of results to return (default: 10, max: 50)

**Response:**

```json
{
  "results": [
    {
      "memory_id": "mem_abc123",
      "entity_type": "document",
      "entity_id": "doc_abc123",
      "content": "This is an important document that contains information about...",
      "metadata": {
        "title": "Important Document",
        "tags": ["research", "ai", "cortex"],
        "source": "user_upload"
      },
      "relevance_score": 0.95,
      "created_at": "2025-03-05T13:00:00Z"
    },
    {
      "memory_id": "mem_def456",
      "entity_type": "conversation",
      "entity_id": "conv_def456",
      "content": "In this conversation, we discussed the importance of...",
      "metadata": {
        "title": "Strategy Discussion",
        "tags": ["meeting", "strategy"],
        "source": "conversation"
      },
      "relevance_score": 0.82,
      "created_at": "2025-03-04T10:30:00Z"
    }
  ]
}
```

### Task Management

```http
POST /v1/tasks
```

Create a new task.

**Request Headers:**

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "description": "Analyze the quarterly sales data and prepare a summary report",
  "priority": "high",
  "due_date": "2025-03-10T17:00:00Z",
  "metadata": {
    "project": "Q1 Analysis",
    "department": "Sales"
  }
}
```

**Response:**

```json
{
  "task_id": "task_abc123",
  "description": "Analyze the quarterly sales data and prepare a summary report",
  "status": "pending",
  "priority": "high",
  "due_date": "2025-03-10T17:00:00Z",
  "created_at": "2025-03-05T14:00:00Z",
  "metadata": {
    "project": "Q1 Analysis",
    "department": "Sales"
  }
}
```

```http
GET /v1/tasks/{task_id}
```

Get task status.

**Request Headers:**

```
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "task_id": "task_abc123",
  "description": "Analyze the quarterly sales data and prepare a summary report",
  "status": "in_progress",
  "priority": "high",
  "due_date": "2025-03-10T17:00:00Z",
  "created_at": "2025-03-05T14:00:00Z",
  "started_at": "2025-03-05T14:05:00Z",
  "progress": 0.35,
  "metadata": {
    "project": "Q1 Analysis",
    "department": "Sales"
  }
}
```

## Domain Expert APIs

### Code Assistant API

```http
POST /v1/experts/code/analyze
```

Analyze code for issues and suggestions.

**Request Headers:**

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "code": "function calculateTotal(items) {\n  let total = 0;\n  for (let i = 0; i < items.length; i++) {\n    total += items[i].price;\n  }\n  return total;\n}",
  "language": "javascript",
  "analysis_type": ["performance", "security", "style"],
  "context": {
    "project_type": "web",
    "environment": "browser"
  }
}
```

**Response:**

```json
{
  "analysis_id": "ana_abc123",
  "language": "javascript",
  "issues": [
    {
      "type": "performance",
      "severity": "low",
      "message": "Consider using Array.reduce() for better readability",
      "line_start": 2,
      "line_end": 5,
      "suggestion": "return items.reduce((total, item) => total + item.price, 0);"
    },
    {
      "type": "security",
      "severity": "medium",
      "message": "No input validation for item.price, could cause NaN issues",
      "line_start": 3,
      "line_end": 3,
      "suggestion": "total += typeof item.price === 'number' ? item.price : 0;"
    }
  ],
  "summary": "Function is mostly sound but could benefit from modern JavaScript practices and defensive coding."
}
```

### Deep Research API

```http
POST /v1/experts/research/query
```

Perform deep research on a topic.

**Request Headers:**

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "query": "What are the latest developments in quantum computing?",
  "depth": "comprehensive",
  "sources": ["academic", "news", "patents"],
  "time_range": {
    "start": "2024-01-01",
    "end": "2025-03-01"
  }
}
```

**Response:**

```json
{
  "research_id": "res_abc123",
  "query": "What are the latest developments in quantum computing?",
  "status": "in_progress",
  "estimated_completion": "2025-03-05T15:30:00Z"
}
```

```http
GET /v1/experts/research/{research_id}
```

Get research results.

**Request Headers:**

```
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "research_id": "res_abc123",
  "query": "What are the latest developments in quantum computing?",
  "status": "completed",
  "completed_at": "2025-03-05T15:25:00Z",
  "results": {
    "summary": "Recent developments in quantum computing have focused on three main areas: error correction, qubit stability, and practical applications...",
    "key_findings": [
      {
        "title": "Breakthrough in error correction techniques",
        "description": "Researchers at MIT developed a new quantum error correction method that...",
        "sources": [
          {
            "title": "Advanced Quantum Error Correction",
            "authors": ["J. Smith", "L. Zhang"],
            "publication": "Nature Quantum Information",
            "date": "2024-11-15",
            "url": "https://example.com/paper1"
          }
        ]
      }
      // Additional findings...
    ],
    "sources": [
      // List of all sources consulted...
    ]
  }
}
```

## Integration APIs

### VS Code Extension API

```http
POST /v1/integrations/vscode/analyze-project
```

Analyze a VS Code project.

**Request Headers:**

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "project_files": [
    {
      "path": "src/main.js",
      "content": "// File content here...",
      "language": "javascript"
    },
    {
      "path": "src/utils.js",
      "content": "// File content here...",
      "language": "javascript"
    }
  ],
  "dependencies": {
    "react": "18.2.0",
    "lodash": "4.17.21"
  },
  "context": {
    "selected_file": "src/main.js",
    "cursor_position": {
      "line": 24,
      "column": 15
    }
  }
}
```

**Response:**

```json
{
  "analysis_id": "proj_abc123",
  "recommendations": [
    {
      "type": "architecture",
      "message": "Consider separating UI components into their own directory",
      "details": "The project mixes business logic and UI components in the same files, which could lead to maintainability issues."
    },
    {
      "type": "dependency",
      "message": "lodash usage could be replaced with native JS methods",
      "details": "The project only uses 2 lodash methods which have native JS equivalents: map and filter."
    }
  ],
  "context_specific": {
    "file": "src/main.js",
    "suggestions": [
      {
        "line": 24,
        "message": "Consider using React.memo for this component to prevent unnecessary re-renders",
        "code_snippet": "export const UserList = React.memo(({ users }) => { ... })"
      }
    ]
  }
}
```

### Browser Extension API

```http
POST /v1/integrations/browser/analyze-page
```

Analyze a web page.

**Request Headers:**

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "url": "https://example.com/page",
  "html": "<!DOCTYPE html><html>...</html>",
  "context": {
    "selected_element": {
      "tag": "div",
      "id": "product-list",
      "classes": ["container", "products"]
    },
    "scroll_position": 0.45
  }
}
```

**Response:**

```json
{
  "analysis_id": "page_abc123",
  "page_summary": {
    "title": "Example Product Page",
    "main_content_type": "e-commerce",
    "key_elements": [
      {
        "type": "navigation",
        "importance": "high"
      },
      {
        "type": "product_listing",
        "importance": "primary"
      },
      {
        "type": "footer",
        "importance": "low"
      }
    ]
  },
  "context_specific": {
    "element_analysis": {
      "tag": "div",
      "id": "product-list",
      "content_type": "product_grid",
      "observations": [
        "Contains 12 product items",
        "Uses infinite scroll loading pattern",
        "Missing accessibility attributes on product cards"
      ]
    }
  },
  "actions": [
    {
      "type": "extract_data",
      "description": "Extract product information from the current view",
      "endpoint": "/v1/integrations/browser/extract-data"
    },
    {
      "type": "interact",
      "description": "Interact with page elements",
      "endpoint": "/v1/integrations/browser/interact"
    }
  ]
}
```

### M365 Apps API

```http
POST /v1/integrations/m365/analyze-document
```

Analyze an M365 document.

**Request Headers:**

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "app": "word",
  "document_id": "doc_abc123",
  "content": {
    "text": "Document content here...",
    "structure": [
      {
        "type": "heading1",
        "content": "Project Proposal"
      },
      {
        "type": "paragraph",
        "content": "This proposal outlines..."
      }
    ]
  },
  "context": {
    "cursor_position": 250,
    "selected_text": "budget allocation",
    "document_properties": {
      "title": "Project Alpha Proposal",
      "author": "Jane Smith",
      "created_date": "2025-02-15T09:00:00Z"
    }
  }
}
```

**Response:**

```json
{
  "analysis_id": "m365_abc123",
  "document_analysis": {
    "type": "business_proposal",
    "structure_completeness": 0.85,
    "key_sections": [
      {
        "name": "Executive Summary",
        "present": true,
        "completeness": 0.9
      },
      {
        "name": "Budget",
        "present": true,
        "completeness": 0.7,
        "issues": ["Missing contingency allocation"]
      },
      {
        "name": "Timeline",
        "present": false
      }
    ]
  },
  "suggestions": [
    {
      "type": "content",
      "description": "Add a project timeline section",
      "importance": "high",
      "template": "## Project Timeline\n\n| Phase | Start Date | End Date | Deliverables |\n| ----- | ---------- | -------- | ------------ |\n| Planning | [Date] | [Date] | [Deliverables] |\n"
    },
    {
      "type": "enhancement",
      "description": "Expand the budget allocation section with more detail",
      "importance": "medium",
      "related_to": "selected_text"
    }
  ],
  "actions": [
    {
      "type": "insert_content",
      "description": "Insert suggested timeline section",
      "endpoint": "/v1/integrations/m365/insert-content"
    },
    {
      "type": "format_document",
      "description": "Apply consistent formatting",
      "endpoint": "/v1/integrations/m365/format-document"
    }
  ]
}
```

## Management API

### User Management

```http
POST /v1/management/users
```

Create a new user.

**Request Headers:**

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "name": "Jane Smith",
  "role": "user",
  "metadata": {
    "department": "Engineering",
    "location": "Remote"
  }
}
```

**Response:**

```json
{
  "user_id": "user_abc123",
  "email": "user@example.com",
  "name": "Jane Smith",
  "role": "user",
  "created_at": "2025-03-05T16:00:00Z",
  "status": "pending_activation",
  "metadata": {
    "department": "Engineering",
    "location": "Remote"
  }
}
```

### System Status

```http
GET /v1/management/status
```

Get system status.

**Request Headers:**

```
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "status": "operational",
  "components": [
    {
      "name": "Core AI",
      "status": "operational",
      "latency": 120
    },
    {
      "name": "Memory System",
      "status": "operational",
      "latency": 85
    },
    {
      "name": "Code Assistant",
      "status": "degraded_performance",
      "latency": 350,
      "issue": "Experiencing higher than normal request volume"
    }
  ],
  "incidents": [
    {
      "id": "inc_abc123",
      "title": "Degraded performance in Code Assistant",
      "status": "investigating",
      "started_at": "2025-03-05T15:30:00Z",
      "updates": [
        {
          "timestamp": "2025-03-05T15:35:00Z",
          "message": "We are investigating reports of increased latency in the Code Assistant service."
        }
      ]
    }
  ]
}
```

## Error Handling

All APIs use standard HTTP status codes:

- 200 OK - The request was successful
- 201 Created - A resource was successfully created
- 400 Bad Request - The request was invalid
- 401 Unauthorized - Authentication is required
- 403 Forbidden - The authenticated user lacks permission
- 404 Not Found - The requested resource was not found
- 429 Too Many Requests - Rate limit exceeded
- 500 Internal Server Error - An unexpected error occurred

Error responses follow this format:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "The request was invalid or malformed",
    "details": [
      {
        "field": "email",
        "issue": "must be a valid email address"
      }
    ],
    "request_id": "req_abc123"
  }
}
```

## Rate Limiting

API requests are subject to rate limiting. The current limits are included in response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1614556800
```

## Webhook Notifications

Register webhooks to receive notifications about events:

```http
POST /v1/webhooks
```

**Request Headers:**

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**

```json
{
  "url": "https://example.com/webhook",
  "events": ["conversation.created", "message.created", "task.completed"],
  "secret": "your_webhook_secret"
}
```

**Response:**

```json
{
  "webhook_id": "hook_abc123",
  "url": "https://example.com/webhook",
  "events": ["conversation.created", "message.created", "task.completed"],
  "created_at": "2025-03-05T17:00:00Z",
  "status": "active"
}
```

Webhook payloads follow this format:

```json
{
  "event": "message.created",
  "timestamp": "2025-03-05T17:05:00Z",
  "data": {
    "message_id": "msg_def456",
    "conversation_id": "conv_abc123",
    "role": "assistant",
    "created_at": "2025-03-05T17:05:00Z"
  }
}
```

## SDK Support

Official SDKs are available for:

- JavaScript/TypeScript
- Python
- Java
- C#

See the [SDK Documentation](02-SDK_Documentation.md) for details.

## API Versioning

The API is versioned using the URL path (e.g., `/v1/conversations`). When breaking changes are introduced, the version number will be incremented (e.g., `/v2/conversations`).

## Support

If you encounter issues or have questions, contact developer support at api-support@cortex-platform.example.com or visit the [Developer Portal](https://developers.cortex-platform.example.com).
