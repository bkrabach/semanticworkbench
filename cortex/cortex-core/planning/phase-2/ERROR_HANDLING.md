# Error Handling Framework for Cortex Core

## Overview

This document provides a comprehensive guide to error handling in the Cortex Core system for Phase 2. It outlines a consistent approach to identifying, processing, and responding to errors across all layers of the application. By following these guidelines, you'll create a robust system that fails gracefully, provides helpful feedback to clients, and maintains proper logging for debugging.

## Table of Contents

1. [Error Handling Philosophy](#error-handling-philosophy)
2. [Error Response Standard](#error-response-standard)
3. [Error Types and Classification](#error-types-and-classification)
4. [Exception Handling Architecture](#exception-handling-architecture)
5. [API Error Handling](#api-error-handling)
6. [Service Layer Error Handling](#service-layer-error-handling)
7. [Repository Layer Error Handling](#repository-layer-error-handling)
8. [Database Error Handling](#database-error-handling)
9. [Error Logging](#error-logging)
10. [Testing Error Scenarios](#testing-error-scenarios)
11. [Error Handling with SQLite](#error-handling-with-sqlite)
12. [Common Error Patterns](#common-error-patterns)
13. [Security Considerations](#security-considerations)
14. [Implementation Examples](#implementation-examples)

## Error Handling Philosophy

The Cortex Core error handling approach is guided by several key principles:

### 1. Fail Fast, Fail Clearly

- Detect errors as early as possible in the request lifecycle
- Provide clear, actionable error messages to clients
- Include enough detail to fix the issue without exposing sensitive information

### 2. Consistent Error Structure

- Use a single, consistent format for all API error responses
- Use standardized error codes across the system
- Maintain consistency in error logging format

### 3. Appropriate Error Handling by Layer

- Each layer has distinct error handling responsibilities
- Higher layers translate lower-level errors to appropriate responses
- Avoid leaking implementation details through errors

### 4. Error as Documentation

- Error responses should serve as implicit API documentation
- Error messages should teach users how to use the API correctly
- Include links to documentation where appropriate

### 5. Balance between Information and Security

- Provide helpful error messages while avoiding information leakage
- More detailed errors in development, sanitized errors in production
- Never expose sensitive data, stack traces, or implementation details to clients

## Error Response Standard

All API error responses follow a consistent JSON format:

```json
{
  "error": {
    "code": "specific_error_code",
    "message": "Human-readable error message",
    "details": {
      "field_name": "Field-specific error information",
      "additional_info": "More context when helpful"
    }
  }
}
```

### Core Fields

- `error.code`: String identifier for the error type (e.g., `validation_error`, `not_found`)
- `error.message`: Human-readable description of what went wrong
- `error.details`: Optional object with additional error context; can include field-specific errors

### HTTP Status Codes

Each error response must use an appropriate HTTP status code:

| HTTP Status               | Usage                                                           |
| ------------------------- | --------------------------------------------------------------- |
| 400 Bad Request           | Invalid input, malformed request syntax                         |
| 401 Unauthorized          | Missing or invalid authentication                               |
| 403 Forbidden             | Authentication succeeded, but access denied                     |
| 404 Not Found             | Requested resource not found                                    |
| 409 Conflict              | Request conflicts with current state (e.g., duplicate resource) |
| 422 Unprocessable Entity  | Validation errors (field-level)                                 |
| 429 Too Many Requests     | Rate limit exceeded                                             |
| 500 Internal Server Error | Unexpected server error                                         |
| 503 Service Unavailable   | Service temporarily unavailable (maintenance, overload)         |

## Error Types and Classification

Categorize errors into several types to establish appropriate handling strategies:

### 1. Client Errors (4xx)

Errors caused by client actions that can be corrected by the client.

#### Validation Errors

- **Code**: `validation_error`
- **HTTP Status**: 400 Bad Request or 422 Unprocessable Entity
- **Description**: Request data failed validation
- **Response Example**:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid input data",
    "details": {
      "name": "must be between 1 and 100 characters",
      "description": "required field"
    }
  }
}
```

#### Authentication Errors

- **Code**: `unauthorized`
- **HTTP Status**: 401 Unauthorized
- **Description**: Missing or invalid authentication credentials
- **Response Example**:

```json
{
  "error": {
    "code": "unauthorized",
    "message": "Authentication required"
  }
}
```

#### Authorization Errors

- **Code**: `forbidden`
- **HTTP Status**: 403 Forbidden
- **Description**: Insufficient permissions to access resource
- **Response Example**:

```json
{
  "error": {
    "code": "forbidden",
    "message": "You do not have access to this workspace"
  }
}
```

#### Resource Not Found Errors

- **Code**: `not_found`
- **HTTP Status**: 404 Not Found
- **Description**: Requested resource does not exist
- **Response Example**:

```json
{
  "error": {
    "code": "not_found",
    "message": "Workspace with ID '550e8400-e29b-41d4-a716-446655440000' not found"
  }
}
```

#### Conflict Errors

- **Code**: `conflict`
- **HTTP Status**: 409 Conflict
- **Description**: Request cannot be completed due to conflict with current state
- **Response Example**:

```json
{
  "error": {
    "code": "conflict",
    "message": "A workspace with name 'Project X' already exists"
  }
}
```

#### Rate Limit Errors

- **Code**: `rate_limit_exceeded`
- **HTTP Status**: 429 Too Many Requests
- **Description**: Client has sent too many requests in a given time period
- **Response Example**:

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Too many requests, please try again later",
    "details": {
      "retry_after": 30
    }
  }
}
```

### 2. Server Errors (5xx)

Errors caused by server issues that require server-side resolution.

#### Internal Errors

- **Code**: `internal_error`
- **HTTP Status**: 500 Internal Server Error
- **Description**: Unexpected server error
- **Response Example**:

```json
{
  "error": {
    "code": "internal_error",
    "message": "An unexpected error occurred"
  }
}
```

#### Service Unavailable Errors

- **Code**: `service_unavailable`
- **HTTP Status**: 503 Service Unavailable
- **Description**: Service temporarily unavailable
- **Response Example**:

```json
{
  "error": {
    "code": "service_unavailable",
    "message": "Service temporarily unavailable, please try again later"
  }
}
```

### 3. Database Errors

Errors related to database operations, translated to appropriate API errors.

#### Common Database Errors

- **Foreign Key Violation**: Maps to 404 Not Found (reference not found) or 400 Bad Request (invalid reference)
- **Unique Constraint Violation**: Maps to 409 Conflict (duplicate resource)
- **Check Constraint Violation**: Maps to 400 Bad Request (invalid data)
- **Database Connection Error**: Maps to 503 Service Unavailable

## Exception Handling Architecture

The Cortex Core exception handling architecture follows a multi-layered approach:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  API Layer      │────▶│  Service Layer  │────▶│  Repository Layer│
│  Exceptions     │◀────│  Exceptions     │◀────│  Exceptions     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│HTTPException with│     │ServiceError and │     │RepositoryError │
│appropriate status│     │subclasses for   │     │and subclasses  │
│and error response│     │different errors │     │for DB errors   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Custom Exception Hierarchy

Create a hierarchy of custom exceptions to represent different error types:

```python
class CoreError(Exception):
    """Base exception for all Cortex Core errors."""

    def __init__(self, message: str, original_exception: Exception = None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(message)

# Repository Layer Exceptions
class RepositoryError(CoreError):
    """Base exception for repository errors."""
    pass

class EntityNotFoundError(RepositoryError):
    """Entity not found error."""

    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        message = f"{entity_type} not found: {entity_id}"
        super().__init__(message)

class DuplicateEntityError(RepositoryError):
    """Duplicate entity error."""

    def __init__(self, entity_type: str, field: str, value: str):
        self.entity_type = entity_type
        self.field = field
        self.value = value
        message = f"{entity_type} with {field}='{value}' already exists"
        super().__init__(message)

class DatabaseError(RepositoryError):
    """Database error."""
    pass

# Service Layer Exceptions
class ServiceError(CoreError):
    """Base exception for service errors."""
    pass

class ValidationError(ServiceError):
    """Validation error."""

    def __init__(self, errors: Dict[str, str]):
        self.errors = errors
        message = "Validation error"
        super().__init__(message)

class AuthorizationError(ServiceError):
    """Authorization error."""

    def __init__(self, resource_type: str, resource_id: str, user_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.user_id = user_id
        message = f"User {user_id} does not have access to {resource_type} {resource_id}"
        super().__init__(message)
```

## API Error Handling

### Global Exception Handler

Implement a global exception handler to catch and map exceptions to appropriate HTTP responses:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.exceptions import EntityNotFoundError, DuplicateEntityError, AuthorizationError, ValidationError as AppValidationError

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors."""
    errors = {}
    for error in exc.errors():
        # Extract field name from error location
        # The location is a tuple like ("body", "name")
        field = error["loc"][-1] if len(error["loc"]) > 1 else "request"
        message = error["msg"]
        errors[field] = message

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

@app.exception_handler(EntityNotFoundError)
async def not_found_exception_handler(request: Request, exc: EntityNotFoundError):
    """Handle entity not found errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "not_found",
                "message": str(exc),
                "details": {
                    "entity_type": exc.entity_type,
                    "entity_id": exc.entity_id
                }
            }
        }
    )

@app.exception_handler(DuplicateEntityError)
async def duplicate_entity_exception_handler(request: Request, exc: DuplicateEntityError):
    """Handle duplicate entity errors."""
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "conflict",
                "message": str(exc),
                "details": {
                    "entity_type": exc.entity_type,
                    "field": exc.field,
                    "value": exc.value
                }
            }
        }
    )

@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors."""
    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "code": "forbidden",
                "message": str(exc)
            }
        }
    )

@app.exception_handler(AppValidationError)
async def app_validation_exception_handler(request: Request, exc: AppValidationError):
    """Handle application validation errors."""
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "validation_error",
                "message": str(exc),
                "details": exc.errors
            }
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    # Log the exception with traceback
    import logging
    import traceback
    logging.error(f"Unhandled exception: {exc}")
    logging.error(traceback.format_exc())

    # In production, return a generic error message
    # In development, you might want to include more details
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred"
            }
        }
    )
```

### Endpoint-Specific Error Handling

Individual endpoints may need specific error handling:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.config import get_db
from app.models.api.request import WorkspaceCreate
from app.models.api.response import WorkspaceResponse
from app.services.workspace import WorkspaceService
from app.utils.auth import get_current_user
from app.core.exceptions import EntityNotFoundError, DuplicateEntityError, AuthorizationError

router = APIRouter(prefix="/config", tags=["config"])

@router.post("/workspace", response_model=WorkspaceResponse)
async def create_workspace(
    request: WorkspaceCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new workspace."""
    try:
        # Create workspace
        service = WorkspaceService()
        workspace = await service.create_workspace(
            name=request.name,
            description=request.description,
            owner_id=current_user["user_id"],
            metadata=request.metadata or {}
        )

        # Commit transaction
        await db.commit()

        # Return response
        return WorkspaceResponse(
            status="workspace created",
            workspace=workspace
        )
    except Exception as e:
        # Rollback transaction on error
        await db.rollback()

        # Re-raise the exception to be handled by global handlers
        raise
```

## Service Layer Error Handling

The service layer handles business logic and translates between the API and repository layers. It should:

1. Catch repository exceptions and translate them to service exceptions
2. Validate business rules and raise appropriate service exceptions
3. Never leak repository or database implementation details

```python
from typing import Dict, Any, Optional
import uuid

from app.models.domain import Workspace
from app.database.unit_of_work import UnitOfWork
from app.core.exceptions import EntityNotFoundError, DuplicateEntityError, AuthorizationError, ValidationError

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
            ValidationError: If input validation fails
            EntityNotFoundError: If owner does not exist
            DuplicateEntityError: If workspace with same name already exists
        """
        # Validate inputs
        errors = {}
        if not name or len(name.strip()) == 0:
            errors["name"] = "cannot be empty"
        elif len(name) > 100:
            errors["name"] = "cannot exceed 100 characters"

        if not description or len(description.strip()) == 0:
            errors["description"] = "cannot be empty"
        elif len(description) > 500:
            errors["description"] = "cannot exceed 500 characters"

        if errors:
            raise ValidationError(errors)

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
                # Check if owner exists
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
                # These exceptions are already in the format we want, so re-raise
                raise
            except Exception as e:
                # Log unexpected exceptions
                import logging
                logging.error(f"Unexpected error creating workspace: {str(e)}")

                # Re-raise as a generic error
                raise Exception(f"Failed to create workspace: {str(e)}")
```

## Repository Layer Error Handling

The repository layer interacts with the database and should:

1. Translate database errors to repository exceptions
2. Ensure transactions are properly managed
3. Provide detailed error information for debugging

```python
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database.models import Workspace as DbWorkspace
from app.models.domain import Workspace
from app.core.exceptions import EntityNotFoundError, DuplicateEntityError, DatabaseError
import json

class WorkspaceRepository:
    """Repository for workspace operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

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
            DatabaseError: For other database errors
        """
        try:
            # Convert domain model to database model
            db_workspace = DbWorkspace(
                id=workspace.id,
                name=workspace.name,
                description=workspace.description,
                owner_id=workspace.owner_id,
                metadata_json=json.dumps(workspace.metadata) if workspace.metadata else "{}"
            )

            # Add to session
            self.session.add(db_workspace)

            # Flush to generate errors without committing
            await self.session.flush()

            # Convert back to domain model
            return self._to_domain(db_workspace)
        except IntegrityError as e:
            # Handle specific integrity errors
            error_message = str(e).lower()

            if "foreign key constraint" in error_message and "owner_id" in error_message:
                # Owner doesn't exist
                raise EntityNotFoundError("User", workspace.owner_id)
            elif "unique constraint" in error_message and "name" in error_message:
                # Duplicate name
                raise DuplicateEntityError("Workspace", "name", workspace.name)
            else:
                # Other integrity error
                raise DatabaseError(f"Database integrity error: {str(e)}", e)
        except DBAPIError as e:
            # General database error
            raise DatabaseError(f"Database error: {str(e)}", e)
        except Exception as e:
            # Unexpected error
            raise DatabaseError(f"Unexpected database error: {str(e)}", e)

    async def get_by_id(self, workspace_id: str, owner_id: Optional[str] = None) -> Optional[Workspace]:
        """
        Get workspace by ID.

        Args:
            workspace_id: Workspace ID
            owner_id: Optional owner ID for access control

        Returns:
            Workspace if found and accessible, None otherwise

        Raises:
            DatabaseError: For database errors
        """
        try:
            # Build query
            query = select(DbWorkspace).where(DbWorkspace.id == workspace_id)

            # Add owner filter if provided (for access control)
            if owner_id:
                query = query.where(DbWorkspace.owner_id == owner_id)

            # Execute query
            result = await self.session.execute(query)
            db_workspace = result.scalars().first()

            # Return domain model or None
            return self._to_domain(db_workspace) if db_workspace else None
        except DBAPIError as e:
            # Database error
            raise DatabaseError(f"Database error: {str(e)}", e)
        except Exception as e:
            # Unexpected error
            raise DatabaseError(f"Unexpected error getting workspace: {str(e)}", e)

    def _to_domain(self, db_workspace: DbWorkspace) -> Workspace:
        """Convert database model to domain model."""
        if not db_workspace:
            return None

        # Parse metadata from JSON
        metadata = {}
        if db_workspace.metadata_json:
            try:
                metadata = json.loads(db_workspace.metadata_json)
            except json.JSONDecodeError:
                # Handle invalid JSON
                import logging
                logging.warning(f"Invalid JSON metadata for workspace {db_workspace.id}: {db_workspace.metadata_json}")

        # Create domain model
        return Workspace(
            id=db_workspace.id,
            name=db_workspace.name,
            description=db_workspace.description,
            owner_id=db_workspace.owner_id,
            metadata=metadata
        )
```

## Database Error Handling

Database errors require special attention due to their variety and impact:

### Common SQLite Errors

1. **SQLITE_CONSTRAINT**: Constraint violation (foreign key, unique, check)
2. **SQLITE_BUSY**: Database is locked (concurrent write operations)
3. **SQLITE_NOTFOUND**: Entity not found
4. **SQLITE_CORRUPT**: Database file is corrupt
5. **SQLITE_IOERR**: I/O error (disk full, permissions)

### Handling Database Connection Errors

```python
from sqlalchemy.exc import OperationalError
import time

async def execute_with_retry(session, query, max_retries=3, retry_delay=0.5):
    """
    Execute a database query with retry for connection errors.

    Args:
        session: Database session
        query: Query to execute
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds

    Returns:
        Query result

    Raises:
        DatabaseError: If query fails after retries
    """
    retries = 0
    last_error = None

    while retries < max_retries:
        try:
            return await session.execute(query)
        except OperationalError as e:
            # Check if database is locked
            if "database is locked" in str(e).lower():
                last_error = e
                retries += 1

                if retries < max_retries:
                    # Wait before retrying
                    await asyncio.sleep(retry_delay * (2 ** (retries - 1)))
                    continue

            # Other operational error
            raise DatabaseError(f"Database operational error: {str(e)}", e)
        except Exception as e:
            # Other database error
            raise DatabaseError(f"Database error: {str(e)}", e)

    # Max retries reached
    raise DatabaseError(f"Database operation failed after {max_retries} retries: {str(last_error)}", last_error)
```

### Handling SQLite-Specific Errors

```python
def handle_sqlite_error(e: Exception) -> Exception:
    """
    Map SQLite errors to appropriate exception types.

    Args:
        e: SQLite exception

    Returns:
        Mapped exception
    """
    error_message = str(e).lower()

    if "foreign key constraint failed" in error_message:
        # Extract referenced entity from error message
        # Example: "FOREIGN KEY constraint failed - foreign key mismatch - users.user_id"
        parts = error_message.split(".")
        if len(parts) > 1:
            entity_type = parts[-2].split(" - ")[-1].strip()
            field = parts[-1].strip()
            return EntityNotFoundError(entity_type.capitalize(), field)

        return EntityNotFoundError("Referenced entity", "unknown")

    if "unique constraint failed" in error_message:
        # Extract table and column from error message
        # Example: "UNIQUE constraint failed: workspaces.name"
        parts = error_message.split(":")
        if len(parts) > 1:
            table_column = parts[1].strip().split(".")
            if len(table_column) > 1:
                entity_type = table_column[0].strip().capitalize()
                if entity_type.endswith("s"):
                    entity_type = entity_type[:-1]  # Remove plural 's'
                field = table_column[1].strip()
                return DuplicateEntityError(entity_type, field, "unknown value")

        return DuplicateEntityError("Entity", "unknown", "unknown value")

    if "check constraint failed" in error_message:
        return ValidationError({"field": "check constraint failed"})

    if "database is locked" in error_message:
        return DatabaseError("Database is locked, try again later", e)

    if "disk i/o error" in error_message:
        return DatabaseError("Database disk I/O error", e)

    if "no such table" in error_message:
        return DatabaseError("Database schema is not initialized", e)

    # Generic database error
    return DatabaseError(f"Database error: {str(e)}", e)
```

## Error Logging

Proper error logging is essential for debugging and monitoring:

### Logging Configuration

```python
import logging
import sys
from typing import Dict, Any

def configure_logging(log_level: str = "INFO", log_format: str = None):
    """
    Configure application logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format
    """
    # Set default format if not provided
    if not log_format:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set SQLAlchemy logging level
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Set uvicorn access logging level
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
```

### Request Context Logging

```python
import logging
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import time

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""

    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())

        # Set request ID in request state
        request.state.request_id = request_id

        # Log request
        logger.info(f"Request {request_id} started: {request.method} {request.url.path}")

        # Track request timing
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate request duration
            duration = time.time() - start_time

            # Log successful response
            logger.info(f"Request {request_id} completed: {response.status_code} in {duration:.3f}s")

            return response
        except Exception as e:
            # Calculate request duration
            duration = time.time() - start_time

            # Log failed request
            logger.error(f"Request {request_id} failed: {str(e)} in {duration:.3f}s")

            # Re-raise the exception
            raise

app = FastAPI()
app.add_middleware(RequestLoggingMiddleware)
```

### Error Context Logging

```python
def log_error(error: Exception, context: Dict[str, Any] = None):
    """
    Log an error with contextual information.

    Args:
        error: The exception
        context: Optional context information
    """
    logger = logging.getLogger(__name__)

    # Format error message
    error_message = f"Error: {error.__class__.__name__}: {str(error)}"

    # Add context information if provided
    if context:
        context_str = ", ".join([f"{key}={value}" for key, value in context.items()])
        error_message += f" | Context: {context_str}"

    # Log error
    logger.error(error_message, exc_info=True)

# Example usage in repository
async def get_by_id(self, entity_id: str):
    try:
        # Query database
        result = await self.session.execute(
            select(DbEntity).where(DbEntity.id == entity_id)
        )
        return result.scalars().first()
    except Exception as e:
        # Log error with context
        log_error(e, {
            "method": "get_by_id",
            "entity_id": entity_id,
            "repository": self.__class__.__name__
        })

        # Re-raise appropriate exception
        raise DatabaseError(f"Failed to get entity: {str(e)}", e)
```

### Sensitive Data in Logs

Be careful not to log sensitive information:

```python
def sanitize_for_logging(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive fields from data before logging.

    Args:
        data: Data to sanitize

    Returns:
        Sanitized data
    """
    # Make a copy to avoid modifying the original
    sanitized = data.copy()

    # List of sensitive fields to remove
    sensitive_fields = [
        "password", "token", "secret", "key", "auth", "credentials",
        "jwt", "session", "cookie"
    ]

    # Remove sensitive fields
    for field in sensitive_fields:
        if field in sanitized:
            sanitized[field] = "[REDACTED]"

    return sanitized

# Example usage
try:
    # Process login
    user = await authenticate_user(request.username, request.password)
    # ...
except Exception as e:
    # Log without sensitive data
    sanitized_data = sanitize_for_logging(request.dict())
    log_error(e, {"request_data": sanitized_data})
    raise
```

## Testing Error Scenarios

### Writing Tests for Error Scenarios

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.exceptions import EntityNotFoundError, DuplicateEntityError
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_workspace_not_found():
    """Test workspace not found error."""
    # Mock get_workspace to raise EntityNotFoundError
    with patch("app.services.workspace.WorkspaceService.get_workspace") as mock_get:
        # Set up mock to raise error
        mock_get.side_effect = EntityNotFoundError("Workspace", "test-id")

        # Make request
        response = client.get(
            "/config/workspace/test-id",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        # Assert response
        assert response.status_code == 404
        assert "error" in response.json()
        assert response.json()["error"]["code"] == "not_found"
        assert "Workspace not found" in response.json()["error"]["message"]

def test_duplicate_workspace():
    """Test duplicate workspace error."""
    # Mock create_workspace to raise DuplicateEntityError
    with patch("app.services.workspace.WorkspaceService.create_workspace") as mock_create:
        # Set up mock to raise error
        mock_create.side_effect = DuplicateEntityError("Workspace", "name", "Test Workspace")

        # Make request
        response = client.post(
            "/config/workspace",
            json={"name": "Test Workspace", "description": "Test description"},
            headers={"Authorization": f"Bearer {test_token}"}
        )

        # Assert response
        assert response.status_code == 409
        assert "error" in response.json()
        assert response.json()["error"]["code"] == "conflict"
        assert "already exists" in response.json()["error"]["message"]
```

### Testing Validation Errors

```python
def test_workspace_validation():
    """Test workspace validation errors."""
    # Missing required fields
    response = client.post(
        "/config/workspace",
        json={},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 400
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "validation_error"
    assert "name" in response.json()["error"]["details"]

    # Invalid name (too long)
    response = client.post(
        "/config/workspace",
        json={"name": "a" * 101, "description": "Test description"},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 400
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "validation_error"
    assert "name" in response.json()["error"]["details"]
```

### Testing Database Errors

```python
@pytest.mark.asyncio
async def test_database_error():
    """Test database error handling."""
    # Create repository with mocked session
    session = MagicMock()
    repo = WorkspaceRepository(session)

    # Mock session.execute to raise OperationalError
    session.execute.side_effect = OperationalError("statement", {}, "database is locked")

    # Call repository method
    with pytest.raises(DatabaseError) as excinfo:
        await repo.get_by_id("test-id")

    # Assert exception
    assert "database is locked" in str(excinfo.value)
```

## Error Handling with SQLite

SQLite has specific error handling considerations:

### Handling SQLite Locking Errors

SQLite allows only one writer at a time, which can lead to locking errors:

```python
import asyncio
from sqlalchemy.exc import OperationalError

async def execute_with_retry(session, operation, max_retries=3, base_delay=0.1):
    """
    Execute a database operation with retries for locking errors.

    Args:
        session: Database session
        operation: Callable that performs the database operation
        max_retries: Maximum number of retries
        base_delay: Base delay between retries (exponential backoff)

    Returns:
        Operation result

    Raises:
        DatabaseError: If operation fails after retries
    """
    retries = 0

    while True:
        try:
            # Execute operation
            result = await operation()
            return result
        except OperationalError as e:
            error_str = str(e).lower()

            # Check if database is locked
            if "database is locked" in error_str:
                retries += 1

                if retries > max_retries:
                    raise DatabaseError(f"Database locked after {max_retries} retries", e)

                # Wait with exponential backoff
                delay = base_delay * (2 ** (retries - 1))
                await asyncio.sleep(delay)
                continue

            # Other operational error
            raise DatabaseError(f"Database error: {str(e)}", e)
        except Exception as e:
            # Other exception
            raise DatabaseError(f"Database operation failed: {str(e)}", e)

# Example usage
async def get_workspace(self, workspace_id: str):
    async def operation():
        result = await self.session.execute(
            select(DbWorkspace).where(DbWorkspace.id == workspace_id)
        )
        return result.scalars().first()

    return await execute_with_retry(self.session, operation)
```

### Handling Transaction Errors

Ensure transactions are properly managed, especially in error cases:

```python
class UnitOfWork:
    """Manages a database transaction."""

    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        """Start a transaction."""
        # Transaction is started automatically when session is created
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End the transaction."""
        if exc_type:
            # An exception occurred, rollback
            await self.session.rollback()
        else:
            # No exception, commit
            try:
                await self.session.commit()
            except Exception as e:
                # Failed to commit, rollback
                await self.session.rollback()

                # Re-raise appropriate exception
                raise DatabaseError(f"Failed to commit transaction: {str(e)}", e)

    async def commit(self):
        """Commit the transaction."""
        await self.session.commit()

    async def rollback(self):
        """Rollback the transaction."""
        await self.session.rollback()
```

## Common Error Patterns

Here are some common error scenarios and patterns for handling them:

### Entity Not Found

```python
async def get_workspace(workspace_id: str, user_id: str):
    """Get workspace by ID."""
    # Get workspace from repository
    workspace = await workspace_repository.get_by_id(workspace_id)

    # Check if workspace exists
    if not workspace:
        raise EntityNotFoundError("Workspace", workspace_id)

    # Check if user has access
    if workspace.owner_id != user_id:
        raise AuthorizationError("Workspace", workspace_id, user_id)

    return workspace
```

### Validation Failure

```python
async def create_conversation(workspace_id: str, topic: str, participant_ids: List[str], user_id: str):
    """Create a new conversation."""
    # Validate input
    errors = {}

    if not topic or not topic.strip():
        errors["topic"] = "cannot be empty"
    elif len(topic) > 200:
        errors["topic"] = "cannot exceed 200 characters"

    if not participant_ids:
        errors["participant_ids"] = "must include at least one participant"

    if errors:
        raise ValidationError(errors)

    # Get workspace
    workspace = await workspace_repository.get_by_id(workspace_id)

    if not workspace:
        raise EntityNotFoundError("Workspace", workspace_id)

    if workspace.owner_id != user_id:
        raise AuthorizationError("Workspace", workspace_id, user_id)

    # Create conversation
    conversation = Conversation(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        topic=topic.strip(),
        participant_ids=participant_ids,
        metadata={}
    )

    # Save conversation
    return await conversation_repository.create(conversation)
```

### Database Transaction Failure

```python
async def update_conversation(conversation_id: str, topic: str, participant_ids: List[str], user_id: str):
    """Update a conversation."""
    async with UnitOfWork.for_transaction() as uow:
        try:
            # Get conversation
            conversation_repo = uow.repositories.get_conversation_repository()
            conversation = await conversation_repo.get_by_id(conversation_id)

            if not conversation:
                raise EntityNotFoundError("Conversation", conversation_id)

            # Check access
            workspace_repo = uow.repositories.get_workspace_repository()
            workspace = await workspace_repo.get_by_id(conversation.workspace_id)

            if workspace.owner_id != user_id and user_id not in conversation.participant_ids:
                raise AuthorizationError("Conversation", conversation_id, user_id)

            # Update conversation
            conversation.topic = topic
            conversation.participant_ids = participant_ids

            # Save changes
            updated_conversation = await conversation_repo.update(conversation)

            # Commit transaction
            await uow.commit()

            return updated_conversation
        except IntegrityError as e:
            # Handle integrity errors
            error_str = str(e).lower()

            if "foreign key constraint" in error_str:
                raise EntityNotFoundError("Referenced entity", "unknown")
            elif "unique constraint" in error_str:
                raise DuplicateEntityError("Conversation", "field", "value")
            else:
                raise DatabaseError(f"Database integrity error: {str(e)}", e)
```

## Security Considerations

### Avoiding Information Leakage

Be careful not to leak sensitive information in error responses:

- Don't include stack traces in API responses
- Don't expose internal implementation details
- Don't expose database queries or schema
- Don't expose file paths or system information

### Sanitizing Error Messages

```python
def sanitize_error_message(message: str) -> str:
    """
    Sanitize error message for API responses.

    Args:
        message: Original error message

    Returns:
        Sanitized message
    """
    # List of patterns to sanitize
    sensitive_patterns = [
        (r"(SELECT|INSERT|UPDATE|DELETE).*?FROM.*", "SQL query error"),
        (r"at [/\\].*?\.py", "Internal server error"),
        (r"line \d+", "Internal server error"),
        (r"psycopg2.*", "Database error"),
        (r"sqlalchemy.*", "Database error"),
        (r"/home/.*?/", ""),
        (r"\w+@\w+\.\w+", "[email]")
    ]

    # Apply sanitization
    sanitized = message
    for pattern, replacement in sensitive_patterns:
        import re
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized

# Example usage
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    # Log the full error
    import logging
    import traceback
    logging.error(f"Unhandled exception: {exc}")
    logging.error(traceback.format_exc())

    # Return sanitized error
    sanitized_message = sanitize_error_message(str(exc))

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred" if sanitized_message else "Internal server error"
            }
        }
    )
```

### Environment-Specific Error Handling

```python
# Configuration
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Generic error handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    # Log the error
    import logging
    import traceback
    logging.error(f"Unhandled exception: {exc}")
    logging.error(traceback.format_exc())

    if DEBUG:
        # Detailed error in development
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": str(exc),
                    "details": {
                        "exception": exc.__class__.__name__,
                        "traceback": traceback.format_exc().split("\n")
                    }
                }
            }
        )
    else:
        # Generic error in production
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred"
                }
            }
        )
```

## Implementation Examples

### Complete FastAPI Error Handling

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
import traceback
import os

from app.core.exceptions import (
    EntityNotFoundError, DuplicateEntityError,
    AuthorizationError, ValidationError as AppValidationError,
    DatabaseError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Create FastAPI app
app = FastAPI()

# Get environment variables
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# FastAPI validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors."""
    errors = {}
    for error in exc.errors():
        # Extract field name from error location
        field = error["loc"][-1] if len(error["loc"]) > 1 else "request"
        message = error["msg"]
        errors[field] = message

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

# Pydantic validation error handler
@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    errors = {}
    for error in exc.errors():
        field = ".".join(error["loc"])
        message = error["msg"]
        errors[field] = message

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "validation_error",
                "message": "Invalid data",
                "details": errors
            }
        }
    )

# Not found error handler
@app.exception_handler(EntityNotFoundError)
async def not_found_exception_handler(request: Request, exc: EntityNotFoundError):
    """Handle entity not found errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "not_found",
                "message": str(exc),
                "details": {
                    "entity_type": exc.entity_type,
                    "entity_id": exc.entity_id
                }
            }
        }
    )

# Duplicate entity error handler
@app.exception_handler(DuplicateEntityError)
async def duplicate_entity_exception_handler(request: Request, exc: DuplicateEntityError):
    """Handle duplicate entity errors."""
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "conflict",
                "message": str(exc),
                "details": {
                    "entity_type": exc.entity_type,
                    "field": exc.field,
                    "value": exc.value
                }
            }
        }
    )

# Authorization error handler
@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors."""
    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "code": "forbidden",
                "message": str(exc),
                "details": {
                    "resource_type": exc.resource_type,
                    "resource_id": exc.resource_id,
                    "user_id": exc.user_id
                }
            }
        }
    )

# Application validation error handler
@app.exception_handler(AppValidationError)
async def app_validation_exception_handler(request: Request, exc: AppValidationError):
    """Handle application validation errors."""
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "validation_error",
                "message": "Validation error",
                "details": exc.errors
            }
        }
    )

