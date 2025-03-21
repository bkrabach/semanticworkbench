# PostgreSQL Migration Guide

## Overview

This document provides comprehensive instructions for migrating the Cortex Core platform from SQLite to PostgreSQL as part of Phase 5. This migration is a critical step toward production readiness, enabling improved performance, scalability, and reliability.

## Why PostgreSQL?

SQLite served as an ideal database for the early phases due to its simplicity and zero-configuration nature. However, as we prepare for production deployment, PostgreSQL offers several critical advantages:

1. **Concurrency Support**: Unlike SQLite's file-based locking, PostgreSQL provides true concurrent access
2. **Scalability**: Supports larger datasets and higher request volumes
3. **Advanced Features**: JSON/JSONB support, full-text search, triggers, stored procedures
4. **Robust Transactions**: ACID compliance with sophisticated isolation levels
5. **Connection Pooling**: Efficient handling of multiple concurrent connections
6. **Replication & Failover**: High availability options
7. **Enterprise Security**: Row-level security, authentication options, encryption

## Prerequisites

Before beginning the migration, ensure you have:

- PostgreSQL 14.0 or higher installed (locally or accessible)
- Python 3.10 or higher
- Access to the Cortex Core Phase 4 codebase
- `psycopg2` or `asyncpg` package (we'll use `asyncpg` for async support)
- Alembic for database migrations
- SQLAlchemy 2.0 or higher

## Project Structure Updates

We'll need to add or modify the following files:

```
cortex-core/
├── alembic/                   # Migration scripts
│   ├── env.py                 # Alembic environment configuration
│   ├── README                 # Migration documentation
│   ├── script.py.mako         # Migration script template
│   └── versions/              # Migration script versions
│       └── 001_sqlite_to_postgres.py  # Initial migration script
├── app/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── session.py         # Updated DB session management
│   │   ├── connection.py      # Connection pooling
│   │   └── repositories/      # Repository implementations
│   │       ├── base.py        # Base repository with PG support
│   │       ├── workspace.py   # Workspace repository
│   │       ├── conversation.py # Conversation repository
│   │       └── message.py     # Message repository
│   └── models/
│       └── database/          # SQLAlchemy ORM models
├── migrations/                # Data migration scripts
│   └── sqlite_to_postgres.py  # Data migration script
└── scripts/
    └── backup_postgres.py     # Backup script
```

## PostgreSQL Setup

### Local Development Installation

#### Ubuntu/Debian

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start the service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create a database and user
sudo -u postgres psql -c "CREATE USER cortex WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "CREATE DATABASE cortexcore;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cortexcore TO cortex;"
sudo -u postgres psql -c "ALTER USER cortex WITH SUPERUSER;"
```

#### macOS

```bash
# Using Homebrew
brew install postgresql

# Start the service
brew services start postgresql

# Create a database and user
psql postgres -c "CREATE USER cortex WITH PASSWORD 'your_password';"
psql postgres -c "CREATE DATABASE cortexcore;"
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE cortexcore TO cortex;"
psql postgres -c "ALTER USER cortex WITH SUPERUSER;"
```

#### Windows

Download and install PostgreSQL from [postgresql.org](https://www.postgresql.org/download/windows/).

During installation:

1. Set password for postgres user
2. Keep the default port (5432)
3. After installation, use pgAdmin to:
   - Create a new user: `cortex` with password `your_password`
   - Create a new database: `cortexcore`
   - Grant all privileges to `cortex` user

### Cloud Provider PostgreSQL (Production)

For production, we recommend using a managed PostgreSQL service:

#### Azure Database for PostgreSQL

```bash
# Create a PostgreSQL server
az postgres server create \
    --resource-group myResourceGroup \
    --name cortexcoredb \
    --location westus \
    --admin-user cortex \
    --admin-password your_secure_password \
    --sku-name GP_Gen5_2 \
    --version 14

# Configure firewall rules
az postgres server firewall-rule create \
    --resource-group myResourceGroup \
    --server-name cortexcoredb \
    --name AllowAll \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 255.255.255.255

# Create a database
az postgres db create \
    --resource-group myResourceGroup \
    --server-name cortexcoredb \
    --name cortexcore
```

#### AWS RDS for PostgreSQL

```bash
# Using AWS CLI
aws rds create-db-instance \
    --db-instance-identifier cortexcoredb \
    --db-instance-class db.t3.small \
    --engine postgres \
    --engine-version 14.5 \
    --master-username cortex \
    --master-user-password your_secure_password \
    --allocated-storage 20 \
    --db-name cortexcore
```

## Configuration Updates

### Environment Variables

Add PostgreSQL-specific environment variables:

```
# Database configuration
DATABASE_URL=postgresql+asyncpg://cortex:your_password@localhost:5432/cortexcore
POSTGRES_USER=cortex
POSTGRES_PASSWORD=your_password
POSTGRES_DB=cortexcore
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Connection pool settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
DB_ECHO=false
```

### Update Settings Module

Modify the settings module to include PostgreSQL configuration:

```python
# app/config.py
from pydantic import BaseSettings, PostgresDsn

class Settings(BaseSettings):
    # Existing settings...

    # PostgreSQL settings
    DATABASE_URL: PostgresDsn
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # Connection pool settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

## Database Connection and Session Management

First, create a robust connection management module:

````python
# app/database/connection.py
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from app.config import settings

logger = logging.getLogger(__name__)

# Create async engine with connection pooling
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Verify connections before using them
    poolclass=QueuePool
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session.

    Yields:
        AsyncSession: A database session

    Example:
        ```python
        async with get_db_session() as session:
            result = await session.execute(query)
        ```
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.exception(f"Database session error: {e}")
        raise
    finally:
        await session.close()

# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    async for session in get_db_session():
        yield session
````

Then, update the session middleware for FastAPI:

```python
# app/database/session.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db

def db_session(db: AsyncSession = Depends(get_db)):
    """FastAPI dependency for database session with error handling."""
    return db
```

## Database Models (SQLAlchemy)

Create or update SQLAlchemy ORM models with PostgreSQL-specific features:

```python
# app/models/database/base.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class BaseModel:
    """Base model with common fields."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

# app/models/database/user.py
from app.models.database.base import Base, BaseModel
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import JSONB

class User(Base, BaseModel):
    """User SQLAlchemy model."""
    __tablename__ = "users"

    user_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    metadata = Column(JSONB, default={}, nullable=False)

# app/models/database/workspace.py
from app.models.database.base import Base, BaseModel
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

class Workspace(Base, BaseModel):
    """Workspace SQLAlchemy model."""
    __tablename__ = "workspaces"

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    owner_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    metadata = Column(JSONB, default={}, nullable=False)

    # Relationships
    owner = relationship("User", backref="workspaces")
    conversations = relationship("Conversation", back_populates="workspace", cascade="all, delete-orphan")

# app/models/database/conversation.py
from app.models.database.base import Base, BaseModel
from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import relationship

class Conversation(Base, BaseModel):
    """Conversation SQLAlchemy model."""
    __tablename__ = "conversations"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    topic = Column(String(200), nullable=False)
    participant_ids = Column(ARRAY(String), nullable=False)
    metadata = Column(JSONB, default={}, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("ix_conversations_participant_ids", participant_ids, postgresql_using="gin"),
    )

# app/models/database/message.py
from app.models.database.base import Base, BaseModel
from sqlalchemy import Column, String, Text, ForeignKey, Index, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

class Message(Base, BaseModel):
    """Message SQLAlchemy model."""
    __tablename__ = "messages"

    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    metadata = Column(JSONB, default={}, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", backref="messages")

    # Indexes
    __table_args__ = (
        Index("ix_messages_conversation_timestamp", conversation_id, timestamp),
    )
```

## Alembic Setup for Migrations

Initialize Alembic for database migrations:

```bash
# Install Alembic if not already installed
pip install alembic

# Initialize Alembic
alembic init alembic

# Update alembic.ini with your database URL
sed -i 's/sqlalchemy.url = driver:\/\/user:pass@localhost\/dbname/sqlalchemy.url = postgresql+asyncpg:\/\/cortex:your_password@localhost:5432\/cortexcore/' alembic.ini
```

Update the Alembic environment:

```python
# alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context

# Import your models
from app.models.database.base import Base
from app.models.database.user import User
from app.models.database.workspace import Workspace
from app.models.database.conversation import Conversation
from app.models.database.message import Message

# this is the Alembic Config object
config = context.config

# Import project settings
from app.config import settings
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

# Add your model's MetaData objects here
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# ... usual Alembic env.py content ...

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

## Create Initial Migration Script

Generate the initial migration:

```bash
alembic revision --autogenerate -m "initial migration"
```

This will create a file in `alembic/versions/`. Review it for correctness, then run the migration:

```bash
alembic upgrade head
```

## Repository Pattern Implementation

Create a base repository and implement specific repositories:

```python
# app/database/repositories/base.py
from typing import Generic, TypeVar, Type, List, Optional, Any, Dict, Union, Callable
from uuid import UUID
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.models.database.base import Base

# Type variables
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def create(self, db: AsyncSession, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        obj_data = obj_in.model_dump(exclude_unset=True)
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get(self, db: AsyncSession, id: Union[UUID, str]) -> Optional[ModelType]:
        """Get a record by ID."""
        query = select(self.model).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalars().first()

    async def get_by(self, db: AsyncSession, **kwargs) -> Optional[ModelType]:
        """Get a record by specified attributes."""
        query = select(self.model)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        result = await db.execute(query)
        return result.scalars().first()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[Callable] = None
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        query = select(self.model).offset(skip).limit(limit)
        if order_by:
            query = query.order_by(order_by())
        result = await db.execute(query)
        return result.scalars().all()

    async def update(
        self,
        db: AsyncSession,
        *,
        obj_current: ModelType,
        obj_new: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """Update a record."""
        obj_data = obj_current.__dict__
        if isinstance(obj_new, dict):
            update_data = obj_new
        else:
            update_data = obj_new.model_dump(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(obj_current, field, update_data[field])
        db.add(obj_current)
        await db.flush()
        await db.refresh(obj_current)
        return obj_current

    async def remove(self, db: AsyncSession, id: Union[UUID, str]) -> Optional[ModelType]:
        """Remove a record."""
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj

    async def count(self, db: AsyncSession, **kwargs) -> int:
        """Count records with optional filtering."""
        from sqlalchemy import func
        query = select(func.count()).select_from(self.model)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        result = await db.execute(query)
        return result.scalar() or 0
```

Implement specific repositories:

```python
# app/database/repositories/workspace.py
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database.workspace import Workspace
from app.models.domain import WorkspaceCreate, WorkspaceUpdate
from app.database.repositories.base import BaseRepository

class WorkspaceRepository(BaseRepository[Workspace, WorkspaceCreate, WorkspaceUpdate]):
    """Repository for workspace operations."""

    def __init__(self):
        super().__init__(Workspace)

    async def list_by_owner(
        self, db: AsyncSession, owner_id: str, skip: int = 0, limit: int = 100
    ) -> List[Workspace]:
        """List workspaces by owner ID."""
        query = (
            select(Workspace)
            .where(Workspace.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .order_by(Workspace.created_at.desc())
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def get_with_conversations(self, db: AsyncSession, id: UUID) -> Optional[Workspace]:
        """Get workspace with conversations included."""
        query = (
            select(Workspace)
            .where(Workspace.id == id)
            .options(selectinload(Workspace.conversations))
        )
        result = await db.execute(query)
        return result.scalars().first()

# Similar repositories for Conversation and Message
```

## Domain Model to Database Model Mapping

Create mappers to convert between domain models and database models:

```python
# app/database/mappers.py
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models.database.workspace import Workspace as DbWorkspace
from app.models.database.conversation import Conversation as DbConversation
from app.models.database.message import Message as DbMessage
from app.models.domain import Workspace, Conversation, Message

class ModelMapper:
    """Map between domain models and database models."""

    @staticmethod
    def workspace_db_to_domain(db_workspace: DbWorkspace) -> Workspace:
        """Convert database workspace to domain workspace."""
        return Workspace(
            id=str(db_workspace.id),
            name=db_workspace.name,
            description=db_workspace.description,
            owner_id=db_workspace.owner_id,
            metadata=db_workspace.metadata or {},
            created_at=db_workspace.created_at.isoformat() if db_workspace.created_at else None,
            updated_at=db_workspace.updated_at.isoformat() if db_workspace.updated_at else None
        )

    @staticmethod
    def conversation_db_to_domain(db_conversation: DbConversation) -> Conversation:
        """Convert database conversation to domain conversation."""
        return Conversation(
            id=str(db_conversation.id),
            workspace_id=str(db_conversation.workspace_id),
            topic=db_conversation.topic,
            participant_ids=db_conversation.participant_ids,
            metadata=db_conversation.metadata or {},
            created_at=db_conversation.created_at.isoformat() if db_conversation.created_at else None,
            updated_at=db_conversation.updated_at.isoformat() if db_conversation.updated_at else None
        )

    @staticmethod
    def message_db_to_domain(db_message: DbMessage) -> Message:
        """Convert database message to domain message."""
        return Message(
            id=str(db_message.id),
            conversation_id=str(db_message.conversation_id),
            sender_id=db_message.sender_id,
            content=db_message.content,
            timestamp=db_message.timestamp.isoformat() if db_message.timestamp else None,
            metadata=db_message.metadata or {},
            created_at=db_message.created_at.isoformat() if db_message.created_at else None,
            updated_at=db_message.updated_at.isoformat() if db_message.updated_at else None
        )

    @staticmethod
    def workspaces_db_to_domain(db_workspaces: List[DbWorkspace]) -> List[Workspace]:
        """Convert list of database workspaces to domain workspaces."""
        return [ModelMapper.workspace_db_to_domain(w) for w in db_workspaces]

    @staticmethod
    def conversations_db_to_domain(db_conversations: List[DbConversation]) -> List[Conversation]:
        """Convert list of database conversations to domain conversations."""
        return [ModelMapper.conversation_db_to_domain(c) for c in db_conversations]

    @staticmethod
    def messages_db_to_domain(db_messages: List[DbMessage]) -> List[Message]:
        """Convert list of database messages to domain messages."""
        return [ModelMapper.message_db_to_domain(m) for m in db_messages]
```

## Service Layer Updates

Update services to use the new repositories:

```python
# app/services/workspace_service.py
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.workspace import WorkspaceRepository
from app.models.domain import WorkspaceCreate, WorkspaceUpdate, Workspace
from app.database.mappers import ModelMapper
from app.exceptions import NotFoundException, PermissionDeniedException

class WorkspaceService:
    """Service for workspace operations."""

    def __init__(self):
        self.repository = WorkspaceRepository()

    async def create_workspace(
        self, db: AsyncSession, workspace_create: WorkspaceCreate, owner_id: str
    ) -> Workspace:
        """Create a new workspace."""
        # Create workspace in database
        db_workspace = await self.repository.create(
            db,
            WorkspaceCreate(**workspace_create.model_dump(), owner_id=owner_id)
        )

        # Map to domain model and return
        return ModelMapper.workspace_db_to_domain(db_workspace)

    async def get_workspace(
        self, db: AsyncSession, workspace_id: UUID, user_id: str
    ) -> Workspace:
        """Get a workspace by ID."""
        db_workspace = await self.repository.get(db, workspace_id)
        if not db_workspace:
            raise NotFoundException(f"Workspace {workspace_id} not found")

        # Check permission
        if db_workspace.owner_id != user_id:
            raise PermissionDeniedException("You don't have access to this workspace")

        return ModelMapper.workspace_db_to_domain(db_workspace)

    async def list_workspaces(
        self, db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[Workspace]:
        """List workspaces for a user."""
        db_workspaces = await self.repository.list_by_owner(db, user_id, skip, limit)
        return ModelMapper.workspaces_db_to_domain(db_workspaces)

    async def update_workspace(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        workspace_update: WorkspaceUpdate,
        user_id: str
    ) -> Workspace:
        """Update a workspace."""
        # Get existing workspace
        db_workspace = await self.repository.get(db, workspace_id)
        if not db_workspace:
            raise NotFoundException(f"Workspace {workspace_id} not found")

        # Check permission
        if db_workspace.owner_id != user_id:
            raise PermissionDeniedException("You don't have permission to update this workspace")

        # Update workspace
        updated_workspace = await self.repository.update(
            db, obj_current=db_workspace, obj_new=workspace_update
        )

        return ModelMapper.workspace_db_to_domain(updated_workspace)

    async def delete_workspace(
        self, db: AsyncSession, workspace_id: UUID, user_id: str
    ) -> bool:
        """Delete a workspace."""
        # Get existing workspace
        db_workspace = await self.repository.get(db, workspace_id)
        if not db_workspace:
            raise NotFoundException(f"Workspace {workspace_id} not found")

        # Check permission
        if db_workspace.owner_id != user_id:
            raise PermissionDeniedException("You don't have permission to delete this workspace")

        # Delete workspace
        await self.repository.remove(db, workspace_id)
        return True
```

## Update API Endpoints

Update API endpoints to use the new services with database sessions:

```python
# app/api/endpoints/workspaces.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import db_session
from app.models.domain import User, Workspace, WorkspaceCreate, WorkspaceUpdate
from app.models.api.response import WorkspaceResponse, WorkspacesListResponse
from app.services.workspace_service import WorkspaceService
from app.auth.dependencies import get_current_user
from app.exceptions import NotFoundException, PermissionDeniedException

router = APIRouter()
workspace_service = WorkspaceService()

@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_create: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(db_session)
):
    """Create a new workspace."""
    try:
        workspace = await workspace_service.create_workspace(
            db, workspace_create, current_user.user_id
        )
        return WorkspaceResponse(status="workspace created", workspace=workspace)
    except Exception as e:
        # Log exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workspace: {str(e)}"
        )

@router.get("/", response_model=WorkspacesListResponse)
async def list_workspaces(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(db_session)
):
    """List workspaces for the current user."""
    try:
        workspaces = await workspace_service.list_workspaces(
            db, current_user.user_id, skip, limit
        )
        return WorkspacesListResponse(workspaces=workspaces)
    except Exception as e:
        # Log exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workspaces: {str(e)}"
        )

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(db_session)
):
    """Get a workspace by ID."""
    try:
        workspace = await workspace_service.get_workspace(
            db, workspace_id, current_user.user_id
        )
        return WorkspaceResponse(status="success", workspace=workspace)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionDeniedException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        # Log exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workspace: {str(e)}"
        )

@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    workspace_update: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(db_session)
):
    """Update a workspace."""
    try:
        workspace = await workspace_service.update_workspace(
            db, workspace_id, workspace_update, current_user.user_id
        )
        return WorkspaceResponse(status="workspace updated", workspace=workspace)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionDeniedException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        # Log exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workspace: {str(e)}"
        )

