# Persistence Implementation Guide for Cortex Core (Phase 2)

This document provides a comprehensive guide to implementing the SQLite-based persistence layer for Phase 2 of the Cortex Core. It covers database setup, SQLAlchemy integration, repository pattern implementation, and migration strategies to move from the in-memory storage of Phase 1 to the persistent storage in Phase 2.

## Table of Contents

1. [Overview](#overview)
2. [Database Configuration](#database-configuration)
3. [SQLAlchemy Models](#sqlalchemy-models)
4. [Repository Pattern Implementation](#repository-pattern-implementation)
5. [Transaction Management](#transaction-management)
6. [Domain Model Mapping](#domain-model-mapping)
7. [Database Initialization](#database-initialization)
8. [Error Handling](#error-handling)
9. [Migration Strategy](#migration-strategy)
10. [Testing Approach](#testing-approach)
11. [Performance Considerations](#performance-considerations)
12. [Common Pitfalls](#common-pitfalls)
13. [Appendix: Complete Implementation Examples](#appendix-complete-implementation-examples)

## Overview

Phase 2 transitions the Cortex Core from in-memory storage to SQLite persistence. This transition allows data to survive application restarts while maintaining a simple deployment model with a single file database.

### Key Design Principles

1. **Simplicity over Sophistication**: Keep the database schema as simple as possible
2. **Repository Pattern**: Abstract data access through repositories to separate business logic from data storage
3. **Clear Separation**: Maintain distinct database models (SQLAlchemy) and domain models (Pydantic)
4. **User Partitioning**: Continue enforcing strict data partitioning by user ID
5. **Transaction Safety**: Use transactions to maintain data consistency
6. **Minimal Schema**: Focus on essential tables and relationships only
7. **Pragmatic Storage**: Use TEXT/JSON fields where appropriate instead of complex normalization

### Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  API Layer  │────▶│   Services  │────▶│ Repositories │────▶│  SQLAlchemy │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                                        │                   │
       │                                        │                   │
       ▼                                        ▼                   ▼
┌─────────────┐                        ┌─────────────┐      ┌─────────────┐
│ Pydantic    │                        │ Repository  │      │ SQLite      │
│ Models      │                        │ Interfaces  │      │ Database    │
└─────────────┘                        └─────────────┘      └─────────────┘
```

## Database Configuration

### Environment Variables

Add these variables to your `.env` file:

```
# Database configuration
DATABASE_URL=sqlite+aiosqlite:///./cortex.db
DB_ECHO=false  # Set to true for development to log SQL queries
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```

### Required Dependencies

Add these to your `requirements.txt`:

```
sqlalchemy>=2.0.0
aiosqlite>=0.17.0
alembic>=1.8.0  # Optional, for database migrations
```

### SQLAlchemy Configuration and Setup

Create a new file `app/database/config.py`:

```python
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./cortex.db")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

# Create engine
engine = create_async_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    poolclass=QueuePool,
    pool_size=int(os.getenv("DB_POOL_SIZE", 20)),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 10)),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", 30)),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", 1800)),
)

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)

async def get_session() -> AsyncSession:
    """
    Get a database session.

    Returns:
        AsyncSession: Database session
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
```

### Database Session Management

Create a dependency to provide database sessions in FastAPI endpoints:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.config import get_session

# Use this dependency to get a session in your endpoints
async def get_db() -> AsyncSession:
    async for session in get_session():
        yield session

# Example usage in an endpoint
@app.get("/items")
async def read_items(db: AsyncSession = Depends(get_db)):
    # Use db session here
    pass
```

## SQLAlchemy Models

### Base Model Setup

Create a new file `app/database/models.py`:

```python
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Text, ForeignKey, Table, MetaData, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class BaseModel:
    """Base model with common methods for SQLAlchemy models."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create model from dictionary."""
        return cls(**data)

    def get_metadata(self) -> Dict[str, Any]:
        """Get model metadata."""
        if hasattr(self, 'metadata_json') and self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Set model metadata."""
        if hasattr(self, 'metadata_json'):
            self.metadata_json = json.dumps(metadata) if metadata else "{}"
```

### Entity Models

Now define the database models for each entity:

```python
class User(Base, BaseModel):
    """User database model."""
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    metadata_json = Column(Text, default="{}")

    # Relationships
    workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="sender", cascade="all, delete-orphan")

class Workspace(Base, BaseModel):
    """Workspace database model."""
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    metadata_json = Column(Text, default="{}")

    # Relationships
    owner = relationship("User", back_populates="workspaces")
    conversations = relationship("Conversation", back_populates="workspace", cascade="all, delete-orphan")

class Conversation(Base, BaseModel):
    """Conversation database model."""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True)
    topic = Column(String(200), nullable=False)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    metadata_json = Column(Text, default="{}")

    # Store participant IDs as JSON in SQLite
    # In a more normalized schema, this would be a separate table
    participant_ids_json = Column(Text, nullable=False, default="[]")

    # Relationships
    workspace = relationship("Workspace", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    @property
    def participant_ids(self) -> list:
        """Get participant IDs as a list."""
        try:
            return json.loads(self.participant_ids_json)
        except (json.JSONDecodeError, TypeError):
            return []

    @participant_ids.setter
    def participant_ids(self, value: list) -> None:
        """Set participant IDs from a list."""
        self.participant_ids_json = json.dumps(value) if value else "[]"

class Message(Base, BaseModel):
    """Message database model."""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    content = Column(Text, nullable=False)
    sender_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    timestamp = Column(String(50), nullable=False)  # ISO format timestamp
    metadata_json = Column(Text, default="{}")

    # Relationships
    sender = relationship("User", back_populates="messages")
    conversation = relationship("Conversation", back_populates="messages")
```

### Indices for Performance

Create indices for frequently queried fields:

```python
from sqlalchemy import Index

# Add these at the end of the models.py file

# Indices
Index('idx_workspace_owner', Workspace.owner_id)
Index('idx_conversation_workspace', Conversation.workspace_id)
Index('idx_message_conversation', Message.conversation_id)
Index('idx_message_sender', Message.sender_id)
Index('idx_message_timestamp', Message.timestamp)
```

## Repository Pattern Implementation

### Repository Interface

Create the repository interface in `app/database/repositories/base.py`:

```python
from typing import TypeVar, Generic, List, Optional, Any, Dict, Type
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T]):
    """Base repository interface for database operations."""

    def __init__(self, session: AsyncSession, model_type: Type[T]):
        """
        Initialize repository.

        Args:
            session: SQLAlchemy async session
            model_type: Pydantic model type for this repository
        """
        self.session = session
        self.model_type = model_type

    async def create(self, entity: T) -> T:
        """
        Create a new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity
        """
        raise NotImplementedError

    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        raise NotImplementedError

    async def list(self, filters: Dict[str, Any] = None, limit: int = 100, offset: int = 0) -> List[T]:
        """
        List entities with optional filtering.

        Args:
            filters: Optional filters
            limit: Maximum number of entities to return
            offset: Pagination offset

        Returns:
            List of entities
        """
        raise NotImplementedError

    async def update(self, entity: T) -> T:
        """
        Update an existing entity.

        Args:
            entity: Entity to update

        Returns:
            Updated entity
        """
        raise NotImplementedError

    async def delete(self, entity_id: str) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            True if entity was deleted, False otherwise
        """
        raise NotImplementedError

    async def count(self, filters: Dict[str, Any] = None) -> int:
        """
        Count entities with optional filtering.

        Args:
            filters: Optional filters

        Returns:
            Count of entities
        """
        raise NotImplementedError
```

### Specific Repository Implementations

#### User Repository

Create `app/database/repositories/user_repository.py`:

```python
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User as DbUser
from app.models.domain import User
from app.database.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    """Repository for user operations."""

    def __init__(self, session: AsyncSession):
        """Initialize user repository."""
        super().__init__(session, User)

    async def create(self, entity: User) -> User:
        """Create a new user."""
        # Map domain model to database model
        db_user = DbUser(
            user_id=entity.user_id,
            name=entity.name,
            email=entity.email,
            metadata_json=self._serialize_metadata(entity.metadata)
        )

        # Add to session
        self.session.add(db_user)
        await self.session.flush()

        # Return domain model
        return self._to_domain(db_user)

    async def get_by_id(self, entity_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(DbUser).where(DbUser.user_id == entity_id)
        )
        db_user = result.scalars().first()
        return self._to_domain(db_user) if db_user else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(
            select(DbUser).where(DbUser.email == email)
        )
        db_user = result.scalars().first()
        return self._to_domain(db_user) if db_user else None

    async def list(self, filters: Dict[str, Any] = None, limit: int = 100, offset: int = 0) -> List[User]:
        """List users with optional filtering."""
        query = select(DbUser)

        # Apply filters if provided
        if filters:
            if 'email' in filters:
                query = query.where(DbUser.email == filters['email'])

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Execute query
        result = await self.session.execute(query)
        db_users = result.scalars().all()

        # Convert to domain models
        return [self._to_domain(db_user) for db_user in db_users]

    async def update(self, entity: User) -> User:
        """Update an existing user."""
        # Get existing user
        result = await self.session.execute(
            select(DbUser).where(DbUser.user_id == entity.user_id)
        )
        db_user = result.scalars().first()

        if not db_user:
            raise ValueError(f"User not found: {entity.user_id}")

        # Update fields
        db_user.name = entity.name
        db_user.email = entity.email
        db_user.metadata_json = self._serialize_metadata(entity.metadata)

        # Flush changes
        await self.session.flush()

        # Return domain model
        return self._to_domain(db_user)

    async def delete(self, entity_id: str) -> bool:
        """Delete user by ID."""
        result = await self.session.execute(
            delete(DbUser).where(DbUser.user_id == entity_id)
        )
        return result.rowcount > 0

    async def count(self, filters: Dict[str, Any] = None) -> int:
        """Count users with optional filtering."""
        query = select(func.count()).select_from(DbUser)

        # Apply filters if provided
        if filters:
            if 'email' in filters:
                query = query.where(DbUser.email == filters['email'])

        # Execute query
        result = await self.session.execute(query)
        return result.scalar() or 0

    def _to_domain(self, db_user: DbUser) -> User:
        """Convert database model to domain model."""
        if not db_user:
            return None

        return User(
            user_id=db_user.user_id,
            name=db_user.name,
            email=db_user.email,
            metadata=self._deserialize_metadata(db_user.metadata_json)
        )

    def _serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        """Serialize metadata to JSON string."""
        import json
        return json.dumps(metadata) if metadata else "{}"

    def _deserialize_metadata(self, metadata_json: str) -> Dict[str, Any]:
        """Deserialize metadata from JSON string."""
        import json
        if not metadata_json:
            return {}
        try:
            return json.loads(metadata_json)
        except json.JSONDecodeError:
            return {}
```

#### Workspace Repository

Create `app/database/repositories/workspace_repository.py`:

```python
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Workspace as DbWorkspace
from app.models.domain import Workspace
from app.database.repositories.base import BaseRepository

class WorkspaceRepository(BaseRepository[Workspace]):
    """Repository for workspace operations."""

    def __init__(self, session: AsyncSession):
        """Initialize workspace repository."""
        super().__init__(session, Workspace)

    async def create(self, entity: Workspace) -> Workspace:
        """Create a new workspace."""
        # Map domain model to database model
        db_workspace = DbWorkspace(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            owner_id=entity.owner_id,
            metadata_json=self._serialize_metadata(entity.metadata)
        )

        # Add to session
        self.session.add(db_workspace)
        await self.session.flush()

        # Return domain model
        return self._to_domain(db_workspace)

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

    async def list_by_owner(self, owner_id: str, limit: int = 100, offset: int = 0) -> List[Workspace]:
        """List workspaces for a specific owner."""
        result = await self.session.execute(
            select(DbWorkspace)
            .where(DbWorkspace.owner_id == owner_id)
            .limit(limit)
            .offset(offset)
        )
        db_workspaces = result.scalars().all()
        return [self._to_domain(db_workspace) for db_workspace in db_workspaces]

    async def list(self, filters: Dict[str, Any] = None, limit: int = 100, offset: int = 0) -> List[Workspace]:
        """List workspaces with optional filtering."""
        query = select(DbWorkspace)

        # Apply filters if provided
        if filters:
            if 'owner_id' in filters:
                query = query.where(DbWorkspace.owner_id == filters['owner_id'])
            if 'name' in filters:
                query = query.where(DbWorkspace.name.like(f"%{filters['name']}%"))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Execute query
        result = await self.session.execute(query)
        db_workspaces = result.scalars().all()

        # Convert to domain models
        return [self._to_domain(db_workspace) for db_workspace in db_workspaces]

    async def update(self, entity: Workspace) -> Workspace:
        """Update an existing workspace."""
        # Get existing workspace
        result = await self.session.execute(
            select(DbWorkspace).where(DbWorkspace.id == entity.id)
        )
        db_workspace = result.scalars().first()

        if not db_workspace:
            raise ValueError(f"Workspace not found: {entity.id}")

        # Verify ownership (optional but recommended)
        if db_workspace.owner_id != entity.owner_id:
            raise ValueError(f"Workspace {entity.id} does not belong to user {entity.owner_id}")

        # Update fields
        db_workspace.name = entity.name
        db_workspace.description = entity.description
        db_workspace.metadata_json = self._serialize_metadata(entity.metadata)

        # Flush changes
        await self.session.flush()

        # Return domain model
        return self._to_domain(db_workspace)

    async def delete(self, entity_id: str, owner_id: Optional[str] = None) -> bool:
        """
        Delete workspace by ID.

        Args:
            entity_id: Workspace ID
            owner_id: Optional owner ID for access control

        Returns:
            True if workspace was deleted, False otherwise
        """
        query = delete(DbWorkspace).where(DbWorkspace.id == entity_id)

        # Apply owner filter if provided (for access control)
        if owner_id:
            query = query.where(DbWorkspace.owner_id == owner_id)

        result = await self.session.execute(query)
        return result.rowcount > 0

    async def count(self, filters: Dict[str, Any] = None) -> int:
        """Count workspaces with optional filtering."""
        query = select(func.count()).select_from(DbWorkspace)

        # Apply filters if provided
        if filters:
            if 'owner_id' in filters:
                query = query.where(DbWorkspace.owner_id == filters['owner_id'])
            if 'name' in filters:
                query = query.where(DbWorkspace.name.like(f"%{filters['name']}%"))

        # Execute query
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_by_owner(self, owner_id: str) -> int:
        """Count workspaces for a specific owner."""
        result = await self.session.execute(
            select(func.count())
            .select_from(DbWorkspace)
            .where(DbWorkspace.owner_id == owner_id)
        )
        return result.scalar() or 0

    def _to_domain(self, db_workspace: DbWorkspace) -> Workspace:
        """Convert database model to domain model."""
        if not db_workspace:
            return None

        return Workspace(
            id=db_workspace.id,
            name=db_workspace.name,
            description=db_workspace.description,
            owner_id=db_workspace.owner_id,
            metadata=self._deserialize_metadata(db_workspace.metadata_json)
        )

    def _serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        """Serialize metadata to JSON string."""
        import json
        return json.dumps(metadata) if metadata else "{}"

    def _deserialize_metadata(self, metadata_json: str) -> Dict[str, Any]:
        """Deserialize metadata from JSON string."""
        import json
        if not metadata_json:
            return {}
        try:
            return json.loads(metadata_json)
        except json.JSONDecodeError:
            return {}
```

#### Conversation Repository

Create `app/database/repositories/conversation_repository.py`:

```python
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Conversation as DbConversation
from app.models.domain import Conversation
from app.database.repositories.base import BaseRepository

class ConversationRepository(BaseRepository[Conversation]):
    """Repository for conversation operations."""

    def __init__(self, session: AsyncSession):
        """Initialize conversation repository."""
        super().__init__(session, Conversation)

    async def create(self, entity: Conversation) -> Conversation:
        """Create a new conversation."""
        # Map domain model to database model
        db_conversation = DbConversation(
            id=entity.id,
            topic=entity.topic,
            workspace_id=entity.workspace_id,
            metadata_json=self._serialize_metadata(entity.metadata)
        )

        # Set participant IDs
        db_conversation.participant_ids = entity.participant_ids

        # Add to session
        self.session.add(db_conversation)
        await self.session.flush()

        # Return domain model
        return self._to_domain(db_conversation)

    async def get_by_id(self, entity_id: str, user_id: Optional[str] = None) -> Optional[Conversation]:
        """
        Get conversation by ID.

        Args:
            entity_id: Conversation ID
            user_id: Optional user ID for access control

        Returns:
            Conversation if found and accessible, None otherwise
        """
        query = select(DbConversation).where(DbConversation.id == entity_id)

        result = await self.session.execute(query)
        db_conversation = result.scalars().first()

        if not db_conversation:
            return None

        # Check if user has access to this conversation
        if user_id and user_id not in db_conversation.participant_ids:
            # Get the workspace to check if user is the owner
            from app.database.models import Workspace
            workspace_result = await self.session.execute(
                select(Workspace).where(Workspace.id == db_conversation.workspace_id)
            )
            workspace = workspace_result.scalars().first()

            if not workspace or workspace.owner_id != user_id:
                return None

        return self._to_domain(db_conversation)

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
        # First check if user has access to the workspace
        if user_id:
            from app.database.models import Workspace
            workspace_result = await self.session.execute(
                select(Workspace).where(
                    Workspace.id == workspace_id,
                    Workspace.owner_id == user_id
                )
            )
            workspace = workspace_result.scalars().first()

            if not workspace:
                return []

        # Get conversations
        result = await self.session.execute(
            select(DbConversation)
            .where(DbConversation.workspace_id == workspace_id)
            .limit(limit)
            .offset(offset)
        )
        db_conversations = result.scalars().all()

        # Convert to domain models
        return [self._to_domain(db_conversation) for db_conversation in db_conversations]

    async def list(self, filters: Dict[str, Any] = None, limit: int = 100, offset: int = 0) -> List[Conversation]:
        """List conversations with optional filtering."""
        query = select(DbConversation)

        # Apply filters if provided
        if filters:
            if 'workspace_id' in filters:
                query = query.where(DbConversation.workspace_id == filters['workspace_id'])
            if 'topic' in filters:
                query = query.where(DbConversation.topic.like(f"%{filters['topic']}%"))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Execute query
        result = await self.session.execute(query)
        db_conversations = result.scalars().all()

        # Convert to domain models
        return [self._to_domain(db_conversation) for db_conversation in db_conversations]

    async def update(self, entity: Conversation) -> Conversation:
        """Update an existing conversation."""
        # Get existing conversation
        result = await self.session.execute(
            select(DbConversation).where(DbConversation.id == entity.id)
        )
        db_conversation = result.scalars().first()

        if not db_conversation:
            raise ValueError(f"Conversation not found: {entity.id}")

        # Update fields
        db_conversation.topic = entity.topic
        db_conversation.participant_ids = entity.participant_ids
        db_conversation.metadata_json = self._serialize_metadata(entity.metadata)

        # Flush changes
        await self.session.flush()

        # Return domain model
        return self._to_domain(db_conversation)

    async def delete(self, entity_id: str, user_id: Optional[str] = None) -> bool:
        """
        Delete conversation by ID.

        Args:
            entity_id: Conversation ID
            user_id: Optional user ID for access control

        Returns:
            True if conversation was deleted, False otherwise
        """
        # Check if user has access to delete this conversation
        if user_id:
            # Get the conversation to check workspace
            result = await self.session.execute(
                select(DbConversation).where(DbConversation.id == entity_id)
            )
            db_conversation = result.scalars().first()

            if not db_conversation:
                return False

            # Get the workspace to check if user is the owner
            from app.database.models import Workspace
            workspace_result = await self.session.execute(
                select(Workspace).where(Workspace.id == db_conversation.workspace_id)
            )
            workspace = workspace_result.scalars().first()

            if not workspace or workspace.owner_id != user_id:
                return False

        # Delete the conversation
        result = await self.session.execute(
            delete(DbConversation).where(DbConversation.id == entity_id)
        )
        return result.rowcount > 0

    async def count(self, filters: Dict[str, Any] = None) -> int:
        """Count conversations with optional filtering."""
        query = select(func.count()).select_from(DbConversation)

        # Apply filters if provided
        if filters:
            if 'workspace_id' in filters:
                query = query.where(DbConversation.workspace_id == filters['workspace_id'])
            if 'topic' in filters:
                query = query.where(DbConversation.topic.like(f"%{filters['topic']}%"))

        # Execute query
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_by_workspace(self, workspace_id: str) -> int:
        """Count conversations in a specific workspace."""
        result = await self.session.execute(
            select(func.count())
            .select_from(DbConversation)
            .where(DbConversation.workspace_id == workspace_id)
        )
        return result.scalar() or 0

    def _to_domain(self, db_conversation: DbConversation) -> Conversation:
        """Convert database model to domain model."""
        if not db_conversation:
            return None

        return Conversation(
            id=db_conversation.id,
            topic=db_conversation.topic,
            workspace_id=db_conversation.workspace_id,
            participant_ids=db_conversation.participant_ids,
            metadata=self._deserialize_metadata(db_conversation.metadata_json)
        )

    def _serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        """Serialize metadata to JSON string."""
        import json
        return json.dumps(metadata) if metadata else "{}"

    def _deserialize_metadata(self, metadata_json: str) -> Dict[str, Any]:
        """Deserialize metadata from JSON string."""
        import json
        if not metadata_json:
            return {}
        try:
            return json.loads(metadata_json)
        except json.JSONDecodeError:
            return {}
```

#### Message Repository

Create `app/database/repositories/message_repository.py`:

```python
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Message as DbMessage
from app.models.domain import Message
from app.database.repositories.base import BaseRepository

class MessageRepository(BaseRepository[Message]):
    """Repository for message operations."""

    def __init__(self, session: AsyncSession):
        """Initialize message repository."""
        super().__init__(session, Message)

    async def create(self, entity: Message) -> Message:
        """Create a new message."""
        # Map domain model to database model
        db_message = DbMessage(
            id=entity.id,
            content=entity.content,
            sender_id=entity.sender_id,
            conversation_id=entity.conversation_id,
            timestamp=entity.timestamp,
            metadata_json=self._serialize_metadata(entity.metadata)
        )

        # Add to session
        self.session.add(db_message)
        await self.session.flush()

        # Return domain model
        return self._to_domain(db_message)

    async def get_by_id(self, entity_id: str, user_id: Optional[str] = None) -> Optional[Message]:
        """
        Get message by ID.

        Args:
            entity_id: Message ID
            user_id: Optional user ID for access control

        Returns:
            Message if found and accessible, None otherwise
        """
        query = select(DbMessage).where(DbMessage.id == entity_id)

        result = await self.session.execute(query)
        db_message = result.scalars().first()

        if not db_message:
            return None

        # Check if user has access to this message
        if user_id and user_id != db_message.sender_id:
            # Get the conversation to check participants
            from app.database.models import Conversation
            conversation_result = await self.session.execute(
                select(Conversation).where(Conversation.id == db_message.conversation_id)
            )
            conversation = conversation_result.scalars().first()

            if not conversation or user_id not in conversation.participant_ids:
                # Check workspace ownership
                from app.database.models import Workspace
                workspace_result = await self.session.execute(
                    select(Workspace).where(Workspace.id == conversation.workspace_id)
                )
                workspace = workspace_result.scalars().first()

                if not workspace or workspace.owner_id != user_id:
                    return None

        return self._to_domain(db_message)

    async def list_by_conversation(self, conversation_id: str, user_id: Optional[str] = None,
                                 limit: int = 100, offset: int = 0) -> List[Message]:
        """
        List messages in a conversation.

        Args:
            conversation_id: Conversation ID
            user_id: Optional user ID for access control
            limit: Maximum number of messages to return
            offset: Pagination offset

        Returns:
            List of messages
        """
        # First check if user has access to the conversation
        if user_id:
            from app.database.models import Conversation
            conversation_result = await self.session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = conversation_result.scalars().first()

            if not conversation or (user_id not in conversation.participant_ids):
                # Check workspace ownership
                from app.database.models import Workspace
                workspace_result = await self.session.execute(
                    select(Workspace).where(Workspace.id == conversation.workspace_id)
                )
                workspace = workspace_result.scalars().first()

                if not workspace or workspace.owner_id != user_id:
                    return []

        # Get messages
        result = await self.session.execute(
            select(DbMessage)
            .where(DbMessage.conversation_id == conversation_id)
            .order_by(DbMessage.timestamp)
            .limit(limit)
            .offset(offset)
        )
        db_messages = result.scalars().all()

        # Convert to domain models
        return [self._to_domain(db_message) for db_message in db_messages]

    async def list(self, filters: Dict[str, Any] = None, limit: int = 100, offset: int = 0) -> List[Message]:
        """List messages with optional filtering."""
        query = select(DbMessage)

        # Apply filters if provided
        if filters:
            if 'conversation_id' in filters:
                query = query.where(DbMessage.conversation_id == filters['conversation_id'])
            if 'sender_id' in filters:
                query = query.where(DbMessage.sender_id == filters['sender_id'])

        # Apply sorting and pagination
        query = query.order_by(DbMessage.timestamp).limit(limit).offset(offset)

        # Execute query
        result = await self.session.execute(query)
        db_messages = result.scalars().all()

        # Convert to domain models
        return [self._to_domain(db_message) for db_message in db_messages]

    async def update(self, entity: Message) -> Message:
        """Update an existing message."""
        # Get existing message
        result = await self.session.execute(
            select(DbMessage).where(DbMessage.id == entity.id)
        )
        db_message = result.scalars().first()

        if not db_message:
            raise ValueError(f"Message not found: {entity.id}")

        # Verify sender (optional but recommended)
        if db_message.sender_id != entity.sender_id:
            raise ValueError(f"Message {entity.id} does not belong to user {entity.sender_id}")

        # Update fields
        db_message.content = entity.content
        db_message.metadata_json = self._serialize_metadata(entity.metadata)

        # Flush changes
        await self.session.flush()

        # Return domain model
        return self._to_domain(db_message)

    async def delete(self, entity_id: str, user_id: Optional[str] = None) -> bool:
        """
        Delete message by ID.

        Args:
            entity_id: Message ID
            user_id: Optional user ID for access control

        Returns:
            True if message was deleted, False otherwise
        """
        # Check if user has access to delete this message
        if user_id:
            # Get the message
            result = await self.session.execute(
                select(DbMessage).where(DbMessage.id == entity_id)
            )
            db_message = result.scalars().first()

            if not db_message:
                return False

            # Only allow sender or workspace owner to delete
            if db_message.sender_id != user_id:
                # Check workspace ownership
                from app.database.models import Conversation, Workspace
                conversation_result = await self.session.execute(
                    select(Conversation).where(Conversation.id == db_message.conversation_id)
                )
                conversation = conversation_result.scalars().first()

                if not conversation:
                    return False

                workspace_result = await self.session.execute(
                    select(Workspace).where(Workspace.id == conversation.workspace_id)
                )
                workspace = workspace_result.scalars().first()

                if not workspace or workspace.owner_id != user_id:
                    return False

        # Delete the message
        result = await self.session.execute(
            delete(DbMessage).where(DbMessage.id == entity_id)
        )
        return result.rowcount > 0

    async def count(self, filters: Dict[str, Any] = None) -> int:
        """Count messages with optional filtering."""
        query = select(func.count()).select_from(DbMessage)

        # Apply filters if provided
        if filters:
            if 'conversation_id' in filters:
                query = query.where(DbMessage.conversation_id == filters['conversation_id'])
            if 'sender_id' in filters:
                query = query.where(DbMessage.sender_id == filters['sender_id'])

        # Execute query
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_by_conversation(self, conversation_id: str) -> int:
        """Count messages in a specific conversation."""
        result = await self.session.execute(
            select(func.count())
            .select_from(DbMessage)
            .where(DbMessage.conversation_id == conversation_id)
        )
        return result.scalar() or 0

    def _to_domain(self, db_message: DbMessage) -> Message:
        """Convert database model to domain model."""
        if not db_message:
            return None

        return Message(
            id=db_message.id,
            content=db_message.content,
            sender_id=db_message.sender_id,
            conversation_id=db_message.conversation_id,
            timestamp=db_message.timestamp,
            metadata=self._deserialize_metadata(db_message.metadata_json)
        )

    def _serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        """Serialize metadata to JSON string."""
        import json
        return json.dumps(metadata) if metadata else "{}"

    def _deserialize_metadata(self, metadata_json: str) -> Dict[str, Any]:
        """Deserialize metadata from JSON string."""
        import json
        if not metadata_json:
            return {}
        try:
            return json.loads(metadata_json)
        except json.JSONDecodeError:
            return {}
```

### Repository Factory

Create a factory to easily create repositories in `app/database/repositories/factory.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Type, TypeVar, Dict, Any

from app.database.repositories.base import BaseRepository
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.workspace_repository import WorkspaceRepository
from app.database.repositories.conversation_repository import ConversationRepository
from app.database.repositories.message_repository import MessageRepository

# Type variables
T = TypeVar('T')
R = TypeVar('R', bound=BaseRepository)

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

    def get_user_repository(self) -> UserRepository:
        """Get user repository."""
        return self._get_repository(UserRepository)

    def get_workspace_repository(self) -> WorkspaceRepository:
        """Get workspace repository."""
        return self._get_repository(WorkspaceRepository)

    def get_conversation_repository(self) -> ConversationRepository:
        """Get conversation repository."""
        return self._get_repository(ConversationRepository)

    def get_message_repository(self) -> MessageRepository:
        """Get message repository."""
        return self._get_repository(MessageRepository)

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

### FastAPI Dependency for Repositories

Create a dependency to provide repositories in FastAPI endpoints:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.config import get_db
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

# Example usage in an endpoint
@app.get("/workspaces")
async def get_workspaces(
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
    current_user: dict = Depends(get_current_user)
):
    workspace_repo = repo_factory.get_workspace_repository()
    workspaces = await workspace_repo.list_by_owner(current_user["user_id"])
    return {"workspaces": workspaces}
```

## Transaction Management

### Unit of Work Pattern

Implement the Unit of Work pattern to manage transactions in `app/database/unit_of_work.py`:

````python
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncContextManager, Optional

from app.database.config import get_session
from app.database.repositories.factory import RepositoryFactory

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

# Usage example
async def create_workspace_with_conversation(workspace_data, conversation_data, owner_id):
    """
    Create a workspace with an initial conversation in a single transaction.

    Args:
        workspace_data: Workspace data
        conversation_data: Conversation data
        owner_id: Owner user ID

    Returns:
        Created workspace and conversation
    """
    async with UnitOfWork.for_transaction() as uow:
        try:
            # Create workspace
            workspace_repo = uow.repositories.get_workspace_repository()
            workspace = await workspace_repo.create(workspace_data)

            # Set workspace ID in conversation data
            conversation_data.workspace_id = workspace.id

            # Create conversation
            conversation_repo = uow.repositories.get_conversation_repository()
            conversation = await conversation_repo.create(conversation_data)

            # Commit transaction
            await uow.commit()

            return workspace, conversation
        except Exception as e:
            # Transaction is automatically rolled back
            # Log the error
            import logging
            logging.error(f"Failed to create workspace with conversation: {str(e)}")
            raise
````

### Using Transactions in Services

Create a service layer to encapsulate business logic with transactions:

```python
from app.database.unit_of_work import UnitOfWork
from app.models.domain import Workspace, Conversation

class WorkspaceService:
    """Service for workspace operations."""

    @staticmethod
    async def create_workspace_with_default_conversation(
        name: str,
        description: str,
        owner_id: str,
        metadata: dict = None
    ) -> Workspace:
        """
        Create a workspace with a default conversation.

        Args:
            name: Workspace name
            description: Workspace description
            owner_id: Owner user ID
            metadata: Optional metadata

        Returns:
            Created workspace
        """
        import uuid
        from datetime import datetime

        async with UnitOfWork.for_transaction() as uow:
            try:
                # Create workspace
                workspace_repo = uow.repositories.get_workspace_repository()
                workspace = Workspace(
                    id=str(uuid.uuid4()),
                    name=name,
                    description=description,
                    owner_id=owner_id,
                    metadata=metadata or {}
                )
                created_workspace = await workspace_repo.create(workspace)

                # Create default conversation
                conversation_repo = uow.repositories.get_conversation_repository()
                conversation = Conversation(
                    id=str(uuid.uuid4()),
                    topic="General",
                    workspace_id=created_workspace.id,
                    participant_ids=[owner_id],
                    metadata={"default": True}
                )
                await conversation_repo.create(conversation)

                # Commit transaction
                await uow.commit()

                return created_workspace
            except Exception as e:
                # Transaction is automatically rolled back
                # Log the error
                import logging
                logging.error(f"Failed to create workspace with default conversation: {str(e)}")
                raise
```

## Domain Model Mapping

### Mapping Strategy

The clear separation between database models (SQLAlchemy) and domain models (Pydantic) requires proper mapping logic. Here are the key strategies:

1. **Repository-based Mapping**: Each repository is responsible for mapping between its database and domain models
2. **Metadata Handling**: JSON fields in SQLite are serialized/deserialized to dictionaries
3. **Relationship Handling**: Related entities are loaded as needed, but not automatically included in domain models

### Mapping between Domain and Database Models

For comprehensive mapping, add explicit mapping methods to repositories:

```python
def _db_to_domain(self, db_entity) -> Optional[DomainEntity]:
    """Map database entity to domain entity."""
    if not db_entity:
        return None

    # Extract fields from database entity
    # Map to domain entity
    return DomainEntity(...)

def _domain_to_db(self, domain_entity, db_entity=None) -> DbEntity:
    """
    Map domain entity to database entity.

    Args:
        domain_entity: Domain entity to map
        db_entity: Optional existing database entity to update

    Returns:
        Database entity
    """
    if not db_entity:
        db_entity = DbEntity()

    # Map fields from domain entity to database entity
    db_entity.field1 = domain_entity.field1
    db_entity.field2 = domain_entity.field2
    ...

    return db_entity
```

## Database Initialization

### Initial Setup

Create a script to initialize the database with tables in `app/database/init_db.py`:

```python
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool
from app.database.models import Base
from app.database.config import DATABASE_URL, DB_ECHO
from app.database.seed import create_default_user

async def init_database():
    """Initialize database with tables."""
    logging.info(f"Initializing database at {DATABASE_URL}")

    # Create engine for initialization
    engine = create_async_engine(
        DATABASE_URL,
        echo=DB_ECHO,
        poolclass=QueuePool,
    )

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    logging.info("Database initialized successfully")

    # Create default user if needed
    await create_default_user()

    # Close engine
    await engine.dispose()

    logging.info("Database initialization completed")

if __name__ == "__main__":
    # Run initialization
    asyncio.run(init_database())
```

### Seed Data

Create a script to seed the database with initial data in `app/database/seed.py`:

```python
import asyncio
import logging
import uuid
from app.database.unit_of_work import UnitOfWork
from app.models.domain import User

async def create_default_user():
    """Create default user if it doesn't exist."""
    logging.info("Checking for default user")

    async with UnitOfWork.for_transaction() as uow:
        try:
            # Check if default user exists
            user_repo = uow.repositories.get_user_repository()
            default_user = await user_repo.get_by_email("user@example.com")

            if not default_user:
                logging.info("Creating default user")

                # Create default user
                default_user = User(
                    user_id="550e8400-e29b-41d4-a716-446655440000",
                    name="Default User",
                    email="user@example.com",
                    metadata={"default": True}
                )
                await user_repo.create(default_user)

                # Commit transaction
                await uow.commit()

                logging.info("Default user created successfully")
            else:
                logging.info("Default user already exists")
        except Exception as e:
            logging.error(f"Failed to create default user: {str(e)}")
            raise

if __name__ == "__main__":
    # Run seeding
    asyncio.run(create_default_user())
```

### Integration with Application Startup

Update `app/main.py` to initialize the database on startup:

```python
@app.on_event("startup")
async def startup_event():
    """Application startup event handler."""
    # Initialize database
    from app.database.init_db import init_database
    await init_database()
```

## Error Handling

### Database Error Types

1. **Connection Errors**: Failures to connect to the database
2. **Constraint Violations**: Unique constraint failures, foreign key violations, etc.
3. **Transaction Errors**: Failures during transaction commit/rollback
4. **SQLite Locks**: "database is locked" errors due to concurrent access
5. **Validation Errors**: Failures during model validation

### Custom Database Exceptions

Create custom exceptions for database errors in `app/database/exceptions.py`:

```python
class DatabaseError(Exception):
    """Base exception for database errors."""

    def __init__(self, message: str, original_exception: Exception = None):
        """
        Initialize database error.

        Args:
            message: Error message
            original_exception: Original exception that caused this error
        """
        self.message = message
        self.original_exception = original_exception
        super().__init__(message)

class ConnectionError(DatabaseError):
    """Database connection error."""
    pass

class ConstraintError(DatabaseError):
    """Database constraint violation error."""
    pass

class TransactionError(DatabaseError):
    """Database transaction error."""
    pass

class ConcurrencyError(DatabaseError):
    """Database concurrency error."""
    pass

class EntityNotFoundError(DatabaseError):
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

class AccessDeniedError(DatabaseError):
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
```

### Error Handler Middleware

Create a middleware to handle database errors in `app/api/middleware/error_handler.py`:

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.database.exceptions import (
    DatabaseError, ConnectionError, ConstraintError,
    TransactionError, ConcurrencyError, EntityNotFoundError,
    AccessDeniedError
)

logger = logging.getLogger(__name__)

async def database_error_handler(request: Request, call_next):
    """Middleware to handle database errors."""
    try:
        # Try to process the request
        return await call_next(request)
    except EntityNotFoundError as e:
        # Entity not found
        logger.warning(f"Entity not found: {str(e)}")
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "not_found",
                    "message": str(e),
                    "details": {
                        "entity_type": e.entity_type,
                        "entity_id": e.entity_id
                    }
                }
            }
        )
    except AccessDeniedError as e:
        # Access denied
        logger.warning(f"Access denied: {str(e)}")
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "forbidden",
                    "message": "Access denied",
                    "details": {
                        "entity_type": e.entity_type,
                        "entity_id": e.entity_id
                    }
                }
            }
        )
    except ConstraintError as e:
        # Constraint violation
        logger.warning(f"Constraint violation: {str(e)}")
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "conflict",
                    "message": str(e)
                }
            }
        )
    except ConcurrencyError as e:
        # Concurrency error
        logger.warning(f"Concurrency error: {str(e)}")
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "concurrency_error",
                    "message": str(e)
                }
            }
        )
    except ConnectionError as e:
        # Connection error
        logger.error(f"Database connection error: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "service_unavailable",
                    "message": "Database connection error"
                }
            }
        )
    except TransactionError as e:
        # Transaction error
        logger.error(f"Transaction error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "transaction_error",
                    "message": "Transaction failed"
                }
            }
        )
    except DatabaseError as e:
        # Generic database error
        logger.error(f"Database error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "database_error",
                    "message": "Database operation failed"
                }
            }
        )
    except SQLAlchemyError as e:
        # SQLAlchemy error
        logger.error(f"SQLAlchemy error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "database_error",
                    "message": "Database operation failed"
                }
            }
        )
```

### Error Mapping in Repositories

Add error mapping to each repository to convert SQLAlchemy errors to custom exceptions:

```python
def _handle_db_error(self, error: Exception, message: str):
    """
    Handle database error.

    Args:
        error: Original exception
        message: Error message

    Raises:
        DatabaseError: Appropriate database error
    """
    from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

    # Map SQLAlchemy errors to custom exceptions
    if isinstance(error, IntegrityError):
        # Check for specific integrity errors
        error_str = str(error).lower()
        if "unique constraint" in error_str:
            raise ConstraintError(f"{message}: unique constraint violation", error)
        if "foreign key constraint" in error_str:
            raise ConstraintError(f"{message}: foreign key constraint violation", error)
        # Generic integrity error
        raise ConstraintError(f"{message}: integrity error", error)
    elif isinstance(error, OperationalError):
        # Check for specific operational errors
        error_str = str(error).lower()
        if "database is locked" in error_str:
            raise ConcurrencyError(f"{message}: database is locked", error)
        if "connection" in error_str:
            raise ConnectionError(f"{message}: connection error", error)
        # Generic operational error
        raise DatabaseError(f"{message}: operational error", error)
    elif isinstance(error, ProgrammingError):
        # Programming error (usually SQL syntax)
        raise DatabaseError(f"{message}: programming error", error)
    else:
        # Generic database error
        raise DatabaseError(f"{message}: {str(error)}", error)
```

## Migration Strategy

### Migrating from In-Memory to SQLite

Create a script to migrate data from in-memory storage to SQLite in `app/database/migrate_from_memory.py`:

```python
import asyncio
import logging
from app.core.storage import storage as memory_storage
from app.database.unit_of_work import UnitOfWork
from app.models.domain import User, Workspace, Conversation, Message

async def migrate_from_memory():
    """Migrate data from in-memory storage to SQLite."""
    logging.info("Starting migration from in-memory storage to SQLite")

    async with UnitOfWork.for_transaction() as uow:
        try:
            # Migrate users
            logging.info("Migrating users")
            user_repo = uow.repositories.get_user_repository()
            for user_dict in memory_storage.users.values():
                user = User(**user_dict)
                await user_repo.create(user)

            # Migrate workspaces
            logging.info("Migrating workspaces")
            workspace_repo = uow.repositories.get_workspace_repository()
            for workspace_dict in memory_storage.workspaces.values():
                workspace = Workspace(**workspace_dict)
                await workspace_repo.create(workspace)

            # Migrate conversations
            logging.info("Migrating conversations")
            conversation_repo = uow.repositories.get_conversation_repository()
            for conversation_dict in memory_storage.conversations.values():
                conversation = Conversation(**conversation_dict)
                await conversation_repo.create(conversation)

            # Migrate messages
            logging.info("Migrating messages")
            message_repo = uow.repositories.get_message_repository()
            for message_dict in memory_storage.messages.values():
                message = Message(**message_dict)
                await message_repo.create(message)

            # Commit transaction
            await uow.commit()

            logging.info("Migration completed successfully")
        except Exception as e:
            logging.error(f"Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    # Run migration
    asyncio.run(migrate_from_memory())
```

### Integration with Application Startup

Update `app/main.py` to check if migration is needed on startup:

```python
@app.on_event("startup")
async def startup_event():
    """Application startup event handler."""
    # Initialize database
    from app.database.init_db import init_database
    await init_database()

    # Check if migration is needed
    import os
    from app.core.storage import storage as memory_storage
    from app.database.migrate_from_memory import migrate_from_memory

    # Only migrate if there's data in memory and the database file exists but is empty
    if (memory_storage.users or memory_storage.workspaces or
        memory_storage.conversations or memory_storage.messages):
        db_path = "cortex.db"  # Path should match DATABASE_URL
        if os.path.exists(db_path) and os.path.getsize(db_path) == 0:
            # Migrate data from memory to SQLite
            await migrate_from_memory()
```

## Testing Approach

### Repository Tests

Create tests for repositories in `tests/database/test_repositories.py`:

```python
import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base
from app.models.domain import User, Workspace, Conversation, Message
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.workspace_repository import WorkspaceRepository
from app.database.repositories.conversation_repository import ConversationRepository
from app.database.repositories.message_repository import MessageRepository

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

@pytest.fixture
def workspace_data(user_data):
    """Create test workspace data."""
    return Workspace(
        id=str(uuid.uuid4()),
        name="Test Workspace",
        description="Test Workspace Description",
        owner_id=user_data.user_id,
        metadata={"test": True}
    )

@pytest.fixture
def conversation_data(workspace_data):
    """Create test conversation data."""
    return Conversation(
        id=str(uuid.uuid4()),
        topic="Test Conversation",
        workspace_id=workspace_data.id,
        participant_ids=[workspace_data.owner_id],
        metadata={"test": True}
    )

@pytest.fixture
def message_data(conversation_data):
    """Create test message data."""
    return Message(
        id=str(uuid.uuid4()),
        content="Test Message",
        sender_id=conversation_data.participant_ids[0],
        conversation_id=conversation_data.id,
        timestamp="2023-01-01T00:00:00Z",
        metadata={"test": True}
    )

@pytest.mark.asyncio
async def test_user_repository_crud(test_db, user_data):
    """Test user repository CRUD operations."""
    # Create repository
    repo = UserRepository(test_db)

    # Create
    created_user = await repo.create(user_data)
    assert created_user.user_id == user_data.user_id
    assert created_user.name == user_data.name
    assert created_user.email == user_data.email
    assert created_user.metadata == user_data.metadata

    # Get by ID
    retrieved_user = await repo.get_by_id(user_data.user_id)
    assert retrieved_user is not None
    assert retrieved_user.user_id == user_data.user_id

    # Update
    retrieved_user.name = "Updated Name"
    updated_user = await repo.update(retrieved_user)
    assert updated_user.name == "Updated Name"

    # Delete
    result = await repo.delete(user_data.user_id)
    assert result is True

    # Verify deleted
    deleted_user = await repo.get_by_id(user_data.user_id)
    assert deleted_user is None

@pytest.mark.asyncio
async def test_workspace_repository_crud(test_db, user_data, workspace_data):
    """Test workspace repository CRUD operations."""
    # Create user first
    user_repo = UserRepository(test_db)
    await user_repo.create(user_data)

    # Create workspace repository
    repo = WorkspaceRepository(test_db)

    # Create
    created_workspace = await repo.create(workspace_data)
    assert created_workspace.id == workspace_data.id
    assert created_workspace.name == workspace_data.name

    # Get by ID
    retrieved_workspace = await repo.get_by_id(workspace_data.id)
    assert retrieved_workspace is not None
    assert retrieved_workspace.id == workspace_data.id

    # List by owner
    workspaces = await repo.list_by_owner(user_data.user_id)
    assert len(workspaces) == 1
    assert workspaces[0].id == workspace_data.id

    # Update
    retrieved_workspace.name = "Updated Name"
    updated_workspace = await repo.update(retrieved_workspace)
    assert updated_workspace.name == "Updated Name"

    # Delete
    result = await repo.delete(workspace_data.id)
    assert result is True

    # Verify deleted
    deleted_workspace = await repo.get_by_id(workspace_data.id)
    assert deleted_workspace is None

# Add similar tests for conversation and message repositories
```

### Unit of Work Tests

Create tests for the Unit of Work pattern in `tests/database/test_unit_of_work.py`:

```python
import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base
from app.models.domain import User, Workspace
from app.database.unit_of_work import UnitOfWork

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

@pytest.mark.asyncio
async def test_unit_of_work_commit(test_db):
    """Test Unit of Work commit."""
    # Create UnitOfWork with test session
    uow = UnitOfWork(test_db)

    # Create test data
    user_id = str(uuid.uuid4())
    user = User(
        user_id=user_id,
        name="Test User",
        email="test@example.com",
        metadata={"test": True}
    )

    # Create user
    user_repo = uow.repositories.get_user_repository()
    await user_repo.create(user)

    # Commit
    await uow.commit()

    # Verify user was created
    retrieved_user = await user_repo.get_by_id(user_id)
    assert retrieved_user is not None
    assert retrieved_user.user_id == user_id

@pytest.mark.asyncio
async def test_unit_of_work_rollback(test_db):
    """Test Unit of Work rollback."""
    # Create UnitOfWork with test session
    uow = UnitOfWork(test_db)

    # Create test data
    user_id = str(uuid.uuid4())
    user = User(
        user_id=user_id,
        name="Test User",
        email="test@example.com",
        metadata={"test": True}
    )

    # Create user
    user_repo = uow.repositories.get_user_repository()
    await user_repo.create(user)

    # Rollback
    await uow.rollback()

    # Verify user was not created
    retrieved_user = await user_repo.get_by_id(user_id)
    assert retrieved_user is None

@pytest.mark.asyncio
async def test_unit_of_work_context_manager():
    """Test Unit of Work context manager."""
    # Create test data
    user_id = str(uuid.uuid4())
    user = User(
        user_id=user_id,
        name="Test User",
        email="test@example.com",
        metadata={"test": True}
    )

    # Use context manager
    async with UnitOfWork.for_transaction() as uow:
        # Create user
        user_repo = uow.repositories.get_user_repository()
        await user_repo.create(user)

        # Commit
        await uow.commit()

    # Verify in another Unit of Work
    async with UnitOfWork.for_transaction() as uow2:
        user_repo = uow2.repositories.get_user_repository()
        retrieved_user = await user_repo.get_by_id(user_id)
        assert retrieved_user is not None
        assert retrieved_user.user_id == user_id

@pytest.mark.asyncio
async def test_unit_of_work_exception_handling():
    """Test Unit of Work exception handling."""
    # Create test data
    user_id = str(uuid.uuid4())
    user = User(
        user_id=user_id,
        name="Test User",
        email="test@example.com",
        metadata={"test": True}
    )

    try:
        async with UnitOfWork.for_transaction() as uow:
            # Create user
            user_repo = uow.repositories.get_user_repository()
            await user_repo.create(user)

            # Raise exception
            raise ValueError("Test exception")

            # Shouldn't reach here
            await uow.commit()
    except ValueError:
        pass

    # Verify user was not created
    async with UnitOfWork.for_transaction() as uow2:
        user_repo = uow2.repositories.get_user_repository()
        retrieved_user = await user_repo.get_by_id(user_id)
        assert retrieved_user is None
```

### Integration Tests with SQLite

Create integration tests with SQLite in `tests/database/test_integration.py`:

```python
import pytest
import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base
from app.models.domain import User, Workspace, Conversation, Message
from app.database.unit_of_work import UnitOfWork

# Create file-based test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(scope="module")
async def setup_test_db():
    """Set up test database for integration tests."""
    # Create engine
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Yield engine
    yield engine

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Close engine
    await engine.dispose()

    # Remove database file
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture
async def test_user():
    """Create test user."""
    user_id = str(uuid.uuid4())
    user = User(
        user_id=user_id,
        name="Test User",
        email=f"test_{user_id}@example.com",
        metadata={"test": True}
    )

    # Create user
    async with UnitOfWork.for_transaction() as uow:
        user_repo = uow.repositories.get_user_repository()
        created_user = await user_repo.create(user)
        await uow.commit()

    return created_user

@pytest.mark.asyncio
async def test_workspace_with_conversations(setup_test_db, test_user):
    """Test creating a workspace with conversations and messages."""
    # Create workspace
    workspace = Workspace(
        id=str(uuid.uuid4()),
        name="Test Workspace",
        description="Test Workspace Description",
        owner_id=test_user.user_id,
        metadata={"test": True}
    )

    conversation_ids = []

    async with UnitOfWork.for_transaction() as uow:
        # Create workspace
        workspace_repo = uow.repositories.get_workspace_repository()
        created_workspace = await workspace_repo.create(workspace)

        # Create conversations
        conversation_repo = uow.repositories.get_conversation_repository()

        for i in range(3):
            conversation = Conversation(
                id=str(uuid.uuid4()),
                topic=f"Test Conversation {i}",
                workspace_id=created_workspace.id,
                participant_ids=[test_user.user_id],
                metadata={"test": True, "index": i}
            )
            created_conversation = await conversation_repo.create(conversation)
            conversation_ids.append(created_conversation.id)

        # Commit
        await uow.commit()

    # Create messages
    async with UnitOfWork.for_transaction() as uow:
        message_repo = uow.repositories.get_message_repository()

        for conversation_id in conversation_ids:
            for i in range(5):
                message = Message(
                    id=str(uuid.uuid4()),
                    content=f"Test Message {i} in {conversation_id}",
                    sender_id=test_user.user_id,
                    conversation_id=conversation_id,
                    timestamp=f"2023-01-01T{i:02d}:00:00Z",
                    metadata={"test": True, "index": i}
                )
                await message_repo.create(message)

        # Commit
        await uow.commit()

    # Verify everything was created correctly
    async with UnitOfWork.for_transaction() as uow:
        # Get workspace
        workspace_repo = uow.repositories.get_workspace_repository()
        retrieved_workspace = await workspace_repo.get_by_id(workspace.id)
        assert retrieved_workspace is not None
        assert retrieved_workspace.name == workspace.name

        # Get conversations
        conversation_repo = uow.repositories.get_conversation_repository()
        conversations = await conversation_repo.list_by_workspace(workspace.id)
        assert len(conversations) == 3

        # Get messages for first conversation
        message_repo = uow.repositories.get_message_repository()
        messages = await message_repo.list_by_conversation(conversation_ids[0])
        assert len(messages) == 5

        # Test filter and pagination
        messages = await message_repo.list(
            filters={"conversation_id": conversation_ids[0]},
            limit=2,
            offset=1
        )
        assert len(messages) == 2
```

## Performance Considerations

### SQLite Limitations

SQLite has some limitations to be aware of:

1. **Concurrency**: Only one writer can access the database at a time
2. **Performance**: Not optimized for high-throughput workloads
3. **Locking**: Whole-database locking can cause "database is locked" errors
4. **Size**: Not suitable for very large datasets

### Optimization Strategies

1. **Connection Pooling**: Configure appropriate pool size and timeout
2. **Transaction Scope**: Keep transactions as short as possible
3. **Indices**: Create appropriate indices for frequently queried fields
4. **JSON Handling**: Be careful with large JSON fields, as they are stored as text
5. **Query Optimization**: Use specific queries instead of loading large datasets
6. **Pagination**: Always use pagination for list operations

### Connection Pool Configuration

Configure connection pool parameters based on expected load:

```python
# Low load (development)
pool_size=5
max_overflow=10
pool_timeout=30
pool_recycle=1800

# Medium load
pool_size=20
max_overflow=20
pool_timeout=30
pool_recycle=1800

# High load (not recommended for SQLite)
pool_size=50
max_overflow=50
pool_timeout=60
pool_recycle=1800
```

## Common Pitfalls

### SQLite-Specific Issues

1. **Database Locks**: SQLite locks the entire database during writes

   - Solution: Keep transactions short and use appropriate timeouts
   - Example: `await session.execute(..., execution_options={"timeout": 5})`

2. **Connection Limits**: SQLite has limited concurrent connections

   - Solution: Configure pool size appropriately and handle connection errors
   - Example: `pool_size=20, max_overflow=10`

3. **File Permissions**: SQLite requires proper file permissions

   - Solution: Ensure the application has read/write access to the database file
   - Example: `chmod 644 cortex.db`

4. **JSON Storage**: SQLite stores JSON as text
   - Solution: Use proper serialization/deserialization and validate JSON structures
   - Example: `json.loads(db_entity.metadata_json) if db_entity.metadata_json else {}`

### General Database Issues

1. **Open Transactions**: Forgetting to commit or rollback transactions

   - Solution: Use the Unit of Work pattern and context managers
   - Example: `async with UnitOfWork.for_transaction() as uow: ...`

2. **Connection Leaks**: Not closing connections properly

   - Solution: Use context managers and proper cleanup
   - Example: `async with engine.begin() as conn: ...`

3. **N+1 Query Problem**: Making multiple queries for related data

   - Solution: Use appropriate joins or eager loading
   - Example: `select(DbWorkspace).options(selectinload(DbWorkspace.conversations))`

4. **Large Result Sets**: Loading too much data at once
   - Solution: Always use pagination and specific queries
   - Example: `query.limit(limit).offset(offset)`

## Appendix: Complete Implementation Examples

### Repository Integration Example

This example shows how to use the repository pattern with FastAPI endpoints:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.config import get_db
from app.database.repositories.factory import RepositoryFactory
from app.utils.auth import get_current_user
from app.models.api.request import WorkspaceCreate, WorkspaceUpdate
from app.models.api.response import WorkspaceResponse, WorkspacesListResponse
from app.models.domain import Workspace

router = APIRouter(prefix="/config", tags=["config"])

@router.post("/workspace", response_model=WorkspaceResponse)
async def create_workspace(
    request: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new workspace."""
    # Create workspace entity
    import uuid
    workspace = Workspace(
        id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        owner_id=current_user["user_id"],
        metadata=request.metadata
    )

    try:
        # Create repository and save workspace
        repo_factory = RepositoryFactory(db)
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

        # Handle error
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail="Workspace with this name already exists"
            )

        # Generic error
        raise HTTPException(
            status_code=500,
            detail="Failed to create workspace"
        )

@router.get("/workspace", response_model=WorkspacesListResponse)
async def list_workspaces(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List workspaces for the current user."""
    try:
        # Create repository
        repo_factory = RepositoryFactory(db)
        workspace_repo = repo_factory.get_workspace_repository()

        # Get workspaces
        workspaces = await workspace_repo.list_by_owner(
            current_user["user_id"],
            limit=limit,
            offset=offset
        )

        # Get total count
        total = await workspace_repo.count_by_owner(current_user["user_id"])

        # Return response
        return WorkspacesListResponse(
            workspaces=workspaces,
            total=total
        )
    except Exception as e:
        # Handle error
        raise HTTPException(
            status_code=500,
            detail="Failed to list workspaces"
        )
```

### Complete Service Implementation

This example shows a complete service implementation that uses the Unit of Work pattern:

```python
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from app.database.unit_of_work import UnitOfWork
from app.models.domain import Workspace, Conversation, Message
from app.database.exceptions import EntityNotFoundError, AccessDeniedError

class WorkspaceService:
    """Service for workspace operations."""

    @staticmethod
    async def create_workspace(
        name: str,
        description: str,
        owner_id: str,
        metadata: Dict[str, Any] = None,
        with_default_conversation: bool = True
    ) -> Workspace:
        """
        Create a workspace with optional default conversation.

        Args:
            name: Workspace name
            description: Workspace description
            owner_id: Owner user ID
            metadata: Optional metadata
            with_default_conversation: Whether to create a default conversation

        Returns:
            Created workspace
        """
        # Create workspace ID
        workspace_id = str(uuid.uuid4())

        async with UnitOfWork.for_transaction() as uow:
            try:
                # Create workspace
                workspace = Workspace(
                    id=workspace_id,
                    name=name,
                    description=description,
                    owner_id=owner_id,
                    metadata=metadata or {}
                )

                workspace_repo = uow.repositories.get_workspace_repository()
                created_workspace = await workspace_repo.create(workspace)

                # Create default conversation if requested
                if with_default_conversation:
                    conversation = Conversation(
                        id=str(uuid.uuid4()),
                        topic="General",
                        workspace_id=workspace_id,
                        participant_ids=[owner_id],
                        metadata={"default": True}
                    )

                    conversation_repo = uow.repositories.get_conversation_repository()
                    await conversation_repo.create(conversation)

                # Commit transaction
                await uow.commit()

                return created_workspace
            except Exception as e:
                # Log error
                import logging
                logging.error(f"Failed to create workspace: {str(e)}")

                # Rollback handled by context manager
                raise

    @staticmethod
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
        """
        async with UnitOfWork.for_transaction() as uow:
            try:
                # Get workspace
                workspace_repo = uow.repositories.get_workspace_repository()
                workspace = await workspace_repo.get_by_id(workspace_id)

                if not workspace:
                    raise EntityNotFoundError("Workspace", workspace_id)

                # Check access
                if workspace.owner_id != user_id:
                    raise AccessDeniedError("Workspace", workspace_id, user_id)

                return workspace
            except Exception as e:
                # Handle repository exceptions
                if isinstance(e, (EntityNotFoundError, AccessDeniedError)):
                    raise

                # Log other errors
                import logging
                logging.error(f"Failed to get workspace: {str(e)}")

                # Rollback handled by context manager
                raise

    @staticmethod
    async def delete_workspace_with_contents(workspace_id: str, user_id: str) -> bool:
        """
        Delete workspace and all its contents.

        Args:
            workspace_id: Workspace ID
            user_id: User ID for access control

        Returns:
            True if workspace was deleted

        Raises:
            EntityNotFoundError: If workspace not found
            AccessDeniedError: If user does not have access
        """
        async with UnitOfWork.for_transaction() as uow:
            try:
                # Get workspace to check access
                workspace_repo = uow.repositories.get_workspace_repository()
                workspace = await workspace_repo.get_by_id(workspace_id)

                if not workspace:
                    raise EntityNotFoundError("Workspace", workspace_id)

                # Check access
                if workspace.owner_id != user_id:
                    raise AccessDeniedError("Workspace", workspace_id, user_id)

                # Get conversations in workspace
                conversation_repo = uow.repositories.get_conversation_repository()
                conversations = await conversation_repo.list_by_workspace(workspace_id)

                # Delete messages in each conversation
                message_repo = uow.repositories.get_message_repository()
                for conversation in conversations:
                    # Get messages
                    messages = await message_repo.list_by_conversation(conversation.id)

                    # Delete each message
                    for message in messages:
                        await message_repo.delete(message.id)

                # Delete conversations
                for conversation in conversations:
                    await conversation_repo.delete(conversation.id)

                # Delete workspace
                result = await workspace_repo.delete(workspace_id)

                # Commit transaction
                await uow.commit()

                return result
            except Exception as e:
                # Handle repository exceptions
                if isinstance(e, (EntityNotFoundError, AccessDeniedError)):
                    raise

                # Log other errors
                import logging
                logging.error(f"Failed to delete workspace: {str(e)}")

                # Rollback handled by context manager
                raise

    @staticmethod
    async def update_workspace(
        workspace_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Workspace:
        """
        Update workspace.

        Args:
            workspace_id: Workspace ID
            user_id: User ID for access control
            name: Optional new name
            description: Optional new description
            metadata: Optional new metadata

        Returns:
            Updated workspace

        Raises:
            EntityNotFoundError: If workspace not found
            AccessDeniedError: If user does not have access
        """
        async with UnitOfWork.for_transaction() as uow:
            try:
                # Get workspace
                workspace_repo = uow.repositories.get_workspace_repository()
                workspace = await workspace_repo.get_by_id(workspace_id)

                if not workspace:
                    raise EntityNotFoundError("Workspace", workspace_id)

                # Check access
                if workspace.owner_id != user_id:
                    raise AccessDeniedError("Workspace", workspace_id, user_id)

                # Update fields if provided
                if name is not None:
                    workspace.name = name

                if description is not None:
                    workspace.description = description

                if metadata is not None:
                    # Merge metadata instead of replacing
                    workspace.metadata = {**workspace.metadata, **metadata}

                # Save changes
                updated_workspace = await workspace_repo.update(workspace)

                # Commit transaction
                await uow.commit()

                return updated_workspace
            except Exception as e:
                # Handle repository exceptions
                if isinstance(e, (EntityNotFoundError, AccessDeniedError)):
                    raise

                # Log other errors
                import logging
                logging.error(f"Failed to update workspace: {str(e)}")

                # Rollback handled by context manager
                raise

    @staticmethod
    async def list_workspaces(
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Workspace], int]:
        """
        List workspaces for a user.

        Args:
            user_id: User ID
            limit: Maximum number of workspaces to return
            offset: Pagination offset

        Returns:
            Tuple of (workspaces, total count)
        """
        async with UnitOfWork.for_transaction() as uow:
            try:
                # Get workspace repository
                workspace_repo = uow.repositories.get_workspace_repository()

                # Get workspaces
                workspaces = await workspace_repo.list_by_owner(user_id, limit, offset)

                # Get total count
                total = await workspace_repo.count_by_owner(user_id)

                return workspaces, total
            except Exception as e:
                # Log error
                import logging
                logging.error(f"Failed to list workspaces: {str(e)}")

                # Rollback handled by context manager
                raise
```

### Integration with Event Bus

This example shows how to integrate the repository pattern with the existing event bus:

```python
from app.core.event_bus import event_bus
from app.database.unit_of_work import UnitOfWork
from app.models.domain import Message
from datetime import datetime

async def handle_input_event(event):
    """
    Handle input event from event bus.

    Args:
        event: Input event
    """
    # Extract data from event
    user_id = event.get("user_id")
    event_data = event.get("data", {})
    content = event_data.get("content")
    conversation_id = event_data.get("conversation_id", "default")
    timestamp = event_data.get("timestamp", datetime.now().isoformat())
    metadata = event.get("metadata", {})

    # Create message
    message = Message(
        id=str(uuid.uuid4()),
        content=content,
        sender_id=user_id,
        conversation_id=conversation_id,
        timestamp=timestamp,
        metadata=metadata
    )

    # Store message in database
    async with UnitOfWork.for_transaction() as uow:
        try:
            # Get message repository
            message_repo = uow.repositories.get_message_repository()

            # Store message
            await message_repo.create(message)

            # Commit transaction
            await uow.commit()

            # Log success
            import logging
            logging.info(f"Message stored in database: {message.id}")
        except Exception as e:
            # Log error
            import logging
            logging.error(f"Failed to store message in database: {str(e)}")
            # Transaction is automatically rolled back

# Subscribe to input events
import asyncio
async def subscribe_to_events():
    """Subscribe to events and set up handlers."""
    # Create input queue
    input_queue = asyncio.Queue()

    # Subscribe to event bus
    event_bus.subscribe(input_queue)

    # Create background task to process events
    async def process_events():
        while True:
            try:
                # Get next event
                event = await input_queue.get()

                # Check event type
                if event.get("type") == "input":
                    # Handle input event
                    await handle_input_event(event)
            except Exception as e:
                # Log error
                import logging
                logging.error(f"Error processing event: {str(e)}")
            finally:
                # Mark task as done
                input_queue.task_done()

    # Start background task
    event_bus.create_background_task(process_events())

# Call this during application startup
# app.add_event_handler("startup", subscribe_to_events)
```

### Complete API Endpoint Implementation

This example shows a complete implementation of the conversation API endpoints:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database.config import get_db
from app.database.unit_of_work import UnitOfWork
from app.utils.auth import get_current_user
from app.models.api.request import ConversationCreate, ConversationUpdate
from app.models.api.response import ConversationResponse, ConversationsListResponse
from app.models.domain import Conversation
from app.database.exceptions import EntityNotFoundError, AccessDeniedError

router = APIRouter(prefix="/config", tags=["config"])

@router.post("/conversation", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new conversation in a workspace."""
    # Get user ID
    user_id = current_user["user_id"]

    async with UnitOfWork.for_transaction() as uow:
        try:
            # Check if workspace exists and user has access
            workspace_repo = uow.repositories.get_workspace_repository()
            workspace = await workspace_repo.get_by_id(request.workspace_id)

            if not workspace:
                raise HTTPException(
                    status_code=404,
                    detail=f"Workspace not found: {request.workspace_id}"
                )

            if workspace.owner_id != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied to workspace"
                )

            # Ensure current user is in participants
            participant_ids = list(request.participant_ids) if request.participant_ids else []
            if user_id not in participant_ids:
                participant_ids.append(user_id)

            # Create conversation
            conversation = Conversation(
                id=str(uuid.uuid4()),
                topic=request.topic,
                workspace_id=request.workspace_id,
                participant_ids=participant_ids,
                metadata=request.metadata or {}
            )

            # Save conversation
            conversation_repo = uow.repositories.get_conversation_repository()
            created_conversation = await conversation_repo.create(conversation)

            # Commit transaction
            await uow.commit()

            # Return response
            return ConversationResponse(
                status="conversation created",
                conversation=created_conversation
            )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log error
            import logging
            logging.error(f"Failed to create conversation: {str(e)}")

            # Generic error
            raise HTTPException(
                status_code=500,
                detail="Failed to create conversation"
            )

@router.get("/conversation", response_model=ConversationsListResponse)
async def list_conversations(
    workspace_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """List conversations in a workspace."""
    # Get user ID
    user_id = current_user["user_id"]

    async with UnitOfWork.for_transaction() as uow:
        try:
            # Check if workspace exists and user has access
            workspace_repo = uow.repositories.get_workspace_repository()
            workspace = await workspace_repo.get_by_id(workspace_id)

            if not workspace:
                raise HTTPException(
                    status_code=404,
                    detail=f"Workspace not found: {workspace_id}"
                )

            if workspace.owner_id != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied to workspace"
                )

            # Get conversations
            conversation_repo = uow.repositories.get_conversation_repository()
            conversations = await conversation_repo.list_by_workspace(
                workspace_id,
                limit=limit,
                offset=offset
            )

            # Get total count
            total = await conversation_repo.count_by_workspace(workspace_id)

            # Return response
            return ConversationsListResponse(
                conversations=conversations,
                total=total
            )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log error
            import logging
            logging.error(f"Failed to list conversations: {str(e)}")

            # Generic error
            raise HTTPException(
                status_code=500,
                detail="Failed to list conversations"
            )

@router.get("/conversation/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific conversation."""
    # Get user ID
    user_id = current_user["user_id"]

    async with UnitOfWork.for_transaction() as uow:
        try:
            # Get conversation repository
            conversation_repo = uow.repositories.get_conversation_repository()

            # Get conversation
            conversation = await conversation_repo.get_by_id(conversation_id, user_id)

            if not conversation:
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation not found: {conversation_id}"
                )

            # Check access
            if user_id not in conversation.participant_ids:
                # Check if user is workspace owner
                workspace_repo = uow.repositories.get_workspace_repository()
                workspace = await workspace_repo.get_by_id(conversation.workspace_id)

                if not workspace or workspace.owner_id != user_id:
                    raise HTTPException(
                        status_code=403,
                        detail="Access denied to conversation"
                    )

            # Return response
            return ConversationResponse(
                status="conversation found",
                conversation=conversation
            )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log error
            import logging
            logging.error(f"Failed to get conversation: {str(e)}")

            # Generic error
            raise HTTPException(
                status_code=500,
                detail="Failed to get conversation"
            )

@router.put("/conversation/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a conversation."""
    # Get user ID
    user_id = current_user["user_id"]

    async with UnitOfWork.for_transaction() as uow:
        try:
            # Get conversation repository
            conversation_repo = uow.repositories.get_conversation_repository()

            # Get conversation
            conversation = await conversation_repo.get_by_id(conversation_id)

            if not conversation:
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation not found: {conversation_id}"
                )

            # Check access
            if user_id not in conversation.participant_ids:
                # Check if user is workspace owner
                workspace_repo = uow.repositories.get_workspace_repository()
                workspace = await workspace_repo.get_by_id(conversation.workspace_id)

                if not workspace or workspace.owner_id != user_id:
                    raise HTTPException(
                        status_code=403,
                        detail="Access denied to conversation"
                    )

            # Update fields
            if request.topic is not None:
                conversation.topic = request.topic

            if request.participant_ids is not None:
                # Ensure current user is in participants
                participant_ids = list(request.participant_ids)
                if user_id not in participant_ids:
                    participant_ids.append(user_id)
                conversation.participant_ids = participant_ids

            if request.metadata is not None:
                # Merge metadata instead of replacing
                conversation.metadata = {**conversation.metadata, **request.metadata}

            # Save changes
            updated_conversation = await conversation_repo.update(conversation)

            # Commit transaction
            await uow.commit()

            # Return response
            return ConversationResponse(
                status="conversation updated",
                conversation=updated_conversation
            )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log error
            import logging
            logging.error(f"Failed to update conversation: {str(e)}")

            # Generic error
            raise HTTPException(
                status_code=500,
                detail="Failed to update conversation"
            )

@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a conversation."""
    # Get user ID
    user_id = current_user["user_id"]

    async with UnitOfWork.for_transaction() as uow:
        try:
            # Get conversation repository
            conversation_repo = uow.repositories.get_conversation_repository()

            # Get conversation to check access
            conversation = await conversation_repo.get_by_id(conversation_id)

            if not conversation:
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation not found: {conversation_id}"
                )

            # Check if user is workspace owner
            workspace_repo = uow.repositories.get_workspace_repository()
            workspace = await workspace_repo.get_by_id(conversation.workspace_id)

            if not workspace or workspace.owner_id != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: only workspace owner can delete conversations"
                )

            # Delete all messages first
            message_repo = uow.repositories.get_message_repository()
            messages = await message_repo.list_by_conversation(conversation_id)

            for message in messages:
                await message_repo.delete(message.id)

            # Delete conversation
            result = await conversation_repo.delete(conversation_id)

            # Commit transaction
            await uow.commit()

            # Return response
            return {"status": "conversation deleted", "success": result}
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log error
            import logging
            logging.error(f"Failed to delete conversation: {str(e)}")

            # Generic error
            raise HTTPException(
                status_code=500,
                detail="Failed to delete conversation"
            )
```

This completes the PERSISTENCE_IMPLEMENTATION.md guide, providing a comprehensive reference for implementing SQLite persistence in Phase 2 of the Cortex Core platform.
