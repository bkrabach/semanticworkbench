# Simplified Cortex Architecture Blueprint

## Core Design Philosophy

The simplified Cortex platform follows these core principles:

1. **Minimal Viable Components**: Implement only essential components with clear responsibilities
2. **Simple Communication Patterns**: Use direct communication where possible, event-based only when necessary
3. **Reduced Abstraction Layers**: Fewer layers between components for easier reasoning and debugging
4. **Pragmatic Type Safety**: Strong typing without excessive overhead
5. **Developer-Friendly Interfaces**: Clean, well-documented interfaces between components
6. **Real Implementation First**: Focus on working implementation before excessive abstraction

## Core Components

### 1. API Layer
- FastAPI REST endpoints for client interaction
- WebSocket endpoint for real-time communication
- JWT authentication and authorization
- Request/response models using Pydantic

### 2. Service Layer
- Business logic orchestration
- Core services: User, Workspace, Conversation, Memory
- Clean interfaces that hide implementation details
- Domain model transformations

### 3. Repository Layer
- Database access abstraction 
- SQLAlchemy ORM mapping to domain models
- Transaction management
- Query optimization

### 4. Message Router
- Simple dispatcher with no separate queue
- Direct routing decisions (no complex action types)
- Single pathway for messages
- Integration with LLM service

### 5. LLM Service
- Direct integration with key providers
- Streaming and non-streaming support
- Tool registration and function calling
- Simple abstraction that follows OpenAI API conventions

### 6. WebSocket Manager
- Connection management for real-time updates
- Simple, in-memory connection tracking
- Broadcast and directed messages
- Automatic reconnection handling

### 7. Memory System
- Database-backed context management
- Simple key-value storage with metadata
- Message history with basic filtering
- Extensible for future vector capabilities

### 8. Domain Expert Framework
- HTTP-based client/server protocol
- Tool registration API
- OpenAI-compatible function calling format
- Simplified authentication and discovery

## Core Interfaces

### Message Flow Interface
```python
# Simple message input interface
async def process_message(
    conversation_id: str,
    content: str,
    user_id: str,
    workspace_id: str,
    metadata: dict = None
) -> str:
    """Process a message and return ID of created message"""
```

### WebSocket Interface
```python
# WebSocket connection interface
async def connect(
    user_id: str, 
    resource_type: str, 
    resource_id: str
) -> WebSocketConnection:
    """Establish WebSocket connection for specified resource"""

async def send_message(
    resource_type: str, 
    resource_id: str, 
    event_type: str, 
    data: dict
) -> bool:
    """Send message to all connections for a resource"""
```

### LLM Interface
```python
# LLM service interface
async def complete(
    prompt: str,
    system_prompt: str = None,
    tools: list = None,
    stream: bool = False
) -> Union[str, AsyncIterator[str]]:
    """Get completion from LLM provider"""
```

### Memory Interface
```python
# Memory system interface
async def store_memory(
    workspace_id: str,
    memory_type: str,
    content: Any,
    metadata: dict = None
) -> str:
    """Store memory item and return its ID"""

async def retrieve_memory(
    workspace_id: str,
    memory_type: str = None,
    query: str = None,
    metadata_filter: dict = None,
    limit: int = 20
) -> List[MemoryItem]:
    """Retrieve memory items matching criteria"""
```

### Domain Expert Interface
```python
# Domain expert registration
async def register_expert(
    name: str,
    endpoint: str,
    capabilities: List[str],
    auth_token: str = None
) -> str:
    """Register a domain expert endpoint"""

# Domain expert tool execution
async def execute_tool(
    expert_name: str,
    tool_name: str,
    arguments: dict
) -> dict:
    """Execute a tool on a domain expert"""
```

## Data Flow Diagrams

### Primary Message Flow
```
Client → API Endpoint → Service → Repository (Save) → Message Router
                                                       ↓
Client ← WebSocket ← Repository (Save) ← LLM Service ← Domain Experts (if needed)
```

### Authentication Flow
```
Client → Authentication Endpoint → Token Service → Repository
                                      ↓
Client ← Token ← Token Service
```

### Memory Retrieval Flow
```
Client → API Endpoint → Memory Service → Repository
                                  ↓
Client ← API Response ← Memory Service
```

## Implementation Priorities

1. **Foundation Tier** (Week 1-2)
   - Database schema and repository layer
   - Basic API endpoints for conversations
   - WebSocket implementation for real-time updates
   - Basic LLM service integration

2. **Core Experience Tier** (Week 3-4)
   - Message routing implementation
   - Memory system basic implementation
   - Full conversation flow with LLM integration
   - Authentication and user management

3. **Extension Tier** (Week 5+)
   - Domain expert HTTP protocol
   - Tool registration and execution
   - Enhanced memory capabilities
   - Multi-workspace support

## Technology Choices

1. **Backend Framework**: FastAPI
2. **Database**: PostgreSQL with SQLAlchemy ORM
3. **Real-time**: WebSockets via FastAPI's WebSocket support
4. **Authentication**: JWT tokens with httpx-oauth
5. **LLM Integration**: Direct provider integration (OpenAI, Anthropic)
6. **API Documentation**: OpenAPI via FastAPI
7. **Testing**: pytest with async support
8. **Type Safety**: Pydantic + mypy

## Simplification Benefits

1. **Reduced Code Size**: ~50% fewer lines of code vs. original implementation
2. **Faster Development**: Focus on working features over excessive abstraction
3. **Easier Debugging**: Simpler flow makes issues easier to identify
4. **Better Performance**: Fewer layers of indirection
5. **Maintainable Architecture**: Clear interfaces that preserve architectural boundaries
6. **Extensible Design**: Core abstractions that support future enhancements
7. **Minimal Dependencies**: Fewer external libraries
8. **Clearer Documentation**: Simpler patterns make documentation more effective

## Migration Path

While this is a new implementation, existing Cortex clients can be gradually migrated by:

1. Implementing compatible API endpoints
2. Supporting existing authentication patterns
3. Maintaining WebSocket/SSE communication protocols
4. Preserving data models at the API boundary

## Next Steps

1. Create database schema design
2. Implement core repository layer
3. Add basic API endpoints
4. Develop WebSocket manager
5. Create simple LLM integration
6. Implement message flow between components