@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(db_session)
):
    """Delete a workspace."""
    try:
        await workspace_service.delete_workspace(
            db, workspace_id, current_user.user_id
        )
        return None
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionDeniedException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        # Log exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workspace: {str(e)}"
        )
```

## Data Migration Script

Create a script to migrate data from SQLite to PostgreSQL:

```python
# migrations/sqlite_to_postgres.py
import os
import asyncio
import sqlite3
import json
import logging
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.database.base import Base
from app.models.database.user import User
from app.models.database.workspace import Workspace
from app.models.database.conversation import Conversation
from app.models.database.message import Message

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SQLite database path
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/cortexcore.db")

# PostgreSQL connection string
PG_CONNECTION_STRING = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://cortex:your_password@localhost:5432/cortexcore"
)

async def get_postgres_session():
    """Get a PostgreSQL session."""
    engine = create_async_engine(PG_CONNECTION_STRING)

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    return async_session()

def get_sqlite_connection():
    """Get a SQLite connection."""
    return sqlite3.connect(SQLITE_DB_PATH)

async def migrate_users(sqlite_conn, pg_session):
    """Migrate users from SQLite to PostgreSQL."""
    logger.info("Migrating users...")

    # Get all users from SQLite
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute("SELECT user_id, name, email, metadata FROM users")
    users = sqlite_cursor.fetchall()

    # Insert users into PostgreSQL
    for user_id, name, email, metadata in users:
        try:
            # Parse metadata JSON
            metadata_dict = json.loads(metadata) if metadata else {}

            # Check if user already exists
            stmt = select(User).where(User.user_id == user_id)
            result = await pg_session.execute(stmt)
            existing_user = result.scalars().first()

            if not existing_user:
                # Create new user
                pg_user = User(
                    user_id=user_id,
                    name=name,
                    email=email,
                    metadata=metadata_dict
                )
                pg_session.add(pg_user)
                logger.info(f"Added user: {user_id}")
            else:
                logger.info(f"User already exists: {user_id}")

        except Exception as e:
            logger.error(f"Error migrating user {user_id}: {e}")

    # Commit changes
    await pg_session.commit()
    logger.info(f"Migrated {len(users)} users")