# Database error handler
@app.exception_handler(DatabaseError)
async def database_exception_handler(request: Request, exc: DatabaseError):
    """Handle database errors."""
    # Log the detailed error
    logging.error(f"Database error: {str(exc)}")
    if exc.original_exception:
        logging.error(f"Original exception: {str(exc.original_exception)}")

    # Return sanitized response
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "database_error",
                "message": "A database error occurred"
            }
        }
    )

# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "http_error",
                "message": exc.detail
            }
        }
    )

# Generic exception handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    # Log the error
    logging.error(f"Unhandled exception: {exc}")
    logging.error(traceback.format_exc())

    if DEBUG:
        # Detailed error in development
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": str(exc),
                    "details": {
                        "exception": exc.__class__.__name__,
                        "traceback": traceback.format_exc().split("\n")
                    }
                }
            }
        )
    else:
        # Generic error in production
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred"
                }
            }
        )

# Request logging middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log request and response."""
    # Generate request ID
    import uuid
    request_id = str(uuid.uuid4())

    # Add request ID to request state
    request.state.request_id = request_id

    # Log request
    logging.info(f"Request {request_id} started: {request.method} {request.url.path}")

    # Process request
    import time
    start_time = time.time()

    try:
        response = await call_next(request)

        # Log successful response
        duration = time.time() - start_time
        logging.info(f"Request {request_id} completed: {response.status_code} in {duration:.3f}s")

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
    except Exception as e:
        # Log failed request
        duration = time.time() - start_time
        logging.error(f"Request {request_id} failed: {str(e)} in {duration:.3f}s")

        # Generate error response
        error_response = await generic_exception_handler(request, e)

        # Add request ID to response headers
        error_response.headers["X-Request-ID"] = request_id

        return error_response
