# Revised Simplified Cortex Architecture Blueprint

## Core Design Philosophy

The simplified Cortex platform follows these core principles:

1. **Minimal Viable Components**: Implement only essential components with clear responsibilities
2. **Focused Implementation**: Simpler implementations of core architectural patterns
3. **Reduced Abstraction Layers**: Fewer layers between components for easier reasoning and debugging
4. **Pragmatic Type Safety**: Strong typing without excessive overhead
5. **Developer-Friendly Interfaces**: Clean, well-documented interfaces between components
6. **Real Implementation First**: Focus on working implementation before excessive abstraction

## Core Architectural Patterns

We will maintain several key architectural patterns from the original Cortex design:

1. **MCP Client/Server Protocol**: Use Model Context Protocol for all backend service communication
2. **Server-Sent Events (SSE)**: Use SSE for real-time client connections
3. **Separate Input/Output Channels**: Maintain distinct input receivers and output publishers
4. **Event-Based Communication**: Simplified event system for inter-component messaging
5. **Domain-Driven Repository Pattern**: Three-layer model approach (DB, Domain, API)

## Core Components

### 1. API Layer
- FastAPI REST endpoints for client interaction
- Server-Sent Events (SSE) endpoint for real-time updates
- JWT authentication and authorization
- Request/response models using Pydantic

### 2. Input/Output Channels
- **Input Receivers**: Process inputs from various sources (conversations, voice, webhooks)
- **Output Publishers**: Deliver messages to appropriate destinations
- Clean separation between input and output flows
- Channel-specific formatting and protocol handling

### 3. Service Layer
- Business logic orchestration
- Core services: User, Workspace, Conversation, Memory
- Clean interfaces that hide implementation details
- Domain model transformations

### 4. Repository Layer
- Database access abstraction 
- SQLAlchemy ORM mapping to domain models
- Transaction management
- Query optimization

### 5. Message Router
- Simplified queue-based message processor
- Input message handling with appropriate routing
- Integration with other components via MCP
- Support for various action types

### 6. Event System
- Simplified topic-based event system
- Publish/subscribe pattern for loose coupling
- Consistent event payloads
- No wildcard pattern matching complexity

### 7. SSE Connection Manager
- Connection lifecycle management
- Resource-based client subscriptions
- Efficient event delivery
- Simple heartbeat mechanism

### 8. MCP Integration Hub
- Central hub for MCP-based communication
- Simplified connection management
- Domain expert discovery and registration
- Tool execution via MCP protocol

### 9. LLM Service
- Direct integration with key providers
- Streaming and non-streaming support
- Tool registration and function calling
- OpenAI-compatible interface

### 10. Memory System
- MCP-based memory service
- Database-backed context management
- Message history with basic filtering
- Extensible for future vector capabilities

## Core Interfaces

### Input Receiver Interface
```python
class InputReceiverInterface(Protocol):
    """Interface for components that receive inputs from external sources"""
    
    async def receive_input(self, **kwargs) -> bool:
        """Process incoming input and forward it to the Router"""
        ...
    
    def get_channel_id(self) -> str:
        """Get the unique ID for this input channel"""
        ...
    
    def get_channel_type(self) -> ChannelType:
        """Get the type of this input channel"""
        ...
```

### Output Publisher Interface
```python
class OutputPublisherInterface(Protocol):
    """Interface for components that send outputs to external destinations"""
    
    async def publish(self, message: OutputMessage) -> bool:
        """Publish a message to this output channel"""
        ...
    
    def get_channel_id(self) -> str:
        """Get the unique ID for this output channel"""
        ...
    
    def get_channel_type(self) -> ChannelType:
        """Get the type of this output channel"""
        ...
```

### Router Interface
```python
class RouterInterface(Protocol):
    """Interface for the message router"""
    
    async def process_input(self, message: InputMessage) -> bool:
        """Process an input message"""
        ...
        
    async def cleanup(self) -> None:
        """Clean up resources when shutting down"""
        ...
```

### Event System Interface
```python
class EventSystemInterface(Protocol):
    """Interface for the event system"""
    
    async def publish(self, event_type: str, data: Dict[str, Any], source: str) -> None:
        """Publish an event to all subscribers"""
        ...
    
    async def subscribe(self, event_type: str, callback: EventCallback) -> str:
        """Subscribe to events of a specific type"""
        ...
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        ...
```