async def migrate_workspaces(sqlite_conn, pg_session):
    """Migrate workspaces from SQLite to PostgreSQL."""
    logger.info("Migrating workspaces...")

    # Get all workspaces from SQLite
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute("SELECT id, name, description, owner_id, metadata FROM workspaces")
    workspaces = sqlite_cursor.fetchall()

    # Track ID mappings (old ID -> new ID)
    id_mapping = {}

    # Insert workspaces into PostgreSQL
    for workspace_id, name, description, owner_id, metadata in workspaces:
        try:
            # Parse metadata JSON
            metadata_dict = json.loads(metadata) if metadata else {}

            # Generate new UUID for workspace
            new_id = uuid4()
            id_mapping[workspace_id] = new_id

            # Create new workspace
            pg_workspace = Workspace(
                id=new_id,
                name=name,
                description=description,
                owner_id=owner_id,
                metadata=metadata_dict
            )
            pg_session.add(pg_workspace)
            logger.info(f"Added workspace: {workspace_id} -> {new_id}")

        except Exception as e:
            logger.error(f"Error migrating workspace {workspace_id}: {e}")

    # Commit changes
    await pg_session.commit()
    logger.info(f"Migrated {len(workspaces)} workspaces")

    return id_mapping

async def migrate_conversations(sqlite_conn, pg_session, workspace_id_mapping):
    """Migrate conversations from SQLite to PostgreSQL."""
    logger.info("Migrating conversations...")

    # Get all conversations from SQLite
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute("SELECT id, workspace_id, topic, participant_ids, metadata FROM conversations")
    conversations = sqlite_cursor.fetchall()

    # Track ID mappings (old ID -> new ID)
    id_mapping = {}

    # Insert conversations into PostgreSQL
    for conv_id, workspace_id, topic, participant_ids, metadata in conversations:
        try:
            # Parse metadata and participant_ids JSON
            metadata_dict = json.loads(metadata) if metadata else {}
            participant_ids_list = json.loads(participant_ids) if participant_ids else []

            # Map workspace ID
            new_workspace_id = workspace_id_mapping.get(workspace_id)
            if not new_workspace_id:
                logger.warning(f"Workspace {workspace_id} not found in mapping, skipping conversation {conv_id}")
                continue

            # Generate new UUID for conversation
            new_id = uuid4()
            id_mapping[conv_id] = new_id

            # Create new conversation
            pg_conversation = Conversation(
                id=new_id,
                workspace_id=new_workspace_id,
                topic=topic,
                participant_ids=participant_ids_list,
                metadata=metadata_dict
            )
            pg_session.add(pg_conversation)
            logger.info(f"Added conversation: {conv_id} -> {new_id}")

        except Exception as e:
            logger.error(f"Error migrating conversation {conv_id}: {e}")

    # Commit changes
    await pg_session.commit()
    logger.info(f"Migrated {len(conversations)} conversations")

    return id_mapping