```

### Repository with Complete Error Handling

```python
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import json
import logging
import asyncio

from app.database.models import Workspace as DbWorkspace
from app.models.domain import Workspace
from app.core.exceptions import (
    EntityNotFoundError, DuplicateEntityError,
    DatabaseError, ValidationError
)

logger = logging.getLogger(__name__)

class WorkspaceRepository:
    """Repository for workspace operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

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
            ValidationError: If workspace data is invalid
            DatabaseError: For other database errors
        """
        try:
            # Validate workspace
            self._validate_workspace(workspace)

            # Convert domain model to database model
            db_workspace = self._to_db(workspace)

            # Add to session
            self.session.add(db_workspace)

            # Flush to generate errors without committing
            try:
                await self.session.flush()
            except IntegrityError as e:
                # Handle integrity errors
                await self.session.rollback()
                raise self._handle_integrity_error(e, workspace)
            except OperationalError as e:
                # Handle operational errors
                await self.session.rollback()
                raise self._handle_operational_error(e)
            except Exception as e:
                # Handle other errors
                await self.session.rollback()
                raise DatabaseError(f"Failed to create workspace: {str(e)}", e)

            # Convert back to domain model
            return self._to_domain(db_workspace)
        except (EntityNotFoundError, DuplicateEntityError, ValidationError):
            # Re-raise these exceptions
            raise
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error creating workspace: {str(e)}")

            # Re-raise as database error
            raise DatabaseError(f"Failed to create workspace: {str(e)}", e)

    async def get_by_id(self, workspace_id: str, owner_id: Optional[str] = None) -> Optional[Workspace]:
        """
        Get workspace by ID.

        Args:
            workspace_id: Workspace ID
            owner_id: Optional owner ID for access control

        Returns:
            Workspace if found and accessible, None otherwise

        Raises:
            DatabaseError: For database errors
        """
        try:
            # Build query
            query = select(DbWorkspace).where(DbWorkspace.id == workspace_id)

            # Add owner filter if provided (for access control)
            if owner_id:
                query = query.where(DbWorkspace.owner_id == owner_id)

            # Execute query with retry for locking errors
            db_workspace = await self._execute_with_retry(
                lambda: self.session.execute(query).scalars().first()
            )

            # Return domain model or None
            return self._to_domain(db_workspace) if db_workspace else None
        except Exception as e:
            # Log error
            logger.error(f"Error getting workspace {workspace_id}: {str(e)}")

            # Re-raise as database error
            raise DatabaseError(f"Failed to get workspace: {str(e)}", e)

    async def _execute_with_retry(self, operation, max_retries=3, base_delay=0.1):
        """
        Execute a database operation with retries for locking errors.

        Args:
            operation: Callable that performs the database operation
            max_retries: Maximum number of retries
            base_delay: Base delay between retries (exponential backoff)

        Returns:
            Operation result

        Raises:
            DatabaseError: If operation fails after retries
        """
        retries = 0

        while True:
            try:
                # Execute operation
                return await operation()
            except OperationalError as e:
                error_str = str(e).lower()

                # Check if database is locked
                if "database is locked" in error_str:
                    retries += 1

                    if retries > max_retries:
                        raise DatabaseError(f"Database locked after {max_retries} retries", e)

                    # Wait with exponential backoff
                    delay = base_delay * (2 ** (retries - 1))
                    await asyncio.sleep(delay)
                    continue

                # Other operational error
                raise DatabaseError(f"Database error: {str(e)}", e)
            except Exception as e:
                # Other exception
                raise DatabaseError(f"Database operation failed: {str(e)}", e)

    def _handle_integrity_error(self, error: IntegrityError, workspace: Workspace) -> Exception:
        """
        Handle SQLite integrity errors.

        Args:
            error: The integrity error
            workspace: The workspace being created/updated

        Returns:
            Mapped exception
        """
        error_str = str(error).lower()

        # Foreign key constraint violation
        if "foreign key constraint failed" in error_str:
            if "owner_id" in error_str:
                return EntityNotFoundError("User", workspace.owner_id)
            return EntityNotFoundError("Referenced entity", "unknown")

        # Unique constraint violation
        if "unique constraint failed" in error_str:
            if "name" in error_str:
                return DuplicateEntityError("Workspace", "name", workspace.name)
            return DuplicateEntityError("Entity", "field", "value")

        # Check constraint violation
        if "check constraint failed" in error_str:
            return ValidationError({"constraint": "check constraint failed"})

        # Other integrity error
        return DatabaseError(f"Database integrity error: {str(error)}", error)

    def _handle_operational_error(self, error: OperationalError) -> Exception:
        """
        Handle SQLite operational errors.

        Args:
            error: The operational error

        Returns:
            Mapped exception
        """
        error_str = str(error).lower()

        # Database is locked
        if "database is locked" in error_str:
            return DatabaseError("Database is locked, try again later", error)

        # Disk I/O error
        if "disk i/o error" in error_str:
            return DatabaseError("Database disk I/O error", error)

        # No such table
        if "no such table" in error_str:
            return DatabaseError("Database schema is not initialized", error)

        # Other operational error
        return DatabaseError(f"Database operational error: {str(error)}", error)

    def _validate_workspace(self, workspace: Workspace) -> None:
        """
        Validate workspace data.

        Args:
            workspace: Workspace to validate

        Raises:
            ValidationError: If validation fails
        """
        errors = {}

        # Validate ID
        try:
            import uuid
            uuid.UUID(workspace.id)
        except (ValueError, AttributeError):
            errors["id"] = "must be a valid UUID"

        # Validate name
        if not workspace.name or not workspace.name.strip():
            errors["name"] = "cannot be empty"
        elif len(workspace.name) > 100:
            errors["name"] = "cannot exceed 100 characters"

        # Validate description
        if not workspace.description or not workspace.description.strip():
            errors["description"] = "cannot be empty"
        elif len(workspace.description) > 500:
            errors["description"] = "cannot exceed 500 characters"

        # Validate owner_id
        if not workspace.owner_id:
            errors["owner_id"] = "cannot be empty"

        # Raise validation error if any errors found
        if errors:
            raise ValidationError(errors)

    def _to_domain(self, db_workspace: DbWorkspace) -> Optional[Workspace]:
        """Convert database model to domain model."""
        if not db_workspace:
            return None

        # Parse metadata from JSON
        metadata = {}
        if db_workspace.metadata_json:
            try:
                metadata = json.loads(db_workspace.metadata_json)
            except json.JSONDecodeError:
                # Handle invalid JSON
                logger.warning(f"Invalid JSON metadata for workspace {db_workspace.id}: {db_workspace.metadata_json}")
                metadata = {}

        # Create domain model
        return Workspace(
            id=db_workspace.id,
            name=db_workspace.name,
            description=db_workspace.description,
            owner_id=db_workspace.owner_id,
            metadata=metadata
        )

    def _to_db(self, workspace: Workspace) -> DbWorkspace:
        """Convert domain model to database model."""
        return DbWorkspace(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            owner_id=workspace.owner_id,
            metadata_json=json.dumps(workspace.metadata) if workspace.metadata else "{}"
        )
```

This error handling framework provides a comprehensive approach to identifying, processing, and responding to errors across all layers of the Cortex Core system. By following these guidelines, you'll create a robust system that fails gracefully, provides helpful feedback to clients, and maintains proper logging for debugging.
