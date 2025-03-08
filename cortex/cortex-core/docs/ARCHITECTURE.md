# Cortex Core Architecture

This document describes the high-level architecture of Cortex Core, its components, and design principles.

## Overview

Cortex Core is designed as a modular system with clear separation of concerns, following clean architecture principles. The application is built around a layered design where each layer has specific responsibilities and dependencies flow inward.

## Architectural Principles

1. **Separation of Concerns**: Each component has a single responsibility
2. **Dependency Inversion**: High-level modules don't depend on low-level modules
3. **Interface Segregation**: Clients depend only on interfaces they use
4. **Clean Architecture**: Dependencies point inward toward domain entities
5. **Repository Pattern**: Data access is abstracted behind repository interfaces

## Layered Architecture

```
┌─────────────────┐
│   API Layer     │ ← HTTP concerns only
├─────────────────┤
│  Service Layer  │ ← Business logic
├─────────────────┤
│ Repository Layer│ ← Data access
├─────────────────┤
│   Data Layer    │ ← Database/ORM
└─────────────────┘
```

### API Layer

The API layer is responsible for handling HTTP requests and responses. It:
- Defines routes and endpoint handlers
- Validates input data
- Handles authentication and authorization
- Returns formatted responses
- Doesn't contain business logic

### Service Layer

The service layer contains the core business logic of the application. It:
- Implements business rules and workflows
- Orchestrates operations across multiple repositories
- Handles domain events
- Doesn't know about HTTP or database details

### Repository Layer

The repository layer abstracts data access. It:
- Provides a collection-like interface for domain entities
- Hides database implementation details
- Translates between domain entities and database models
- Handles serialization/deserialization to/from database formats

### Data Layer

The data layer contains the database models and connections. It:
- Defines database schema
- Provides ORM models
- Handles database connections and sessions

## Components and Interfaces

### Event System

The event system provides a publish-subscribe mechanism for loose coupling between components. Events represent things that have happened in the system. The event system consists of:

1. **Event Bus**: Core publish-subscribe mechanism for internal communication
2. **Event Subscribers**: Components that listen for and react to events
3. **SSE System**: Server-Sent Events module for real-time client communication

#### SSE Architecture

The SSE system follows a clean, modular design with a unified endpoint structure:

```
┌───────────────────────────────┐
│       Unified SSE API         │ ← HTTP endpoints (/v1/{channel_type}/{resource_id})
├───────────────────────────────┤
│         SSE Service           │ ← Orchestration layer
├───────────┬─────────┬─────────┤
│Connection │   Auth  │  Event  │ ← Component layer
│ Manager   │ Service │Subscriber│
└───────────┴─────────┴─────────┘
```

This modular architecture provides:
- Clean separation of concerns with specialized components
- Improved testability through dependency injection
- Easier maintenance and evolution
- Consistent interface for all event types
- Unified authentication and authorization

The key advantages of this architecture include:

1. **Unified Endpoint Pattern**: All SSE endpoints follow the consistent `/v1/{channel_type}/{resource_id}` pattern
2. **Modularity**: Each component has a single responsibility and clear interfaces
3. **Extensibility**: New channel types can be added without changing the API structure
4. **Security**: Centralized authentication and authorization for all SSE connections
5. **Performance**: Efficient connection management with proper resource cleanup
6. **Observability**: Built-in statistics and monitoring capabilities

### Integration Hub and MCP Architecture

The Integration Hub manages communication between Cortex Core and Domain Expert services using the Model Context Protocol (MCP). This is a central component of the platform's architecture for service-to-service communication:

```
┌────────────────────┐           ┌────────────────────┐
│    Cortex Core     │           │   Domain Experts   │
│                    │◄────────►│                    │
│ ┌────────────────┐ │           │ ┌────────────────┐ │
│ │Integration Hub │ │   MCP     │ │  FastMCP API   │ │
│ │with MCP Client │◄┼──────────┼►│  Server         │ │
│ └────────────────┘ │           │ └────────────────┘ │
└────────────────────┘           └────────────────────┘
```