async def migrate_messages(sqlite_conn, pg_session, conversation_id_mapping):
    """Migrate messages from SQLite to PostgreSQL."""
    logger.info("Migrating messages...")

    # Get all messages from SQLite
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute("SELECT id, conversation_id, sender_id, content, timestamp, metadata FROM messages")
    messages = sqlite_cursor.fetchall()

    # Insert messages into PostgreSQL
    count = 0
    for msg_id, conversation_id, sender_id, content, timestamp, metadata in messages:
        try:
            # Parse metadata JSON
            metadata_dict = json.loads(metadata) if metadata else {}

            # Parse timestamp to datetime
            try:
                timestamp_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp_dt = datetime.utcnow()

            # Map conversation ID
            new_conversation_id = conversation_id_mapping.get(conversation_id)
            if not new_conversation_id:
                logger.warning(f"Conversation {conversation_id} not found in mapping, skipping message {msg_id}")
                continue

            # Generate new UUID for message
            new_id = uuid4()

            # Create new message
            pg_message = Message(
                id=new_id,
                conversation_id=new_conversation_id,
                sender_id=sender_id,
                content=content,
                timestamp=timestamp_dt,
                metadata=metadata_dict
            )
            pg_session.add(pg_message)
            count += 1

            # Commit in batches of 100
            if count % 100 == 0:
                await pg_session.commit()
                logger.info(f"Migrated {count}/{len(messages)} messages")

        except Exception as e:
            logger.error(f"Error migrating message {msg_id}: {e}")

    # Commit final batch
    await pg_session.commit()
    logger.info(f"Migrated {count} messages")

