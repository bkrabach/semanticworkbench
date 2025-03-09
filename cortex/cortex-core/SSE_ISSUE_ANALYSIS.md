# Domain-Driven Repository Architecture Implementation Plan

## Overview

This document outlines a comprehensive plan to enhance our architecture by fully separating database models from domain and API models. This architectural improvement addresses current inconsistencies in the repository pattern implementation and establishes a more maintainable, testable, and clean design.

## Implementation Progress

### Completed (Phase 1)

- ✅ Created directory structure for domain models (`app/models/domain/`)
- ✅ Created directory structure for API models (`app/models/api/request/` and `app/models/api/response/`)  
- ✅ Created directory structure for repositories (`app/database/repositories/`)
- ✅ Implemented base domain models (`DomainModel`, `TimestampedModel`, etc.)
- ✅ Implemented core domain models (User, Workspace, Conversation)
- ✅ Implemented SSE-specific domain models
- ✅ Implemented base repository interface pattern
- ✅ Implemented ResourceAccessRepository with domain-driven approach
- ✅ Updated SSE components to use domain models
- ✅ Ensured tests pass with new architecture

### Progress with Phase 2

- ✅ Implement service layer for SSE components
  - Created SSEService in app/services/sse_service.py
  - Enhanced dependency injection pattern
  - Refactored API endpoints to use service layer instead of components directly
  - Maintained backward compatibility during transition
- ✅ Completed domain-driven architecture for SSE components
  - Updated SSEConnectionManager to use domain models instead of raw dictionaries
  - Enhanced SSEEventSubscriber to create and use proper domain models
  - Improved type safety with strongly-typed ConnectionInfo class
  - Fixed tests to work with the new domain model implementation
  - Ensured consistent error handling and model conversion
- ✅ Implemented ConversationRepository with domain-driven pattern
  - Created a fully type-safe repository implementation for conversations
  - Improved JSON serialization and error handling
  - Implemented proper type conversion between SQLAlchemy and domain models
  - Added comprehensive data validation and safety features
- ✅ Implemented ConversationService layer
  - Created service with business logic for conversations
  - Added event publishing for conversation changes
  - Implemented clean interfaces between layers
  - Enhanced error handling and traceability
- ✅ Created Conversation API models and updated endpoints
  - Defined specialized request models for different operations
  - Created detailed response models with proper validation
  - Updated API endpoints to use the service layer
  - Improved error handling and typing
- ✅ Implemented UserRepository with domain-driven pattern
  - Created dedicated repository class in app/database/repositories/user_repository.py
  - Implemented type-safe methods with proper domain model conversion
  - Added robust error handling for JSON deserialization
  - Created factory function for dependency injection
- ✅ Implemented UserService layer
  - Created service with business logic for user operations in app/services/user_service.py
  - Added event publishing for user-related events
  - Implemented clean interfaces with domain models
  - Added proper error handling for all operations
- ✅ Created User API models and updated Auth endpoints
  - Created request models for login and registration
  - Created response models for user information and authentication
  - Updated authentication endpoints to use the service layer
  - Improved type safety and documentation
- ✅ Implemented WorkspaceRepository with domain-driven pattern
  - Created dedicated repository class in app/database/repositories/workspace_repository.py
  - Implemented CRUD operations with proper domain model conversion
  - Added error handling for all operations
  - Created factory function for dependency injection
- ✅ Implemented WorkspaceService layer
  - Created service with business logic for workspace operations
  - Added event publishing for workspace lifecycle events
  - Implemented proper validation and error handling
  - Created comprehensive test suite for the service
- ✅ Updated Workspace API endpoints to use the new architecture
  - Created request models for workspace operations in app/models/api/request/workspace.py
  - Created response models for workspace data in app/models/api/response/workspace.py
  - Refactored workspace API to use the service layer and domain models
  - Added proper error handling and type safety
  - Implemented additional endpoints (GET, PUT, DELETE) for complete CRUD operations
  - Wrote comprehensive tests for the API endpoints
  - Fixed dependency injection patterns to avoid FastAPI response model issues
  - Made all endpoints compatible with the event system for notifications

## Core Architecture

Our enhanced architecture consists of three distinct model layers:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API Models    │     │  Domain Models  │     │  Database Models│
│   (Pydantic)    │◄───►│   (Pydantic)    │◄───►│  (SQLAlchemy)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    API Layer    │     │  Service Layer  │     │Repository Layer │
│  (Controllers)  │     │(Business Logic) │     │ (Data Access)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Key Components

1. **Database Models**
   - SQLAlchemy ORM models
   - Database-oriented naming (e.g., `meta_data`)
   - Reflect database schema constraints
   - Located in `app/database/models.py`

