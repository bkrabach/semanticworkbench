# Cortex Core Components

This document details the core components and interfaces of the Cortex Core system.

## Table of Contents

- [Session Manager](#session-manager)
- [Dispatcher](#dispatcher)
- [Cortex Router](#cortex-router)
- [Context Manager](#context-manager)
- [Integration Hub](#integration-hub)
- [Workspace Manager](#workspace-manager)
- [Security Manager](#security-manager)
- [Memory System Interface](#memory-system-interface)
- [Domain Expert Interface](#domain-expert-interface)

## Session Manager

The Session Manager is responsible for creating, validating, and managing user sessions.

### Responsibilities

- User session creation, validation, and termination
- Session state persistence
- Association of sessions with workspaces
- Session-specific configuration management

### Implementation Details

```python
class Session(Base):
    """Session model"""
    __tablename__ = "sessions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    active_workspace_id = Column(String(36), nullable=False)
    config = Column(Text, default="{}")  # Stored as JSON string
    meta_data = Column(Text, default="{}")  # Stored as JSON string
    # Relationships
    user = relationship("User", back_populates="sessions")
```

### Interface

```python
class SessionManager:
    async def create_session(self, user_id: str, workspace_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Session:
        """Create a new user session"""
        pass

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get an existing session"""
        pass

    async def terminate_session(self, session_id: str) -> bool:
        """Terminate an existing session"""
        pass

    async def validate_session(self, session_id: str) -> bool:
        """Check if a session is active and valid"""
        pass

    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> Optional[Session]:
        """Update session metadata or configuration"""
        pass
```

## Dispatcher

The Dispatcher routes incoming requests to appropriate handlers based on the request type.

### Responsibilities

- Route incoming requests to appropriate handlers
- Prioritize and queue requests when necessary
- Invoke domain experts for specialized tasks
- Coordinate between different processing pathways

### Implementation Details

The Dispatcher is implemented as a core component of the FastAPI application, using middleware and routing mechanisms to handle request processing.

```python
# Pseudocode for dispatcher functionality
@app.middleware("http")
async def dispatch_middleware(request: Request, call_next):
    """Dispatch requests to appropriate handlers"""
    # Determine request type and route to appropriate handler
    # Prioritize requests based on context and user needs
    # Delegate specialized tasks to domain experts
    response = await call_next(request)
    return response
```

## Cortex Router

The Cortex Router is responsible for determining how to handle incoming messages from various input channels.

### Responsibilities

- Analyze incoming messages to determine the appropriate action
- Provide immediate feedback about processing status
- Prioritize messages based on content and context
- Decide whether to respond directly, retrieve memory, or delegate to a specialized system
- Coordinate between conversational flows and more complex processing paths

### Implementation Details

```python
class RouterRequest(BaseModel):
    """Input request to be routed"""
    content: str
    conversation_id: str
    workspace_id: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime

class RoutingDecision(BaseModel):
    """Routing decision made by the router"""
    action_type: str  # "respond", "process", "retrieve_memory", "delegate", "ignore"
    priority: int = 1  # 1 (lowest) to 5 (highest)
    target_system: Optional[str] = None
    status_message: Optional[str] = None
    metadata: Dict[str, Any] = {}

class CortexRouterInterface(ABC):
    """Interface for the Cortex Router"""
    
    @abstractmethod
    async def route(self, request: RouterRequest) -> RoutingDecision:
        """Determine how to route an incoming message"""
        pass
    
    @abstractmethod
    async def process_feedback(self, request_id: str, success: bool, metadata: Dict[str, Any]) -> None:
        """Process feedback about a previous routing decision"""
        pass
```

### Integration

The Cortex Router is integrated into the conversation flow, intercepting messages before they reach their final destination:

1. User sends a message through a conversation endpoint
2. Message is passed to the Router for analysis
3. Router determines the appropriate action and priority
4. Status updates are sent to the user while processing
5. The appropriate system handles the message based on the routing decision
6. Results are returned to the user through the original conversation channel

## Context Manager

The Context Manager interfaces with the memory system to retrieve and update the context for processing requests.

### Responsibilities

- Retrieve relevant context for processing requests
- Update the memory state with new information
- Maintain an in-memory cache of recent context for performance

### Interface

```python
class ContextManager:
    async def get_context(self, session_id: str, workspace_id: str, query: Optional[str] = None) -> Context:
        """Get context relevant to a specific query or task"""
        pass

    async def update_context(self, session_id: str, workspace_id: str, context_update: ContextUpdate) -> None:
        """Update the context with new information"""
        pass

    async def prune_context(self, session_id: str, workspace_id: str, older_than: Optional[datetime] = None) -> None:
        """Clear outdated or irrelevant context"""
        pass
```

## Integration Hub

The Integration Hub facilitates communication with external services and tools, managing MCP client/server interactions.

### Responsibilities

- Implement the MCP client/server protocol
- Manage connections to external tools and services
- Route data between the core system and external components
- Handle protocol translation when necessary

### Implementation Details

```python
class IntegrationHub:
    async def register_integration(self, integration: Integration) -> None:
        """Register a new external integration"""
        pass

    async def get_integration(self, integration_id: str) -> Optional[Integration]:
        """Get an integration by ID"""
        pass

    async def forward_request(self, integration_id: str, request: Any) -> Any:
        """Forward a request to an external integration"""
        pass

    async def handle_external_request(self, integration_id: str, request: Any) -> Any:
        """Handle incoming requests from external integrations"""
        pass

    async def list_integrations(self) -> List[Integration]:
        """List all active integrations"""
        pass
```

## Workspace Manager

The Workspace Manager handles the creation, retrieval, and organization of workspaces and associated conversations.

### Responsibilities

- Create and manage workspaces for organizing user interactions
- Handle creation and retrieval of conversations within workspaces
- Transform raw activity logs into modality-specific conversation views
- Expose APIs for workspace and conversation management

### Implementation Details

```python
class Workspace(Base):
    """Workspace model"""
    __tablename__ = "workspaces"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    config = Column(Text, default="{}")  # Stored as JSON string
    meta_data = Column(Text, default="{}")  # Stored as JSON string
    # Relationships
    user = relationship("User", back_populates="workspaces")
    conversations = relationship("Conversation", back_populates="workspace", cascade="all, delete-orphan")
    memory_items = relationship("MemoryItem", back_populates="workspace", cascade="all, delete-orphan")
    workspace_sharings = relationship("WorkspaceSharing", back_populates="workspace", cascade="all, delete-orphan")

class Conversation(Base):
    """Conversation model"""
    __tablename__ = "conversations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    modality = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    entries = Column(Text, default="[]")  # Stored as JSON array string
    meta_data = Column(Text, default="{}")  # Stored as JSON string
    # Relationships
    workspace = relationship("Workspace", back_populates="conversations")
```

### Interface

```python
class WorkspaceManager:
    async def create_workspace(self, user_id: str, name: str, config: Optional[Dict[str, Any]] = None) -> Workspace:
        """Create a new workspace"""
        pass

    async def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get workspace by ID"""
        pass

    async def list_workspaces(self, user_id: str) -> List[Workspace]:
        """List workspaces for a user"""
        pass

    async def create_conversation(self, workspace_id: str, modality: str, title: Optional[str] = None) -> Conversation:
        """Create a conversation in a workspace"""
        pass

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        pass

    async def list_conversations(self, workspace_id: str, filter: Optional[Dict[str, Any]] = None) -> List[Conversation]:
        """List conversations in a workspace"""
        pass

    async def add_conversation_entry(self, conversation_id: str, entry: Dict[str, Any]) -> None:
        """Add an entry to a conversation"""
        pass
```

## Security Manager

The Security Manager handles authentication, data encryption, and authorization processes.

### Responsibilities

- User authentication and authorization
- API key and access token management
- Data encryption for sensitive information
- Access control policy enforcement

### Implementation Details

```python
class SecurityManager:
    """Security Manager implementation"""
    def __init__(self):
        # Derive encryption key from the provided key
        key_bytes = hashlib.sha256(settings.security.encryption_key.encode()).digest()
        self.fernet = Fernet(base64.urlsafe_b64encode(key_bytes))

    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise

    def stringify_json(self, data: Any) -> str:
        """Convert object to JSON string"""
        try:
            return json.dumps(data)
        except Exception as e:
            logger.error(f"JSON stringify failed: {str(e)}")
            return "{}"

    def parse_json(self, json_str: str) -> Any:
        """Parse JSON string to object"""
        try:
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"JSON parse failed: {str(e)}")
            return {}

    async def check_access(self, user_id: str, resource: str, action: str) -> bool:
        """Check if a user has access to a resource"""
        # Implementation details
        pass
```

### Authentication Functions

```python
def generate_jwt_token(data: TokenData, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a JWT token"""
    to_encode = data.model_dump()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=settings.security.token_expiry_seconds)

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, settings.security.jwt_secret, algorithm="HS256")

def verify_jwt_token(token: str) -> Optional[TokenData]:
    """Verify a JWT token"""
    try:
        payload = jwt.decode(token, settings.security.jwt_secret, algorithms=["HS256"])

        user_id = payload.get("user_id")
        if user_id is None:
            return None

        scopes = payload.get("scopes", [])

        return TokenData(user_id=user_id, scopes=scopes)

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid token")
        return None
```

## Memory System Interface

The Memory System Interface defines the contract for memory systems (Whiteboard, JAKE, etc.).

### Interface Definition

```python
class RetentionPolicy(BaseModel):
    """Retention policy for memory items"""
    default_ttl_days: int
    type_specific_ttl: Optional[Dict[str, int]] = None  # type -> days
    max_items: Optional[int] = None

class MemoryConfig(BaseModel):
    """Memory system configuration"""
    storage_type: str  # "in_memory" or "persistent"
    retention_policy: Optional[RetentionPolicy] = None
    encryption_enabled: bool = False

class MemoryItem(BaseModel):
    """Memory item model"""
    id: Optional[str] = None
    type: str  # "message", "entity", "file", "event"
    content: Any
    metadata: Dict[str, Any] = {}
    timestamp: datetime
    expires_at: Optional[datetime] = None

class MemoryQuery(BaseModel):
    """Memory query parameters"""
    types: Optional[List[str]] = None
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None
    content_query: Optional[str] = None
    metadata_filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None
    include_expired: bool = False

class SynthesizedMemory(BaseModel):
    """Synthesized memory result"""
    raw_items: List[MemoryItem]
    summary: str
    entities: Dict[str, Any]
    relevance_score: float

class MemorySystemInterface(ABC):
    """
    Interface for memory systems in Cortex Core
    """
    @abstractmethod
    async def initialize(self, config: MemoryConfig) -> None:
        """Initialize the memory system"""
        pass

    @abstractmethod
    async def store(self, workspace_id: str, item: MemoryItem) -> str:
        """Store a memory item"""
        pass

    @abstractmethod
    async def retrieve(self, workspace_id: str, query: MemoryQuery) -> List[MemoryItem]:
        """Retrieve memory items based on a query"""
        pass

    @abstractmethod
    async def update(self, workspace_id: str, item_id: str, updates: MemoryItem) -> None:
        """Update an existing memory item"""
        pass

    @abstractmethod
    async def delete(self, workspace_id: str, item_id: str) -> None:
        """Delete a memory item"""
        pass

    @abstractmethod
    async def synthesize_context(self, workspace_id: str, query: MemoryQuery) -> SynthesizedMemory:
        """Generate a synthetic/enriched context from raw memory"""
        pass
```

## Domain Expert Interface

The Domain Expert Interface defines the contract for domain expert entities.

### Interface Definition

```python
class ExpertTaskConstraints(BaseModel):
    """Constraints for expert tasks"""
    deadline: Optional[datetime] = None
    max_tokens: Optional[int] = None
    priority_level: Literal["high", "normal", "low"] = "normal"
    max_retries: Optional[int] = None

class ExpertTask(BaseModel):
    """Task for domain expert"""
    id: Optional[str] = None
    type: str
    content: Any
    context: Optional[Any] = None
    constraints: Optional[ExpertTaskConstraints] = None
    metadata: Dict[str, Any] = {}

class TaskStatus(BaseModel):
    """Status of a domain expert task"""
    id: str
    state: Literal["queued", "processing", "completed", "failed", "cancelled"]
    progress: Optional[int] = None  # 0-100
    estimated_completion_time: Optional[datetime] = None
    status_message: Optional[str] = None

class ExpertTaskResult(BaseModel):
    """Result from a domain expert task"""
    task_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None

class ExpertCapabilities(BaseModel):
    """Capabilities of a domain expert"""
    supported_task_types: List[str]
    supports_async_tasks: bool
    supports_cancellation: bool
    supports_progress: bool
    max_concurrent_tasks: Optional[int] = None

class DomainExpertInterface(ABC):
    """
    Interface for domain expert entities in Cortex Core
    """
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the domain expert"""
        pass

    @abstractmethod
    async def handle_task(self, task: ExpertTask) -> str:
        """Handle a domain expert task"""
        pass

    @abstractmethod
    async def check_status(self, task_id: str) -> TaskStatus:
        """Check the status of a task"""
        pass

    @abstractmethod
    async def get_result(self, task_id: str) -> ExpertTaskResult:
        """Get the result of a completed task"""
        pass

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel an in-progress task"""
        pass

    @abstractmethod
    def get_capabilities(self) -> ExpertCapabilities:
        """Get the capabilities of this domain expert"""
        pass
```

This document provides an overview of the key components and interfaces that make up the Cortex Core system. Each component is designed to be modular and extensible, allowing for easy replacement or enhancement as the system evolves.
