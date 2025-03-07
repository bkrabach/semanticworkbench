# Enhancing Cortex Core: Architectural Improvements from Alternative Implementations

## Overview

This document outlines key architectural improvements for our Python/FastAPI-based Cortex Core platform. These concepts are derived from examining alternative implementations but adapted specifically for our existing codebase. The recommendations focus on enhancing modularity, communication patterns, state management, and component interfaces.

## 1. Event-Driven Architecture

### Current Implementation

Our current implementation handles inter-component communication through direct function calls and some ad-hoc event handling in the SSE module. This creates tight coupling between components and makes it difficult to extend functionality.

### Recommended Improvements

#### A. Centralized Event System

Implement a proper event system based on the publisher/subscriber pattern:

```python
class EventSystem:
    def __init__(self):
        self.subscribers = defaultdict(list)
        self.subscription_ids = {}  # Track subscription IDs

    async def publish(self, event_name: str, data: Any) -> None:
        """Publish an event to all subscribers"""
        for callback in self.subscribers.get(event_name, []):
            await callback(event_name, data)

    async def subscribe(self, event_pattern: str, callback: Callable) -> str:
        """Subscribe to events matching a pattern, returns subscription ID"""
        subscription_id = str(uuid.uuid4())
        self.subscribers[event_pattern].append(callback)
        self.subscription_ids[subscription_id] = (event_pattern, callback)
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe using a subscription ID"""
        if subscription_id not in self.subscription_ids:
            return False

        event_pattern, callback = self.subscription_ids[subscription_id]
        self.subscribers[event_pattern].remove(callback)
        del self.subscription_ids[subscription_id]
        return True
```

#### B. Structured Event Types

Define clear event types and payloads for all system events:

```python
class EventTypes:
    # Conversation events
    CONVERSATION_MESSAGE_RECEIVED = "conversation.message.received"
    CONVERSATION_MESSAGE_SENT = "conversation.message.sent"
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_UPDATED = "conversation.updated"

    # Workspace events
    WORKSPACE_CREATED = "workspace.created"
    WORKSPACE_UPDATED = "workspace.updated"

    # Session events
    SESSION_CREATED = "session.created"
    SESSION_EXPIRED = "session.expired"

    # System events
    SYSTEM_ERROR = "system.error"
    INTEGRATION_CONNECTED = "integration.connected"
    INTEGRATION_DISCONNECTED = "integration.disconnected"
```

#### C. Event-Based Component Communication

Update components to use the event system instead of direct calls where appropriate:

```python
# Example of a component publishing an event
async def add_conversation_entry(self, conversation_id: str, entry: dict) -> str:
    # Add entry to database...

    # Publish event for interested components
    await self.event_system.publish(
        EventTypes.CONVERSATION_MESSAGE_RECEIVED,
        {
            "conversation_id": conversation_id,
            "entry": entry
        }
    )

    return entry_id
```

## 2. Enhanced Context Management

### Current Implementation

Our context data is scattered across multiple components with no centralized management. The interfaces between memory systems, conversations, and the router are not clearly defined.

### Recommended Improvements

#### A. Dedicated Context Manager

Implement a `ContextManager` to centralize conversation context handling:

```python
class ContextManager:
    def __init__(self, memory_system: MemorySystemInterface):
        self.memory_system = memory_system
        self.CONTEXT_CACHE_PREFIX = 'context:'
        self.CONTEXT_CACHE_TTL = 3600  # 1 hour in seconds

    async def get_context(self, session_id: str, workspace_id: str, query: Optional[str] = None) -> Context:
        """Get context relevant to a specific query or task"""
        # Try cache first
        # Fall back to memory system
        # Return consolidated context object

    async def update_context(self, session_id: str, workspace_id: str, context_update: ContextUpdate) -> None:
        """Update the context with new information"""
        # Apply update to local context
        # Persist to memory system
        # Update cache

    async def prune_context(self, session_id: str, workspace_id: str, older_than: Optional[datetime] = None) -> None:
        """Clear outdated or irrelevant context"""
        # Remove old entries based on date or other criteria
```

#### B. Context Data Structures

Define clear models for context data and operations:

```python
class Message(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Entity(BaseModel):
    id: str
    type: str
    name: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class Context(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)

class ContextUpdate(BaseModel):
    add_messages: Optional[List[Message]] = None
    remove_message_ids: Optional[List[str]] = None
    add_entities: Optional[List[Entity]] = None
    remove_entity_ids: Optional[List[str]] = None
    update_metadata: Optional[Dict[str, Any]] = None
```

## 3. Input/Output Modality Abstraction

### Current Implementation

Our system has limited abstraction for different input/output modalities, mostly focused on chat conversations.

### Recommended Improvements

#### A. Modality Interface

Define a clear interface for different modalities:

```python
class ModalityType(str, Enum):
    CHAT = "chat"
    VOICE = "voice"
    CANVAS = "canvas"
    CLI = "cli"
    EMAIL = "email"
    SMS = "sms"
    NOTIFICATION = "notification"
    CUSTOM = "custom"

class ModalityCapabilities(BaseModel):
    supported_content_types: List[str]
    supports_prioritization: bool
    supports_interruption: bool
    supports_multiple_destinations: bool

class ModalityInterface(Protocol):
    """Interface for modality components that handle specific I/O formats"""

    async def get_capabilities(self) -> ModalityCapabilities:
        """Get the capabilities of this modality"""
        ...
```

#### B. Input Modality Implementation

Define an interface for input modalities:

```python
class InputModalityHandler(Protocol):
    """Handler for input from a specific modality"""

    async def handle_input(self, input_data: Any, session_id: str, metadata: Dict[str, Any] = None) -> None:
        """Process input from this modality"""
        ...

    async def get_capabilities(self) -> ModalityCapabilities:
        """Get the capabilities of this modality"""
        ...
```

#### C. Output Modality Implementation

Define an interface for output modalities:

```python
class OutputModalityHandler(Protocol):
    """Handler for output to a specific modality"""

    async def handle_output(self, output_data: Any, session_id: str, priority: str = "normal", metadata: Dict[str, Any] = None) -> None:
        """Send output via this modality"""
        ...

    async def get_capabilities(self) -> ModalityCapabilities:
        """Get the capabilities of this modality"""
        ...
```

#### D. Modality Manager

Implement a central manager for all modalities:

```python
class ModalityManager:
    def __init__(self, event_system: EventSystem):
        self.event_system = event_system
        self.input_handlers: Dict[str, InputModalityHandler] = {}
        self.output_handlers: Dict[str, OutputModalityHandler] = {}

    def register_input_modality(self, modality_type: str, handler: InputModalityHandler) -> None:
        """Register a new input modality handler"""
        self.input_handlers[modality_type] = handler

    def register_output_modality(self, modality_type: str, handler: OutputModalityHandler) -> None:
        """Register a new output modality handler"""
        self.output_handlers[modality_type] = handler

    async def process_input(self, modality_type: str, input_data: Any, session_id: str, metadata: Dict[str, Any] = None) -> None:
        """Process input from a specific modality"""

    async def send_output(self, modality_type: str, output_data: Any, session_id: str, priority: str = "normal", metadata: Dict[str, Any] = None) -> None:
        """Send output to a specific modality"""

    async def broadcast_output(self, output_data: Any, session_id: str, priority: str = "normal", metadata: Dict[str, Any] = None) -> None:
        """Send output to all suitable modalities"""

    def get_best_output_modality(self, content_type: str, session_preferences: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Find the best modality for a specific content type"""
```

## 4. Enhanced Router Implementation

### Current Implementation

Our current `CortexRouter` has a rigid input/output flow that makes it difficult to extend with new capabilities or integrate with external systems.

### Recommended Improvements

#### A. Clearer Request/Response Models

Define better models for internal requests and responses:

```python
class Request(BaseModel):
    id: str
    type: str
    session_id: str
    modality: str
    content: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

class Response(BaseModel):
    request_id: str
    status: Literal["success", "error", "pending"]
    content: Any
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None
```

#### B. Request Handler Interface

Define a handler interface for processing requests:

```python
class RequestHandler(Protocol):
    """Interface for components that can handle requests"""

    async def handle_request(self, request: Request) -> Response:
        """Process a request and produce a response"""
        ...

    def can_handle(self, request: Request) -> bool:
        """Check if this handler can process the given request"""
        ...
```

