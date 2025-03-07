# Cortex Core Architecture Overview

## Introduction

Cortex Core is the backend component of the Cortex Platform, providing a central intelligent system that manages conversations, orchestrates AI interactions, and integrates with external tools. Built with FastAPI and SQLAlchemy, it implements the vision of a modular, extensible AI ecosystem with a unified memory and context-aware processing.

## System Architecture

Cortex Core follows a modular architecture with clear separation of concerns:

```
cortex_core/
├── api/                # API endpoints and routing
│   ├── endpoints.py    # FastAPI routes
│   └── routes/         # Additional route modules
├── core/               # Core business logic
│   ├── auth.py         # Authentication and session management
│   ├── config.py       # Configuration management
│   ├── conversation.py # Conversation handler
│   ├── llm.py          # LLM integration
│   ├── mcp_client.py   # Model Context Protocol client
│   ├── memory.py       # Memory/context management 
│   ├── router.py       # Message router/event bus
│   └── sse.py          # Server-Sent Events
├── db/                 # Database layer
│   ├── database.py     # Database connection
│   └── models.py       # SQLAlchemy models
├── models/             # Data models
│   └── schemas.py      # Pydantic schemas
└── utils/              # Utility functions
```

## Key Components

### 1. Message Router (`router.py`)

The Message Router acts as a central event bus that facilitates communication between components. It implements a publisher-subscriber pattern where components can:

- Register as subscribers for specific event types
- Publish events to notify all interested subscribers

This approach decouples components and allows for a more flexible, extensible architecture. Events might include new messages, conversation updates, or tool execution results.

### 2. Conversation Handler (`conversation.py`)

The Conversation Handler is responsible for managing the lifecycle of conversations:

- Processing incoming user messages
- Interfacing with the LLM to generate responses
- Managing conversation context and state
- Orchestrating tool usage through function calling
- Storing conversation history

When a user message is received, the handler enriches it with contextual information from the memory system, processes it through the LLM, handles any tool invocations, and returns the response.

### 3. Memory System (`memory.py`)

The Memory Adapter provides persistent storage for conversation context:

- Maintains conversation history
- Stores and retrieves contextual information
- Implements a simplified "whiteboard" model for the current implementation
- Designed to be replaceable with more sophisticated memory systems in the future

The memory system ensures that each interaction builds upon previous context, creating a coherent user experience.

### 4. LLM Integration (`llm.py`)

The LLM Client manages interactions with language models:

- Supports multiple providers through LiteLLM
- Handles prompt construction and context management
- Processes function calling requests for tool usage
- Manages streaming responses

### 5. MCP Client (`mcp_client.py`)

The Model Context Protocol (MCP) Client enables integration with external tools:

- Manages connections to MCP servers
- Routes tool execution requests to appropriate servers
- Handles tool execution results
- Integrates tool outputs into the conversation flow

This component enables the extensibility of the system through standardized tool integration.

### 6. Authentication System (`auth.py`)

The Auth System manages user identity and sessions:

- User authentication via multiple methods
- Session creation and validation
- Access control for secure API endpoints

### 7. SSE Manager (`sse.py`)

The Server-Sent Events Manager handles real-time communication:

- Maintains active client connections
- Streams response chunks as they're generated
- Provides real-time updates for conversation changes

## Database Schema

The database uses SQLAlchemy ORM with the following key models:

- **User**: User information and account management
- **LoginAccount**: Authentication accounts (supports multiple types)
- **Session**: User session tracking
- **Conversation**: Container for conversation threads
- **Message**: Individual messages in conversations (user, assistant, system, tool)
- **MemoryEntry**: Persisted information for long-term context
- **MCPServer & MCPTool**: External tool integration configuration
- **ToolExecution**: Record of tool invocations and results
- **SSEConnection**: Real-time connection management

### Key Relationships:

- Users have many Conversations
- Conversations contain many Messages
- Messages can have associated ToolExecutions
- MCPServers provide multiple MCPTools
- Users have multiple Sessions and LoginAccounts

## API Endpoints

The REST API is built with FastAPI and includes these key endpoints:

- **Authentication**:
  - `POST /api/login`: Authenticate a user
  - `GET /api/validate-session`: Validate a session token
  - `POST /api/logout`: End a user session

- **Conversations**:
  - `GET /api/conversations`: List conversations
  - `POST /api/conversations`: Create a new conversation
  - `GET /api/conversations/{id}`: Get conversation details
  - `DELETE /api/conversations/{id}`: Delete a conversation

- **Messages**:
  - `GET /api/conversations/{id}/messages`: Get messages in a conversation
  - `POST /api/conversations/{id}/messages`: Add a message to a conversation

- **Real-time Updates**:
  - `GET /api/sse/conversations/{id}`: SSE endpoint for real-time updates

## Data Flow

1. **Request Handling**:
   - Client requests arrive at FastAPI endpoints
   - Authentication middleware validates user sessions
   - Requests are dispatched to appropriate handlers

2. **Message Processing**:
   ```
   ┌────────────┐    ┌─────────────┐    ┌─────────────┐
   │ API        │    │ Conversation │    │ Memory      │
   │ Endpoints  │───>│ Handler     │<───>│ Adapter     │
   └────────────┘    └──────┬──────┘    └─────────────┘
                           │
                           ▼
                     ┌─────────────┐
                     │ LLM Client  │
                     └──────┬──────┘
                            │
                     ┌──────┴──────┐
                     │ MCP Client  │
                     └─────────────┘
   ```

3. **Event Propagation**:
   - Component actions trigger events via the Message Router
   - Subscribed components react to relevant events
   - SSE Manager sends real-time updates to connected clients

## Configuration

Configuration is managed through:
- Environment variables
- `.env` file support for local development
- Pydantic `Settings` class with validation and defaults

Key configuration options include:
- Database connection settings
- LLM provider configuration
- Authentication settings
- Logging configuration

## Initialization Process

1. Application startup sequence:
   - Load configuration
   - Initialize database connection
   - Set up Message Router
   - Initialize core components (Memory, MCP Client, Auth, Conversation Handler, SSE)
   - Register API routes
   - Set up default data if needed

2. Component dependency order:
   - Message Router (first, as others depend on it)
   - Memory Adapter
   - MCP Client Manager
   - User Session Manager
   - Conversation Handler
   - SSE Manager

## Extension Points

Cortex Core is designed to be extensible in several ways:

1. **Memory Systems**: The Memory Adapter interface allows for replacing the current implementation with more sophisticated systems.

2. **LLM Providers**: Support for multiple LLM providers through LiteLLM.

3. **MCP Tools**: New tools can be added by registering them with MCP servers.

4. **Authentication Methods**: The authentication system supports multiple login types.

## Conclusion

Cortex Core provides a robust, modular foundation for the Cortex Platform. Its event-driven architecture, clear separation of concerns, and standardized interfaces enable both current functionality and future extensions as the platform evolves.