2. **Domain Models**
   - Pydantic models representing core business entities
   - Domain-oriented naming (e.g., `metadata`)
   - Business validation rules
   - Independent of database implementation
   - Located in `app/models/domain/`

3. **API Models**
   - Pydantic models for request/response handling
   - API-specific validation rules
   - Documentation via FastAPI
   - Located in `app/models/api/`

4. **Repository Layer**
   - Interfaces defined via ABC
   - Implementations that translate between DB and domain models
   - Only place where SQLAlchemy is directly used
   - Located in `app/database/repositories/`

5. **Service Layer**
   - Business logic implementation
   - Works exclusively with domain models
   - Orchestrates operations across repositories
   - Located in `app/services/`

6. **API Layer**
   - HTTP request/response handling
   - Authentication and permission checks
   - Converts between API and domain models
   - Delegates to services for business logic
   - Located in `app/api/`

## Implementation Process

### Phase 1: Directory Structure and Core Models

1. Create new directory structure:
   ```
   app/
   ├── models/
   │   ├── domain/
   │   │   ├── __init__.py
   │   │   ├── base.py
   │   │   ├── conversation.py
   │   │   ├── user.py
   │   │   ├── workspace.py
   │   │   └── ...
   │   ├── api/
   │   │   ├── __init__.py
   │   │   ├── request/
   │   │   │   ├── __init__.py
   │   │   │   ├── conversation.py
   │   │   │   └── ...
   │   │   ├── response/
   │   │   │   ├── __init__.py
   │   │   │   ├── conversation.py
   │   │   │   └── ...
   │   │   └── ...
   │   └── __init__.py
   ├── services/
   │   ├── __init__.py
   │   ├── conversation_service.py
   │   ├── user_service.py
   │   └── ...
   └── database/
       ├── repositories/
       │   ├── __init__.py
       │   ├── base.py
       │   ├── conversation_repository.py
       │   ├── user_repository.py
       │   └── ...
       └── ...
   ```

2. Create base domain models in `app/models/domain/base.py`:
   ```python
   from datetime import datetime
   from typing import Optional, Dict, Any
   from pydantic import BaseModel, Field

   class DomainModel(BaseModel):
       """Base class for all domain models"""
       id: str

   class TimestampedModel(DomainModel):
       """Base class for models with timestamps"""
       created_at: datetime
       updated_at: Optional[datetime] = None
   ```

3. Implement initial domain models for core entities:
   - Users
   - Workspaces
   - Conversations
   - Messages

### Phase 2: Repository Structure and Implementation

1. Create abstract base repository in `app/database/repositories/base.py`:
   ```python
   from abc import ABC, abstractmethod
   from typing import TypeVar, Generic, Optional, List, Type
   from sqlalchemy.orm import Session
   from pydantic import BaseModel

   T = TypeVar('T', bound=BaseModel)
   M = TypeVar('M')  # SQLAlchemy model type

   class Repository(Generic[T, M], ABC):
       """
       Base repository interface
       
       T: Domain model type (Pydantic)
       M: Database model type (SQLAlchemy)
       """
       
       def __init__(self, db_session: Session):
           self.db = db_session
           
       @abstractmethod
       def _to_domain(self, db_model: M) -> T:
           """Convert DB model to domain model"""
           pass
           
       @abstractmethod
       def _to_db_model(self, domain_model: T) -> M:
           """Convert domain model to DB model"""
           pass
   ```

2. Implement concrete repositories starting with conversation repository:
   ```python
   from typing import Optional, List, Dict, Any
   from sqlalchemy.orm import Session
   import json

   from app.database.models import Conversation as ConversationDB
   from app.models.domain.conversation import Conversation, Message
   from app.database.repositories.base import Repository

   class ConversationRepository(Repository[Conversation, ConversationDB]):
       """Repository for conversation data access"""
       
       def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
           """Get a conversation by ID"""
           db_model = self.db.query(ConversationDB).filter(
               ConversationDB.id == conversation_id
           ).first()
           
           if not db_model:
               return None
               
           return self._to_domain(db_model)
           
       # ... other repository methods
       
       def _to_domain(self, db_model: ConversationDB) -> Conversation:
           """Convert DB model to domain model"""
           # Parse JSON fields
           try:
               metadata = json.loads(db_model.meta_data) if db_model.meta_data else {}
           except (json.JSONDecodeError, TypeError):
               metadata = {}
               
           try:
               entries = json.loads(db_model.entries) if db_model.entries else []
           except (json.JSONDecodeError, TypeError):
               entries = []
               
           # Convert entries to Message objects
           messages = [
               Message(
                   id=entry.get("id"),
                   content=entry.get("content", ""),
                   role=entry.get("role", "user"),
                   created_at=entry.get("created_at_utc"),
                   metadata=entry.get("metadata", {})
               )
               for entry in entries
           ]
           
           # Create and return domain model
           return Conversation(
               id=db_model.id,
               workspace_id=db_model.workspace_id,
               title=db_model.title,
               modality=db_model.modality,
               created_at=db_model.created_at_utc,
               updated_at=db_model.updated_at_utc if hasattr(db_model, "updated_at_utc") else None,
               last_active_at=db_model.last_active_at_utc,
               metadata=metadata,
               messages=messages
           )
           
       def _to_db_model(self, domain_model: Conversation) -> ConversationDB:
           """Convert domain model to DB model"""
           # This will be used for create/update operations
           # ... implementation details
   ```