#### C. Improved Dispatcher

Implement a more flexible dispatcher:

```python
class Dispatcher:
    def __init__(self, context_manager: ContextManager, event_system: EventSystem):
        self.context_manager = context_manager
        self.event_system = event_system
        self.handlers: Dict[str, List[RequestHandler]] = {}
        self.in_progress_requests: Dict[str, Any] = {}

    def register_handler(self, request_type: str, handler: RequestHandler) -> None:
        """Register a handler for a specific request type"""
        if request_type not in self.handlers:
            self.handlers[request_type] = []
        self.handlers[request_type].append(handler)

    async def dispatch(self, request: Request) -> Response:
        """Dispatch a request to the appropriate handler"""
        # Find eligible handlers
        # Delegate to first handler that can handle the request
        # Track in-progress requests
        # Update context with request/response
        # Return response

    async def cancel_request(self, request_id: str) -> bool:
        """Cancel an in-progress request"""
        # Remove from in-progress requests
        # Return cancellation success status
```

## 5. Enhanced Integration Hub

### Current Implementation

Our integration with external systems is limited and lacks standardization.

### Recommended Improvements

#### A. Integration Interface

Define a clear model for integrations:

```python
class IntegrationType(str, Enum):
    VSCODE = "vscode"
    M365 = "m365"
    BROWSER = "browser"
    OTHER = "other"

class ConnectionProtocol(str, Enum):
    MCP = "mcp"
    REST = "rest"
    WEBSOCKET = "websocket"

class ConnectionDetails(BaseModel):
    protocol: ConnectionProtocol
    endpoint: str
    auth_token: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Integration(BaseModel):
    id: str
    name: str
    type: IntegrationType
    connection_details: ConnectionDetails
    capabilities: List[str] = Field(default_factory=list)
    status: Literal["connected", "disconnected", "error"] = "disconnected"
    last_active: datetime = Field(default_factory=datetime.now)
```

#### B. Integration Hub Implementation

Create a hub for managing all integrations:

```python
class IntegrationHub:
    def __init__(self, event_system: EventSystem):
        self.event_system = event_system
        self.integrations: Dict[str, Integration] = {}
        self.clients: Dict[str, Any] = {}  # Clients for each integration

    async def initialize(self) -> None:
        """Initialize the integration hub"""
        # Load stored integrations
        # Setup MCP server if needed

    async def register_integration(self, integration_data: dict) -> Integration:
        """Register a new integration"""
        # Create integration record
        # Store in database
        # Add to in-memory registry
        # Emit event

    async def get_integration(self, integration_id: str) -> Optional[Integration]:
        """Get integration by ID"""

    async def forward_request(self, integration_id: str, request: dict) -> Any:
        """Forward a request to an integration"""
        # Find integration
        # Forward based on protocol
        # Return response

    async def handle_external_request(self, integration_id: str, request: dict) -> Any:
        """Handle request from an external integration"""
        # Validate integration exists
        # Update last active timestamp
        # Emit event for request
        # Return response

    async def list_integrations(self) -> List[Integration]:
        """List all registered integrations"""
```

## 6. Domain Expert Interface

### Current Implementation

We lack a standardized way to delegate tasks to specialized domain experts.

### Recommended Improvements

#### A. Domain Expert Models

Define clear models for expert tasks:

```python
class TaskConstraints(BaseModel):
    deadline: Optional[datetime] = None
    max_tokens: Optional[int] = None
    priority_level: Literal["high", "normal", "low"] = "normal"
    max_retries: Optional[int] = None

class ExpertTask(BaseModel):
    id: Optional[str] = None
    type: str
    content: Any
    context: Optional[Any] = None
    constraints: Optional[TaskConstraints] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TaskStatus(BaseModel):
    id: str
    state: Literal["queued", "processing", "completed", "failed", "cancelled"]
    progress: Optional[int] = None  # 0-100
    estimated_completion_time: Optional[datetime] = None
    status_message: Optional[str] = None

class ExpertTaskResult(BaseModel):
    task_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None

class ExpertCapabilities(BaseModel):
    supported_task_types: List[str]
    supports_async_tasks: bool
    supports_cancellation: bool
    supports_progress: bool
    max_concurrent_tasks: Optional[int] = None
```

