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

## Recent Architectural Improvements

In March 2025, we refactored the conversations API to use the Repository Pattern, which:

1. Separated data access concerns from API logic
2. Made tests more robust by eliminating brittle JSON serialization mocks
3. Improved error handling with repository-specific error returns
4. Created a cleaner, more maintainable codebase

This approach should be followed for all new features and when refactoring existing code.

## Architecture Decision Records

For major architectural decisions, we maintain ADRs (Architecture Decision Records) in the `/docs/adr` directory.