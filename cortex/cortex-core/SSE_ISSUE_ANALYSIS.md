# Domain-Driven Repository Architecture Implementation Plan

## Overview

This document outlines a comprehensive plan to enhance our architecture by fully separating database models from domain and API models. This architectural improvement addresses current inconsistencies in the repository pattern implementation and establishes a more maintainable, testable, and clean design.

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

## Concrete Migration Example: Conversations API

### Step 1: Create domain models

```python
# app/models/domain/conversation.py
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.models.domain.base import TimestampedModel

class Message(BaseModel):
    id: str
    content: str
    role: str
    created_at: datetime
    metadata: Dict[str, Any] = {}

class Conversation(TimestampedModel):
    workspace_id: str
    title: str
    modality: str
    last_active_at: datetime
    metadata: Dict[str, Any] = {}
    messages: List[Message] = []
```

### Step 2: Update repository with translation logic

```python
# app/database/repositories/conversation_repository.py
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
import uuid
from sqlalchemy.orm import Session

from app.database.models import Conversation as ConversationDB
from app.models.domain.conversation import Conversation, Message
from app.utils.json_helpers import DateTimeEncoder

class ConversationRepository:
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        db_model = self.db.query(ConversationDB).filter(
            ConversationDB.id == conversation_id
        ).first()
        
        if not db_model:
            return None
            
        return self._to_domain(db_model)
        
    def create(self, workspace_id: str, title: str, modality: str, metadata: Dict[str, Any] = None) -> Conversation:
        """Create a new conversation"""
        now = datetime.now(timezone.utc)
        metadata_json = json.dumps(metadata or {}, cls=DateTimeEncoder)
        
        db_model = ConversationDB(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            title=title,
            modality=modality,
            created_at_utc=now,
            last_active_at_utc=now,
            entries="[]",
            meta_data=metadata_json
        )
        
        self.db.add(db_model)
        self.db.commit()
        self.db.refresh(db_model)
        
        return self._to_domain(db_model)
        
    def _to_domain(self, db_model: ConversationDB) -> Conversation:
        """Convert database model to domain model"""
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
```

### Step 3: Implement service layer

```python
# app/services/conversation_service.py
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.domain.conversation import Conversation, Message
from app.database.repositories.conversation_repository import ConversationRepository

class ConversationService:
    def __init__(self, db_session: Session, repository: ConversationRepository):
        self.db = db_session
        self.repository = repository
        
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        return self.repository.get_by_id(conversation_id)
        
    def create_conversation(self, workspace_id: str, title: str, modality: str, metadata: Dict[str, Any] = None) -> Conversation:
        """Create a new conversation"""
        # Business logic, validation, etc.
        
        conversation = self.repository.create(
            workspace_id=workspace_id,
            title=title,
            modality=modality,
            metadata=metadata or {}
        )
        
        # Post-creation logic (e.g., publish event)
        
        return conversation
```

### Step 4: Update API endpoints