### SSE Connection Manager Interface
```python
class SSEConnectionManager(Protocol):
    """Interface for managing SSE connections"""
    
    async def register_connection(
        self, channel_type: str, resource_id: str, user_id: str
    ) -> Tuple[asyncio.Queue, str]:
        """Register an SSE connection"""
        ...
        
    async def remove_connection(
        self, channel_type: str, resource_id: str, connection_id: str
    ) -> None:
        """Remove an SSE connection"""
        ...
        
    async def send_event(
        self, channel_type: str, resource_id: str, event_type: str, data: Dict[str, Any]
    ) -> None:
        """Send an event to a specific channel"""
        ...
```

### MCP Client Interface
```python
class McpClientInterface(Protocol):
    """Interface for MCP client operations"""
    
    async def connect(self) -> None:
        """Connect to the MCP server"""
        ...
        
    async def close(self) -> None:
        """Close the MCP connection"""
        ...
        
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools from the MCP server"""
        ...
        
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        ...
```

### LLM Service Interface
```python
class LlmServiceInterface(Protocol):
    """Interface for LLM service operations"""
    
    async def get_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Get a completion from an LLM"""
        ...
        
    async def get_streaming_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Get a streaming completion from an LLM"""
        ...
```

### Memory System Interface
```python
class MemorySystemInterface(Protocol):
    """Interface for memory system operations"""
    
    async def store(self, workspace_id: str, item: MemoryItem) -> str:
        """Store a memory item"""
        ...
        
    async def retrieve(self, workspace_id: str, query: MemoryQuery) -> List[MemoryItem]:
        """Retrieve memory items based on a query"""
        ...
        
    async def update(self, workspace_id: str, item_id: str, updates: MemoryItem) -> None:
        """Update an existing memory item"""
        ...
        
    async def delete(self, workspace_id: str, item_id: str) -> None:
        """Delete a memory item"""
        ...
```

## Data Flow Diagrams

### Primary Message Flow
```
Client → API Endpoint → Input Receiver → Message Router → MCP → LLM Service
                                                                   ↓
Client ← SSE ← Output Publisher ← Event System ← Message Router ← MCP Response
```

### Authentication Flow
```
Client → Authentication Endpoint → Token Service → Repository
                                      ↓
Client ← Token ← Token Service
```

### Memory Retrieval Flow
```
Router → Memory Service (MCP) → Memory System → Repository
           ↓
Router ← MCP Response ← Memory Service
```

## Simplification Opportunities

While maintaining the core architectural patterns, we can still simplify:

1. **Streamlined MCP Client**: Simplified connection handling and error management
2. **Focused SSE Implementation**: Cleaner connection lifecycle management
3. **Simplified Event System**: Topic-based with no complex pattern matching
4. **Cleaner Router Implementation**: More direct message processing with less complexity
5. **Unified Error Handling**: Consistent approach to errors across components
6. **Reduced Boilerplate**: Less repetitive code through careful abstraction

## Technology Choices

1. **Backend Framework**: FastAPI
2. **Database**: PostgreSQL with SQLAlchemy ORM
3. **Real-time**: SSE via FastAPI SSE extension
4. **Authentication**: JWT tokens with httpx-oauth
5. **Service Communication**: MCP protocol for backend services
6. **LLM Integration**: Direct provider integration (OpenAI, Anthropic)
7. **API Documentation**: OpenAPI via FastAPI
8. **Testing**: pytest with async support
9. **Type Safety**: Pydantic + mypy

## Implementation Priorities

1. **Foundation Tier** (Week 1-2)
   - Database schema and repository layer
   - Basic API endpoints for conversations
   - SSE implementation for real-time updates
   - Simplified MCP client implementation

2. **Core Experience Tier** (Week 3-4)
   - Input/output channels implementation
   - Message routing implementation
   - LLM service integration
   - Basic memory system via MCP

3. **Extension Tier** (Week 5+)
   - Advanced MCP-based domain experts
   - Enhanced memory capabilities
   - Multi-channel support
   - Additional input/output types

## Next Steps

1. Create database schema design
2. Implement core repository layer
3. Add basic API endpoints
4. Develop simplified SSE manager
5. Create streamlined MCP client
6. Implement input/output channels
7. Develop simplified message router