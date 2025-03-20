# Cortex Core Architecture Overview

This document provides a high-level overview of the Cortex Core architecture as implemented in Phase 1. It serves as a comprehensive guide for developers working with the codebase.

## System Purpose

Cortex Core is a centralized API service that manages communication between input clients (which send data) and output clients (which receive processed data). It provides a clean, reliable communication channel between these clients while ensuring proper data isolation between users.

## Core Architecture Principles

The Cortex Core architecture is built upon these fundamental principles:

1. **Ruthless Simplicity**: Every component is designed to be as simple as possible while maintaining functionality.
2. **Clean Separation**: Input and output paths are strictly separated.
3. **Event-Driven Communication**: An event bus handles all internal communication.
4. **User Partitioning**: All data is strictly partitioned by user ID.
5. **Stateless API Design**: No server-side sessions; authentication via JWT.

## Phase 1 Implementation

Phase 1 implements a complete, functional input/output system with in-memory storage. This enables immediate development of client applications while laying the groundwork for future enhancements.

### High-Level Architecture Diagram

```mermaid
graph TD
    InputClient[Input Client] -->|HTTP POST| FastAPI[FastAPI Application]
    FastAPI -->|Validate| Auth[Auth System]
    FastAPI -->|Publish| EventBus[Event Bus]
    EventBus -->|Store| Storage[In-Memory Storage]
    OutputClient[Output Client] -->|SSE| FastAPI
    FastAPI -->|Filter Events| OutputClient

    subgraph "Core Components"
        FastAPI
        Auth
        EventBus
        Storage
    end

    classDef client stroke:#f9f,stroke-width:4px;
    classDef core stroke:#bbf,stroke-width:4px;

    class InputClient,OutputClient client;
    class FastAPI,Auth,EventBus,Storage core;
```

### Core Components

#### 1. FastAPI Application (`app/main.py`)

- Main application entry point
- Router registration and middleware configuration
- Dependency injection configuration
- Application lifecycle management

```python
# Basic structure
app = FastAPI(title="Cortex Core API")
app.include_router(auth_router)
app.include_router(input_router)
app.include_router(output_router)
app.include_router(config_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup code (event bus initialization, etc.)
    yield
    # Cleanup code
```

#### 2. Authentication System (`app/utils/auth.py`, `app/api/auth.py`)

- JWT token generation and validation
- User authentication endpoints
- Token validation dependencies for protected endpoints

#### 3. Event Bus (`app/core/event_bus.py`)

- In-memory message bus using asyncio
- Subscription management and event publishing
- Event filtering by user ID

```python
# Basic structure
class EventBus:
    def __init__(self):
        self.subscribers = []  # List of asyncio.Queue objects

    def subscribe(self, queue: asyncio.Queue) -> None:
        self.subscribers.append(queue)

    async def publish(self, event: Dict[str, Any]) -> None:
        # Distribute events to all subscribers
        for queue in self.subscribers:
            await queue.put(event)

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        if queue in self.subscribers:
            self.subscribers.remove(queue)
```

#### 4. Input API (`app/api/input.py`)

- Endpoint for receiving data from clients
- Request validation and authentication
- Event publication to the Event Bus

```python
# Basic structure
@router.post("/input")
async def receive_input(
    input_data: InputRequest,
    user: UserData = Depends(get_current_user),
    event_bus: EventBus = Depends(get_event_bus),
    storage: InMemoryStorage = Depends(get_storage)
) -> Dict[str, Any]:
    # Validate, process input, and publish event
    event = {
        "type": "input",
        "data": input_data.dict(),
        "user_id": user.user_id,
        "timestamp": datetime.now().isoformat()
    }

    # Store in memory and publish to event bus
    await storage.store_message(user.user_id, input_data.conversation_id, event)
    await event_bus.publish(event)

    return {"status": "received"}
```

#### 5. Output API with SSE (`app/api/output.py`)

- Server-Sent Events endpoint for streaming output
- User-specific event filtering
- Connection management with proper cleanup