#### B. Domain Expert Interface

Create an interface for domain expert handlers:

```python
class ExpertHandler(Protocol):
    """Interface for domain expert handlers"""

    async def handle_task(self, task: ExpertTask) -> str:
        """Handle a task and return task ID"""
        ...

    async def check_status(self, task_id: str) -> TaskStatus:
        """Check status of a task"""
        ...

    async def get_result(self, task_id: str) -> ExpertTaskResult:
        """Get result of a completed task"""
        ...

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        ...

    def get_capabilities(self) -> ExpertCapabilities:
        """Get capabilities of this expert"""
        ...
```

#### C. Domain Expert Manager

Implement a manager for all domain experts:

```python
class DomainExpertManager:
    def __init__(self, event_system: EventSystem):
        self.event_system = event_system
        self.experts: Dict[str, ExpertHandler] = {}
        self.task_registry: Dict[str, dict] = {}

    def register_expert(self, expert_type: str, handler: ExpertHandler) -> None:
        """Register a new domain expert"""
        self.experts[expert_type] = handler

    async def delegate_task(self, expert_type: str, task: ExpertTask) -> str:
        """Delegate a task to a domain expert"""
        # Validate expert exists
        # Submit task
        # Register task
        # Monitor task status
        # Return task ID

    async def check_task_status(self, task_id: str) -> TaskStatus:
        """Check status of a delegated task"""

    async def get_task_result(self, task_id: str) -> ExpertTaskResult:
        """Get result of a completed task"""

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel an in-progress task"""

    async def list_experts(self) -> List[dict]:
        """List all registered domain experts"""
```

## 7. Improved Session Management

### Current Implementation

Our session management is basic and lacks configuration options and proper state tracking.

### Recommended Improvements

#### A. Enhanced Session Model

Define a more complete session model:

```python
class SessionConfig(BaseModel):
    timeout_minutes: int = 60
    default_workspace_id: Optional[str] = None
    preferred_modalities: List[str] = Field(default_factory=lambda: ["chat"])

class Session(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    last_active_at: datetime
    active_workspace_id: str
    config: SessionConfig
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### B. Session Manager Implementation

Create a more powerful session manager:

```python
class SessionManager:
    def __init__(self, event_system: EventSystem):
        self.event_system = event_system
        self.DEFAULT_TIMEOUT_MINUTES = 60
        self.SESSION_CACHE_PREFIX = 'session:'

    async def create_session(self, user_id: str, config: Optional[Dict[str, Any]] = None) -> Session:
        """Create a new user session"""
        # Generate session ID
        # Create default workspace if needed
        # Create session with config
        # Store in database
        # Cache session
        # Emit event
        # Return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve an existing session"""
        # Try cache first
        # Fall back to database
        # Return session if found

    async def get_active_sessions_for_user(self, user_id: str) -> List[Session]:
        """Get all active sessions for a user"""

    async def terminate_session(self, session_id: str) -> bool:
        """Terminate an existing session"""

    async def validate_session(self, session_id: str) -> bool:
        """Validate if a session is active and valid"""

    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> Session:
        """Update session metadata or configuration"""

    async def set_active_workspace(self, session_id: str, workspace_id: str) -> Session:
        """Set the active workspace for a session"""
```

## 8. Real-Time Communication Enhancements

### Current Implementation

Our SSE implementation has limitations and potential race conditions.

### Recommended Improvements

#### A. Enhanced SSE Implementation

Improve the SSE implementation to be more robust:

```python
class SSEManager:
    def __init__(self, event_system: EventSystem):
        self.event_system = event_system
        self.active_connections = {
            "global": [],
            "users": {},
            "workspaces": {},
            "conversations": {},
        }

    async def add_connection(self, channel_type: str, channel_id: str, queue: asyncio.Queue, metadata: Dict[str, Any] = None) -> str:
        """Add a new SSE connection"""
        # Generate connection ID
        # Store connection info
        # Return connection ID

    async def remove_connection(self, connection_id: str) -> bool:
        """Remove an SSE connection"""

    async def broadcast_to_channel(self, channel_type: str, channel_id: str, event_type: str, data: Any) -> int:
        """Broadcast an event to all connections in a channel"""
        # Find all connections for this channel
        # Send event to each connection
        # Return count of messages sent

    async def send_event_to_conversation(self, conversation_id: str, event_type: str, data: Any) -> int:
        """Send an event to all connections for a specific conversation"""

    async def send_event_to_workspace(self, workspace_id: str, event_type: str, data: Any) -> int:
        """Send an event to all connections for a specific workspace"""

    async def send_event_to_user(self, user_id: str, event_type: str, data: Any) -> int:
        """Send an event to all connections for a specific user"""

    async def send_global_event(self, event_type: str, data: Any) -> int:
        """Send an event to all global connections"""