3. Implement dependency injection for repositories:
   ```python
   from fastapi import Depends
   from sqlalchemy.orm import Session
   from typing import Callable, Dict, Type

   from app.database.connection import get_db
   from app.database.repositories.base import Repository

   # Registry of repository factories
   repository_factories: Dict[Type[Repository], Callable] = {}

   def register_repository(repo_class: Type[Repository]):
       """Decorator to register a repository factory function"""
       def decorator(factory_func: Callable):
           repository_factories[repo_class] = factory_func
           return factory_func
       return decorator

   def get_repository(repo_class: Type[Repository], db: Session = Depends(get_db)):
       """Get a repository instance by its class"""
       if repo_class not in repository_factories:
           raise ValueError(f"No factory registered for repository: {repo_class.__name__}")
           
       factory = repository_factories[repo_class]
       return factory(db)
   ```

### Phase 3: Service Layer Implementation

1. Create base service class in `app/services/base.py`:
   ```python
   from typing import TypeVar, Generic, Type
   from sqlalchemy.orm import Session

   from app.database.repositories.base import Repository
   from app.models.domain.base import DomainModel

   T = TypeVar('T', bound=DomainModel)
   R = TypeVar('R', bound=Repository)

   class Service(Generic[T, R]):
       """
       Base service class
       
       T: Domain model type
       R: Repository type
       """
       
       def __init__(self, db_session: Session, repository: R):
           self.db = db_session
           self.repository = repository
   ```

2. Implement conversation service in `app/services/conversation_service.py`:
   ```python
   from typing import List, Optional, Dict, Any
   from sqlalchemy.orm import Session

   from app.models.domain.conversation import Conversation, Message
   from app.database.repositories.conversation_repository import ConversationRepository
   from app.services.base import Service

   class ConversationService(Service[Conversation, ConversationRepository]):
       """Service for conversation-related operations"""
       
       def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
           """Get a conversation by ID"""
           return self.repository.get_by_id(conversation_id)
           
       def create_conversation(self, workspace_id: str, title: str, modality: str, metadata: Dict[str, Any] = None) -> Conversation:
           """Create a new conversation"""
           # Business logic goes here
           # Validation, default values, etc.
           
           return self.repository.create(
               workspace_id=workspace_id,
               title=title,
               modality=modality,
               metadata=metadata or {}
           )
           
       def add_message(self, conversation_id: str, content: str, role: str, metadata: Dict[str, Any] = None) -> Optional[Message]:
           """Add a message to a conversation"""
           # Business logic, validation, etc.
           
           message = self.repository.add_message(
               conversation_id=conversation_id,
               content=content,
               role=role,
               metadata=metadata or {}
           )
           
           # Post-processing logic
           # E.g., publish event, update statistics, etc.
           
           return message
   ```

3. Implement service factory functions:
   ```python
   from fastapi import Depends
   from sqlalchemy.orm import Session

   from app.database.connection import get_db
   from app.database.repositories.conversation_repository import ConversationRepository, get_conversation_repository
   from app.services.conversation_service import ConversationService

   def get_conversation_service(
       db: Session = Depends(get_db),
       repo: ConversationRepository = Depends(get_conversation_repository)
   ) -> ConversationService:
       """Get a conversation service instance"""
       return ConversationService(db, repo)
   ```

### Phase 4: API Layer Integration

1. Update API models in `app/models/api/request/conversation.py`:
   ```python
   from typing import Dict, Any, Optional
   from pydantic import BaseModel, Field

   class CreateConversationRequest(BaseModel):
       title: str = Field(..., description="Conversation title")
       modality: str = Field(..., description="Conversation modality")
       metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")
       
   class AddMessageRequest(BaseModel):
       content: str = Field(..., description="Message content")
       role: str = Field(..., description="Message role (user or assistant)")
       metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")
   ```

