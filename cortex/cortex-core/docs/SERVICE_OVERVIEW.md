# Cortex Core Service Overview

## Architectural Overview

Cortex Core is a central orchestration engine built on FastAPI that provides user management, conversation handling, and real-time updates. It follows a modular design with clear separation of concerns and a RESTful API architecture.

The system employs a layered architecture:

1. **Presentation Layer**: FastAPI routes and endpoints
2. **Business Logic Layer**: Components and services
3. **Data Access Layer**: Database models and connection management
4. **Infrastructure Layer**: Caching, security, and external communication

The service uses asynchronous programming throughout, leveraging FastAPI's async support and SQLAlchemy's async capabilities for optimal performance.

## Key Components and Their Responsibilities

### FastAPI Application (app/main.py)

- Central entry point for the application
- Configures middleware, CORS settings, and error handling
- Registers routers and defines the application lifespan

### Configuration Management (app/config.py)

- Defines settings for all system components
- Uses Pydantic for validation and environment variable overrides
- Separates concerns into domain-specific configuration classes

### Security Manager (app/components/security_manager.py)

- Handles authentication and authorization
- Manages token generation and verification
- Provides encryption/decryption for sensitive data

### Database Management (app/database/)

- Models define the data schema
- Connection management with automatic migrations
- Session handling and transaction support

### Memory System (app/interfaces/memory_system.py)

- Interface defining the contract for memory implementations
- Allows pluggable memory backends (Whiteboard, JAKE)
- Manages conversation history and knowledge persistence

### Caching (app/cache/redis_client.py)

- Provides Redis-based caching with in-memory fallback
- Transparent API regardless of underlying implementation
- Handles connection management and error recovery

## API Endpoint Organization

The API is organized into logical groups via FastAPI routers:

### Authentication (/auth)

- `POST /auth/login`: Authenticate user and return JWT token
- `POST /auth/refresh`: Refresh an authentication token
- `POST /auth/logout`: Log out and invalidate token
- `POST /auth/key/generate`: Generate an API key

### Workspaces (/workspaces)

- `GET /workspaces`: List workspaces for current user
- `POST /workspaces`: Create a new workspace

### Conversations

- `GET /workspaces/{workspace_id}/conversations`: List conversations in a workspace
- `POST /workspaces/{workspace_id}/conversations`: Create a new conversation
- `GET /conversations/{conversation_id}`: Get conversation details
- `PUT /conversations/{conversation_id}`: Update conversation details
- `DELETE /conversations/{conversation_id}`: Delete a conversation
- `GET /conversations/{conversation_id}/messages`: Get messages in a conversation
- `POST /conversations/{conversation_id}/messages`: Add a message to a conversation
- `POST /conversations/{conversation_id}/messages/stream`: Stream message responses

### Server-Sent Events

- `GET /events`: Global events endpoint
- `GET /users/{user_id}/events`: User-specific events
- `GET /workspaces/{workspace_id}/events`: Workspace-specific events
- `GET /conversations/{conversation_id}/events`: Conversation-specific events

## Authentication Flow

1. **User Authentication**:

   - User submits credentials via `/auth/login`
   - System validates credentials and generates JWT token
   - Token contains user_id and is signed with JWT secret

2. **Token Usage**:

   - Client includes token in Authorization header
   - `get_current_user` dependency validates token for protected endpoints
   - Token expiry is managed via expiration claims

3. **API Key Authentication**:
   - Alternative to password auth for programmatic access
   - Keys are securely stored with encryption
   - Keys have configurable expiry and scopes

## Data Flow Between Components

1. **Client Request Flow**:

   - Request arrives at FastAPI endpoint
   - Request logging middleware captures timing and metadata
   - Authentication middleware validates token if required
   - Route handler processes the request, accessing database/cache as needed
   - Response is formatted and returned to client

2. **Event Flow**:

   - Actions that modify state trigger events via SSE
   - Events are broadcast to relevant subscribers
   - Clients receive real-time updates

3. **Conversation Flow**:
   - User sends message to conversation
   - Message is stored in database
   - Response is generated (simulated in current version)
   - Real-time updates via SSE notify clients of new messages

## Integration Points

The system provides several integration points:

1. **REST API**: Primary interface for client applications
2. **Server-Sent Events**: Real-time updates for clients
3. **Streaming API**: For conversation message streaming
4. **Redis Interface**: For distributed caching and pub/sub
5. **Database Migrations**: For schema evolution

Future integration points (mentioned in code):

- MCP (Multi-Cloud Platform) integration
- LLM service integration
- MSAL (Microsoft Authentication Library) integration

## Caching Strategy

The caching system uses Redis with an in-memory fallback mechanism:

1. **Redis Primary Cache**:

   - Used when available for distributed caching
   - Handles all standard operations (get, set, expire, etc.)

2. **In-Memory Fallback**:

   - Activates automatically when Redis is unavailable
   - Implements same interface for transparent usage
   - Background thread manages TTL expirations

3. **Cache Usage**:
   - Session state
   - Authentication tokens
   - Frequently accessed data
   - Rate limiting implementation

## Event System

The Server-Sent Events (SSE) system provides real-time updates:

1. **Connection Management**:

   - Connections are tracked in memory by channel type
   - Channels include global, user-specific, workspace-specific, and conversation-specific

2. **Event Broadcasting**:

   - Events are sent to specific channels
   - Clients subscribe to channels relevant to their context
   - Heartbeats maintain connections

3. **Event Types**:
   - `connect`: Initial connection established
   - `heartbeat`: Keep-alive signal
   - `conversation_created`: New conversation created
   - `conversation_updated`: Conversation details changed
   - `message_received`: New message in conversation
   - `typing_indicator`: User/assistant typing status

## Memory System

The memory system provides a flexible architecture for conversation history and knowledge storage:

1. **Interface Contract**:

   - Defined in `app/interfaces/memory_system.py`
   - Methods for store, retrieve, update, delete, and synthesize
   - Consistent API regardless of implementation

2. **Memory Item Structure**:

   - ID, type, content, metadata, timestamp
   - Expiration based on retention policy

3. **Implementations** (planned):
   - Whiteboard: Simple in-memory/database storage
   - JAKE: More advanced knowledge engine with semantic capabilities

The service is designed to be extensible with new features while maintaining backward compatibility through careful API design and versioning.