```python
# Basic structure
@router.get("/output/stream")
async def output_stream(
    request: Request,
    user: UserData = Depends(get_current_user),
    event_bus: EventBus = Depends(get_event_bus)
) -> StreamingResponse:
    # Create a queue for this connection
    queue = asyncio.Queue()

    # Subscribe to the event bus
    event_bus.subscribe(queue)

    async def event_generator():
        try:
            while True:
                # Get event from queue with timeout
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)

                    # Filter events for this user
                    if event.get("user_id") == user.user_id:
                        yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat on timeout
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            # Client disconnected, clean up
            raise
        finally:
            # Always unsubscribe to prevent memory leaks
            event_bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

#### 6. In-Memory Storage (`app/core/storage.py`)

- Simple in-memory data store
- User-partitioned data structure
- Storage for users, workspaces, conversations, and messages

```python
# Basic structure
class InMemoryStorage:
    def __init__(self):
        self.users = {}
        self.workspaces = {}
        self.conversations = {}
        self.messages = {}

    async def store_message(self, user_id: str, conversation_id: str, message: Dict[str, Any]) -> None:
        # Store message in memory with proper user partitioning
        if user_id not in self.messages:
            self.messages[user_id] = {}

        if conversation_id not in self.messages[user_id]:
            self.messages[user_id][conversation_id] = []

        self.messages[user_id][conversation_id].append(message)
```

#### 7. Configuration API (`app/api/config.py`)

- Endpoints for workspace and conversation management
- User-specific configuration

#### 8. Data Models

- Base models with metadata (`app/models/base.py`)
- Domain models for users, workspaces, conversations (`app/models/domain.py`)
- API request/response models (`app/models/api/request.py`, `app/models/api/response.py`)

## Key Flows

### Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant AuthAPI as Authentication API
    participant JWT as JWT Handler

    Client->>AuthAPI: POST /auth/login (username, password)
    AuthAPI->>AuthAPI: Validate credentials
    AuthAPI->>JWT: Generate JWT token
    JWT-->>AuthAPI: JWT token
    AuthAPI-->>Client: Return token

    Client->>AuthAPI: Request with Bearer token
    AuthAPI->>JWT: Validate token
    JWT-->>AuthAPI: User information
    AuthAPI-->>Client: Protected resource
```

### Input Flow

```mermaid
sequenceDiagram
    participant Client
    participant InputAPI as Input API
    participant EventBus as Event Bus
    participant Storage as In-Memory Storage

    Client->>InputAPI: POST /input with data
    InputAPI->>InputAPI: Validate request
    InputAPI->>EventBus: Publish input event
    InputAPI->>Storage: Store message
    InputAPI-->>Client: Confirmation response
```

### Output Flow

```mermaid
sequenceDiagram
    participant Client
    participant OutputAPI as Output API
    participant EventBus as Event Bus

    Client->>OutputAPI: GET /output/stream
    OutputAPI->>OutputAPI: Create SSE connection
    OutputAPI->>EventBus: Subscribe to events

    loop While Connection Open
        EventBus-->>OutputAPI: Events for all users
        OutputAPI->>OutputAPI: Filter by user_id
        OutputAPI-->>Client: User-specific events
    end

    Note over Client,OutputAPI: Client disconnects

    OutputAPI->>EventBus: Unsubscribe
```

## Error Handling

The system implements structured error handling:

1. API errors return appropriate HTTP status codes with consistent error format
2. Authentication errors return 401 Unauthorized with clear error messages
3. Validation errors return 422 Unprocessable Entity with field-specific details
4. Server errors are logged with contextual information
5. SSE connections handle disconnections gracefully with proper cleanup

## Resource Management

Special attention is paid to proper resource management:

1. All background tasks are properly tracked and cleaned up
2. SSE connections are cleaned up when clients disconnect
3. Event Bus subscriptions are properly removed when no longer needed
4. Asyncio resources are managed with proper error handling
5. The application implements proper lifespan management for startup/shutdown

## Security

The system implements these security measures:

1. JWT authentication for all protected endpoints
2. User ID validation on every request
3. Strict user partitioning for all data
4. No cross-user data access
5. CORS protection with configurable allowed origins

## Future Expansion

While Phase 1 implements a complete input/output system with in-memory storage, future phases will add:

1. Persistent storage (SQL database)
2. Azure B2C integration for production authentication
3. MCP (Model Context Protocol) client and service integrations
4. Memory and cognition service integration
5. More sophisticated error handling and recovery mechanisms
6. Production deployment configuration

## Development Guidelines

When working with this architecture:

1. Maintain strict separation between input and output paths
2. Always partition data by user ID
3. Handle asyncio exceptions properly, especially CancelledError
4. Clean up resources in finally blocks
5. Keep components as simple as possible
6. Follow the existing patterns for consistency
