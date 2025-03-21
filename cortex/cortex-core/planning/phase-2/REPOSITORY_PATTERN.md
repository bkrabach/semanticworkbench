# Repository Pattern Implementation Guide

## Overview

This document provides a comprehensive guide to implementing the Repository Pattern in Phase 2 of the Cortex Core. The Repository Pattern is a crucial architectural component that abstracts data access logic, separates domain models from persistence details, and enables clean separation of concerns throughout the application.

## Table of Contents

1. [Introduction to the Repository Pattern](#introduction-to-the-repository-pattern)
2. [Repository Architecture](#repository-architecture)
3. [Core Components](#core-components)
4. [Generic Repository Implementation](#generic-repository-implementation)
5. [Entity-Specific Repositories](#entity-specific-repositories)
6. [Repository Factory](#repository-factory)
7. [Domain Model Mapping](#domain-model-mapping)
8. [Transaction Management](#transaction-management)
9. [Error Handling](#error-handling)
10. [User-Based Access Control](#user-based-access-control)
11. [Using Repositories with FastAPI](#using-repositories-with-fastapi)
12. [Testing Repositories](#testing-repositories)
13. [Best Practices and Pitfalls](#best-practices-and-pitfalls)
14. [Integration with Other Components](#integration-with-other-components)

## Introduction to the Repository Pattern

### Definition and Purpose

The Repository Pattern is a design pattern that abstracts the data access layer from the rest of the application. It provides a collection-like interface for accessing domain objects, hiding the details of data access logic from the business logic.

In the context of Cortex Core Phase 2, the Repository Pattern serves to:

1. **Abstract Database Access**: Hide SQLite implementation details from the business logic
2. **Separate Concerns**: Keep domain models clean from persistence-specific code
3. **Simplify Testing**: Allow for easy mocking of data access in unit tests
4. **Enable Future Changes**: Facilitate future migration to PostgreSQL in Phase 5
5. **Enforce Data Partitioning**: Ensure proper access control at the data layer

### Key Benefits

1. **Maintainability**: Changes to the database layer don't affect the business logic
2. **Testability**: Business logic can be tested independently from the database
3. **Flexibility**: Database technology can be changed with minimal impact
4. **Centralized Data Logic**: All data access follows consistent patterns
5. **Transaction Control**: Simplified transaction management
6. **Query Encapsulation**: Complex queries are encapsulated within repositories

### Repository vs. Active Record

While some ORM frameworks like SQLAlchemy support an Active Record pattern where model objects save themselves, we've chosen the Repository Pattern for several reasons:

1. **Cleaner Models**: Our domain models remain pure data objects
2. **Explicit Transactions**: Transaction boundaries are explicit
3. **Better Control**: Finer control over query optimization
4. **Clearer Testing**: Easier to mock repositories than to mock model methods
5. **Access Control**: User-based access control is enforced consistently

## Repository Architecture

### Where Repositories Fit

Repositories sit between the domain models and the database, acting as an abstraction layer:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  API Layer  │────▶│   Services  │────▶│ Repositories │────▶│  Database   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                                        │                   │
       │                                        │                   │
       ▼                                        ▼                   ▼
┌─────────────┐                        ┌─────────────┐      ┌─────────────┐
│ API Models  │                        │ Domain      │      │ Database    │
│ (Pydantic)  │                        │ Models      │      │ Models      │
└─────────────┘                        └─────────────┘      └─────────────┘
```

### Repository Pattern Layers

1. **Interface Layer**: Abstract repository interfaces defining operations
2. **Implementation Layer**: Concrete repository implementations for SQLite
3. **Factory Layer**: Factory for creating repository instances

### Model Types

The Repository Pattern manages the interaction between different model types:

1. **Domain Models (Pydantic)**: Used by business logic and services
2. **Database Models (SQLAlchemy)**: Used for ORM mapping to the database
3. **API Models (Pydantic)**: Used for HTTP request/response

Repositories are responsible for mapping between domain models and database models.

## Core Components

### Generic Repository Interface

The base repository interface defines common operations for all entity types:

```python
from typing import TypeVar, Generic, List, Optional, Any, Dict, Type
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T]):
    """Base repository interface for database operations."""

    def __init__(self, session, model_type: Type[T]):
        """
        Initialize repository.

        Args:
            session: Database session
            model_type: Pydantic model type for this repository
        """
        self.session = session
        self.model_type = model_type

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        raise NotImplementedError

    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        raise NotImplementedError

    async def list(self, filters: Dict[str, Any] = None, limit: int = 100, offset: int = 0) -> List[T]:
        """List entities with optional filtering."""
        raise NotImplementedError

    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        raise NotImplementedError

    async def delete(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        raise NotImplementedError

    async def count(self, filters: Dict[str, Any] = None) -> int:
        """Count entities with optional filtering."""
        raise NotImplementedError
```

### Entity-Specific Repository Interfaces

For each entity type, we define a specific repository interface that extends the base interface:

```python
from typing import List, Optional, Dict, Any
from app.models.domain import User, Workspace, Conversation, Message
from app.database.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    """Repository for user operations."""

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        raise NotImplementedError

class WorkspaceRepository(BaseRepository[Workspace]):
    """Repository for workspace operations."""

    async def list_by_owner(self, owner_id: str, limit: int = 100, offset: int = 0) -> List[Workspace]:
        """List workspaces for a specific owner."""
        raise NotImplementedError

    async def get_by_id(self, entity_id: str, owner_id: Optional[str] = None) -> Optional[Workspace]:
        """
        Get workspace by ID.

        Args:
            entity_id: Workspace ID
            owner_id: Optional owner ID for access control
        """
        raise NotImplementedError

class ConversationRepository(BaseRepository[Conversation]):
    """Repository for conversation operations."""

    async def list_by_workspace(self, workspace_id: str, limit: int = 100, offset: int = 0) -> List[Conversation]:
        """List conversations in a specific workspace."""
        raise NotImplementedError

class MessageRepository(BaseRepository[Message]):
    """Repository for message operations."""

    async def list_by_conversation(self, conversation_id: str, limit: int = 100, offset: int = 0) -> List[Message]:
        """List messages in a specific conversation."""
        raise NotImplementedError
```

## Generic Repository Implementation

The generic repository provides the foundation for all specific repositories:

```python
from typing import TypeVar, Generic, List, Optional, Any, Dict, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)
DB = TypeVar('DB')  # Database model type

class GenericRepository(Generic[T, DB]):
    """Generic repository implementation."""

    def __init__(self, session: AsyncSession, model_type: Type[T], db_model_type: Type[DB]):
        """
        Initialize repository.

        Args:
            session: SQLAlchemy async session
            model_type: Pydantic model type
            db_model_type: SQLAlchemy model type
        """
        self.session = session
        self.model_type = model_type
        self.db_model_type = db_model_type

    async def create(self, entity: T) -> T:
        """
        Create a new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity
        """
        # Convert domain model to database model
        db_entity = self._to_db(entity)

        # Add to session
        self.session.add(db_entity)
        await self.session.flush()

        # Convert back to domain model and return
        return self._to_domain(db_entity)

    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        result = await self.session.execute(
            select(self.db_model_type).where(self.db_model_type.id == entity_id)
        )
        db_entity = result.scalars().first()

        # Convert to domain model if found
        return self._to_domain(db_entity) if db_entity else None

    async def list(self, filters: Dict[str, Any] = None, limit: int = 100, offset: int = 0) -> List[T]:
        """
        List entities with optional filtering.

        Args:
            filters: Optional filters as field-value pairs
            limit: Maximum number of entities to return
            offset: Pagination offset

        Returns:
            List of entities
        """
        # Build query
        query = select(self.db_model_type)

        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.db_model_type, field):
                    query = query.where(getattr(self.db_model_type, field) == value)

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Execute query
        result = await self.session.execute(query)
        db_entities = result.scalars().all()

        # Convert to domain models
        return [self._to_domain(db_entity) for db_entity in db_entities]

    async def update(self, entity: T) -> T:
        """
        Update an existing entity.

        Args:
            entity: Entity to update

        Returns:
            Updated entity
        """
        # Get entity ID (assumes entity has 'id' attribute)
        entity_id = getattr(entity, 'id')

        # Get existing entity
        result = await self.session.execute(
            select(self.db_model_type).where(self.db_model_type.id == entity_id)
        )
        db_entity = result.scalars().first()

        if not db_entity:
            raise ValueError(f"Entity not found: {entity_id}")

        # Update fields
        db_entity = self._update_db_entity(db_entity, entity)

        # Flush changes
        await self.session.flush()

        # Return updated entity
        return self._to_domain(db_entity)

    async def delete(self, entity_id: str) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            True if entity was deleted, False otherwise
        """
        result = await self.session.execute(
            delete(self.db_model_type).where(self.db_model_type.id == entity_id)
        )
        return result.rowcount > 0

    async def count(self, filters: Dict[str, Any] = None) -> int:
        """
        Count entities with optional filtering.

        Args:
            filters: Optional filters as field-value pairs

        Returns:
            Count of entities
        """
        # Build query
        query = select(func.count()).select_from(self.db_model_type)

        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.db_model_type, field):
                    query = query.where(getattr(self.db_model_type, field) == value)

        # Execute query
        result = await self.session.execute(query)
        return result.scalar() or 0

    def _to_domain(self, db_entity) -> Optional[T]:
        """
        Convert database entity to domain entity.

        Args:
            db_entity: Database entity

        Returns:
            Domain entity
        """
        raise NotImplementedError("Subclasses must implement _to_domain")

    def _to_db(self, entity: T):
        """
        Convert domain entity to database entity.

        Args:
            entity: Domain entity

        Returns:
            Database entity
        """
        raise NotImplementedError("Subclasses must implement _to_db")

    def _update_db_entity(self, db_entity, entity: T):
        """
        Update database entity from domain entity.

        Args:
            db_entity: Database entity to update
            entity: Domain entity with new values

        Returns:
            Updated database entity
        """
        raise NotImplementedError("Subclasses must implement _update_db_entity")
```

## Entity-Specific Repositories

For each entity type, we implement a concrete repository that extends the generic repository. Here are the key implementations to understand:

### User Repository

```python
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User as DbUser
from app.models.domain import User
from app.database.repositories.generic import GenericRepository

class UserRepositoryImpl(GenericRepository[User, DbUser]):
    """Implementation of user repository."""

    def __init__(self, session: AsyncSession):
        """Initialize user repository."""
        super().__init__(session, User, DbUser)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        result = await self.session.execute(
            select(DbUser).where(DbUser.email == email)
        )
        db_user = result.scalars().first()
        return self._to_domain(db_user) if db_user else None

    def _to_domain(self, db_user: DbUser) -> Optional[User]:
        """Convert database user to domain user."""
        if not db_user:
            return None

        import json
        metadata = {}
        if db_user.metadata_json:
            try:
                metadata = json.loads(db_user.metadata_json)
            except json.JSONDecodeError:
                pass

        return User(
            user_id=db_user.user_id,
            name=db_user.name,
            email=db_user.email,
            metadata=metadata
        )

    def _to_db(self, user: User) -> DbUser:
        """Convert domain user to database user."""
        import json
        metadata_json = json.dumps(user.metadata) if user.metadata else "{}"

        return DbUser(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            metadata_json=metadata_json
        )

    def _update_db_entity(self, db_user: DbUser, user: User) -> DbUser:
        """Update database user from domain user."""
        import json

        db_user.name = user.name
        db_user.email = user.email
        db_user.metadata_json = json.dumps(user.metadata) if user.metadata else "{}"

        return db_user
```

### Workspace Repository

```python
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Workspace as DbWorkspace
from app.models.domain import Workspace
from app.database.repositories.generic import GenericRepository

class WorkspaceRepositoryImpl(GenericRepository[Workspace, DbWorkspace]):
    """Implementation of workspace repository."""

    def __init__(self, session: AsyncSession):
        """Initialize workspace repository."""
        super().__init__(session, Workspace, DbWorkspace)

    async def list_by_owner(self, owner_id: str, limit: int = 100, offset: int = 0) -> List[Workspace]:
        """
        List workspaces for a specific owner.

        Args:
            owner_id: Owner user ID
            limit: Maximum number of workspaces to return
            offset: Pagination offset

        Returns:
            List of workspaces
        """
        result = await self.session.execute(
            select(DbWorkspace)
            .where(DbWorkspace.owner_id == owner_id)
            .limit(limit)
            .offset(offset)
        )
        db_workspaces = result.scalars().all()
        return [self._to_domain(db_workspace) for db_workspace in db_workspaces]

    async def get_by_id(self, entity_id: str, owner_id: Optional[str] = None) -> Optional[Workspace]:
        """
        Get workspace by ID.

        Args:
            entity_id: Workspace ID
            owner_id: Optional owner ID for access control

        Returns:
            Workspace if found and accessible, None otherwise
        """
        query = select(DbWorkspace).where(DbWorkspace.id == entity_id)

        # Apply owner filter if provided (for access control)
        if owner_id:
            query = query.where(DbWorkspace.owner_id == owner_id)

        result = await self.session.execute(query)
        db_workspace = result.scalars().first()
        return self._to_domain(db_workspace) if db_workspace else None

    async def count_by_owner(self, owner_id: str) -> int:
        """
        Count workspaces for a specific owner.

        Args:
            owner_id: Owner user ID

        Returns:
            Count of workspaces
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(DbWorkspace)
            .where(DbWorkspace.owner_id == owner_id)
        )
        return result.scalar() or 0

    def _to_domain(self, db_workspace: DbWorkspace) -> Optional[Workspace]:
        """Convert database workspace to domain workspace."""
        if not db_workspace:
            return None

        import json
        metadata = {}
        if db_workspace.metadata_json:
            try:
                metadata = json.loads(db_workspace.metadata_json)
            except json.JSONDecodeError:
                pass

        return Workspace(
            id=db_workspace.id,
            name=db_workspace.name,
            description=db_workspace.description,
            owner_id=db_workspace.owner_id,
            metadata=metadata
        )

    def _to_db(self, workspace: Workspace) -> DbWorkspace:
        """Convert domain workspace to database workspace."""
        import json
        metadata_json = json.dumps(workspace.metadata) if workspace.metadata else "{}"

        return DbWorkspace(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            owner_id=workspace.owner_id,
            metadata_json=metadata_json
        )

    def _update_db_entity(self, db_workspace: DbWorkspace, workspace: Workspace) -> DbWorkspace:
        """Update database workspace from domain workspace."""
        import json

        db_workspace.name = workspace.name
        db_workspace.description = workspace.description
        db_workspace.metadata_json = json.dumps(workspace.metadata) if workspace.metadata else "{}"

        return db_workspace
```

### Conversation Repository

```python
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Conversation as DbConversation
from app.models.domain import Conversation
from app.database.repositories.generic import GenericRepository

class ConversationRepositoryImpl(GenericRepository[Conversation, DbConversation]):
    """Implementation of conversation repository."""

    def __init__(self, session: AsyncSession):
        """Initialize conversation repository."""
        super().__init__(session, Conversation, DbConversation)

    async def list_by_workspace(self, workspace_id: str, user_id: Optional[str] = None,
                              limit: int = 100, offset: int = 0) -> List[Conversation]:
        """
        List conversations in a workspace.

        Args:
            workspace_id: Workspace ID
            user_id: Optional user ID for access control
            limit: Maximum number of conversations to return
            offset: Pagination offset

        Returns:
            List of conversations
        """
        # Get conversations for workspace
        result = await self.session.execute(
            select(DbConversation)
            .where(DbConversation.workspace_id == workspace_id)
            .limit(limit)
            .offset(offset)
        )
        db_conversations = result.scalars().all()

        # Convert to domain models
        return [self._to_domain(db_conversation) for db_conversation in db_conversations]

    async def count_by_workspace(self, workspace_id: str) -> int:
        """
        Count conversations in a specific workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            Count of conversations
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(DbConversation)
            .where(DbConversation.workspace_id == workspace_id)
        )
        return result.scalar() or 0

    def _to_domain(self, db_conversation: DbConversation) -> Optional[Conversation]:
        """Convert database conversation to domain conversation."""
        if not db_conversation:
            return None

        import json
        metadata = {}
        if db_conversation.metadata_json:
            try:
                metadata = json.loads(db_conversation.metadata_json)
            except json.JSONDecodeError:
                pass

        # Get participant IDs
        participant_ids = []
        if db_conversation.participant_ids_json:
            try:
                participant_ids = json.loads(db_conversation.participant_ids_json)
            except json.JSONDecodeError:
                pass

        return Conversation(
            id=db_conversation.id,
            topic=db_conversation.topic,
            workspace_id=db_conversation.workspace_id,
            participant_ids=participant_ids,
            metadata=metadata
        )

    def _to_db(self, conversation: Conversation) -> DbConversation:
        """Convert domain conversation to database conversation."""
        import json
        metadata_json = json.dumps(conversation.metadata) if conversation.metadata else "{}"
        participant_ids_json = json.dumps(conversation.participant_ids) if conversation.participant_ids else "[]"

        return DbConversation(
            id=conversation.id,
            topic=conversation.topic,
            workspace_id=conversation.workspace_id,
            participant_ids_json=participant_ids_json,
            metadata_json=metadata_json
        )

    def _update_db_entity(self, db_conversation: DbConversation, conversation: Conversation) -> DbConversation:
        """Update database conversation from domain conversation."""
        import json

        db_conversation.topic = conversation.topic
        db_conversation.participant_ids_json = json.dumps(conversation.participant_ids) if conversation.participant_ids else "[]"
        db_conversation.metadata_json = json.dumps(conversation.metadata) if conversation.metadata else "{}"

        return db_conversation
```

### Message Repository

```python
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Message as DbMessage
from app.models.domain import Message
from app.database.repositories.generic import GenericRepository

class MessageRepositoryImpl(GenericRepository[Message, DbMessage]):
    """Implementation of message repository."""

    def __init__(self, session: AsyncSession):
        """Initialize message repository."""
        super().__init__(session, Message, DbMessage)

    async def list_by_conversation(self, conversation_id: str, limit: int = 100, offset: int = 0) -> List[Message]:
        """
        List messages in a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return
            offset: Pagination offset

        Returns:
            List of messages
        """
        result = await self.session.execute(
            select(DbMessage)
            .where(DbMessage.conversation_id == conversation_id)
            .order_by(DbMessage.timestamp)
            .limit(limit)
            .offset(offset)
        )
        db_messages = result.scalars().all()
        return [self._to_domain(db_message) for db_message in db_messages]

    async def count_by_conversation(self, conversation_id: str) -> int:
        """
        Count messages in a specific conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Count of messages
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(DbMessage)
            .where(DbMessage.conversation_id == conversation_id)
        )
        return result.scalar() or 0

    def _to_domain(self, db_message: DbMessage) -> Optional[Message]:
        """Convert database message to domain message."""
        if not db_message:
            return None

        import json
        metadata = {}
        if db_message.metadata_json:
            try:
                metadata = json.loads(db_message.metadata_json)
            except json.JSONDecodeError:
                pass

        return Message(
            id=db_message.id,
            content=db_message.content,
            sender_id=db_message.sender_id,
            conversation_id=db_message.conversation_id,
            timestamp=db_message.timestamp,
            metadata=metadata
        )

    def _to_db(self, message: Message) -> DbMessage:
        """Convert domain message to database message."""
        import json
        metadata_json = json.dumps(message.metadata) if message.metadata else "{}"

        return DbMessage(
            id=message.id,
            content=message.content,
            sender_id=message.sender_id,
            conversation_id=message.conversation_id,
            timestamp=message.timestamp,
            metadata_json=metadata_json
        )

    def _update_db_entity(self, db_message: DbMessage, message: Message) -> DbMessage:
        """Update database message from domain message."""
        import json

        db_message.content = message.content
        db_message.metadata_json = json.dumps(message.metadata) if message.metadata else "{}"

        return db_message
```

## Repository Factory

The Repository Factory creates and manages repository instances, ensuring they all use the same database session:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Type, TypeVar, Dict, Any

from app.database.repositories.user import UserRepositoryImpl
from app.database.repositories.workspace import WorkspaceRepositoryImpl
from app.database.repositories.conversation import ConversationRepositoryImpl
from app.database.repositories.message import MessageRepositoryImpl

# Type variables
T = TypeVar('T')
R = TypeVar('R')  # Repository type

class RepositoryFactory:
    """Factory for creating repositories."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository factory.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self._repositories: Dict[Type[R], R] = {}

    def get_user_repository(self) -> UserRepositoryImpl:
        """Get user repository."""
        return self._get_repository(UserRepositoryImpl)

    def get_workspace_repository(self) -> WorkspaceRepositoryImpl:
        """Get workspace repository."""
        return self._get_repository(WorkspaceRepositoryImpl)

    def get_conversation_repository(self) -> ConversationRepositoryImpl:
        """Get conversation repository."""
        return self._get_repository(ConversationRepositoryImpl)

    def get_message_repository(self) -> MessageRepositoryImpl:
        """Get message repository."""
        return self._get_repository(MessageRepositoryImpl)

    def _get_repository(self, repository_type: Type[R]) -> R:
        """
        Get repository of specified type.

        Args:
            repository_type: Repository type

        Returns:
            Repository instance
        """
        if repository_type not in self._repositories:
            self._repositories[repository_type] = repository_type(self.session)
        return self._repositories[repository_type]
```

## Domain Model Mapping

Domain model mapping is a crucial aspect of the Repository Pattern. Each repository is responsible for converting between domain models (Pydantic) and database models (SQLAlchemy).

### Key Concepts

1. **Repository-based Mapping**: Each repository defines mapping methods
2. **Strict Typing**: Type hints ensure correct model types
3. **Bidirectional Mapping**: Both domain-to-db and db-to-domain conversions
4. **Metadata Handling**: Special handling for JSON fields

### Common Mapping Methods

Each repository implements three key mapping methods:

1. **`_to_domain`**: Converts database model to domain model
2. **`_to_db`**: Converts domain model to database model
3. **`_update_db_entity`**: Updates database model from domain model

### Dealing with JSON Fields

SQLite stores JSON as text, so we need to handle serialization/deserialization:

```python
def _to_domain(self, db_entity) -> Optional[Domain]:
    """Convert database entity to domain entity."""
    if not db_entity:
        return None

    import json
    metadata = {}
    if db_entity.metadata_json:
        try:
            metadata = json.loads(db_entity.metadata_json)
        except json.JSONDecodeError:
            pass

    return Domain(
        # ... other fields ...
        metadata=metadata
    )

def _to_db(self, entity: Domain) -> DbEntity:
    """Convert domain entity to database entity."""
    import json
    metadata_json = json.dumps(entity.metadata) if entity.metadata else "{}"

    return DbEntity(
        # ... other fields ...
        metadata_json=metadata_json
    )
```

### Mapping Relationships

For relationships, we typically map just the IDs rather than loading related entities:

```python
def _to_domain(self, db_conversation: DbConversation) -> Optional[Conversation]:
    """Convert database conversation to domain conversation."""
    if not db_conversation:
        return None

    # ... other mapping ...

    return Conversation(
        id=db_conversation.id,
        topic=db_conversation.topic,
        workspace_id=db_conversation.workspace_id,  # Just map the ID
        participant_ids=participant_ids,
        metadata=metadata
    )
```

## Transaction Management

Transactions ensure database operations are atomic, consistent, isolated, and durable (ACID).

### Session-Based Transactions

SQLAlchemy sessions support transactions natively:

```python
async def create_item(item: Item):
    async with async_session_factory() as session:
        try:
            # Add item to session
            session.add(item)

            # Commit transaction
            await session.commit()
        except Exception:
            # Rollback on error
            await session.rollback()
            raise
```

### Unit of Work Pattern

For operations that span multiple repositories, use the Unit of Work pattern:

````python
class UnitOfWork:
    """
    Unit of Work pattern implementation for managing database transactions.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize Unit of Work.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.repositories = RepositoryFactory(session)

    async def commit(self) -> None:
        """Commit current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback current transaction."""
        await self.session.rollback()

    @classmethod
    @asynccontextmanager
    async def for_transaction(cls) -> AsyncContextManager["UnitOfWork"]:
        """
        Create a Unit of Work for a transaction.

        Example:
            ```
            async with UnitOfWork.for_transaction() as uow:
                # Do work with repositories
                workspace = await uow.repositories.get_workspace_repository().create(new_workspace)
                # Commit transaction
                await uow.commit()
            ```

        Returns:
            Unit of Work instance
        """
        session = None
        try:
            # Get a new session
            session_ctx = get_session()
            session = await session_ctx.__anext__()

            # Create Unit of Work
            uow = cls(session)

            # Yield to caller
            yield uow

            # Session is committed by caller using uow.commit()
        except Exception:
            # Rollback on exception
            if session:
                await session.rollback()
            raise
        finally:
            # Close session
            if session:
                await session.close()
````

### Transaction Usage Examples

#### Single Repository Transaction

```python
async def create_workspace(workspace_data: Dict[str, Any], owner_id: str) -> Workspace:
    """Create a new workspace."""
    async with async_session_factory() as session:
        try:
            # Create workspace entity
            workspace = Workspace(
                id=str(uuid.uuid4()),
                name=workspace_data["name"],
                description=workspace_data["description"],
                owner_id=owner_id,
                metadata=workspace_data.get("metadata", {})
            )

            # Create repository and save workspace
            workspace_repo = WorkspaceRepositoryImpl(session)
            created_workspace = await workspace_repo.create(workspace)

            # Commit transaction
            await session.commit()

            return created_workspace
        except Exception:
            # Rollback on error
            await session.rollback()
            raise
```

#### Multiple Repository Transaction with Unit of Work

```python
async def create_workspace_with_conversation(
    workspace_data: Dict[str, Any],
    conversation_data: Dict[str, Any],
    owner_id: str
) -> tuple[Workspace, Conversation]:
    """Create a workspace with an initial conversation."""
    async with UnitOfWork.for_transaction() as uow:
        try:
            # Create workspace
            workspace = Workspace(
                id=str(uuid.uuid4()),
                name=workspace_data["name"],
                description=workspace_data["description"],
                owner_id=owner_id,
                metadata=workspace_data.get("metadata", {})
            )

            workspace_repo = uow.repositories.get_workspace_repository()
            created_workspace = await workspace_repo.create(workspace)

            # Create conversation in the workspace
            conversation = Conversation(
                id=str(uuid.uuid4()),
                topic=conversation_data["topic"],
                workspace_id=created_workspace.id,
                participant_ids=[owner_id],
                metadata=conversation_data.get("metadata", {})
            )

            conversation_repo = uow.repositories.get_conversation_repository()
            created_conversation = await conversation_repo.create(conversation)

            # Commit transaction
            await uow.commit()

            return created_workspace, created_conversation
        except Exception:
            # Transaction is automatically rolled back by context manager
            raise
```

## Error Handling

Proper error handling is crucial for robust repositories.

### Custom Repository Exceptions

Create custom exceptions for the repository layer:

```python
class RepositoryError(Exception):
    """Base exception for repository errors."""

    def __init__(self, message: str, original_exception: Exception = None):
        """
        Initialize repository error.

        Args:
            message: Error message
            original_exception: Original exception that caused this error
        """
        self.message = message
        self.original_exception = original_exception
        super().__init__(message)

class EntityNotFoundError(RepositoryError):
    """Entity not found error."""

    def __init__(self, entity_type: str, entity_id: str):
        """
        Initialize entity not found error.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
        """
        self.entity_type = entity_type
        self.entity_id = entity_id
        message = f"{entity_type} not found: {entity_id}"
        super().__init__(message)

class AccessDeniedError(RepositoryError):
    """Access denied error."""

    def __init__(self, entity_type: str, entity_id: str, user_id: str):
        """
        Initialize access denied error.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            user_id: User ID
        """
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.user_id = user_id
        message = f"Access denied to {entity_type} {entity_id} for user {user_id}"
        super().__init__(message)

class DuplicateEntityError(RepositoryError):
    """Duplicate entity error."""

    def __init__(self, entity_type: str, field: str, value: str):
        """
        Initialize duplicate entity error.

        Args:
            entity_type: Entity type
            field: Field name
            value: Field value
        """
        self.entity_type = entity_type
        self.field = field
        self.value = value
        message = f"{entity_type} with {field}={value} already exists"
        super().__init__(message)

class DatabaseError(RepositoryError):
    """Database error."""

    def __init__(self, message: str, original_exception: Exception = None):
        """
        Initialize database error.

        Args:
            message: Error message
            original_exception: Original exception that caused this error
        """
        super().__init__(message, original_exception)
```

### Error Mapping in Repositories

Map SQLAlchemy errors to custom repository exceptions:

```python
def _handle_db_error(self, error: Exception, message: str, entity_type: str = None):
    """
    Handle database error.

    Args:
        error: Original exception
        message: Error message
        entity_type: Optional entity type

    Raises:
        RepositoryError: Appropriate repository error
    """
    from sqlalchemy.exc import IntegrityError, OperationalError, NoResultFound

    # Map SQLAlchemy errors to custom exceptions
    if isinstance(error, NoResultFound):
        if entity_type:
            raise EntityNotFoundError(entity_type, "unknown")
        else:
            raise RepositoryError(f"{message}: not found", error)
    elif isinstance(error, IntegrityError):
        # Check for specific errors
        error_str = str(error).lower()
        if "unique constraint" in error_str:
            if entity_type:
                # Try to extract field and value from error message
                field = "unknown"
                value = "unknown"
                raise DuplicateEntityError(entity_type, field, value)
            else:
                raise RepositoryError(f"{message}: unique constraint violation", error)
        else:
            raise RepositoryError(f"{message}: integrity error", error)
    elif isinstance(error, OperationalError):
        raise DatabaseError(f"{message}: database error", error)
    else:
        raise RepositoryError(f"{message}: {str(error)}", error)
```

### Exception Handling in Services

Handle repository exceptions in service methods:

```python
async def get_workspace(workspace_id: str, user_id: str) -> Workspace:
    """
    Get workspace by ID.

    Args:
        workspace_id: Workspace ID
        user_id: User ID for access control

    Returns:
        Workspace if found and accessible

    Raises:
        EntityNotFoundError: If workspace not found
        AccessDeniedError: If user does not have access
        RepositoryError: For other repository errors
    """
    try:
        async with UnitOfWork.for_transaction() as uow:
            workspace_repo = uow.repositories.get_workspace_repository()
            workspace = await workspace_repo.get_by_id(workspace_id)

            if not workspace:
                raise EntityNotFoundError("Workspace", workspace_id)

            if workspace.owner_id != user_id:
                raise AccessDeniedError("Workspace", workspace_id, user_id)

            return workspace
    except (EntityNotFoundError, AccessDeniedError):
        # Re-raise these exceptions
        raise
    except Exception as e:
        # Log and wrap other exceptions
        import logging
        logging.error(f"Error getting workspace {workspace_id}: {str(e)}")
        raise RepositoryError(f"Failed to get workspace: {str(e)}", e)
```

## User-Based Access Control

Implement user-based access control directly in repositories to enforce data partitioning.

### Access Control in Repository Methods

Add user ID parameters to repository methods:

```python
async def get_by_id(self, entity_id: str, user_id: Optional[str] = None) -> Optional[Workspace]:
    """
    Get workspace by ID.

    Args:
        entity_id: Workspace ID
        user_id: Optional user ID for access control

    Returns:
        Workspace if found and accessible, None otherwise
    """
    query = select(DbWorkspace).where(DbWorkspace.id == entity_id)

    # Apply owner filter if provided (for access control)
    if user_id:
        query = query.where(DbWorkspace.owner_id == user_id)

    result = await self.session.execute(query)
    db_workspace = result.scalars().first()
    return self._to_domain(db_workspace) if db_workspace else None
```

### Access Control in Higher Layers

Also enforce access control in service methods for complex cases:

```python
async def get_conversation_with_access_check(conversation_id: str, user_id: str) -> Conversation:
    """
    Get conversation by ID with access check.

    Args:
        conversation_id: Conversation ID
        user_id: User ID for access control

    Returns:
        Conversation if found and accessible

    Raises:
        EntityNotFoundError: If conversation not found
        AccessDeniedError: If user does not have access
    """
    async with UnitOfWork.for_transaction() as uow:
        # Get conversation
        conversation_repo = uow.repositories.get_conversation_repository()
        conversation = await conversation_repo.get_by_id(conversation_id)

        if not conversation:
            raise EntityNotFoundError("Conversation", conversation_id)

        # Check if user is a participant
        if user_id in conversation.participant_ids:
            return conversation

        # Check if user is workspace owner
        workspace_repo = uow.repositories.get_workspace_repository()
        workspace = await workspace_repo.get_by_id(conversation.workspace_id)

        if workspace and workspace.owner_id == user_id:
            return conversation

        # Access denied
        raise AccessDeniedError("Conversation", conversation_id, user_id)
```

## Using Repositories with FastAPI

Integrate repositories with FastAPI endpoints using dependency injection.

### Database Session Dependency

Create a dependency for providing database sessions:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.config import get_session

async def get_db() -> AsyncSession:
    """
    Get database session.

    Returns:
        AsyncSession: Database session
    """
    async for session in get_session():
        try:
            yield session
        finally:
            await session.close()
```

### Repository Factory Dependency

Create a dependency for providing repository factories:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.factory import RepositoryFactory

async def get_repository_factory(db: AsyncSession = Depends(get_db)) -> RepositoryFactory:
    """
    Get repository factory.

    Args:
        db: Database session

    Returns:
        Repository factory
    """
    return RepositoryFactory(db)
```

### Example FastAPI Endpoint

Use repositories in FastAPI endpoints:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.config import get_db
from app.database.repositories.factory import RepositoryFactory
from app.utils.auth import get_current_user
from app.models.api.request import WorkspaceCreate
from app.models.api.response import WorkspaceResponse
from app.models.domain import Workspace
from app.database.exceptions import RepositoryError, EntityNotFoundError, AccessDeniedError

router = APIRouter(prefix="/config", tags=["config"])

@router.post("/workspace", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreate,
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new workspace."""
    try:
        # Create workspace entity
        import uuid
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name=request.name,
            description=request.description,
            owner_id=current_user["user_id"],
            metadata=request.metadata
        )

        # Save workspace
        workspace_repo = repo_factory.get_workspace_repository()
        created_workspace = await workspace_repo.create(workspace)

        # Commit transaction
        await db.commit()

        # Return response
        return WorkspaceResponse(
            status="workspace created",
            workspace=created_workspace
        )
    except Exception as e:
        # Rollback transaction
        await db.rollback()

        # Handle specific errors
        if isinstance(e, RepositoryError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Generic error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workspace"
        )
```

## Testing Repositories

### Unit Testing Repositories

Use in-memory SQLite for unit testing repositories:

```python
import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base
from app.models.domain import User, Workspace
from app.database.repositories.user import UserRepositoryImpl
from app.database.repositories.workspace import WorkspaceRepositoryImpl

# Create in-memory test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db():
    """Create test database."""
    # Create engine
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    # Yield session
    async with async_session() as session:
        yield session

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Close engine
    await engine.dispose()

@pytest.fixture
def user_data():
    """Create test user data."""
    return User(
        user_id=str(uuid.uuid4()),
        name="Test User",
        email="test@example.com",
        metadata={"test": True}
    )

@pytest.mark.asyncio
async def test_user_repository(test_db, user_data):
    """Test user repository."""
    # Create repository
    repo = UserRepositoryImpl(test_db)

    # Create user
    created_user = await repo.create(user_data)
    assert created_user.user_id == user_data.user_id
    assert created_user.name == user_data.name
    assert created_user.email == user_data.email

    # Get user by ID
    retrieved_user = await repo.get_by_id(user_data.user_id)
    assert retrieved_user is not None
    assert retrieved_user.user_id == user_data.user_id

    # Get user by email
    email_user = await repo.get_by_email(user_data.email)
    assert email_user is not None
    assert email_user.user_id == user_data.user_id

    # Update user
    user_data.name = "Updated Name"
    updated_user = await repo.update(user_data)
    assert updated_user.name == "Updated Name"

    # Delete user
    result = await repo.delete(user_data.user_id)
    assert result is True

    # Verify deletion
    deleted_user = await repo.get_by_id(user_data.user_id)
    assert deleted_user is None
```

### Integration Testing with Unit of Work

Test repositories with the Unit of Work pattern:

```python
@pytest.mark.asyncio
async def test_unit_of_work():
    """Test Unit of Work pattern."""
    # Create user data
    user = User(
        user_id=str(uuid.uuid4()),
        name="Test User",
        email="test@example.com",
        metadata={"test": True}
    )

    # Use Unit of Work
    async with UnitOfWork.for_transaction() as uow:
        # Create user
        user_repo = uow.repositories.get_user_repository()
        created_user = await user_repo.create(user)

        # Create workspace
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name="Test Workspace",
            description="Test description",
            owner_id=created_user.user_id,
            metadata={"test": True}
        )

        workspace_repo = uow.repositories.get_workspace_repository()
        created_workspace = await workspace_repo.create(workspace)

        # Commit transaction
        await uow.commit()

    # Verify in new Unit of Work
    async with UnitOfWork.for_transaction() as uow2:
        # Get workspace
        workspace_repo = uow2.repositories.get_workspace_repository()
        retrieved_workspace = await workspace_repo.get_by_id(created_workspace.id)

        assert retrieved_workspace is not None
        assert retrieved_workspace.name == workspace.name
        assert retrieved_workspace.owner_id == user.user_id
```

### Mocking Repositories for Service Testing

Create mock repositories for testing services:

```python
class MockWorkspaceRepository:
    """Mock workspace repository for testing."""

    def __init__(self):
        """Initialize mock repository."""
        self.workspaces = {}

    async def create(self, workspace: Workspace) -> Workspace:
        """Create a workspace."""
        self.workspaces[workspace.id] = workspace
        return workspace

    async def get_by_id(self, entity_id: str, owner_id: Optional[str] = None) -> Optional[Workspace]:
        """Get workspace by ID."""
        workspace = self.workspaces.get(entity_id)

        if not workspace:
            return None

        if owner_id and workspace.owner_id != owner_id:
            return None

        return workspace

    async def list_by_owner(self, owner_id: str, limit: int = 100, offset: int = 0) -> List[Workspace]:
        """List workspaces by owner."""
        return [
            workspace for workspace in self.workspaces.values()
            if workspace.owner_id == owner_id
        ][offset:offset+limit]

    async def update(self, workspace: Workspace) -> Workspace:
        """Update a workspace."""
        if workspace.id not in self.workspaces:
            raise ValueError(f"Workspace not found: {workspace.id}")

        self.workspaces[workspace.id] = workspace
        return workspace

    async def delete(self, entity_id: str, owner_id: Optional[str] = None) -> bool:
        """Delete a workspace."""
        if entity_id not in self.workspaces:
            return False

        workspace = self.workspaces[entity_id]

        if owner_id and workspace.owner_id != owner_id:
            return False

        del self.workspaces[entity_id]
        return True

    async def count_by_owner(self, owner_id: str) -> int:
        """Count workspaces by owner."""
        return len([
            workspace for workspace in self.workspaces.values()
            if workspace.owner_id == owner_id
        ])

@pytest.mark.asyncio
async def test_workspace_service():
    """Test workspace service with mock repository."""
    # Create mock repository
    repo = MockWorkspaceRepository()

    # Create workspace service with mock repository
    from app.services.workspace import WorkspaceService
    service = WorkspaceService(repo)

    # Test get_workspace
    workspace_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())

    # Create test workspace
    workspace = Workspace(
        id=workspace_id,
        name="Test Workspace",
        description="Test description",
        owner_id=owner_id,
        metadata={"test": True}
    )

    # Add to mock repository
    await repo.create(workspace)

    # Test get_workspace
    retrieved_workspace = await service.get_workspace(workspace_id, owner_id)
    assert retrieved_workspace is not None
    assert retrieved_workspace.id == workspace_id
    assert retrieved_workspace.owner_id == owner_id

    # Test access control
    other_user_id = str(uuid.uuid4())
    with pytest.raises(AccessDeniedError):
        await service.get_workspace(workspace_id, other_user_id)
```

## Best Practices and Pitfalls

### Best Practices

1. **Consistent Mapping**: Keep mapping logic consistent across repositories
2. **Use Transactions**: Always use transactions for data consistency
3. **Enforce Access Control**: Always check user access at the repository level
4. **Error Handling**: Use custom exceptions for repository errors
5. **Pagination**: Always use pagination for list operations
6. **Repository Factory**: Use a factory to manage repository instances
7. **Keep Domain Models Pure**: Domain models should not depend on database models
8. **Unit Testing**: Test repositories with in-memory SQLite database

### Common Pitfalls

1. **Leaking Database Models**: Never expose database models outside repositories
2. **Missing Transactions**: Forgetting to commit/rollback transactions
3. **Inappropriate Access Control**: Not checking user access in repositories
4. **Inconsistent Error Handling**: Inconsistent exception handling
5. **N+1 Query Problem**: Making multiple queries for related data
6. **JSON Handling**: Forgetting to handle JSON serialization/deserialization
7. **Connection Management**: Not properly closing database connections
8. **Missing Pagination**: Loading too much data at once

### Performance Considerations

1. **Eager vs. Lazy Loading**: Choose appropriate loading strategies
2. **Index Usage**: Ensure queries use appropriate indices
3. **Pagination**: Always paginate list operations
4. **Transaction Scope**: Keep transactions as short as possible
5. **Connection Pooling**: Configure connection pool appropriately

### Edge Cases to Handle

1. **Concurrent Updates**: Handle database locks and race conditions
2. **Invalid JSON**: Handle invalid JSON in metadata fields
3. **Missing Related Entities**: Handle missing related entities gracefully
4. **Database Unavailability**: Handle database connection errors
5. **Transaction Failures**: Handle transaction rollback failures

## Integration with Other Components

### Using Repositories with Event Bus

Process events with repositories:

```python
from app.core.event_bus import event_bus
from app.database.unit_of_work import UnitOfWork
from app.models.domain import Message
from datetime import datetime

async def handle_input_event(event):
    """
    Handle input event.

    Args:
        event: Input event
    """
    user_id = event.get("user_id")
    data = event.get("data", {})

    # Create message from event
    message = Message(
        id=str(uuid.uuid4()),
        content=data.get("content", ""),
        sender_id=user_id,
        conversation_id=data.get("conversation_id", "default"),
        timestamp=data.get("timestamp", datetime.now().isoformat()),
        metadata=event.get("metadata", {})
    )

    # Store message in database
    async with UnitOfWork.for_transaction() as uow:
        try:
            # Save message
            message_repo = uow.repositories.get_message_repository()
            created_message = await message_repo.create(message)

            # Commit transaction
            await uow.commit()

            # Log success
            logger.info(f"Message stored: {created_message.id}")
        except Exception as e:
            # Log error
            logger.error(f"Failed to store message: {str(e)}")
            # Transaction is automatically rolled back
```

### Using Repositories with Services

Create service layer that uses repositories:

```python
class WorkspaceService:
    """Service for workspace operations."""

    def __init__(self, workspace_repository: WorkspaceRepositoryImpl = None):
        """Initialize workspace service."""
        self.workspace_repository = workspace_repository

    async def create_workspace(self, name: str, description: str, owner_id: str, metadata: Dict[str, Any] = None) -> Workspace:
        """
        Create a new workspace.

        Args:
            name: Workspace name
            description: Workspace description
            owner_id: Owner user ID
            metadata: Optional metadata

        Returns:
            Created workspace
        """
        # Create workspace entity
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            owner_id=owner_id,
            metadata=metadata or {}
        )

        # Save workspace
        async with UnitOfWork.for_transaction() as uow:
            try:
                workspace_repo = self.workspace_repository or uow.repositories.get_workspace_repository()
                created_workspace = await workspace_repo.create(workspace)

                # Commit transaction
                await uow.commit()

                return created_workspace
            except Exception as e:
                # Log error
                logger.error(f"Failed to create workspace: {str(e)}")
                # Transaction is automatically rolled back
                raise
```

This document provides a comprehensive guide to implementing the Repository Pattern in Phase 2 of the Cortex Core. By following these guidelines, you'll create a clean, maintainable abstraction layer between your business logic and the database.