```python
# app/api/conversations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.api.request.conversation import CreateConversationRequest
from app.models.api.response.conversation import ConversationResponse
from app.services.conversation_service import ConversationService
from app.database.repositories.conversation_repository import ConversationRepository
from app.api.auth import get_current_user
from app.models.domain.user import User

router = APIRouter()

# Factory functions
def get_conversation_repository(db: Session = Depends(get_db)) -> ConversationRepository:
    return ConversationRepository(db)

def get_conversation_service(
    db: Session = Depends(get_db),
    repository: ConversationRepository = Depends(get_conversation_repository)
) -> ConversationService:
    return ConversationService(db, repository)

@router.post("/{workspace_id}/conversations", response_model=ConversationResponse)
async def create_conversation(
    workspace_id: str,
    request: CreateConversationRequest,
    service: ConversationService = Depends(get_conversation_service),
    current_user: User = Depends(get_current_user)
):
    """Create a new conversation in a workspace"""
    # Authorization check
    
    # Call service
    conversation = service.create_conversation(
        workspace_id=workspace_id,
        title=request.title,
        modality=request.modality,
        metadata=request.metadata
    )
    
    # Transform to response model
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

## Benefits of This Architecture

1. **Clean Separation of Concerns**
   - API layer focuses only on HTTP concerns
   - Service layer contains all business logic
   - Repository layer handles data access and translations
   - No leakage of database concerns to higher layers

2. **Improved Testability**
   - Each layer can be tested in isolation
   - Domain models can be unit tested without database
   - Services can be tested with mocked repositories
   - APIs can be tested with mocked services

3. **Consistent Naming and Structure**
   - Domain models use domain language (`metadata`)
   - Database models use DB conventions (`meta_data`)
   - No confusion about field names across layers

4. **Type Safety**
   - Pydantic models provide validation and type safety
   - Clear interfaces between layers
   - Better IDE support and autocompletion

5. **Documentation**
   - API models generate OpenAPI documentation
   - Domain models document business concepts
   - Repository interfaces document data access patterns

## Implementation Roadmap

Based on a complete analysis of the codebase, here are all the files that need to be modified or created to implement the new architecture:

### Phase 1: Create Directory Structure and Base Classes

#### New Directories
- `/app/models/domain/`
- `/app/models/api/request/`
- `/app/models/api/response/`
- `/app/services/`
- `/app/database/repositories/`

#### Base Classes
- `/app/models/domain/base.py` (New)
- `/app/services/base.py` (New)
- `/app/database/repositories/base.py` (New)

### Phase 2: Database Models (SQLAlchemy)

No changes needed to:
- `/app/database/models.py` (Keep as-is)

### Phase 3: Domain Models (Pydantic)

Create the following files:
- `/app/models/domain/__init__.py`
- `/app/models/domain/user.py`
- `/app/models/domain/workspace.py`
- `/app/models/domain/conversation.py`

### Phase 4: API Models (Pydantic)

Create the following files:
- `/app/models/api/__init__.py`
- `/app/models/api/request/__init__.py`
- `/app/models/api/request/conversation.py`
- `/app/models/api/request/user.py`
- `/app/models/api/request/workspace.py`
- `/app/models/api/response/__init__.py`
- `/app/models/api/response/conversation.py`
- `/app/models/api/response/user.py`
- `/app/models/api/response/workspace.py`

### Phase 5: Repository Implementation

Refactor current repositories into new structure:
- Migrate from `/app/database/repositories.py` to:
  - `/app/database/repositories/__init__.py`
  - `/app/database/repositories/conversation_repository.py`
  - `/app/database/repositories/user_repository.py`
  - `/app/database/repositories/workspace_repository.py`
  - `/app/database/repositories/resource_access_repository.py`

### Phase 6: Service Layer

Create the following files:
- `/app/services/__init__.py`
- `/app/services/conversation_service.py`
- `/app/services/user_service.py`
- `/app/services/workspace_service.py`

### Phase 7: API Endpoints

Modify the following files to use services instead of repositories:
- `/app/api/conversations.py` (Moderate changes)
- `/app/api/workspaces.py` (Moderate changes)
- `/app/api/auth.py` (Moderate changes)

### Phase 8: Component Refactoring

Modify the following files:
- `/app/components/sse/manager.py` (Minor to moderate changes)
- `/app/components/conversation_channels.py` (Minor changes)

### Phase 9: Test Updates

Update existing tests:
- `/tests/api/test_conversations.py` (Major changes)
- `/tests/api/test_auth.py` (Major changes)
- `/tests/api/test_workspaces.py` (Major changes)
- `/tests/components/test_conversation_channels.py` (Moderate changes)

Create new tests:
- `/tests/models/test_domain_models.py`
- `/tests/services/test_conversation_service.py`
- `/tests/services/test_user_service.py`
- `/tests/services/test_workspace_service.py`
- `/tests/database/repositories/test_conversation_repository.py`
- `/tests/database/repositories/test_user_repository.py`
- `/tests/database/repositories/test_workspace_repository.py`

## Implementation Priority

Based on the complexity and dependencies, we recommend implementing in this order:

1. Base infrastructure (directories and base classes)
2. Domain models
3. Repository split and implementation
4. Service layer
5. API models
6. API endpoint updates
7. Component refactoring
8. Tests

## Effort Estimation

- **Minor changes**: Approximately 1-2 hours per file
- **Moderate changes**: Approximately 2-4 hours per file  
- **Major changes/new files**: Approximately 4-8 hours per file

Total estimated effort: 120-180 hours (3-4.5 weeks for one engineer)

## Conclusion

This architecture provides a robust foundation for Cortex Core's continued development. By clearly separating concerns between different layers and model types, we create a more maintainable, testable, and extensible codebase.

The migration strategy allows for incremental adoption while maintaining backward compatibility where needed. The end result will be a clean, consistent architecture that adheres to best practices and supports future growth.