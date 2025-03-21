# Data Modeling Guide for Cortex Core

## Overview

This document provides a comprehensive guide to data modeling in the Cortex Core system for Phase 2. It covers domain models (Pydantic), database models (SQLAlchemy), their relationships, validation rules, and SQLite-specific considerations to ensure a consistent and maintainable data layer.

## Table of Contents

1. [Data Modeling Philosophy](#data-modeling-philosophy)
2. [Model Types and Relationships](#model-types-and-relationships)
3. [Domain Models (Pydantic)](#domain-models-pydantic)
4. [Database Models (SQLAlchemy)](#database-models-sqlalchemy)
5. [Model Relationships](#model-relationships)
6. [Validation Rules](#validation-rules)
7. [JSON Field Handling](#json-field-handling)
8. [User-Based Data Partitioning](#user-based-data-partitioning)
9. [Schema Simplification Strategies](#schema-simplification-strategies)
10. [Future Migration Considerations](#future-migration-considerations)
11. [SQLite-Specific Considerations](#sqlite-specific-considerations)
12. [Model Migration Strategy](#model-migration-strategy)
13. [Common Pitfalls](#common-pitfalls)

## Data Modeling Philosophy

Cortex Core's data modeling approach is guided by several key principles:

1. **Ruthless Simplicity**: Keep the schema as simple as possible while meeting requirements
2. **Clear Separation**: Maintain distinct domains for API, business logic, and persistence
3. **User Partitioning**: Design for strict data partitioning by user ID
4. **Extensibility**: Use metadata fields for flexible extensions without schema changes
5. **Pragmatic Storage**: Favor TEXT/JSON fields over complex normalization when appropriate
6. **Future-Ready**: Design with eventual PostgreSQL migration in mind

### The Three-Layer Model Approach

We use a three-layer approach to data modeling:

1. **API Models (Pydantic)**: Define request/response schemas for HTTP endpoints
2. **Domain Models (Pydantic)**: Define business entities used by application logic
3. **Database Models (SQLAlchemy)**: Define ORM models mapped to database tables

Each layer has its own concerns:

- API models focus on validation and documentation of HTTP interfaces
- Domain models focus on business rules and object relationships
- Database models focus on persistence, querying, and storage optimization

## Model Types and Relationships

The following diagram shows the relationship between model types:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  API Models │────▶│Domain Models│────▶│ DB Models   │
│  (Pydantic) │     │ (Pydantic)  │     │(SQLAlchemy) │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Request/   │     │  Business   │     │  Database   │
│  Response   │     │   Logic     │     │   Tables    │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Core Entity Types

The core entity types in the system are:

1. **User**: Represents a system user
2. **Workspace**: A top-level container for organizing conversations
3. **Conversation**: A grouping of messages within a workspace
4. **Message**: An individual message within a conversation

The entity relationship diagram:

```
┌─────────┐       ┌───────────┐       ┌─────────────┐       ┌─────────┐
│  User   │──1:N──▶ Workspace │──1:N──▶ Conversation │──1:N──▶ Message │
└─────────┘       └───────────┘       └─────────────┘       └─────────┘
```

## Domain Models (Pydantic)

Domain models represent the core business entities used in the application logic. They are implemented as Pydantic models for automatic validation and serialization.

### Base Model

All domain models extend from a base model with a common metadata field:

```python
from pydantic import BaseModel, Field
from typing import Dict, Any

class BaseModelWithMetadata(BaseModel):
    """Base model with metadata field for storing extra information."""
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### User Model

```python
from pydantic import BaseModel, Field, EmailStr
from typing import Dict, Any

class User(BaseModelWithMetadata):
    """User domain model."""
    user_id: str
    name: str
    email: str
```

**Field Descriptions**:

| Field      | Type   | Description                | Constraints            |
| ---------- | ------ | -------------------------- | ---------------------- |
| `user_id`  | string | Unique user identifier     | UUID format            |
| `name`     | string | User's display name        | Non-empty, ≤ 100 chars |
| `email`    | string | User's email address       | Valid email format     |
| `metadata` | object | Additional user properties | Optional, JSON object  |

### Workspace Model

```python
class Workspace(BaseModelWithMetadata):
    """Workspace domain model."""
    id: str
    name: str
    description: str
    owner_id: str
```

**Field Descriptions**:

| Field         | Type   | Description                     | Constraints            |
| ------------- | ------ | ------------------------------- | ---------------------- |
| `id`          | string | Unique workspace identifier     | UUID format            |
| `name`        | string | Workspace name                  | Non-empty, ≤ 100 chars |
| `description` | string | Workspace description           | Non-empty, ≤ 500 chars |
| `owner_id`    | string | ID of user who owns workspace   | Valid user ID          |
| `metadata`    | object | Additional workspace properties | Optional, JSON object  |

### Conversation Model

```python
from typing import List

class Conversation(BaseModelWithMetadata):
    """Conversation domain model."""
    id: str
    workspace_id: str
    topic: str
    participant_ids: List[str]
```

**Field Descriptions**:

| Field             | Type     | Description                    | Constraints              |
| ----------------- | -------- | ------------------------------ | ------------------------ |
| `id`              | string   | Unique conversation identifier | UUID format              |
| `workspace_id`    | string   | ID of containing workspace     | Valid workspace ID       |
| `topic`           | string   | Conversation topic             | Non-empty, ≤ 200 chars   |
| `participant_ids` | string[] | Array of participant user IDs  | At least one participant |
| `metadata`        | object   | Additional properties          | Optional, JSON object    |

### Message Model

```python
class Message(BaseModelWithMetadata):
    """Message domain model."""
    id: str
    conversation_id: str
    sender_id: str
    content: str
    timestamp: str
```

**Field Descriptions**:

| Field             | Type   | Description                   | Constraints           |
| ----------------- | ------ | ----------------------------- | --------------------- |
| `id`              | string | Unique message identifier     | UUID format           |
| `conversation_id` | string | ID of containing conversation | Valid conversation ID |
| `sender_id`       | string | ID of message sender          | Valid user ID         |
| `content`         | string | Message content               | Non-empty             |
| `timestamp`       | string | When message was sent         | ISO 8601 format       |
| `metadata`        | object | Additional properties         | Optional, JSON object |

### Domain Model Validation

Domain models include Pydantic validation rules:

```python
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Dict, Any, List
import uuid
import re

class User(BaseModelWithMetadata):
    """User domain model with validation."""
    user_id: str = Field(..., description="Unique user identifier")
    name: str = Field(..., min_length=1, max_length=100, description="User's name")
    email: str = Field(..., description="User's email address")

    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user_id is a valid UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('user_id must be a valid UUID')

    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError('Invalid email format')
        return v
```

## Database Models (SQLAlchemy)

Database models represent how data is stored in the database. They are implemented using SQLAlchemy.

### Base Model

```python
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class BaseDbModel:
    """Base database model with common fields."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

### User Model

```python
from sqlalchemy import Column, String, ForeignKey, Text

class User(Base, BaseDbModel):
    """User database model."""
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    metadata_json = Column(Text, default="{}")
```

### Workspace Model

```python
class Workspace(Base, BaseDbModel):
    """Workspace database model."""
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    metadata_json = Column(Text, default="{}")
```

### Conversation Model

```python
class Conversation(Base, BaseDbModel):
    """Conversation database model."""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True)
    topic = Column(String(200), nullable=False)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    participant_ids_json = Column(Text, nullable=False, default="[]")  # Store as JSON array
    metadata_json = Column(Text, default="{}")
```

### Message Model

```python
class Message(Base, BaseDbModel):
    """Message database model."""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    content = Column(Text, nullable=False)
    sender_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    timestamp = Column(String(50), nullable=False)  # ISO format timestamp
    metadata_json = Column(Text, default="{}")
```

### Indexes

Add indexes for frequently queried fields:

```python
from sqlalchemy import Index

# User indexes
Index('idx_user_email', User.email, unique=True)

# Workspace indexes
Index('idx_workspace_owner', Workspace.owner_id)

# Conversation indexes
Index('idx_conversation_workspace', Conversation.workspace_id)

# Message indexes
Index('idx_message_conversation', Message.conversation_id)
Index('idx_message_sender', Message.sender_id)
Index('idx_message_timestamp', Message.timestamp)
```

## Model Relationships

### SQLAlchemy Relationships

Define relationships between models using SQLAlchemy relationship attributes:

```python
from sqlalchemy.orm import relationship

class User(Base, BaseDbModel):
    # ... fields ...

    # Relationships
    workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="sender", cascade="all, delete-orphan")

class Workspace(Base, BaseDbModel):
    # ... fields ...

    # Relationships
    owner = relationship("User", back_populates="workspaces")
    conversations = relationship("Conversation", back_populates="workspace", cascade="all, delete-orphan")

class Conversation(Base, BaseDbModel):
    # ... fields ...

    # Relationships
    workspace = relationship("Workspace", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base, BaseDbModel):
    # ... fields ...

    # Relationships
    sender = relationship("User", back_populates="messages")
    conversation = relationship("Conversation", back_populates="messages")
```

### Relationship Cascades

The `cascade="all, delete-orphan"` option ensures:

1. **Automatic Deletion**: When a parent is deleted, all children are automatically deleted
2. **Orphan Deletion**: When a child is removed from the parent's collection, it is deleted

For example, deleting a workspace will automatically delete all its conversations and their messages.

### Loading Strategies

SQLAlchemy offers different loading strategies:

1. **Lazy Loading**: Related objects are loaded only when accessed (default)
2. **Eager Loading**: Related objects are loaded together with the parent

For Phase 2, we primarily use lazy loading to keep things simple, with selective eager loading for specific use cases:

```python
# Example of eager loading
from sqlalchemy.orm import selectinload

# Get workspace with conversations
workspace = await session.execute(
    select(Workspace)
    .options(selectinload(Workspace.conversations))
    .where(Workspace.id == workspace_id)
)
```

## Validation Rules

### Domain Model Validation

Domain models include validation rules defined by Pydantic:

```python
class Workspace(BaseModelWithMetadata):
    """Workspace domain model with validation."""
    id: str = Field(..., description="Unique workspace identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Workspace name")
    description: str = Field(..., min_length=1, max_length=500, description="Workspace description")
    owner_id: str = Field(..., description="ID of user who owns workspace")

    @validator('id')
    def validate_id(cls, v):
        """Validate ID is a valid UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('id must be a valid UUID')
```

### Database Model Validation

Database models include SQLAlchemy constraints:

```python
class User(Base, BaseDbModel):
    """User database model with constraints."""
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    metadata_json = Column(Text, default="{}")

    # Table-level constraints
    __table_args__ = (
        CheckConstraint('length(name) > 0', name='check_name_not_empty'),
        # Additional constraints as needed
    )
```

### Cross-Model Validation

For validation that spans multiple models, use service-level validation:

```python
async def validate_conversation_access(conversation_id: str, user_id: str) -> bool:
    """
    Validate user has access to conversation.

    Args:
        conversation_id: Conversation ID
        user_id: User ID

    Returns:
        True if user has access, False otherwise
    """
    async with UnitOfWork.for_transaction() as uow:
        # Get conversation
        conversation_repo = uow.repositories.get_conversation_repository()
        conversation = await conversation_repo.get_by_id(conversation_id)

        if not conversation:
            return False

        # Check if user is a participant
        if user_id in conversation.participant_ids:
            return True

        # Check if user is workspace owner
        workspace_repo = uow.repositories.get_workspace_repository()
        workspace = await workspace_repo.get_by_id(conversation.workspace_id)

        if workspace and workspace.owner_id == user_id:
            return True

        return False
```

## JSON Field Handling

SQLite stores JSON as text, requiring explicit serialization and deserialization.

### Storing JSON in SQLite

```python
import json

# Serialize metadata to JSON string
metadata_json = json.dumps(metadata) if metadata else "{}"

# Store in database
db_entity.metadata_json = metadata_json
```

### Reading JSON from SQLite

```python
import json

# Deserialize metadata from JSON string
metadata = {}
if db_entity.metadata_json:
    try:
        metadata = json.loads(db_entity.metadata_json)
    except json.JSONDecodeError:
        # Handle error (invalid JSON)
        pass
```

### Helper Methods for JSON Fields

Add helper methods to database models for working with JSON fields:

```python
class BaseDbModel:
    """Base database model with JSON helpers."""

    def get_metadata(self) -> Dict[str, Any]:
        """Get model metadata."""
        import json
        if hasattr(self, 'metadata_json') and self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Set model metadata."""
        import json
        if hasattr(self, 'metadata_json'):
            self.metadata_json = json.dumps(metadata) if metadata else "{}"
```

### Participant IDs as JSON

For the `participant_ids` field in Conversation, we use a JSON array stored as a text field:

```python
class Conversation(Base, BaseDbModel):
    # ... other fields ...
    participant_ids_json = Column(Text, nullable=False, default="[]")

    @property
    def participant_ids(self) -> List[str]:
        """Get participant IDs as a list."""
        import json
        try:
            return json.loads(self.participant_ids_json)
        except (json.JSONDecodeError, TypeError):
            return []

    @participant_ids.setter
    def participant_ids(self, value: List[str]) -> None:
        """Set participant IDs from a list."""
        import json
        self.participant_ids_json = json.dumps(value) if value else "[]"
```

## User-Based Data Partitioning

All data is partitioned by user ID to ensure strict data separation.

### Data Partitioning Principles

1. **Workspace Ownership**: Workspaces belong to a single owner
2. **Conversation Visibility**: Conversations are visible to participants and the workspace owner
3. **Message Ownership**: Messages belong to a sender and are visible to conversation participants

### Enforcing Data Partitioning in Queries

Always include user ID in queries:

```python
# Get workspaces for user
workspaces = await session.execute(
    select(Workspace).where(Workspace.owner_id == user_id)
)

# Get conversations where user is a participant
# This requires a more complex query since participant_ids is stored as JSON
from sqlalchemy import func

conversations = await session.execute(
    select(Conversation)
    .where(
        or_(
            # User is workspace owner
            Workspace.owner_id == user_id,
            # User is a participant (SQLite JSON query)
            func.json_extract(Conversation.participant_ids_json, '$').like(f'%"{user_id}"%')
        )
    )
    .join(Workspace)
)
```

### Access Control at the Repository Level

Enforce data partitioning in repositories:

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

## Schema Simplification Strategies

For Phase 2, we use several strategies to simplify the database schema.

### JSON for Complex Data

Use JSON for complex data that doesn't need to be queried:

```python
# Instead of a separate table for metadata with key-value pairs:
class Workspace(Base, BaseDbModel):
    # ... other fields ...
    metadata_json = Column(Text, default="{}")
```

### JSON for Simple Relations

Use JSON arrays for simple many-to-many relationships:

```python
# Instead of a complex join table for participants:
class Conversation(Base, BaseDbModel):
    # ... other fields ...
    participant_ids_json = Column(Text, nullable=False, default="[]")
```

### Single Text Fields Instead of Multiple Columns

Use a single text field for large content:

```python
# Instead of separate fields for different content parts:
class Message(Base, BaseDbModel):
    # ... other fields ...
    content = Column(Text, nullable=False)  # Store entire message content
```

### Deferred Normalization

Defer normalization until it's actually needed:

```python
# Instead of separate tables for workspace settings, permissions, etc.
# Just include everything in the workspace table for now
class Workspace(Base, BaseDbModel):
    # ... fields ...
    metadata_json = Column(Text, default="{}")  # Store settings, permissions, etc.
```

## Future Migration Considerations

Design decisions for future migration to PostgreSQL in Phase 5.

### Field Types Compatible with PostgreSQL

Use SQLite types that map well to PostgreSQL:

| SQLite Type | PostgreSQL Type | Notes                  |
| ----------- | --------------- | ---------------------- |
| `String`    | `VARCHAR`       | String with max length |
| `Text`      | `TEXT`          | Arbitrary length text  |
| `DateTime`  | `TIMESTAMP`     | Date and time          |
| `Integer`   | `INTEGER`       | Integer values         |
| `Float`     | `REAL`          | Floating point values  |
| `Boolean`   | `BOOLEAN`       | Boolean values         |

### JSON Field Considerations

In PostgreSQL, we'll use native JSON/JSONB fields:

```python
# SQLite implementation
metadata_json = Column(Text, default="{}")

# PostgreSQL future implementation
metadata = Column(JSONB, default={})
```

The repository mapping logic will handle this difference.

### Future Index Improvements

PostgreSQL supports more advanced indexing for JSON fields:

```python
# Future PostgreSQL-specific index
Index('idx_workspace_metadata_color', Workspace.metadata['color'], postgresql_using='gin')
```

### PostgreSQL-Specific Features to Consider

For future migration, consider:

1. **JSONB Indexing**: Indexing JSON fields for specific queries
2. **Full-Text Search**: Using PostgreSQL's full-text search capabilities
3. **Proper Constraints**: Adding more robust constraints
4. **Triggers**: Using database triggers for specific operations
5. **Views**: Creating database views for common queries

## SQLite-Specific Considerations

Special considerations for working with SQLite in Phase 2.

### SQLite Limitations

Be aware of these SQLite limitations:

1. **Concurrent Writes**: Only one writer can access the database at a time
2. **ALTER TABLE**: Limited support for ALTER TABLE operations
3. **Foreign Key Support**: Must be explicitly enabled
4. **JSON Support**: Limited built-in JSON functions
5. **Transactions**: Default journal_mode may not be optimal

### SQLite Configuration

Configure SQLite for better performance:

```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite configuration options."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()
```

### SQLite JSON Functions

SQLite has limited but useful JSON functions:

```python
from sqlalchemy import func

# Get workspaces with metadata containing 'color' key
workspaces = await session.execute(
    select(Workspace)
    .where(
        func.json_extract(Workspace.metadata_json, '$.color') == 'blue'
    )
)
```

### SQLite Full-Text Search

If full-text search is needed, use SQLite's FTS5 extension:

```python
from sqlalchemy import Table, Column, String, text

# Define FTS5 virtual table
fts_messages = Table(
    'fts_messages', Base.metadata,
    Column('rowid', String, primary_key=True),
    Column('content', String),
    Column('conversation_id', String),
    sqlite_fts_version='FTS5',
    sqlite_fts_columns=['content']
)

# Search for messages
messages = await session.execute(
    text("SELECT m.* FROM messages m JOIN fts_messages f ON m.id = f.rowid WHERE f.content MATCH :query")
    .bindparams(query="search term")
)
```

## Model Migration Strategy

Strategies for migrating from in-memory models to SQLite models.

### Data Migration Function

Create a function to migrate in-memory data to the database:

```python
async def migrate_to_sqlite():
    """Migrate in-memory data to SQLite database."""
    from app.core.storage import in_memory_storage

    async with UnitOfWork.for_transaction() as uow:
        try:
            # Migrate users
            for user_data in in_memory_storage.users.values():
                user = User(**user_data)
                await uow.repositories.get_user_repository().create(user)

            # Migrate workspaces
            for workspace_data in in_memory_storage.workspaces.values():
                workspace = Workspace(**workspace_data)
                await uow.repositories.get_workspace_repository().create(workspace)

            # Migrate conversations
            for conversation_data in in_memory_storage.conversations.values():
                conversation = Conversation(**conversation_data)
                await uow.repositories.get_conversation_repository().create(conversation)

            # Migrate messages
            for message_data in in_memory_storage.messages.values():
                message = Message(**message_data)
                await uow.repositories.get_message_repository().create(message)

            # Commit all changes
            await uow.commit()

            print("Migration completed successfully")
        except Exception as e:
            print(f"Migration failed: {str(e)}")
            # Transaction is automatically rolled back
            raise
```

### Schema Creation and Updates

Create a script to initialize the database schema:

```python
async def create_database_schema():
    """Create database schema."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from app.database.models import Base

    # Create engine
    engine = create_async_engine(DATABASE_URL)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Clean up
    await engine.dispose()
```

## Common Pitfalls

Common pitfalls to avoid when working with this data model.

### JSON Serialization Errors

Ensure proper error handling for JSON serialization/deserialization:

```python
def get_metadata(self) -> Dict[str, Any]:
    """Get metadata with proper error handling."""
    if not self.metadata_json:
        return {}

    try:
        return json.loads(self.metadata_json)
    except json.JSONDecodeError:
        # Log error
        import logging
        logging.error(f"Invalid JSON in metadata field: {self.metadata_json}")
        # Return empty metadata
        return {}
```

### SQLite Locking Issues

Handle database locking issues with proper timeout configurations:

```python
from sqlalchemy.exc import OperationalError

try:
    # Attempt database operation
    await session.execute(query)
except OperationalError as e:
    if "database is locked" in str(e):
        # Handle locking error
        import logging
        logging.warning("Database lock detected, retrying operation")
        # Implement retry logic
    else:
        # Re-raise other operational errors
        raise
```

### Relationship Circular Dependencies

Avoid circular dependencies in model imports:

```python
# Instead of direct imports that can cause circular references:
from app.database.models.user import User
from app.database.models.workspace import Workspace

# Use string references in relationship definitions:
relationship("User", back_populates="workspaces")
```

### Default Values for JSON Fields

Always provide proper default values for JSON fields:

```python
# Define default value for JSON field
metadata_json = Column(Text, default="{}")

# Initialize metadata during object creation
def __init__(self, **kwargs):
    # Set default values
    if 'metadata_json' not in kwargs:
        kwargs['metadata_json'] = '{}'
    super().__init__(**kwargs)
```

### SQLite Case Sensitivity

SQLite string comparisons are case-sensitive by default:

```python
# Case-insensitive search
users = await session.execute(
    select(User)
    .where(func.lower(User.email) == email.lower())
)
```

This document provides a comprehensive guide to data modeling in the Cortex Core Phase 2. By following these guidelines, you'll create a clean, maintainable, and extensible data model that meets the current requirements while preparing for future growth.