async def main():
    """Main migration function."""
    logger.info("Starting migration from SQLite to PostgreSQL")

    # Connect to databases
    sqlite_conn = get_sqlite_connection()
    pg_session = await get_postgres_session()

    try:
        # Migrate data
        await migrate_users(sqlite_conn, pg_session)
        workspace_id_mapping = await migrate_workspaces(sqlite_conn, pg_session)
        conversation_id_mapping = await migrate_conversations(sqlite_conn, pg_session, workspace_id_mapping)
        await migrate_messages(sqlite_conn, pg_session, conversation_id_mapping)

        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        # Close connections
        sqlite_conn.close()
        await pg_session.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## PostgreSQL Performance Optimization

Implement performance optimizations for PostgreSQL:

### Connection Pooling Configuration

Adjust connection pool settings in `app/database/connection.py`:

```python
# Optimal settings for a typical web application
# Feel free to adjust based on your specific workload
DB_POOL_SIZE = settings.DB_POOL_SIZE  # Default: 10
DB_MAX_OVERFLOW = settings.DB_MAX_OVERFLOW  # Default: 20
DB_POOL_TIMEOUT = settings.DB_POOL_TIMEOUT  # Default: 30
DB_POOL_RECYCLE = settings.DB_POOL_RECYCLE  # Default: 1800 (30 minutes)
```

### Query Optimization

Update repository methods to use optimized queries:

```python
# app/database/repositories/message.py

async def get_latest_messages(
    self, db: AsyncSession, conversation_id: UUID, limit: int = 50
) -> List[Message]:
    """
    Get latest messages for a conversation with optimized query.

    This uses an index on (conversation_id, timestamp) for efficiency.
    """
    query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    # Return in chronological order for display
    return list(reversed(result.scalars().all()))

async def count_messages_by_sender(
    self, db: AsyncSession, conversation_id: UUID
) -> Dict[str, int]:
    """
    Count messages by sender in a conversation using an optimized aggregation query.
    """
    from sqlalchemy import func

    query = (
        select(Message.sender_id, func.count(Message.id))
        .where(Message.conversation_id == conversation_id)
        .group_by(Message.sender_id)
    )
    result = await db.execute(query)
    return {sender_id: count for sender_id, count in result.all()}

async def search_messages(
    self, db: AsyncSession, conversation_id: UUID, search_term: str, limit: int = 50
) -> List[Message]:
    """
    Search messages in a conversation using PostgreSQL full-text search.
    """
    from sqlalchemy import text

    # Use PostgreSQL's to_tsquery for better full-text search
    # This requires a GIN index on content using to_tsvector
    # ALTER TABLE messages ADD COLUMN tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
    # CREATE INDEX messages_tsv_idx ON messages USING GIN(tsv);

    query = text("""
        SELECT id, conversation_id, sender_id, content, timestamp, metadata
        FROM messages
        WHERE conversation_id = :conversation_id
          AND tsv @@ to_tsquery('english', :search_term)
        ORDER BY ts_rank(tsv, to_tsquery('english', :search_term)) DESC
        LIMIT :limit
    """)

    # Convert search term to tsquery format (word1 & word2)
    search_term_tsquery = ' & '.join(search_term.split())

    result = await db.execute(
        query,
        {"conversation_id": conversation_id, "search_term": search_term_tsquery, "limit": limit}
    )

    return [Message(**row) for row in result.mappings()]
```

### Indexing Strategy

Create an SQL script for adding optimized indexes:

```sql
-- Create indexes for common query patterns

-- Users
CREATE INDEX idx_users_email ON users(email);

-- Workspaces
CREATE INDEX idx_workspaces_owner_id ON workspaces(owner_id);

-- Conversations
CREATE INDEX idx_conversations_workspace_id ON conversations(workspace_id);
CREATE INDEX idx_conversations_participants ON conversations USING GIN(participant_ids);

-- Messages
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
CREATE INDEX idx_messages_conversation_timestamp ON messages(conversation_id, timestamp);

-- Full-text search for messages
ALTER TABLE messages ADD COLUMN tsv tsvector
   GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
CREATE INDEX idx_messages_tsv ON messages USING GIN(tsv);
```

Save this as `sql/create_indexes.sql` and run it:

```bash
psql -U cortex -d cortexcore -f sql/create_indexes.sql
```

## JSONB Usage for Metadata

PostgreSQL offers powerful JSONB capabilities. Use them for the metadata fields:

````python
# app/database/repositories/workspace.py

async def find_by_metadata(
    self, db: AsyncSession, metadata_query: Dict[str, Any]
) -> List[Workspace]:
    """
    Find workspaces by metadata fields using JSONB queries.

    Example:
    ```
    # Find workspaces with specific tag
    workspaces = await workspace_repo.find_by_metadata(db, {"tags": "important"})

    # Find workspaces with specific color
    workspaces = await workspace_repo.find_by_metadata(db, {"color": "#ff0000"})
    ```
    """
    query = select(Workspace)

    # Add conditions for each metadata field
    for key, value in metadata_query.items():
        # Use the -> operator to access JSONB fields
        if isinstance(value, str):
            # For string values, use the ->> operator
            query = query.where(Workspace.metadata[key].astext == value)
        else:
            # For other values, use jsonb_path_query for more complex comparisons
            query = query.where(
                sql_text(f"jsonb_path_query(metadata, '$.{key}') @> '{json.dumps(value)}'::jsonb")
            )

    result = await db.execute(query)
    return result.scalars().all()
````

## Transaction Management

Implement proper transaction management:

````python
# app/database/transaction.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import async_session_factory

@asynccontextmanager
async def transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a transaction context manager.

    Example:
    ```
    async with transaction() as session:
        # Multiple operations in a single transaction
        user = await user_repo.create(session, user_data)
        workspace = await workspace_repo.create(session, workspace_data)
        # All changes will be committed together, or rolled back on error
    ```
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
````

Use it in service methods that require transaction integrity:

```python
# app/services/workspace_service.py

async def create_workspace_with_conversation(
    self, workspace_create: WorkspaceCreate, conversation_create: ConversationCreate, user_id: str
) -> Tuple[Workspace, Conversation]:
    """
    Create a workspace and an initial conversation in a single transaction.
    """
    async with transaction() as session:
        # Create workspace
        db_workspace = await self.repository.create(
            session,
            WorkspaceCreate(**workspace_create.model_dump(), owner_id=user_id)
        )

        # Create conversation in the workspace
        conversation_repo = ConversationRepository()
        db_conversation = await conversation_repo.create(
            session,
            ConversationCreate(
                workspace_id=str(db_workspace.id),
                topic=conversation_create.topic,
                participant_ids=[user_id] + conversation_create.participant_ids,
                metadata=conversation_create.metadata
            )
        )

        # Map to domain models and return
        return (
            ModelMapper.workspace_db_to_domain(db_workspace),
            ModelMapper.conversation_db_to_domain(db_conversation)
        )
```

## Error Handling for PostgreSQL

Implement PostgreSQL-specific error handling:

```python
# app/exceptions/database.py
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
import logging

logger = logging.getLogger(__name__)

class DatabaseException(Exception):
    """Base exception for database errors."""
    def __init__(self, message: str, original_error: Exception = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)

class DatabaseConnectionError(DatabaseException):
    """Error when unable to connect to the database."""
    pass

class DatabaseQueryError(DatabaseException):
    """Error when a database query fails."""
    pass

class DatabaseIntegrityError(DatabaseException):
    """Error when a database constraint is violated."""
    pass

class DatabaseTimeout(DatabaseException):
    """Error when a database operation times out."""
    pass

def handle_database_error(error: SQLAlchemyError) -> DatabaseException:
    """
    Convert SQLAlchemy errors to our custom exceptions.

    Args:
        error: The SQLAlchemy error

    Returns:
        An appropriate DatabaseException subclass
    """
    # Log the original error
    logger.error(f"Database error: {str(error)}")

    if isinstance(error, IntegrityError):
        # Handle constraint violations
        if "duplicate key" in str(error):
            return DatabaseIntegrityError("A record with this data already exists", error)
        elif "foreign key" in str(error):
            return DatabaseIntegrityError("Referenced record does not exist", error)
        else:
            return DatabaseIntegrityError("Data integrity constraint violated", error)
    elif isinstance(error, OperationalError):
        # Handle connection/operational issues
        if "timeout" in str(error).lower():
            return DatabaseTimeout("Database operation timed out", error)
        elif "connection" in str(error).lower():
            return DatabaseConnectionError("Failed to connect to the database", error)
        else:
            return DatabaseQueryError("Database operational error", error)
    else:
        # Handle other SQLAlchemy errors
        return DatabaseQueryError(f"Database query error: {str(error)}", error)

def database_error_handler(error: SQLAlchemyError) -> HTTPException:
    """
    Convert database errors to appropriate HTTP responses.

    Args:
        error: The SQLAlchemy error

    Returns:
        An HTTPException with appropriate status code and message
    """
    db_error = handle_database_error(error)

    if isinstance(db_error, DatabaseConnectionError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    elif isinstance(db_error, DatabaseTimeout):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Database operation timed out"
        )
    elif isinstance(db_error, DatabaseIntegrityError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=db_error.message
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal database error"
        )
```

Apply this error handling in the API layer:

```python
# app/api/endpoints/workspaces.py

@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_create: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(db_session)
):
    """Create a new workspace."""
    try:
        workspace = await workspace_service.create_workspace(
            db, workspace_create, current_user.user_id
        )
        return WorkspaceResponse(status="workspace created", workspace=workspace)
    except SQLAlchemyError as e:
        # Convert to appropriate HTTP error
        raise database_error_handler(e)
    except Exception as e:
        # Log other exceptions
        logger.exception(f"Unexpected error creating workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workspace: {str(e)}"
        )
```

## PostgreSQL Backup and Recovery

Create a backup script for PostgreSQL:

