# Validation Guide for Cortex Core Phase 2

## Overview

This document provides a comprehensive guide to implementing validation within the Cortex Core system for Phase 2. Proper validation is essential for maintaining data integrity, providing clear feedback to clients, and ensuring system security. This guide covers all aspects of validation from API requests to database constraints.

## Table of Contents

1. [Validation Philosophy](#validation-philosophy)
2. [Validation Layers](#validation-layers)
3. [API Request Validation](#api-request-validation)
4. [Domain Model Validation](#domain-model-validation)
5. [Database Constraints](#database-constraints)
6. [Cross-Entity Validation](#cross-entity-validation)
7. [Error Handling and Responses](#error-handling-and-responses)
8. [Testing Validation Logic](#testing-validation-logic)
9. [Common Validation Patterns](#common-validation-patterns)
10. [SQLite-Specific Considerations](#sqlite-specific-considerations)
11. [Best Practices and Pitfalls](#best-practices-and-pitfalls)
12. [Implementation Examples](#implementation-examples)

## Validation Philosophy

Our validation approach follows three core principles aligned with the overall project philosophy:

1. **Fail Fast, Fail Clearly**: Validate input at the system's entry point before processing begins. Provide clear, actionable error messages that explain exactly what is wrong.

2. **Validation at Appropriate Layers**: Apply validation checks at the appropriate architectural layer. For example, handle format validation at the API level, business rules at the domain level, and referential integrity at the database level.

3. **Minimal but Sufficient Validation**: Implement only the validation rules necessary to ensure system integrity and security. Avoid excessive validation that doesn't provide meaningful benefits.

## Validation Layers

Cortex Core implements validation at three distinct layers, each with specific responsibilities:

```
┌─────────────────┐
│  API Layer      │ → Format validation, type checking, basic constraints
└─────────────────┘
         ↓
┌─────────────────┐
│  Domain Layer   │ → Business rules, entity relationships, complex constraints
└─────────────────┘
         ↓
┌─────────────────┐
│  Database Layer │ → Referential integrity, uniqueness, not-null constraints
└─────────────────┘
```

Each layer builds upon the validation provided by the layer above, creating a defense-in-depth approach to data integrity.

## API Request Validation

The API layer is responsible for validating the structure and basic content of incoming requests.

### Pydantic Model Validation

Cortex Core uses Pydantic models for automatic validation of API requests:

```python
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional
import uuid
import re

class WorkspaceCreate(BaseModel):
    """Request model for creating a workspace."""
    name: str = Field(
        ...,  # Required field
        min_length=1,
        max_length=100,
        description="Workspace name"
    )
    description: str = Field(
        ...,  # Required field
        min_length=1,
        max_length=500,
        description="Workspace description"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for the workspace"
    )

    @validator('name')
    def name_must_not_contain_special_chars(cls, v):
        """Validate that name doesn't contain special characters."""
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise ValueError("Name must contain only alphanumeric characters, spaces, hyphens, and underscores")
        return v
```

### Key Validation Rules for API Models

#### User-Related Validation

For User operations:

- `user_id`: UUID format
- `name`: 1-100 alphanumeric characters, spaces, hyphens, and underscores
- `email`: Valid email format

#### Workspace-Related Validation

For Workspace operations:

- `name`: 1-100 alphanumeric characters, spaces, hyphens, and underscores
- `description`: 1-500 characters
- `metadata`: Optional JSON object

#### Conversation-Related Validation

For Conversation operations:

- `workspace_id`: Valid UUID format, must exist
- `topic`: 1-200 alphanumeric characters, spaces, hyphens, underscores, and common punctuation
- `participant_ids`: List of valid user IDs, must not be empty
- `metadata`: Optional JSON object

#### Message-Related Validation

For Message operations:

- `conversation_id`: Valid UUID format, must exist
- `content`: Non-empty string
- `metadata`: Optional JSON object

### Implementing FastAPI Validation

FastAPI automatically validates incoming requests against Pydantic models:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.api.request import WorkspaceCreate
from app.models.api.response import WorkspaceResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/config", tags=["config"])

@router.post("/workspace", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreate,  # Validation happens automatically here
    current_user: dict = Depends(get_current_user)
):
    """Create a new workspace."""
    # If validation fails, FastAPI returns a 422 Unprocessable Entity error
    # with detailed validation error information

    # Implementation (request is already validated)
    ...
```

### Handling Optional Fields

For optional fields, use the `Optional` type hint and `default` or `default_factory` parameter:

```python
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ConversationUpdate(BaseModel):
    """Request model for updating a conversation."""
    topic: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Conversation topic"
    )
    participant_ids: Optional[List[str]] = Field(
        default=None,
        description="List of user IDs participating in the conversation"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for the conversation"
    )
```

### Custom Validators

Implement custom validators for complex validation rules:

```python
from pydantic import BaseModel, Field, validator
from typing import List
import uuid

class ConversationCreate(BaseModel):
    """Request model for creating a conversation."""
    workspace_id: str = Field(..., description="ID of the parent workspace")
    topic: str = Field(..., min_length=1, max_length=200, description="Conversation topic")
    participant_ids: List[str] = Field(default_factory=list, description="List of user IDs")

    @validator('workspace_id')
    def validate_workspace_id(cls, v):
        """Validate workspace_id is a valid UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('workspace_id must be a valid UUID')

    @validator('participant_ids')
    def validate_participant_ids(cls, v):
        """Validate participant_ids contains valid UUIDs and is not empty."""
        if not v:
            raise ValueError('participant_ids must not be empty')

        for user_id in v:
            try:
                uuid.UUID(user_id)
            except ValueError:
                raise ValueError(f'Invalid user ID format: {user_id}')

        return v
```

### Request Validation with Dependencies

Use FastAPI dependencies for additional request validation:

```python
from fastapi import Depends, HTTPException, status
from app.database.repositories.workspace import WorkspaceRepositoryImpl

async def validate_workspace_exists(
    workspace_id: str,
    repo: WorkspaceRepositoryImpl = Depends(get_workspace_repository)
) -> str:
    """
    Validate that workspace exists.

    Args:
        workspace_id: Workspace ID
        repo: Workspace repository

    Returns:
        Workspace ID if valid

    Raises:
        HTTPException: If workspace does not exist
    """
    workspace = await repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found"
        )
    return workspace_id

@router.post("/conversation")
async def create_conversation(
    request: ConversationCreate,
    workspace_id: str = Depends(validate_workspace_exists),
    current_user: dict = Depends(get_current_user)
):
    """Create a new conversation."""
    # Implementation
    ...
```

## Domain Model Validation

Domain models require validation to ensure business rules are enforced.

### Domain Model Validators

Define validators for domain models:

```python
from pydantic import BaseModel, Field, validator, root_validator
from typing import Dict, Any, List
import uuid

class Conversation(BaseModel):
    """Conversation domain model."""
    id: str
    workspace_id: str
    topic: str
    participant_ids: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('id', 'workspace_id')
    def validate_uuid(cls, v, values, **kwargs):
        """Validate that id and workspace_id are valid UUIDs."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            field_name = kwargs.get('field').name
            raise ValueError(f'{field_name} must be a valid UUID')

    @root_validator
    def validate_participants(cls, values):
        """Validate that participant_ids contains at least one entry."""
        participant_ids = values.get('participant_ids', [])
        if not participant_ids:
            raise ValueError('conversation must have at least one participant')
        return values
```

### Business Rule Validation

Implement domain-specific business rules in validators:

```python
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List
import uuid
from datetime import datetime

class Message(BaseModel):
    """Message domain model."""
    id: str
    conversation_id: str
    sender_id: str
    content: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate timestamp is in ISO format and not in the future."""
        try:
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))

            # Check if timestamp is not in the future
            if dt > datetime.now():
                raise ValueError('timestamp cannot be in the future')

            return v
        except ValueError:
            raise ValueError('timestamp must be a valid ISO 8601 format')
```

## Database Constraints

The database layer provides the final line of defense for data integrity.

### SQLite Table Constraints

Define database constraints in SQLAlchemy models:

```python
from sqlalchemy import Column, String, Table, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    """User database model."""
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    metadata_json = Column(String, default="{}")

    # Check constraints
    __table_args__ = (
        CheckConstraint("length(name) > 0", name="check_name_not_empty"),
    )

class Workspace(Base):
    """Workspace database model."""
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    metadata_json = Column(String, default="{}")

    # Check constraints
    __table_args__ = (
        CheckConstraint("length(name) > 0", name="check_workspace_name_not_empty"),
        CheckConstraint("length(description) > 0", name="check_workspace_description_not_empty"),
    )
```

### Common Database Constraints

Use these constraints to enforce data integrity:

1. **Primary Key**: Ensures each row has a unique identifier:

   ```python
   id = Column(String(36), primary_key=True)
   ```

2. **Foreign Key**: Enforces relationships between tables:

   ```python
   workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
   ```

3. **Not Null**: Ensures required fields are present:

   ```python
   name = Column(String(100), nullable=False)
   ```

4. **Unique**: Prevents duplicate values:

   ```python
   email = Column(String(255), nullable=False, unique=True)
   ```

5. **Check Constraint**: Enforces specific conditions:

   ```python
   CheckConstraint("length(name) > 0", name="check_name_not_empty")
   ```

### SQLite Check Constraints

SQLite supports a limited subset of check constraints. Use these supported operations:

- Comparison operators (`=`, `<>`, `<`, `<=`, `>`, `>=`)
- Logical operators (`AND`, `OR`, `NOT`)
- `IS NULL` and `IS NOT NULL`
- `LIKE` and `GLOB` pattern matching
- `length()` function
- `BETWEEN` operator
- `IN` operator

Example constraint that checks minimum string length:

```python
CheckConstraint("length(name) > 0", name="check_name_not_empty")
```

## Cross-Entity Validation

Some validation rules span multiple entities and require special handling.

### Service-Level Validation

Implement cross-entity validation in service methods:

```python
async def create_conversation(
    workspace_id: str,
    topic: str,
    participant_ids: List[str],
    current_user_id: str
) -> Conversation:
    """
    Create a new conversation.

    Args:
        workspace_id: Workspace ID
        topic: Conversation topic
        participant_ids: List of participant user IDs
        current_user_id: Current user ID

    Returns:
        Created conversation

    Raises:
        ValueError: If validation fails
    """
    async with UnitOfWork.for_transaction() as uow:
        # Validate workspace exists and user has access
        workspace_repo = uow.repositories.get_workspace_repository()
        workspace = await workspace_repo.get_by_id(workspace_id)

        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")

        if workspace.owner_id != current_user_id:
            raise ValueError(f"Access denied to workspace {workspace_id}")

        # Validate participants exist
        user_repo = uow.repositories.get_user_repository()
        for user_id in participant_ids:
            user = await user_repo.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

        # Create conversation
        conversation = Conversation(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            topic=topic,
            participant_ids=participant_ids,
            metadata={}
        )

        # Save conversation
        conversation_repo = uow.repositories.get_conversation_repository()
        created_conversation = await conversation_repo.create(conversation)

        # Commit transaction
        await uow.commit()

        return created_conversation
```

### Repository-Level Validation

Implement validation in repository methods where appropriate:

```python
async def create(self, conversation: Conversation) -> Conversation:
    """
    Create a new conversation.

    Args:
        conversation: Conversation to create

    Returns:
        Created conversation

    Raises:
        ValueError: If validation fails
    """
    # Validate workspace exists
    workspace_result = await self.session.execute(
        select(DbWorkspace).where(DbWorkspace.id == conversation.workspace_id)
    )
    workspace = workspace_result.scalars().first()

    if not workspace:
        raise ValueError(f"Workspace {conversation.workspace_id} not found")

    # Convert to database model
    db_conversation = self._to_db(conversation)

    # Save to database
    self.session.add(db_conversation)
    await self.session.flush()

    # Return domain model
    return self._to_domain(db_conversation)
```

### Using Unit of Work for Transactional Validation

Use the Unit of Work pattern for transactions that require validation across multiple repositories:

```python
async def create_workspace_with_conversation(
    workspace_name: str,
    workspace_description: str,
    conversation_topic: str,
    owner_id: str
) -> Tuple[Workspace, Conversation]:
    """
    Create a workspace with an initial conversation.

    Args:
        workspace_name: Workspace name
        workspace_description: Workspace description
        conversation_topic: Conversation topic
        owner_id: Owner user ID

    Returns:
        Tuple of (workspace, conversation)

    Raises:
        ValueError: If validation fails
    """
    async with UnitOfWork.for_transaction() as uow:
        try:
            # Validate owner exists
            user_repo = uow.repositories.get_user_repository()
            user = await user_repo.get_by_id(owner_id)

            if not user:
                raise ValueError(f"User {owner_id} not found")

            # Create workspace
            workspace = Workspace(
                id=str(uuid.uuid4()),
                name=workspace_name,
                description=workspace_description,
                owner_id=owner_id,
                metadata={}
            )

            workspace_repo = uow.repositories.get_workspace_repository()
            created_workspace = await workspace_repo.create(workspace)

            # Create conversation
            conversation = Conversation(
                id=str(uuid.uuid4()),
                workspace_id=created_workspace.id,
                topic=conversation_topic,
                participant_ids=[owner_id],
                metadata={}
            )

            conversation_repo = uow.repositories.get_conversation_repository()
            created_conversation = await conversation_repo.create(conversation)

            # Commit transaction
            await uow.commit()

            return created_workspace, created_conversation
        except Exception as e:
            # Transaction is automatically rolled back
            raise ValueError(f"Failed to create workspace with conversation: {str(e)}")
```

## Error Handling and Responses

Provide clear, actionable error messages to clients when validation fails.

### FastAPI Validation Exceptions

FastAPI automatically handles Pydantic validation errors, returning a 422 Unprocessable Entity response:

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Custom Exception Handler

Implement a custom exception handler for validation errors:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation exceptions.

    Returns:
        JSONResponse with error details
    """
    errors = {}
    for error in exc.errors():
        # Get the field name (last part of the location)
        field_name = error["loc"][-1] if error["loc"] else "unknown"
        # Get the error message
        message = error["msg"]
        # Add to errors dict
        errors[field_name] = message

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "validation_error",
                "message": "Invalid input data",
                "details": errors
            }
        }
    )
```

### Repository Error Handling

Handle validation errors in repositories:

```python
async def create(self, workspace: Workspace) -> Workspace:
    """
    Create a new workspace.

    Args:
        workspace: Workspace to create

    Returns:
        Created workspace

    Raises:
        RepositoryError: If validation fails
    """
    try:
        # Convert to database model
        db_workspace = self._to_db(workspace)

        # Save to database
        self.session.add(db_workspace)
        await self.session.flush()

        # Return domain model
        return self._to_domain(db_workspace)
    except IntegrityError as e:
        error_message = str(e).lower()
        if "unique constraint" in error_message and "email" in error_message:
            raise DuplicateEntityError("Workspace", "name", workspace.name)
        elif "foreign key constraint" in error_message:
            raise EntityNotFoundError("User", workspace.owner_id)
        else:
            raise RepositoryError(f"Failed to create workspace: {str(e)}", e)
```

### API Error Responses

Define a consistent error response format:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid input data",
    "details": {
      "name": "field required",
      "description": "field required"
    }
  }
}
```

Example API handler with error response:

```python
@router.post("/workspace", response_model=WorkspaceResponse)
async def create_workspace(
    request: WorkspaceCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new workspace."""
    try:
        # Create workspace
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name=request.name,
            description=request.description,
            owner_id=current_user["user_id"],
            metadata=request.metadata or {}
        )

        # Save workspace
        workspace_repo = WorkspaceRepositoryImpl(db)
        created_workspace = await workspace_repo.create(workspace)

        # Commit transaction
        await db.commit()

        # Return response
        return WorkspaceResponse(
            status="workspace created",
            workspace=created_workspace
        )
    except ValueError as e:
        # Validation error
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "validation_error",
                    "message": str(e)
                }
            }
        )
    except EntityNotFoundError as e:
        # Entity not found
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": str(e)
                }
            }
        )
    except DuplicateEntityError as e:
        # Duplicate entity
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "conflict",
                    "message": str(e)
                }
            }
        )
    except Exception as e:
        # Other errors
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred"
                }
            }
        )
```

## Testing Validation Logic

### Testing API Validation

Test API validation using FastAPI's TestClient:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_workspace_validation():
    """Test workspace creation validation."""
    # Missing required fields
    response = client.post(
        "/config/workspace",
        json={},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 400
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "validation_error"

    # Invalid name (too long)
    response = client.post(
        "/config/workspace",
        json={
            "name": "a" * 101,
            "description": "Test description"
        },
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 400
    assert "error" in response.json()
    assert "name" in response.json()["error"]["details"]
```

### Testing Domain Model Validation

Test domain model validation directly:

```python
import pytest
from app.models.domain import Workspace
import uuid

def test_workspace_validation():
    """Test workspace domain model validation."""
    # Valid workspace
    workspace = Workspace(
        id=str(uuid.uuid4()),
        name="Test Workspace",
        description="Test description",
        owner_id=str(uuid.uuid4()),
        metadata={}
    )
    assert workspace.id is not None

    # Invalid ID
    with pytest.raises(ValueError) as exc:
        Workspace(
            id="invalid-uuid",
            name="Test Workspace",
            description="Test description",
            owner_id=str(uuid.uuid4()),
            metadata={}
        )
    assert "id" in str(exc.value).lower()
    assert "uuid" in str(exc.value).lower()
```

### Testing Repository Validation

Test repository validation:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.workspace import WorkspaceRepositoryImpl
from app.models.domain import Workspace
from app.database.exceptions import DuplicateEntityError, EntityNotFoundError
import uuid

@pytest.mark.asyncio
async def test_workspace_repository_validation(test_db):
    """Test workspace repository validation."""
    repo = WorkspaceRepositoryImpl(test_db)

    # Create workspace with non-existent owner
    with pytest.raises(EntityNotFoundError) as exc:
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name="Test Workspace",
            description="Test description",
            owner_id=str(uuid.uuid4()),  # Random non-existent owner
            metadata={}
        )
        await repo.create(workspace)

    assert "user" in str(exc.value).lower()
    assert "not found" in str(exc.value).lower()
```

### Integration Testing

Test validation across multiple components:

```python
import pytest
from httpx import AsyncClient
from app.main import app
from app.utils.auth import create_access_token

@pytest.mark.asyncio
async def test_create_conversation_integration():
    """Test conversation creation with validation."""
    # Create test token
    token = create_access_token({
        "sub": "test@example.com",
        "oid": "test-user-id",
        "name": "Test User",
        "email": "test@example.com"
    })

    # Create test client
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create workspace first
        workspace_response = await client.post(
            "/config/workspace",
            json={
                "name": "Test Workspace",
                "description": "Test description"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["workspace"]["id"]

        # Try to create conversation with invalid workspace ID
        conversation_response = await client.post(
            "/config/conversation",
            json={
                "workspace_id": "invalid-uuid",
                "topic": "Test Topic"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert conversation_response.status_code == 400
        assert "error" in conversation_response.json()
        assert "workspace_id" in conversation_response.json()["error"]["details"]

        # Create valid conversation
        valid_conversation_response = await client.post(
            "/config/conversation",
            json={
                "workspace_id": workspace_id,
                "topic": "Test Topic",
                "participant_ids": ["test-user-id"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert valid_conversation_response.status_code == 201
```

## Common Validation Patterns

### UUID Validation

Validate UUID format:

```python
def validate_uuid(value: str, field_name: str = "id") -> str:
    """
    Validate that a string is a valid UUID.

    Args:
        value: String to validate
        field_name: Field name for error message

    Returns:
        Original value if valid

    Raises:
        ValueError: If value is not a valid UUID
    """
    try:
        uuid.UUID(value)
        return value
    except ValueError:
        raise ValueError(f"{field_name} must be a valid UUID")
```

### Email Validation

Validate email format:

```python
def validate_email(email: str) -> str:
    """
    Validate email format.

    Args:
        email: Email to validate

    Returns:
        Original email if valid

    Raises:
        ValueError: If email is invalid
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        raise ValueError("Invalid email format")
    return email
```

### String Length Validation

Validate string length:

```python
def validate_string_length(value: str, min_length: int, max_length: int, field_name: str) -> str:
    """
    Validate string length.

    Args:
        value: String to validate
        min_length: Minimum length
        max_length: Maximum length
        field_name: Field name for error message

    Returns:
        Original value if valid

    Raises:
        ValueError: If string length is invalid
    """
    if value is None:
        raise ValueError(f"{field_name} cannot be None")

    if len(value) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters")

    if len(value) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")

    return value
```

### List Validation

Validate list contents:

```python
def validate_list_not_empty(value: List[Any], field_name: str) -> List[Any]:
    """
    Validate that a list is not empty.

    Args:
        value: List to validate
        field_name: Field name for error message

    Returns:
        Original list if valid

    Raises:
        ValueError: If list is empty
    """
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value
```

### JSON Validation

Validate JSON format:

```python
def validate_json(value: str, field_name: str = "metadata") -> Dict[str, Any]:
    """
    Validate JSON format and convert to dictionary.

    Args:
        value: JSON string to validate
        field_name: Field name for error message

    Returns:
        Parsed JSON as dictionary

    Raises:
        ValueError: If JSON is invalid
    """
    if not value:
        return {}

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        raise ValueError(f"{field_name} must be valid JSON")
```

## SQLite-Specific Considerations

### JSON Handling in SQLite

SQLite doesn't have a native JSON type, so we store JSON as TEXT and handle serialization/deserialization:

```python
def serialize_json(data: Dict[str, Any]) -> str:
    """
    Serialize dictionary to JSON string.

    Args:
        data: Dictionary to serialize

    Returns:
        JSON string
    """
    if data is None:
        return "{}"
    return json.dumps(data)

def deserialize_json(data: str) -> Dict[str, Any]:
    """
    Deserialize JSON string to dictionary.

    Args:
        data: JSON string to deserialize

    Returns:
        Dictionary
    """
    if not data:
        return {}

    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {}
```

### SQLite Constraints

SQLite has some limitations with constraints:

1. **Case Sensitivity**: String comparisons are case-sensitive by default
2. **Limited Functions**: Only a subset of SQL functions are available
3. **Foreign Key Support**: Must be explicitly enabled
4. **Check Constraints**: Limited expression support

Enable foreign key support for SQLite:

```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

## Best Practices and Pitfalls

### Best Practices

1. **Layer-Appropriate Validation**: Apply validation at the most appropriate layer

2. **Consistent Error Messages**: Use consistent, clear error messages

3. **Fail Fast**: Validate input at the earliest possible point

4. **Defensive Programming**: Don't trust input, even from internal sources

5. **Comprehensive Testing**: Test validation thoroughly, including edge cases

6. **Use Built-in Validators**: Leverage Pydantic's built-in validators where possible

7. **Transaction Safety**: Use transactions for operations that require validation across multiple entities

8. **Type Hints**: Use proper type hints to enable static type checking

9. **Validate at Boundaries**: Always validate data coming from external systems

10. **Normalize Input**: Normalize input before validation (e.g., trimming whitespace)

### Common Pitfalls

1. **Inconsistent Validation**: Different validation rules for the same data in different parts of the system

2. **Missing Validation**: Forgetting to validate some inputs

3. **Over-Validation**: Validating the same thing multiple times unnecessarily

4. **Vague Error Messages**: Error messages that don't help the user fix the problem

5. **Leaking Implementation Details**: Error messages that reveal internal implementation details

6. **Race Conditions**: Not using transactions for cross-entity validation

7. **Assuming Validation**: Assuming that data has been validated elsewhere

8. **Too Restrictive**: Validation rules that are unnecessarily restrictive

9. **Handling Optional Fields**: Confusion between `None`, empty string, and missing fields

10. **JSON Validation**: Not handling JSON serialization/deserialization errors

## Implementation Examples

### Complete API Request Validation

```python
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional
import uuid
import re

class WorkspaceCreate(BaseModel):
    """Request model for creating a workspace."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Workspace name"
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Workspace description"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for the workspace"
    )

    @validator('name')
    def name_must_not_contain_special_chars(cls, v):
        """Validate that name doesn't contain special characters."""
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise ValueError("Name must contain only alphanumeric characters, spaces, hyphens, and underscores")
        return v.strip()

    @validator('description')
    def description_must_not_be_empty(cls, v):
        """Validate that description is not empty."""
        if not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()

class ConversationCreate(BaseModel):
    """Request model for creating a conversation."""
    workspace_id: str = Field(
        ...,
        description="ID of the parent workspace"
    )
    topic: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Conversation topic"
    )
    participant_ids: List[str] = Field(
        default_factory=list,
        description="List of user IDs participating in the conversation"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for the conversation"
    )

    @validator('workspace_id')
    def validate_workspace_id(cls, v):
        """Validate workspace_id is a valid UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('workspace_id must be a valid UUID')

    @validator('topic')
    def validate_topic(cls, v):
        """Validate topic format."""
        if not v.strip():
            raise ValueError("Topic cannot be empty")
        return v.strip()

    @validator('participant_ids')
    def validate_participant_ids(cls, v):
        """Validate participant_ids contains valid UUIDs and is not empty."""
        if not v:
            raise ValueError('participant_ids must not be empty')

        for user_id in v:
            try:
                uuid.UUID(user_id)
            except ValueError:
                raise ValueError(f'Invalid user ID format: {user_id}')

        # Remove duplicates while preserving order
        seen = set()
        return [x for x in v if not (x in seen or seen.add(x))]
```

### Service with Validation

```python
from app.models.domain import Workspace, Conversation
from app.database.unit_of_work import UnitOfWork
from app.database.exceptions import EntityNotFoundError, AccessDeniedError, DuplicateEntityError
from typing import List, Dict, Any, Optional
import uuid

class WorkspaceService:
    """Service for workspace operations."""

    async def create_workspace(
        self,
        name: str,
        description: str,
        owner_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Workspace:
        """
        Create a new workspace.

        Args:
            name: Workspace name
            description: Workspace description
            owner_id: Owner user ID
            metadata: Optional metadata

        Returns:
            Created workspace

        Raises:
            EntityNotFoundError: If owner does not exist
            DuplicateEntityError: If workspace with same name already exists
            ValueError: If validation fails
        """
        # Validate inputs
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")

        if not description or not description.strip():
            raise ValueError("Description cannot be empty")

        if len(name) > 100:
            raise ValueError("Name cannot exceed 100 characters")

        if len(description) > 500:
            raise ValueError("Description cannot exceed 500 characters")

        # Create workspace entity
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name=name.strip(),
            description=description.strip(),
            owner_id=owner_id,
            metadata=metadata or {}
        )

        # Save workspace
        async with UnitOfWork.for_transaction() as uow:
            try:
                # Validate owner exists
                user_repo = uow.repositories.get_user_repository()
                user = await user_repo.get_by_id(owner_id)

                if not user:
                    raise EntityNotFoundError("User", owner_id)

                # Check for duplicate name
                workspace_repo = uow.repositories.get_workspace_repository()
                existing_workspaces = await workspace_repo.list_by_owner(owner_id)

                for existing in existing_workspaces:
                    if existing.name.lower() == workspace.name.lower():
                        raise DuplicateEntityError("Workspace", "name", workspace.name)

                # Save workspace
                created_workspace = await workspace_repo.create(workspace)

                # Commit transaction
                await uow.commit()

                return created_workspace
            except (EntityNotFoundError, DuplicateEntityError):
                # Re-raise these exceptions
                raise
            except Exception as e:
                # Wrap other exceptions
                raise ValueError(f"Failed to create workspace: {str(e)}")
```

### Repository with Validation

```python
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database.models import Workspace as DbWorkspace
from app.models.domain import Workspace
from app.database.repositories.generic import GenericRepository
from app.database.exceptions import EntityNotFoundError, DuplicateEntityError, RepositoryError

class WorkspaceRepositoryImpl(GenericRepository[Workspace, DbWorkspace]):
    """Implementation of workspace repository."""

    def __init__(self, session: AsyncSession):
        """Initialize workspace repository."""
        super().__init__(session, Workspace, DbWorkspace)

    async def create(self, workspace: Workspace) -> Workspace:
        """
        Create a new workspace.

        Args:
            workspace: Workspace to create

        Returns:
            Created workspace

        Raises:
            EntityNotFoundError: If owner does not exist
            DuplicateEntityError: If workspace with same name already exists
            RepositoryError: For other errors
        """
        try:
            # Convert to database model
            db_workspace = self._to_db(workspace)

            # Add to session
            self.session.add(db_workspace)
            await self.session.flush()

            # Convert back to domain model
            return self._to_domain(db_workspace)
        except IntegrityError as e:
            error_message = str(e).lower()

            if "foreign key constraint" in error_message and "owner_id" in error_message:
                raise EntityNotFoundError("User", workspace.owner_id)
            elif "unique constraint" in error_message and "name" in error_message:
                raise DuplicateEntityError("Workspace", "name", workspace.name)
            else:
                raise RepositoryError(f"Failed to create workspace: {str(e)}", e)
        except Exception as e:
            raise RepositoryError(f"Failed to create workspace: {str(e)}", e)

    async def get_by_id(self, entity_id: str, owner_id: Optional[str] = None) -> Optional[Workspace]:
        """
        Get workspace by ID.

        Args:
            entity_id: Workspace ID
            owner_id: Optional owner ID for access control

        Returns:
            Workspace if found and accessible, None otherwise
        """
        try:
            # Build query
            query = select(DbWorkspace).where(DbWorkspace.id == entity_id)

            # Apply owner filter if provided (for access control)
            if owner_id:
                query = query.where(DbWorkspace.owner_id == owner_id)

            # Execute query
            result = await self.session.execute(query)
            db_workspace = result.scalars().first()

            # Convert to domain model if found
            return self._to_domain(db_workspace) if db_workspace else None
        except Exception as e:
            raise RepositoryError(f"Failed to get workspace: {str(e)}", e)
```

### FastAPI Endpoint with Validation

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.config import get_db
from app.models.api.request import WorkspaceCreate
from app.models.api.response import WorkspaceResponse
from app.services.workspace import WorkspaceService
from app.utils.auth import get_current_user
from app.database.exceptions import EntityNotFoundError, DuplicateEntityError

router = APIRouter(prefix="/config", tags=["config"])

@router.post("/workspace", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new workspace.

    Args:
        request: Workspace creation request
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created workspace

    Raises:
        HTTPException: If validation fails or other error occurs
    """
    try:
        # Create workspace service
        service = WorkspaceService()

        # Create workspace
        workspace = await service.create_workspace(
            name=request.name,
            description=request.description,
            owner_id=current_user["user_id"],
            metadata=request.metadata
        )

        # Return response
        return WorkspaceResponse(
            status="workspace created",
            workspace=workspace
        )
    except EntityNotFoundError as e:
        # Entity not found (e.g., owner)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "not_found",
                    "message": str(e)
                }
            }
        )
    except DuplicateEntityError as e:
        # Duplicate entity (e.g., workspace name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "conflict",
                    "message": str(e)
                }
            }
        )
    except ValueError as e:
        # Validation error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "validation_error",
                    "message": str(e)
                }
            }
        )
    except Exception as e:
        # Other errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred"
                }
            }
        )
```

This validation guide provides a comprehensive framework for implementing and testing validation at all levels of the Cortex Core system in Phase 2. By following these guidelines, you can ensure data integrity, provide clear feedback to clients, and maintain a robust system that handles invalid input gracefully.