2. Update API models in `app/models/api/response/conversation.py`:
   ```python
   from typing import Dict, Any, List, Optional
   from datetime import datetime
   from pydantic import BaseModel, Field

   class MessageResponse(BaseModel):
       id: str
       content: str
       role: str
       created_at: datetime
       metadata: Dict[str, Any] = {}
       
   class ConversationResponse(BaseModel):
       id: str
       title: str
       workspace_id: str
       modality: str
       created_at: datetime
       last_active_at: datetime
       metadata: Dict[str, Any] = {}
       
   class ConversationDetailResponse(ConversationResponse):
       messages: List[MessageResponse] = []
   ```

3. Update API endpoints to use services:
   ```python
   from fastapi import APIRouter, Depends, HTTPException
   from typing import List

   from app.models.api.request.conversation import CreateConversationRequest, AddMessageRequest
   from app.models.api.response.conversation import ConversationResponse, ConversationDetailResponse, MessageResponse
   from app.services.conversation_service import ConversationService, get_conversation_service
   from app.api.auth import get_current_user
   from app.models.domain.user import User

   router = APIRouter()

   @router.post("/{workspace_id}/conversations", response_model=ConversationResponse)
   async def create_conversation(
       workspace_id: str,
       request: CreateConversationRequest,
       service: ConversationService = Depends(get_conversation_service),
       current_user: User = Depends(get_current_user)
   ):
       """Create a new conversation in a workspace"""
       # API-specific authorization logic
       
       # Call service with domain models
       conversation = service.create_conversation(
           workspace_id=workspace_id,
           title=request.title,
           modality=request.modality,
           metadata=request.metadata
       )
       
       # Convert domain model to response model
       return ConversationResponse(
           id=conversation.id,
           title=conversation.title,
           workspace_id=conversation.workspace_id,
           modality=conversation.modality,
           created_at=conversation.created_at,
           last_active_at=conversation.last_active_at,
           metadata=conversation.metadata
       )
   ```

### Phase 5: Migration Strategy

1. **Incremental Approach**:
   - Implement one entity type at a time (e.g., Conversations → Workspaces → Users)
   - For each entity, complete all layers before moving to the next entity
   - Start with read operations, then implement write operations

2. **Parallel Implementation**:
   - Keep existing code working while implementing new architecture
   - Add feature flags to switch between old and new implementations
   - Write tests for new implementation before switching

3. **Testing Strategy**:
   - Create unit tests for domain models
   - Create unit tests for repositories with in-memory DB
   - Create integration tests for services
   - Create API tests that verify correct model transformations

# Domain-Driven Repository Architecture Implementation Status

## Overview

This document provides a status update on our progress implementing a comprehensive domain-driven repository architecture across the codebase. The architecture establishes a clean separation between database models, domain models, and API models while creating consistent patterns for data access, business logic, and API interactions.

## Current Status: Phase 3 - Final Refinements ✅

The implementation of the domain-driven repository architecture is now substantially complete. All major components have been successfully migrated to the new architecture, including:

1. **SSE System (Server-Sent Events)**: ✅ COMPLETED
   - Domain models for SSE connections, events, and statistics
   - Repository pattern for resource access checks
   - Service layer with business logic and error handling
   - Clean API endpoints that delegate to the service layer
   - Optimized event handling with factory methods
   - Type-safe implementation with proper annotations
   - Full test coverage with passing component, API, and integration tests

2. **Conversation System**: ✅ COMPLETED
   - Domain models for conversations and messages
   - Repository with proper domain model conversion
   - Service layer with business logic
   - API endpoints with request/response models

3. **User/Auth System**: ✅ COMPLETED
   - Domain models for users
   - Repository for user management
   - Service layer with authentication logic
   - API endpoints with authentication and authorization

4. **Workspace System**: ✅ COMPLETED
   - Domain models for workspaces
   - Repository for workspace data access
   - Service layer with business logic
   - Comprehensive API endpoints for workspace management

## Architecture Overview

Our architecture establishes three distinct model layers:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API Models    │     │  Domain Models  │     │  Database Models│
│   (Pydantic)    │◄───►│   (Pydantic)    │◄───►│  (SQLAlchemy)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    API Layer    │     │  Service Layer  │     │Repository Layer │
│  (Controllers)  │     │(Business Logic) │     │ (Data Access)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Key Components

1. **Database Models**
   - SQLAlchemy ORM models
   - Database-oriented naming (e.g., `meta_data`)
   - Reflect database schema constraints
   - Located in `app/database/models.py`

