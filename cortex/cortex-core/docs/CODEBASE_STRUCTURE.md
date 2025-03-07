# Cortex Core Codebase Structure

## Directory Structure Overview

The Cortex Core codebase follows a modular structure organized around key functionality areas:

```
cortex-core/
├── alembic/                # Database migration scripts
├── app/                    # Main application code
│   ├── api/                # API endpoints and route handlers
│   ├── cache/              # Caching functionality (Redis with in-memory fallback)
│   ├── components/         # Core system components and utilities
│   ├── database/           # Database models and connection management
│   ├── interfaces/         # Abstract interfaces defining system contracts
│   ├── modalities/         # Handling of different interaction modalities
│   └── utils/              # Utility functions and helpers
├── docs/                   # Documentation files
└── tests/                  # Test suite
```

## Key File Descriptions

### Configuration and Setup

- **app/main.py**: Entry point for the FastAPI application. Sets up middleware, routes, and defines lifespan events.
- **app/config.py**: Configuration management using Pydantic. Contains settings for database, security, caching, etc.
- **pyproject.toml**: Project metadata, dependencies, and development tools configuration.
- **Makefile**: Contains commands for database migrations and other development tasks.

### API Endpoints

- **app/api/auth.py**: Authentication endpoints for login, refresh tokens, logout.
- **app/api/conversations.py**: Conversation management endpoints for creating, reading, updating conversations and messages.
- **app/api/workspaces.py**: Workspace management endpoints.
- **app/api/sse.py**: Server-Sent Events for real-time updates.

### Data Models and Database

- **app/database/models.py**: SQLAlchemy models defining the database schema.
- **app/database/connection.py**: Database connection management, with helper methods for JSON handling.

### Core Components

- **app/components/security_manager.py**: Handles authentication, authorization, and encryption.
- **app/components/tokens.py**: JWT token generation, validation, and token data models.
- **app/components/auth_schemes.py**: Authentication schemes for API endpoints.

### Interfaces

- **app/interfaces/memory_system.py**: Interface for memory systems defining the contract for implementations.

### Caching

- **app/cache/redis_client.py**: Redis client with in-memory fallback, providing a consistent API.

## Module Organization

Cortex Core follows a clean architectural approach with clear separation of concerns:

1. **API Layer**: Handles HTTP requests/responses via FastAPI routes, input validation, and response formatting.
2. **Service Layer**: Implements business logic and orchestrates component interactions.
3. **Data Layer**: Manages data persistence and retrieval via SQLAlchemy ORM.
4. **Component Layer**: Provides reusable components and utilities.
5. **Interface Layer**: Defines contracts for extensible system parts.

## Dependency Relationships

The system follows a hierarchical dependency structure:

- API endpoints depend on components and database
- Components depend on configurations and utilities
- Database models are independent of other modules
- Interfaces define contracts that implementations must follow
- Cache is used by multiple components but has no outward dependencies

Key dependencies include:

- FastAPI for REST API
- SQLAlchemy for ORM and database access
- Redis for caching with in-memory fallback
- Pydantic for data validation and settings
- JWT for authentication tokens

## Configuration Details

Configuration is managed using Pydantic's `BaseSettings` in `app/config.py`, with nested configuration classes for different system areas:

- **DatabaseConfig**: Database connection settings
- **CacheConfig**: Redis configuration
- **SecurityConfig**: JWT secrets, encryption keys, token expiry
- **ServerConfig**: Host, port, logging settings
- **MemoryConfig**: Memory system type and retention settings
- **SseConfig**: Server-Sent Events configuration

Configuration values can be overridden via environment variables following naming conventions like `DATABASE_URL` or `SECURITY_JWT_SECRET`.

## Database Schema Overview

The database schema is defined in `app/database/models.py` and includes the following key entities:

- **User**: Application users with authentication details
- **Role**: User roles for authorization
- **Session**: User sessions for tracking active connections
- **ApiKey**: API keys for programmatic access
- **Workspace**: User workspaces for organizing conversations
- **WorkspaceSharing**: Workspace sharing permissions between users
- **Conversation**: Conversations with messages
- **MemoryItem**: Items stored in the memory system
- **Integration**: External system integrations
- **DomainExpertTask**: Tasks for domain-specific processing

Key relationships:

- Users have many workspaces (one-to-many)
- Workspaces have many conversations (one-to-many)
- Users can have multiple roles (many-to-many)
- Workspaces can be shared with multiple users (many-to-many via WorkspaceSharing)
