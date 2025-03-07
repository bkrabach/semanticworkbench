# Cortex Core Database Schema

_Date: 2025-03-07_

This document describes the database schema used by Cortex Core, implemented using SQLAlchemy ORM.

> **Note**: This document reflects the current implementation of the database schema. As the project evolves, the schema may be enhanced to support additional functionality described in the [Project Vision](PROJECT_VISION.md).

## Overview

Cortex Core uses a relational database with SQLAlchemy ORM to store and manage data. The current implementation uses SQLite, but the design supports other database engines as well through SQLAlchemy's database abstraction.

## Entity Relationship Diagram

The following diagram shows the relationships between the main entities in the database:

```
┌─────────┐     ┌───────────────┐     ┌───────────┐
│  User   │<────┤ LoginAccount  │     │  Session  │<───┐
└────┬────┘     └───────────────┘     └───────────┘    │
     │                                                 │
     │ owns                                           owned by
     │                                                 │
     ▼                                                 │
┌─────────────┐     ┌──────────┐     ┌───────────────┐ │
│ Conversation │<────┤ Message  │<────┤ ToolExecution │ │
└─────────────┘     └──────────┘     └───────────────┘ │
     ▲                                                 │
     │                                                 │
     └─────────────────────────────────────────────────┘

     ┌────────────┐     ┌─────────┐
     │ MCPServer  │<────┤ MCPTool │
     └────────────┘     └─────────┘

     ┌─────────────┐
     │ MemoryEntry │
     └─────────────┘

     ┌───────────────┐
     │ SSEConnection │
     └───────────────┘
```

## Tables

### User

Stores information about users of the system.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| username | String | Unique username |
| display_name | String | User's display name |
| created_at | DateTime | When the user was created |
| updated_at | DateTime | When the user was last updated |

### LoginAccount

Supports multiple authentication methods for a single user.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to User |
| account_type | String | Type of account (e.g., local, oauth) |
| account_id | String | External account identifier |
| auth_data | JSON | Authentication data (e.g., hashed password) |
| created_at | DateTime | When the account was created |
| updated_at | DateTime | When the account was last updated |

### Session

Tracks active user sessions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key (session token) |
| user_id | UUID | Foreign key to User |
| expires_at | DateTime | When the session expires |
| created_at | DateTime | When the session was created |
| last_active_at | DateTime | When the session was last active |

### Conversation

Represents a conversation between a user and the assistant.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to User |
| title | String | Conversation title |
| created_at | DateTime | When the conversation was created |
| updated_at | DateTime | When the conversation was last updated |

### Message

Individual messages within a conversation.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| conversation_id | UUID | Foreign key to Conversation |
| role | String | Message role (user, assistant, system, tool) |
| content | Text | Message content |
| metadata | JSON | Additional message metadata |
| created_at | DateTime | When the message was created |

### ToolExecution

Records of tool calls and their results.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| message_id | UUID | Foreign key to Message |
| tool_id | String | Identifier of the tool that was called |
| name | String | Name of the tool function that was called |
| arguments | JSON | Arguments passed to the tool |
| result | Text | Result returned by the tool |
| status | String | Status of the tool execution |
| created_at | DateTime | When the tool execution was created |
| completed_at | DateTime | When the tool execution completed |

### MCPServer

Model Context Protocol servers that provide tools.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | String | Server name |
| url | String | Server URL |
| api_key | String | API key for the server (encrypted) |
| status | String | Server status |
| created_at | DateTime | When the server was created |
| updated_at | DateTime | When the server was last updated |

### MCPTool

Tools provided by MCP servers.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| server_id | UUID | Foreign key to MCPServer |
| name | String | Tool name |
| description | Text | Tool description |
| parameters_schema | JSON | JSON Schema for tool parameters |
| created_at | DateTime | When the tool was created |
| updated_at | DateTime | When the tool was last updated |

### MemoryEntry

Persisted memory entries for long-term context.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to User (optional) |
| conversation_id | UUID | Foreign key to Conversation (optional) |
| key | String | Memory key |
| value | JSON | Memory value |
| expiry | DateTime | When the memory entry expires (optional) |
| created_at | DateTime | When the memory entry was created |
| updated_at | DateTime | When the memory entry was last updated |

### SSEConnection

Server-Sent Events connections for real-time updates.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to User |
| conversation_id | UUID | Foreign key to Conversation |
| client_id | String | Client identifier |
| created_at | DateTime | When the connection was created |
| last_active_at | DateTime | When the connection was last active |

## Relationships

### One-to-Many
- User → Conversation: A user can have multiple conversations
- User → LoginAccount: A user can have multiple login accounts
- User → Session: A user can have multiple sessions
- Conversation → Message: A conversation contains multiple messages
- Message → ToolExecution: A message can have multiple tool executions
- MCPServer → MCPTool: A server can provide multiple tools

### Many-to-One
- Conversation → User: A conversation belongs to one user
- Message → Conversation: A message belongs to one conversation
- ToolExecution → Message: A tool execution belongs to one message
- LoginAccount → User: A login account belongs to one user
- Session → User: A session belongs to one user
- MCPTool → MCPServer: A tool belongs to one server

## Indexes

Key indexes are created on:
- User.username (unique)
- LoginAccount.user_id + LoginAccount.account_type + LoginAccount.account_id (unique)
- Message.conversation_id + Message.created_at (for efficient message retrieval)
- ToolExecution.message_id (for related tool executions)
- MemoryEntry.key (for efficient memory lookups)

## Migrations

The database schema is managed through SQLAlchemy's declarative base and is created at application startup if it doesn't exist. For production deployments, proper database migration tools should be implemented (e.g., Alembic).