```

#### B. WebSocket Support

Consider adding WebSocket support for bidirectional communication:

```python
class WebSocketManager:
    def __init__(self, event_system: EventSystem):
        self.event_system = event_system
        self.active_connections = {}

    async def handle_connection(self, websocket: WebSocket, user_id: str) -> None:
        """Handle a new WebSocket connection"""
        # Accept the connection
        # Register event handlers
        # Setup message receiver
        # Handle disconnection

    async def send_message(self, connection_id: str, message: dict) -> bool:
        """Send a message to a specific connection"""

    async def broadcast(self, room: str, message: dict) -> int:
        """Broadcast a message to all connections in a room"""

    async def join_room(self, connection_id: str, room: str) -> None:
        """Join a room"""

    async def leave_room(self, connection_id: str, room: str) -> None:
        """Leave a room"""
```

## 9. Infrastructure Enhancements

### Current Implementation

Some of our infrastructure components could be more robust.

### Recommended Improvements

#### A. Improved Redis Cache Client

Enhance the Redis client for better resilience:

```python
class RedisClient:
    def __init__(self):
        self.redis = None
        self.memory_cache = {}
        self.using_memory_fallback = False

    async def connect(self, config: dict) -> None:
        """Connect to Redis"""
        # Try to connect
        # Fall back to memory cache on failure

    async def disconnect(self) -> None:
        """Disconnect from Redis"""

    async def set(self, key: str, value: str, ex: Optional[int] = None, px: Optional[int] = None) -> str:
        """Set a key-value pair"""
        # Use Redis or memory fallback

    async def get(self, key: str) -> Optional[str]:
        """Get a value from a key"""

    async def delete(self, key: str) -> int:
        """Delete a key"""

    async def exists(self, key: str) -> int:
        """Check if a key exists"""

    async def expire(self, key: str, seconds: int) -> int:
        """Set expiry time on a key"""

    async def ttl(self, key: str) -> int:
        """Get TTL for a key"""
```

#### B. Enhanced Error Handling

Implement a more comprehensive error handling system:

```python
class ErrorManager:
    def __init__(self, event_system: EventSystem):
        self.event_system = event_system

    async def handle_error(self, context: str, error: Exception, metadata: Dict[str, Any] = None) -> str:
        """Handle an error and return error ID"""
        # Generate error ID
        # Log error
        # Store error details
        # Emit error event
        # Return error ID

    async def get_error(self, error_id: str) -> Optional[dict]:
        """Get error details by ID"""

    async def list_recent_errors(self, limit: int = 10) -> List[dict]:
        """List recent errors"""
```

## Implementation Strategy

To implement these improvements effectively:

1. **Start with the Event System**: This is a foundation for other improvements.
2. **Implement Context Management**: Next, establish proper context handling.
3. **Enhance the Router/Dispatcher**: Improve request handling and routing.
4. **Add Modality Abstraction**: Implement the modality interfaces.
5. **Improve Integration Hub**: Enhance external system integration.
6. **Implement Domain Expert Interface**: Add support for specialized processing.
7. **Enhance Session Management**: Improve user session handling.
8. **Improve Real-Time Communication**: Enhance SSE and consider WebSockets.

## Conclusion

These architectural improvements will make the Cortex Core platform more modular, extensible, and robust. By focusing on clearly defined interfaces, event-driven communication, and proper abstraction layers, we can address the current limitations while maintaining the advantages of our FastAPI-based implementation.

The changes should be implemented incrementally, with careful testing at each stage to ensure backward compatibility and maintain system stability. Once completed, these improvements will provide a solid foundation for future feature additions and integrations.