```python
# scripts/backup_postgres.py
import os
import subprocess
import datetime
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default settings
DEFAULT_BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
DEFAULT_DB_NAME = os.getenv("POSTGRES_DB", "cortexcore")
DEFAULT_DB_USER = os.getenv("POSTGRES_USER", "cortex")
DEFAULT_DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DEFAULT_DB_PORT = os.getenv("POSTGRES_PORT", "5432")

def create_backup(
    backup_dir=DEFAULT_BACKUP_DIR,
    db_name=DEFAULT_DB_NAME,
    db_user=DEFAULT_DB_USER,
    db_host=DEFAULT_DB_HOST,
    db_port=DEFAULT_DB_PORT
):
    """
    Create a PostgreSQL backup.

    Args:
        backup_dir: Directory to store backup files
        db_name: Database name
        db_user: Database user
        db_host: Database host
        db_port: Database port

    Returns:
        Path to the created backup file
    """
    # Create backup directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)

    # Create timestamp for filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"{db_name}_{timestamp}.sql")

    # Build pg_dump command
    cmd = [
        "pg_dump",
        f"--dbname={db_name}",
        f"--username={db_user}",
        f"--host={db_host}",
        f"--port={db_port}",
        "--format=custom",
        f"--file={backup_file}"
    ]

    # Run pg_dump
    logger.info(f"Creating backup: {backup_file}")
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stderr=subprocess.PIPE,
            env=dict(os.environ, PGPASSWORD=os.getenv("POSTGRES_PASSWORD", ""))
        )
        logger.info(f"Backup created successfully: {backup_file}")
        return backup_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Backup failed: {e.stderr.decode()}")
        raise

def restore_backup(
    backup_file,
    db_name=DEFAULT_DB_NAME,
    db_user=DEFAULT_DB_USER,
    db_host=DEFAULT_DB_HOST,
    db_port=DEFAULT_DB_PORT
):
    """
    Restore a PostgreSQL backup.

    Args:
        backup_file: Path to backup file
        db_name: Database name
        db_user: Database user
        db_host: Database host
        db_port: Database port

    Returns:
        True if successful
    """
    # Check if backup file exists
    if not os.path.isfile(backup_file):
        logger.error(f"Backup file not found: {backup_file}")
        return False

    # Build pg_restore command
    cmd = [
        "pg_restore",
        f"--dbname={db_name}",
        f"--username={db_user}",
        f"--host={db_host}",
        f"--port={db_port}",
        "--clean",  # Clean (drop) database objects before recreating
        "--if-exists",  # Only drop existing objects
        "--no-owner",  # Don't restore ownership
        "--no-privileges",  # Don't restore privileges
        backup_file
    ]

    # Run pg_restore
    logger.info(f"Restoring backup: {backup_file}")
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stderr=subprocess.PIPE,
            env=dict(os.environ, PGPASSWORD=os.getenv("POSTGRES_PASSWORD", ""))
        )
        logger.info(f"Backup restored successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Restore failed: {e.stderr.decode()}")
        raise

def list_backups(backup_dir=DEFAULT_BACKUP_DIR):
    """
    List available backups.

    Args:
        backup_dir: Directory containing backup files

    Returns:
        List of backup files
    """
    # Check if backup directory exists
    if not os.path.isdir(backup_dir):
        logger.warning(f"Backup directory not found: {backup_dir}")
        return []

    # List backup files
    backup_files = [f for f in os.listdir(backup_dir) if f.endswith(".sql")]
    backup_files.sort(reverse=True)  # Most recent first

    return backup_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PostgreSQL backup utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a backup")
    backup_parser.add_argument("--dir", help="Backup directory", default=DEFAULT_BACKUP_DIR)
    backup_parser.add_argument("--db", help="Database name", default=DEFAULT_DB_NAME)
    backup_parser.add_argument("--user", help="Database user", default=DEFAULT_DB_USER)
    backup_parser.add_argument("--host", help="Database host", default=DEFAULT_DB_HOST)
    backup_parser.add_argument("--port", help="Database port", default=DEFAULT_DB_PORT)

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore a backup")
    restore_parser.add_argument("backup_file", help="Backup file to restore")
    restore_parser.add_argument("--db", help="Database name", default=DEFAULT_DB_NAME)
    restore_parser.add_argument("--user", help="Database user", default=DEFAULT_DB_USER)
    restore_parser.add_argument("--host", help="Database host", default=DEFAULT_DB_HOST)
    restore_parser.add_argument("--port", help="Database port", default=DEFAULT_DB_PORT)

    # List command
    list_parser = subparsers.add_parser("list", help="List available backups")
    list_parser.add_argument("--dir", help="Backup directory", default=DEFAULT_BACKUP_DIR)

    args = parser.parse_args()

    if args.command == "backup":
        create_backup(args.dir, args.db, args.user, args.host, args.port)
    elif args.command == "restore":
        restore_backup(args.backup_file, args.db, args.user, args.host, args.port)
    elif args.command == "list":
        backup_files = list_backups(args.dir)
        if backup_files:
            print("Available backups:")
            for i, filename in enumerate(backup_files):
                print(f"{i+1}. {filename}")
        else:
            print("No backups found")
    else:
        parser.print_help()
```

## Testing with PostgreSQL

### Unit Testing

Create a test fixture for PostgreSQL:

```python
# tests/conftest.py
import pytest
import asyncio
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.models.database.base import Base

# Test database URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cortex:your_password@localhost:5432/cortexcore_test"
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_engine():
    """Create a database engine for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )

    # Create tables
    async with engine.begin() as conn:
        # Drop all tables first to ensure clean state
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up - drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Dispose engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing."""
    # Create a session factory
    async_session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    # Create a session
    session = async_session_factory()
    try:
        yield session
        # Roll back changes made during the test
        await session.rollback()
    finally:
        await session.close()
```

Use the fixture in repository tests:

```python
# tests/repositories/test_workspace_repository.py
import pytest
import uuid
from sqlalchemy import select
from app.database.repositories.workspace import WorkspaceRepository
from app.models.database.workspace import Workspace
from app.models.domain import WorkspaceCreate, WorkspaceUpdate

@pytest.mark.asyncio
async def test_create_workspace(db_session):
    """Test creating a workspace."""
    # Arrange
    repo = WorkspaceRepository()
    workspace_data = WorkspaceCreate(
        name="Test Workspace",
        description="Test workspace description",
        owner_id="test-user-id",
        metadata={"key": "value"}
    )

    # Act
    workspace = await repo.create(db_session, workspace_data)

    # Assert
    assert workspace is not None
    assert workspace.name == "Test Workspace"
    assert workspace.description == "Test workspace description"
    assert workspace.owner_id == "test-user-id"
    assert workspace.metadata == {"key": "value"}

@pytest.mark.asyncio
async def test_get_workspace(db_session):
    """Test getting a workspace by ID."""
    # Arrange
    repo = WorkspaceRepository()
    workspace_id = uuid.uuid4()
    db_workspace = Workspace(
        id=workspace_id,
        name="Test Workspace",
        description="Test workspace description",
        owner_id="test-user-id",
        metadata={"key": "value"}
    )
    db_session.add(db_workspace)
    await db_session.commit()

    # Act
    workspace = await repo.get(db_session, workspace_id)

    # Assert
    assert workspace is not None
    assert workspace.id == workspace_id
    assert workspace.name == "Test Workspace"

@pytest.mark.asyncio
async def test_list_by_owner(db_session):
    """Test listing workspaces by owner."""
    # Arrange
    repo = WorkspaceRepository()
    owner_id = "test-user-id"

    # Create test workspaces
    workspace1 = Workspace(
        name="Workspace 1",
        description="Description 1",
        owner_id=owner_id
    )
    workspace2 = Workspace(
        name="Workspace 2",
        description="Description 2",
        owner_id=owner_id
    )
    workspace3 = Workspace(
        name="Workspace 3",
        description="Description 3",
        owner_id="other-user-id"
    )

    db_session.add_all([workspace1, workspace2, workspace3])
    await db_session.commit()

    # Act
    workspaces = await repo.list_by_owner(db_session, owner_id)

    # Assert
    assert len(workspaces) == 2
    assert all(w.owner_id == owner_id for w in workspaces)
```

### Integration Testing

Create a test fixture for the FastAPI application:

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from unittest.mock import patch
from app.main import app
from app.database.connection import get_db
from app.auth.dependencies import get_current_user
from app.models.domain import User

@pytest.fixture
async def override_get_db(db_session):
    """Override get_db dependency to use test session."""

    async def _override_get_db():
        yield db_session

    return _override_get_db

@pytest.fixture
def override_get_current_user():
    """Override get_current_user dependency to return a test user."""
    test_user = User(
        user_id="test-user-id",
        name="Test User",
        email="test@example.com",
        roles=["admin"]
    )

    async def _override_get_current_user():
        return test_user

    return _override_get_current_user

