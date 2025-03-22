# Cortex Core Architecture

## Core Technical Requirements

1. **Client Protocol Specifications**

   - Input clients must use HTTP POST to `/input` endpoint with JSON payload
   - Output clients must use Server-Sent Events (SSE) connecting to `/output/stream`
   - Authentication uses JWT bearer tokens in Authorization header
   - No WebSockets, no direct LLM endpoint exposure

2. **Backend Service Requirements**

   - Cortex Core acts as MCP client to all backend services
   - Backend services must implement the MCP server protocol
   - Memory and Cognition services are required; Domain Expert services are optional
   - No direct database access between services

3. **Data Partitioning Requirements**

   - All data must be partitioned by user ID (from Auth0's `sub` claim)
   - Workspaces belong to a single owner
   - Conversations belong to a single workspace
   - All events must include user ID for filtering

4. **Core Architecture Boundaries**
   - Input and output are strictly separated paths
   - Event bus handles all internal communication
   - No shared state between components except through formal interfaces
   - Backend services have no knowledge of each other

## System Components

```mermaid
graph TD
    A[Cortex Core]
    B[FastAPI Client Interfaces]
    C[FastMCP Backend Interfaces]
    D[Dumb Input Clients]
    E[Dumb Output Clients]
    F[Memory Service]
    G[Cognition Service]
    H[Domain Expert Entities]
    I[Event Bus Module]
    M[Config Endpoints]
    N[Auth Endpoints]

    D -->|HTTP POST| B
    B --> A
    A --> I
    I --> A
    A --> C
    C --> F
    C --> G
    C --> H
    A -->|SSE| E
    A --> M
    A --> N
    D --> N
    E --> N
```

### 1. FastAPI Service Interface (Required)

**Endpoints:**

```python
# Input endpoint
@app.post("/input")
async def receive_input(data: dict, user: User = Depends(get_current_user)):
    # Process input
    return {"status": "received", "data": data}

# Output streaming endpoint
@app.get("/output/stream")
async def output_stream(user: User = Depends(get_current_user)):
    # Return SSE stream
    return StreamingResponse(generate_events(), media_type="text/event-stream")

# Authentication endpoints
@app.post("/auth/login")
async def login(credentials: LoginRequest):
    # Validate credentials and return JWT
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/verify")
async def verify_token(user: User = Depends(get_current_user)):
    # Return user info from validated token
    return user

# Configuration endpoints
@app.post("/config/workspace")
async def create_workspace(workspace: WorkspaceCreate, user: User = Depends(get_current_user)):
    # Create workspace
    return {"status": "created", "workspace": workspace_data}

@app.get("/config/workspace")
async def list_workspaces(user: User = Depends(get_current_user)):
    # List workspaces for user
    return {"workspaces": [workspace1, workspace2]}

@app.post("/config/conversation")
async def create_conversation(conversation: ConversationCreate, user: User = Depends(get_current_user)):
    # Create conversation in workspace
    return {"status": "created", "conversation": conversation_data}

@app.get("/config/conversation")
async def list_conversations(workspace_id: str, user: User = Depends(get_current_user)):
    # List conversations in workspace
    return {"conversations": [conversation1, conversation2]}
```

**Implementation Requirements:**

- FastAPI with async endpoints
- JWT authentication with Auth0 claims structure
- SSE implementation with proper connection management
- Request validation using Pydantic models
- No server-side sessions; stateless API design

### 2. Event Bus (Required)

**Interface:**

```python
class EventBus:
    def subscribe(self, queue: asyncio.Queue) -> None:
        """Register a queue to receive events"""
        pass

    async def publish(self, event: dict) -> None:
        """Publish an event to all subscribers"""
        pass

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unregister a queue"""
        pass
```

**Implementation (Simplified):**

```python
class EventBus:
    def __init__(self):
        self.subscribers = []  # List of asyncio.Queue objects

    def subscribe(self, queue: asyncio.Queue) -> None:
        self.subscribers.append(queue)

    async def publish(self, event: dict) -> None:
        for queue in self.subscribers:
            try:
                await queue.put(event)
            except Exception as e:
                logger.error(f"Failed to publish event: {e}")

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        if queue in self.subscribers:
            self.subscribers.remove(queue)
```

**Event Payload Schema:**

```python
{
    "type": str,  # "input", "output", "config_change", etc.
    "data": dict,  # Event-specific payload
    "user_id": str,  # User ID for filtering (from Auth0 sub claim)
    "timestamp": str,  # ISO-format timestamp
    "metadata": dict  # Optional metadata
}
```

**Implementation Requirements:**

- In-memory implementation using a list of asyncio.Queue objects
- No pattern matching or complex routing
- Direct publishing to all subscribers
- Thread-safe implementation
- No persistent storage of events

### 3. MCP Client Manager (Required)

**Interface:**

```python
class McpClient:
    async def connect(self) -> None:
        """Connect to MCP server"""
        pass

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool on the MCP server"""
        pass

    async def get_resource(self, uri: str) -> dict:
        """Get a resource from the MCP server"""
        pass

    async def close(self) -> None:
        """Close the connection"""
        pass
```

**Implementation (Simplified):**

```python
class McpClient:
    def __init__(self, endpoint_url: str, service_name: str):
        self.endpoint_url = endpoint_url
        self.service_name = service_name
        self.client = None
        self.connected = False

    async def connect(self) -> None:
        if self.connected:
            return

        try:
            # Use FastMCP client library
            self.client = await FastMCPClient.connect(self.endpoint_url)
            self.connected = True
        except Exception as e:
            logger.error(f"Failed to connect to {self.service_name}: {e}")
            raise

    async def call_tool(self, name: str, arguments: dict) -> dict:
        if not self.connected:
            await self.connect()

        try:
            result = await self.client.call_tool(name=name, arguments=arguments)
            return result
        except Exception as e:
            logger.error(f"Failed to call tool {name}: {e}")
            # Simple retry logic
            await self.connect()  # Try reconnecting
            return await self.client.call_tool(name=name, arguments=arguments)

    async def close(self) -> None:
        if self.connected and self.client:
            await self.client.close()
            self.connected = False
```

**Implementation Requirements:**

- Direct use of FastMCP client library
- No complex connection pooling
- Basic retry logic for transient failures (max 3 retries)
- No circuit breaker pattern initially
- Timeout of 10 seconds for all operations

### 4. Authentication Module (Required)

**JWT Token Structure:**

```python
{
    "sub": str,      # Subject (user ID)
    "name": str,     # User name
    "email": str,    # User email
    "exp": int,      # Expiration time
    "iat": int,      # Issued at time
    "iss": str,      # Issuer (Auth0 domain)
    "aud": str       # Audience (API identifier)
}
```

**Implementation (Simplified JWT):**

```python
from datetime import datetime, timedelta
from jose import jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=24)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return {"user_id": user_id, "name": payload.get("name"), "email": payload.get("email")}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
```

**Auth0 Integration (Production):**

```python
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
import jwt
from jwt.jwks_client import PyJWKClient

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE")
JWKS_URL = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"

# JWKS client for verifying tokens
jwks_client = PyJWKClient(JWKS_URL)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Get signing key
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Validate Auth0 token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=AUTH0_API_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/"
        )

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        return {
            "user_id": user_id,
            "name": payload.get("name", ""),
            "email": payload.get("email", "")
        }
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
```

**Implementation Requirements:**

- Use python-jose for JWT handling
- Secret key from environment variable
- Token expiration set to 24 hours
- No refresh tokens initially
- Validate tokens on every request

### 5. Memory Service Client (Required)

**Interface:**

```python
class MemoryServiceClient:
    async def store_input(self, user_id: str, input_data: dict) -> dict:
        """Store input data for user"""
        pass

    async def get_history(self, user_id: str) -> List[dict]:
        """Get history for user"""
        pass
```

**Implementation (Simplified):**

```python
class MemoryServiceClient:
    def __init__(self, mcp_client: McpClient):
        self.mcp_client = mcp_client

    async def store_input(self, user_id: str, input_data: dict) -> dict:
        try:
            return await self.mcp_client.call_tool(
                name="store_input",
                arguments={
                    "user_id": user_id,
                    "input_data": input_data
                }
            )
        except Exception as e:
            logger.error(f"Failed to store input: {e}")
            return {"status": "error", "message": str(e)}

    async def get_history(self, user_id: str) -> List[dict]:
        try:
            result = await self.mcp_client.get_resource(f"history/{user_id}")
            return result.get("history", [])
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
```

**Implementation Requirements:**

- Use MCP client to call Memory Service
- Store all inputs immediately after validation
- Call `store_input` tool with user_id and input_data
- Retrieve history using `get_history` resource
- No caching of results

### 6. Cognition Service Client (Required)

**Interface:**

```python
class CognitionServiceClient:
    async def get_context(self, user_id: str) -> dict:
        """Get context for user"""
        pass
```

**Implementation (Simplified):**

```python
class CognitionServiceClient:
    def __init__(self, mcp_client: McpClient):
        self.mcp_client = mcp_client

    async def get_context(self, user_id: str) -> dict:
        try:
            return await self.mcp_client.call_tool(
                name="get_context",
                arguments={"user_id": user_id}
            )
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return {"context": []}
```

**Implementation Requirements:**

- Use MCP client to call Cognition Service
- Call `get_context` tool with user_id
- No preprocessing of results
- No caching of results

## Data Models

### Base Model

```python
class BaseModelWithMetadata(BaseModel):
    """Base model with metadata field"""
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### User Model

```python
class User(BaseModelWithMetadata):
    """System user model"""
    user_id: str  # UUID string, required, from Auth0
    name: str  # Required, non-empty
    email: str  # Required, valid email format
```

### Workspace Model

```python
class Workspace(BaseModelWithMetadata):
    """Workspace model"""
    id: str  # UUID string, auto-generated
    name: str  # Required, non-empty, max 100 chars
    description: str  # Required, max 500 chars
    owner_id: str  # Required, valid user_id from Auth0
```

### Conversation Model

```python
class Conversation(BaseModelWithMetadata):
    """Conversation model"""
    id: str  # UUID string, auto-generated
    workspace_id: str  # Required, valid workspace id
    topic: str  # Required, non-empty, max 200 chars
    participant_ids: List[str]  # Required, at least one user_id
```

### Message Model

```python
class Message(BaseModelWithMetadata):
    """Message model"""
    id: str  # UUID string, auto-generated
    conversation_id: str  # Required, valid conversation id
    sender_id: str  # Required, valid user_id
    content: str  # Required, non-empty
    timestamp: str  # Required, ISO format timestamp
```

### Storage Implementation

**Initial In-Memory Storage:**

```python
# Simple in-memory storage (for development)
class InMemoryStorage:
    def __init__(self):
        self.users = {}
        self.workspaces = {}
        self.conversations = {}
        self.messages = {}

    async def create_workspace(self, workspace_data):
        workspace_id = str(uuid.uuid4())
        workspace = {**workspace_data, "id": workspace_id}
        self.workspaces[workspace_id] = workspace
        return workspace

    async def list_workspaces(self, owner_id):
        return [ws for ws in self.workspaces.values() if ws["owner_id"] == owner_id]

    # Similar methods for conversations and messages
```

**SQLite/PostgreSQL Implementation:**

```python
# SQLAlchemy models (for production)
from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB, UUID

Base = declarative_base()

class WorkspaceModel(Base):
    __tablename__ = "workspaces"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    owner_id = Column(String, nullable=False)
    metadata = Column(JSONB, default={})

# Similar models for Conversation, Message, etc.
```

## Critical Flows

### 1. Input Processing Flow

```mermaid
sequenceDiagram
    participant Client as Input Client
    participant API as FastAPI
    participant Auth as Auth Module
    participant Core as Core Logic
    participant EventBus as Event Bus
    participant Memory as Memory Service

    Client->>API: POST /input with data
    API->>Auth: Validate JWT
    Auth->>API: User context
    API->>Core: Process input
    Core->>EventBus: Publish input event
    Core->>Memory: Store input
    API->>Client: Confirmation response
```

**Implementation Requirements:**

- Validate token before processing input
- Store input in Memory Service regardless of event bus success
- Return immediately after publishing and storing
- Don't wait for subscribers to process the event

### 2. Output Streaming Flow

```mermaid
sequenceDiagram
    participant Client as Output Client
    participant API as FastAPI
    participant Auth as Auth Module
    participant SSE as SSE Manager
    participant EventBus as Event Bus

    Client->>API: GET /output/stream
    API->>Auth: Validate JWT
    Auth->>API: User context
    API->>SSE: Create connection
    SSE->>EventBus: Subscribe
    EventBus-->>SSE: Events
    SSE-->>Client: SSE events (filtered by user_id)
```

**Implementation Steps:**

1. Validate JWT token and extract user_id
2. Create asyncio.Queue for this connection
3. Subscribe queue to event bus
4. Create SSE streaming response with event generator
5. In generator, filter events by user_id
6. Send filtered events to client
7. On client disconnect, unsubscribe queue

**SSE Implementation:**

```python
@app.get("/output/stream")
async def output_stream(request: Request, user: User = Depends(get_current_user)):
    # Create a queue for this connection
    queue = asyncio.Queue()

    # Subscribe to event bus
    event_bus.subscribe(queue)

    async def event_generator():
        try:
            while True:
                # Get event from queue
                event = await queue.get()

                # Filter events for this user
                if event.get("user_id") == user["user_id"]:
                    # Format as SSE
                    yield f"data: {json.dumps(event)}\n\n"

                # Add heartbeat every 30 seconds
                await asyncio.sleep(0.1)  # Prevent CPU hogging
        except asyncio.CancelledError:
            # Client disconnected
            event_bus.unsubscribe(queue)
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

### 3. Memory Storage Flow

```mermaid
sequenceDiagram
    participant Core as Core Logic
    participant MCP as MCP Client
    participant Memory as Memory Service

    Core->>MCP: call_tool("store_input", {user_id, data})
    MCP->>Memory: MCP protocol request
    Memory->>Memory: Store in memory dictionary
    Memory->>MCP: Confirmation response
    MCP->>Core: Result
```

**Memory Service Implementation:**

```python
# memory_service.py
from fastmcp import FastMCP
from typing import Dict, List

# In-memory store
memory_store: Dict[str, List[dict]] = {}

mcp = FastMCP("MemoryService")

@mcp.tool()
async def store_input(user_id: str, input_data: dict) -> dict:
    """Store input data for user"""
    if user_id not in memory_store:
        memory_store[user_id] = []

    # Add timestamp if not present
    if "timestamp" not in input_data:
        input_data["timestamp"] = datetime.now().isoformat()

    memory_store[user_id].append(input_data)
    return {"status": "stored", "user_id": user_id}

@mcp.resource()
async def get_history(user_id: str) -> dict:
    """Get history for user"""
    history = memory_store.get(user_id, [])
    return {"history": history, "user_id": user_id}
```

## File Structure

```
cortex-core/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app and startup
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── input.py           # Input endpoint
│   │   ├── output.py          # Output streaming endpoint
│   │   └── config.py          # Configuration endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── event_bus.py       # Event bus implementation
│   │   └── mcp_client.py      # MCP client implementation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py            # Base models
│   │   ├── api.py             # API models
│   │   └── domain.py          # Domain models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── memory.py          # Memory service client
│   │   └── cognition.py       # Cognition service client
│   └── utils/
│       ├── __init__.py
│       └── auth.py            # Authentication utilities
├── backend/
│   ├── memory_service/
│   │   └── main.py            # Memory service MCP implementation
│   └── cognition_service/
│       └── main.py            # Cognition service MCP implementation
├── tests/
│   ├── __init__.py
│   ├── test_api.py            # API tests
│   ├── test_event_bus.py      # Event bus tests
│   ├── test_mcp_client.py     # MCP client tests
│   └── test_integration.py    # Integration tests
├── .env.example               # Example environment variables
└── requirements.txt           # Project dependencies
```

## Configuration (Environment Variables)

Create a `.env` file with the following variables:

```
# Core configuration
ENV=development
LOG_LEVEL=INFO

# Auth configuration (JWT)
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=RS256

# Auth configuration (Auth0)
AUTH0_DOMAIN=your-auth0-domain.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_API_AUDIENCE=your-api-audience

# Service endpoints
MEMORY_SERVICE_URL=http://localhost:9000
COGNITION_SERVICE_URL=http://localhost:9100

# Database configuration
DATABASE_URL=sqlite:///./cortex_core.db  # Development
# DATABASE_URL=postgresql://user:password@localhost/cortex  # Production
```

## Implementation Priorities

1. **Phase 1: Core API Framework (Must implement first)**

   - FastAPI application setup with endpoint skeletons
   - Basic authentication with JWT (no Auth0 integration yet)
   - In-memory data structures for users, workspaces, conversations
   - Simple event bus implementation

2. **Phase 2: Input/Output Flow (Implement second)**

   - Complete input endpoint with validation
   - SSE implementation for output streaming
   - Event publication and subscription
   - Connection management for SSE

3. **Phase 3: MCP Integration (Implement third)**

   - MCP client implementation
   - Memory service stub implementation
   - Cognition service stub implementation
   - Integration with input processing flow

4. **Phase 4: Configuration Endpoints (Implement fourth)**

   - Workspace management
   - Conversation management
   - User management

5. **Phase 5: Testing & Production Readiness (Implement last)**
   - Integration tests
   - Error handling improvements
   - Logging enhancements
   - Production configuration

## Error Handling Strategy

1. **API Errors**

   - Return appropriate HTTP status codes (400, 401, 404, 500)
   - Include error detail in response body using consistent format:
     ```json
     { "error": { "code": "error_code", "message": "Human readable message" } }
     ```
   - Log all server errors with trace IDs for correlation

2. **MCP Client Errors**

   - Retry transient errors up to 3 times with exponential backoff
   - Return empty results for non-critical failures
   - Log all MCP communication errors

3. **Event Bus Errors**

   - Continue operation if event publication fails
   - Log failed event publications
   - Remove disconnected subscribers automatically

4. **SSE Connection Errors**
   - Handle client disconnections gracefully
   - Clean up resources on disconnection
   - Implement reconnection capability with event ID tracking

## Security Requirements

1. **Authentication**

   - All endpoints except `/auth/login` require valid JWT
   - Tokens must be validated on every request
   - User ID must be extracted and used for data partitioning

2. **Data Access**
   - Users can only access their own data
   - Workspace owners control access to their workspaces
   - No cross-tenant data access

## Development Requirements

1. **Technology Stack**

   - Python 3.10+
   - FastAPI for API layer
   - asyncio for asynchronous processing
   - SQLite for development, PostgreSQL for production

2. **Testing Requirements**
   - All endpoints must have integration tests
   - Event bus must have unit tests
   - MCP client must have mocked tests
   - End-to-end flow must have integration tests

## Important Implementation Notes

1. Never implement shared state between components
2. Always handle asyncio exceptions in tasks
3. Keep the event bus extremely simple
4. Always validate user ID on every request
5. Maintain strict separation between input and output paths
6. Follow incoming-outgoing pattern for all async functions