2. **Domain Models**
   - Pydantic models representing core business entities
   - Domain-oriented naming (e.g., `metadata`)
   - Business validation rules
   - Independent of database implementation
   - Located in `app/models/domain/`

3. **API Models**
   - Pydantic models for request/response handling
   - API-specific validation rules
   - Documentation via FastAPI
   - Located in `app/models/api/`

4. **Repository Layer**
   - Interfaces defined via ABC
   - Implementations that translate between DB and domain models
   - Only place where SQLAlchemy is directly used
   - Located in `app/database/repositories/`

5. **Service Layer**
   - Business logic implementation
   - Works exclusively with domain models
   - Orchestrates operations across repositories
   - Located in `app/services/`

6. **API Layer**
   - HTTP request/response handling
   - Authentication and permission checks
   - Converts between API and domain models
   - Delegates to services for business logic
   - Located in `app/api/`

## Recent SSE Improvements

We've just completed extensive improvements to the SSE (Server-Sent Events) components:

1. **Service-Based Architecture**:
   - Moved helper functionality from API endpoints to the service layer
   - Created a new `create_sse_stream` method to handle all connection setup logic
   - Service now handles authentication, authorization, connection registration, and cleanup

2. **Repository Pattern**:
   - Removed direct database access in `auth.py`
   - Added proper deprecation warnings for legacy code
   - Ensured consistent use of repositories for data access

3. **Optimized Event Handling**:
   - Refactored event subscriber to use a factory pattern
   - Reduced code duplication across event handlers
   - Added better logging and error handling

4. **Enhanced Type Safety**:
   - Added proper type annotations throughout the codebase
   - Fixed mypy issues for better IDE support and runtime safety
   - Used generic types appropriately

5. **Testing Improvements**:
   - Updated tests to work with the new service-based architecture
   - Added better mocking practices
   - Ensured all component, API, and integration tests pass

6. **Code Cleanup**:
   - Removed unused imports
   - Fixed linting issues
   - Improved code organization

## Remaining Tasks

While the implementation is substantially complete, a few polish items remain:

### High Priority

1. **Pydantic Validator Upgrades**: (Est. 1-2 hours)
   - Update `@validator` decorators to `@field_validator` in domain models
   - Address Pydantic V2 deprecation warnings

2. **Documentation Updates**: (Est. 2-3 hours)
   - Update OpenAPI descriptions for the new API models
   - Add architecture diagrams to documentation
   - Document the domain-driven pattern for developers

### Medium Priority

3. **Additional Test Coverage**: (Est. 3-5 hours)
   - Create specific tests for domain model validation
   - Add tests for edge cases in repository implementations
   - Improve coverage for service layer business logic

4. **Performance Review**: (Est. 1-2 hours)
   - Identify potential N+1 query issues
   - Review JSON serialization/deserialization performance
   - Consider caching opportunities

### Low Priority

5. **Developer Tooling**: (Est. 1-2 hours)
   - Create scaffolding tools for new domain models
   - Add code generation for repository boilerplate
   - Develop example templates for common patterns

## Timeline and Effort

The overall SSE implementation following the domain-driven pattern is now complete. All tests pass, and the code is structured according to the defined architecture. The remaining tasks are primarily polish and optimization, estimated at 8-14 hours of work.

## Benefits Achieved

The migration to domain-driven repository architecture has delivered significant benefits:

1. **Clean Separation of Concerns**:
   - API layer focuses purely on HTTP protocol concerns
   - Service layer contains isolated business logic
   - Repository layer handles data access and conversions
   - Models are separated by their purpose (API, domain, database)

2. **Improved Type Safety**:
   - Strong typing throughout the codebase
   - Pydantic validation for all data structures
   - Clear interfaces between components

3. **Enhanced Testability**:
   - Each layer can be tested in isolation
   - Mock interfaces make testing simpler
   - Dependency injection improves test reliability

4. **Consistent Patterns**:
   - The same architecture applies to all components
   - Common naming conventions across the codebase
   - Clear structure for adding new features

5. **Better Error Handling**:
   - Domain-specific error types
   - Consistent error handling patterns
   - Better user-facing error messages

## Conclusion

The SSE component implementation now fully embraces the domain-driven repository architecture. The code is cleaner, more maintainable, and exhibits better separation of concerns. All tests are passing, and the implementation offers improved type safety and error handling.

The remaining tasks are primarily polish and documentation, but the core architectural migration is complete. This successful implementation serves as a model for the rest of the codebase and provides a solid foundation for future development.

We've demonstrated that this architecture is viable, maintainable, and beneficial for the project. The lessons learned from this implementation can now be applied to other components as needed.