The Integration Hub provides:

1. **MCP Client Implementation**: Uses the Python MCP SDK client to communicate with domain expert services
2. **Tool Execution Framework**: Registers, discovers and executes tools provided by domain experts
3. **Service Discovery**: Manages connections to configured MCP endpoints 
4. **Resource Access**: Facilitates access to resources exposed by domain expert services
5. **Error Handling**: Implements robust error handling and retries for domain expert communication

Domain Expert services implement MCP servers using the FastMCP API from the Python SDK, which provides:

1. **Decorator-based Tools**: Simple definition of tools using Python decorators
2. **Type-safe Interfaces**: Automatic validation of parameters using Python type annotations
3. **Resource Templating**: URI-template based resource definitions
4. **Lifecycle Management**: Proper setup and teardown of resources

MCP's role is critical for implementing specialized domain expert services, providing a clean separation between Cortex Core and the various expert services that enhance its capabilities.

### Router

The router dispatches incoming requests to the appropriate handlers based on the message type and context.

### Memory System

The memory system provides short and long-term storage capabilities for conversation context and user preferences.

### Repository Pattern Implementation

We use the Repository Pattern to abstract database access concerns. For example:

```python
# Abstract Repository Interface
class ConversationRepository(ABC):
    @abstractmethod
    def get_conversation_by_id(self, conversation_id: str) -> Optional[Conversation]:
        pass
        
    @abstractmethod
    def get_conversations_by_workspace(self, workspace_id: str, limit: int, offset: int) -> List[Conversation]:
        pass
        
    @abstractmethod
    def add_message(self, conversation_id: str, content: str, role: str, metadata: Optional[Dict] = None) -> Dict:
        pass
        
# Concrete Implementation
class SQLAlchemyConversationRepository(ConversationRepository):
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def get_conversation_by_id(self, conversation_id: str) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        
    # ... other methods
```

## Dependency Injection

We use FastAPI's dependency injection system to provide services and repositories to endpoints:

```python
@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    repository: ConversationRepository = Depends(get_repository),
    user: User = Depends(get_current_user)
):
    conversation = repository.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
```

## Testing Approach

We use a layered testing approach:

1. **Unit tests** for individual components
2. **Integration tests** for interactions between components
3. **API tests** for endpoint functionality

For API tests, we mock repositories rather than database interactions, allowing us to test API behavior without complex database setups.

## Data Flow Examples

### Creating a Conversation

1. Client sends a POST request to `/workspaces/{workspace_id}/conversations`
2. API layer validates the request
3. Service layer performs business logic
4. Repository layer creates the conversation in the database
5. API layer returns the created conversation

### Adding a Message to a Conversation

1. Client sends a POST request to `/conversations/{conversation_id}/messages`
2. API layer validates the request
3. Repository layer adds the message to the conversation
4. Event is published to notify clients
5. API layer returns the created message

## Key Architectural Patterns

### Repository Pattern Implementation

The conversations API uses the Repository Pattern, which:

1. Separates data access concerns from API logic
2. Makes tests robust by eliminating brittle JSON serialization mocks
3. Improves error handling with repository-specific error returns
4. Creates a cleaner, more maintainable codebase

### MCP Integration with FastMCP

The system uses the Python SDK with FastMCP for all MCP implementations:

1. **Simplified Domain Expert Integration**: The FastMCP decorator-based API reduces boilerplate and improves clarity
2. **Type-Safe Interfaces**: Parameter validation using Python type annotations provides early error detection
3. **Improved Testing**: The MCP SDK's testing utilities make tests more reliable and easier to write
4. **Consistent Protocol Implementation**: Using the SDK ensures consistent protocol compliance
5. **Better Documentation**: Clear examples and patterns improve developer onboarding

These approaches should be followed for all new features and development work.

## Architecture Decision Records

For major architectural decisions, we maintain ADRs (Architecture Decision Records) in the `/docs/adr` directory.