@pytest.fixture
async def test_app(override_get_db, override_get_current_user):
    """Create a test app with overridden dependencies."""
    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    yield app

    # Clear dependency overrides
    app.dependency_overrides.clear()

@pytest.fixture
async def test_client(test_app):
    """Create a test client for the FastAPI app."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client
```

Use it in integration tests:

```python
# tests/api/test_workspaces.py
import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_create_workspace(test_client, db_session):
    """Test creating a workspace via the API."""
    # Arrange
    workspace_data = {
        "name": "Test Workspace",
        "description": "Test Description",
        "metadata": {"key": "value"}
    }

    # Act
    response = await test_client.post("/api/workspaces/", json=workspace_data)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "workspace created"
    assert data["workspace"]["name"] == "Test Workspace"
    assert data["workspace"]["description"] == "Test Description"
    assert data["workspace"]["owner_id"] == "test-user-id"

@pytest.mark.asyncio
async def test_list_workspaces(test_client, db_session):
    """Test listing workspaces via the API."""
    # Arrange - Create test workspaces in the database
    from app.models.database.workspace import Workspace

    workspace1 = Workspace(
        name="Workspace 1",
        description="Description 1",
        owner_id="test-user-id"
    )
    workspace2 = Workspace(
        name="Workspace 2",
        description="Description 2",
        owner_id="test-user-id"
    )

    db_session.add_all([workspace1, workspace2])
    await db_session.commit()

    # Act
    response = await test_client.get("/api/workspaces/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["workspaces"]) == 2
    assert data["workspaces"][0]["name"] in ["Workspace 1", "Workspace 2"]
    assert data["workspaces"][1]["name"] in ["Workspace 1", "Workspace 2"]
```

## Common Issues and Troubleshooting

### Connection Issues

If you encounter connection problems:

1. **Check Network Access**:

   ```bash
   # Test connection
   telnet localhost 5432

   # On Linux/macOS
   ping localhost

   # Check if PostgreSQL is running
   ps aux | grep postgres
   ```

2. **Check PostgreSQL Service**:

   ```bash
   # Ubuntu/Debian
   sudo systemctl status postgresql

   # macOS
   brew services list
   ```

3. **Check Connection Settings**:

   - Verify `DATABASE_URL` environment variable
   - Ensure username and password are correct
   - Check that the database exists
   - Verify host and port

4. **Check PostgreSQL Logs**:

   ```bash
   # Ubuntu/Debian
   sudo tail -f /var/log/postgresql/postgresql-14-main.log

   # macOS
   tail -f /usr/local/var/log/postgres.log
   ```

### Migration Issues

If you encounter migration problems:

1. **Alembic Version Mismatch**:

   ```bash
   # Check current database version
   alembic current

   # Get migration history
   alembic history

   # Reset to base
   alembic downgrade base

   # Upgrade to latest
   alembic upgrade head
   ```

2. **Schema Conflicts**:

   - Review the autogenerated migration script
   - Manually edit the script to fix conflicts
   - Test the migration in a staging environment first

3. **Data Type Conversion**:

   - SQLite and PostgreSQL have different type systems
   - Pay attention to date/time fields and JSON data
   - Use explicit type casts if needed

4. **Missing Dependencies**:
   ```bash
   # Install required packages
   pip install alembic psycopg2-binary asyncpg
   ```

### Performance Issues

If your PostgreSQL implementation is slow:

1. **Check Query Performance**:

   ```sql
   -- Add EXPLAIN ANALYZE to your queries
   EXPLAIN ANALYZE SELECT * FROM messages WHERE conversation_id = '123';
   ```

2. **Add Missing Indexes**:

   ```sql
   -- Create index for common query patterns
   CREATE INDEX idx_messages_conversation_timestamp ON messages(conversation_id, timestamp);
   ```

3. **Connection Pooling**:

   - Verify pool settings are appropriate
   - Check if you're leaking connections
   - Use connection debugging:
     ```sql
     SELECT * FROM pg_stat_activity;
     ```

4. **Review Query Patterns**:
   - Use `SELECT` with specific columns instead of `SELECT *`
   - Batch operations where possible
   - Use appropriate transaction isolation levels

## Production Deployment Checklist

Before deploying to production, ensure:

1. **Database Configuration**:

   - PostgreSQL connection string uses environment variables
   - Connection pooling is properly configured
   - Schema migrations have been tested
   - Indexes are in place for common queries

2. **Security Settings**:

   - Database password is secure
   - Network access is restricted
   - SSL connections are enabled
   - Database user has minimum required privileges

3. **Backup Solution**:

   - Regular backup schedule is configured
   - Backup retention policy is defined
   - Restore procedure is documented and tested
   - Sample restore command:
     ```bash
     python scripts/backup_postgres.py restore backups/cortexcore_20250320_120000.sql
     ```

4. **Monitoring and Logging**:

   - Database metrics are being collected
   - Slow query logging is enabled
   - Error logging is properly configured
   - Sample commands:

     ```sql
     -- Enable slow query logging
     ALTER SYSTEM SET log_min_duration_statement = '100ms';

     -- Monitor active connections
     SELECT count(*) FROM pg_stat_activity;
     ```

5. **Performance Tuning**:
   - Database settings are optimized for your workload
   - Connection pooling is correctly sized
   - Critical queries are optimized
   - Sample configurations:
     ```
     # postgresql.conf
     max_connections = 100
     shared_buffers = 1GB
     effective_cache_size = 3GB
     work_mem = 32MB
     maintenance_work_mem = 256MB
     ```

## Conclusion

This guide has covered the complete migration process from SQLite to PostgreSQL for the Cortex Core platform. By implementing these changes, you'll gain improved performance, reliability, and scalability for production deployment.

Key takeaways:

1. **PostgreSQL Advantages**: Better concurrency, advanced features, and performance
2. **Schema Migration**: Use Alembic for managing database schema evolution
3. **Repository Pattern**: Abstract database operations and ensure clean separation
4. **Connection Pooling**: Efficiently manage database connections
5. **Transaction Management**: Ensure data integrity with proper transactions
6. **Performance Optimization**: Indexes, JSONB usage, and query optimization
7. **Testing**: Unit and integration testing with PostgreSQL
8. **Backup and Recovery**: Regular backups for data safety

With these changes implemented, the Cortex Core platform will be ready for production use with a robust, scalable database backend.
