# Testing Strategy for Cortex Core Phase 2

## Overview

This document outlines the comprehensive testing strategy for the Cortex Core system in Phase 2. It provides a structured approach to testing all components, ensuring functionality, reliability, and performance. By following these guidelines, you'll build a robust test suite that gives confidence in the system's behavior while facilitating future changes.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Organization](#test-organization)
3. [Test Types and Coverage](#test-types-and-coverage)
4. [Testing Tools and Setup](#testing-tools-and-setup)
5. [Unit Testing](#unit-testing)
6. [Integration Testing](#integration-testing)
7. [API Testing](#api-testing)
8. [Repository Testing](#repository-testing)
9. [Service Layer Testing](#service-layer-testing)
10. [Test Database Strategy](#test-database-strategy)
11. [Error Handling Testing](#error-handling-testing)
12. [Authentication Testing](#authentication-testing)
13. [Test Data Management](#test-data-management)
14. [Mocking Strategy](#mocking-strategy)
15. [Async Testing Techniques](#async-testing-techniques)
16. [Test Isolation](#test-isolation)
17. [Test Naming and Structure](#test-naming-and-structure)
18. [Test Coverage Requirements](#test-coverage-requirements)
19. [Running Tests](#running-tests)
20. [Common Testing Patterns](#common-testing-patterns)
21. [Implementation Examples](#implementation-examples)

## Testing Philosophy

Cortex Core's testing philosophy aligns with the overall project philosophy of ruthless simplicity:

### 1. Test What Matters

- **Focus on Core Functionality**: Concentrate testing efforts on the most critical paths
- **Pragmatic Coverage**: Aim for high coverage of business logic and error scenarios rather than trivial code
- **Risk-Based Testing**: Allocate more testing effort to complex or high-risk areas

### 2. Test at the Right Level

- **Unit Tests** for isolated business logic and utility functions
- **Integration Tests** for verifying component interactions
- **API Tests** for validating endpoint behavior from the user's perspective
- **Avoid Redundancy**: Don't test the same thing at multiple levels unless necessary

### 3. Fast Feedback

- **Fast Test Suite**: Tests should run quickly to provide rapid feedback
- **Fast Failures**: Tests should fail fast and provide clear error messages
- **Automatic Test Running**: Tests should be easy to run automatically

### 4. Testability by Design

- **Design for Testability**: Code should be structured to facilitate testing
- **Dependency Injection**: Use dependency injection to enable easy mocking
- **Separation of Concerns**: Keep components focused and independent to simplify testing

### 5. Test Confidence, Not Implementation

- **Behavior over Implementation**: Test what the code does, not how it does it
- **Refactoring Safety**: Tests should support, not hinder, code refactoring
- **Test Stability**: Tests should not break with minor implementation changes

## Test Organization

Organize tests to mirror the project structure, making it easy to locate tests for specific components:

```
cortex-core/
├── app/                 # Application code
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── services/
│   └── ...
└── tests/               # Test code
    ├── unit/            # Unit tests
    │   ├── core/        # Tests for app/core
    │   ├── models/      # Tests for app/models
    │   └── services/    # Tests for app/services
    ├── integration/     # Integration tests
    │   ├── repositories/# Tests for database repositories
    │   └── services/    # Tests for service integration
    ├── api/             # API tests
    │   ├── auth/        # Authentication API tests
    │   ├── input/       # Input API tests
    │   ├── output/      # Output API tests
    │   └── config/      # Configuration API tests
    ├── conftest.py      # Shared test fixtures
    └── utils/           # Test utilities
```

## Test Types and Coverage

Different test types serve different purposes and should be used appropriately:

### Unit Tests (60-70% of tests)

- **Purpose**: Verify the functionality of individual components in isolation
- **Scope**: Individual functions, classes, or methods
- **Dependencies**: All dependencies mocked or stubbed
- **Coverage Target**: 80% code coverage for business logic

### Integration Tests (20-30% of tests)

- **Purpose**: Verify interactions between components
- **Scope**: Multiple components working together
- **Dependencies**: Some real, some mocked
- **Coverage Target**: Key integration points and workflows

### API Tests (10-20% of tests)

- **Purpose**: Verify API endpoint behavior from the user's perspective
- **Scope**: HTTP endpoints
- **Dependencies**: All components in the request path
- **Coverage Target**: All API endpoints with key scenarios

### Test Coverage Priorities

Focus testing efforts on these key areas:

1. **API Endpoints**: All endpoints should have tests covering:

   - Happy path scenarios
   - Validation failures
   - Authentication/authorization failures
   - Error conditions

2. **Repository Logic**: All repository methods should be tested for:

   - Successful operations
   - Error handling
   - Edge cases (empty results, large datasets)
   - Transaction behavior

3. **Service Layer**: All service methods should be tested for:

   - Business logic correctness
   - Input validation
   - Error handling
   - Integration with other services

4. **Core Components**:
   - Event bus functionality
   - Authentication logic
   - Error handling middleware

## Testing Tools and Setup

### Primary Testing Tools

For Phase 2, use these core testing tools:

1. **pytest**: Main testing framework
2. **pytest-asyncio**: For testing async functions
3. **pytest-cov**: For measuring test coverage
4. **httpx**: For testing HTTP endpoints
5. **sqlalchemy**: For database testing

### Setup and Configuration

#### Install Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

#### pytest.ini Configuration

Create a `pytest.ini` file in the project root:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    api: API tests
    slow: Slow tests
    repository: Repository tests
    service: Service tests
```

#### conftest.py

Create a `conftest.py` file with shared fixtures:

```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import uuid

from app.database.models import Base
from app.main import app
from app.utils.auth import create_access_token

# SQLite in-memory database URL for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db():
    """Create a test database."""
    # Create async engine
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create session
    async with async_session() as session:
        yield session

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Dispose engine
    await engine.dispose()

@pytest.fixture
def test_client():
    """Create a test client for FastAPI."""
    return TestClient(app)

@pytest.fixture
def test_token():
    """Create a test JWT token."""
    token_data = {
        "sub": "test@example.com",
        "oid": "test-user-id",
        "name": "Test User",
        "email": "test@example.com"
    }
    return create_access_token(token_data)

@pytest.fixture
def auth_headers(test_token):
    """Create authorization headers with test token."""
    return {"Authorization": f"Bearer {test_token}"}

@pytest.fixture
def generate_uuid():
    """Generate a deterministic UUID for testing."""
    return lambda: str(uuid.uuid4())
```

## Unit Testing

Unit tests focus on testing individual components in isolation.

### What to Unit Test

- **Utility Functions**: Pure functions that transform data
- **Model Validation**: Pydantic model validation rules
- **Business Logic**: Core business rules in isolation
- **Edge Cases**: Boundary conditions and exceptional scenarios

### Unit Testing Approach

1. **Isolate the Component**: Test the unit in isolation, mocking all dependencies
2. **Test Happy Path**: Verify correct behavior with valid inputs
3. **Test Edge Cases**: Verify behavior with edge case inputs
4. **Test Error Cases**: Verify proper error handling

### Example: Testing a Utility Function

```python
import pytest
from app.utils.validators import validate_uuid

def test_validate_uuid_valid():
    """Test validate_uuid with valid UUID."""
    valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
    result = validate_uuid(valid_uuid)
    assert result == valid_uuid

def test_validate_uuid_invalid():
    """Test validate_uuid with invalid UUID."""
    invalid_uuid = "not-a-uuid"
    with pytest.raises(ValueError) as excinfo:
        validate_uuid(invalid_uuid)
    assert "must be a valid UUID" in str(excinfo.value)
```

### Example: Testing a Domain Model

```python
import pytest
from pydantic import ValidationError
from app.models.domain import Workspace
import uuid

def test_workspace_model_valid():
    """Test workspace model with valid data."""
    workspace_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())

    workspace = Workspace(
        id=workspace_id,
        name="Test Workspace",
        description="Test description",
        owner_id=owner_id,
        metadata={"key": "value"}
    )

    assert workspace.id == workspace_id
    assert workspace.name == "Test Workspace"
    assert workspace.description == "Test description"
    assert workspace.owner_id == owner_id
    assert workspace.metadata == {"key": "value"}

def test_workspace_model_invalid_id():
    """Test workspace model with invalid ID."""
    with pytest.raises(ValidationError) as excinfo:
        Workspace(
            id="invalid-id",
            name="Test Workspace",
            description="Test description",
            owner_id=str(uuid.uuid4()),
            metadata={}
        )

    errors = excinfo.value.errors()
    assert any(error["loc"][0] == "id" for error in errors)
```

## Integration Testing

Integration tests verify that components work together correctly.

### What to Integration Test

- **Repository Implementation**: Test database operations
- **Service Layer**: Test service methods that coordinate multiple components
- **Authentication Flow**: Test the complete authentication flow
- **Event Bus**: Test event publishing and subscription

### Integration Testing Approach

1. **Identify Integration Points**: Focus on where components interact
2. **Use Real Dependencies**: Use real implementations when practical
3. **Test Complete Workflows**: Verify end-to-end behavior
4. **Test Transactions**: Verify transaction behavior, including rollbacks

### Example: Testing Repository Integration

```python
import pytest
from app.database.repositories import WorkspaceRepository
from app.models.domain import Workspace
import uuid

@pytest.mark.asyncio
async def test_workspace_repository_create(test_db):
    """Test creating a workspace with repository."""
    # Create repository
    repo = WorkspaceRepository(test_db)

    # Create test workspace
    workspace_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())

    workspace = Workspace(
        id=workspace_id,
        name="Test Workspace",
        description="Test description",
        owner_id=owner_id,
        metadata={"key": "value"}
    )

    # Create workspace using repository
    created_workspace = await repo.create(workspace)

    # Verify workspace was created
    assert created_workspace.id == workspace_id
    assert created_workspace.name == "Test Workspace"

    # Verify workspace can be retrieved
    retrieved_workspace = await repo.get_by_id(workspace_id)
    assert retrieved_workspace is not None
    assert retrieved_workspace.id == workspace_id
    assert retrieved_workspace.name == "Test Workspace"
    assert retrieved_workspace.metadata == {"key": "value"}
```

## API Testing

API tests verify the behavior of API endpoints from the client's perspective.

### What to API Test

- **Request Validation**: Verify that invalid requests are rejected
- **Response Format**: Verify that responses have the correct format
- **Authentication**: Verify that authentication is required and working
- **Authorization**: Verify that authorization rules are enforced
- **Error Handling**: Verify that errors are handled correctly

### API Testing Approach

1. **Use TestClient**: Use FastAPI's TestClient to make requests
2. **Test HTTP Status Codes**: Verify correct status codes for different scenarios
3. **Test Response Body**: Verify response body structure and content
4. **Test Headers**: Verify required and response headers

### Example: Testing an API Endpoint

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_workspace_success(auth_headers):
    """Test successful workspace creation."""
    response = client.post(
        "/config/workspace",
        json={
            "name": "Test Workspace",
            "description": "Test description",
            "metadata": {"key": "value"}
        },
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "workspace created"
    assert data["workspace"]["name"] == "Test Workspace"
    assert data["workspace"]["description"] == "Test description"
    assert data["workspace"]["metadata"] == {"key": "value"}

def test_create_workspace_validation_error(auth_headers):
    """Test workspace creation with validation error."""
    response = client.post(
        "/config/workspace",
        json={
            "name": "",  # Empty name (invalid)
            "description": "Test description"
        },
        headers=auth_headers
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "validation_error"
    assert "name" in data["error"]["details"]

def test_create_workspace_unauthorized():
    """Test workspace creation without authentication."""
    response = client.post(
        "/config/workspace",
        json={
            "name": "Test Workspace",
            "description": "Test description"
        }
    )

    assert response.status_code == 401
```

## Repository Testing

Repository tests verify the data access layer works correctly.

### What to Repository Test

- **CRUD Operations**: Create, read, update, delete operations
- **Query Filters**: Filtering and pagination
- **Transaction Behavior**: Commit and rollback
- **Constraints**: Enforce unique constraints and foreign keys
- **Error Handling**: Handle database errors properly

### Repository Testing Approach

1. **Use In-Memory SQLite**: Test with SQLite in-memory database
2. **Test Transaction Boundaries**: Verify transaction behavior
3. **Test with Real Queries**: Use actual SQL queries, not mocks
4. **Test Data Mapping**: Verify correct mapping between models

### Example: Testing a Repository

```python
import pytest
from sqlalchemy import select
from app.database.repositories import WorkspaceRepository
from app.database.models import Workspace as DbWorkspace
from app.models.domain import Workspace
from app.database.exceptions import EntityNotFoundError, DuplicateEntityError
import uuid

@pytest.mark.asyncio
async def test_workspace_repository_get_by_id(test_db):
    """Test getting a workspace by ID."""
    # Create test workspace directly in database
    workspace_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())

    db_workspace = DbWorkspace(
        id=workspace_id,
        name="Test Workspace",
        description="Test description",
        owner_id=owner_id,
        metadata_json="{\"key\": \"value\"}"
    )

    test_db.add(db_workspace)
    await test_db.commit()

    # Clear session to ensure fresh data retrieval
    await test_db.close()

    # Create repository
    repo = WorkspaceRepository(test_db)

    # Get workspace
    workspace = await repo.get_by_id(workspace_id)

    # Verify workspace
    assert workspace is not None
    assert workspace.id == workspace_id
    assert workspace.name == "Test Workspace"
    assert workspace.description == "Test description"
    assert workspace.owner_id == owner_id
    assert workspace.metadata == {"key": "value"}

@pytest.mark.asyncio
async def test_workspace_repository_create_duplicate(test_db):
    """Test creating a workspace with duplicate name."""
    # Create repository
    repo = WorkspaceRepository(test_db)

    # Create owner
    owner_id = str(uuid.uuid4())

    # Create first workspace
    workspace1 = Workspace(
        id=str(uuid.uuid4()),
        name="Test Workspace",
        description="Test description",
        owner_id=owner_id,
        metadata={}
    )

    await repo.create(workspace1)

    # Try to create workspace with same name
    workspace2 = Workspace(
        id=str(uuid.uuid4()),
        name="Test Workspace",  # Same name
        description="Another description",
        owner_id=owner_id,
        metadata={}
    )

    # Verify duplicate error is raised
    with pytest.raises(DuplicateEntityError) as excinfo:
        await repo.create(workspace2)

    assert "already exists" in str(excinfo.value)
    assert "name" in str(excinfo.value)
```

## Service Layer Testing

Service layer tests verify business logic and coordination between components.

### What to Service Test

- **Business Logic**: Verify business rules and calculations
- **Transaction Coordination**: Verify operations across multiple repositories
- **Input Validation**: Verify input validation at the service level
- **Error Handling**: Verify error handling and propagation
- **Event Generation**: Verify events are published when expected

### Service Testing Approach

1. **Mock Repositories**: Use mock repositories for faster tests
2. **Test Business Rules**: Focus on business logic and validation
3. **Test Complete Use Cases**: Verify entire use cases, not just methods
4. **Test Authorization Rules**: Verify authorization rules are enforced

### Example: Testing a Service

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services import WorkspaceService
from app.models.domain import Workspace, User
from app.database.exceptions import EntityNotFoundError, DuplicateEntityError
import uuid

@pytest.mark.asyncio
async def test_workspace_service_create_workspace():
    """Test creating a workspace with service."""
    # Mock repositories
    user_repo = AsyncMock()
    workspace_repo = AsyncMock()

    # Mock user_repo.get_by_id to return a user
    user_id = str(uuid.uuid4())
    user = User(user_id=user_id, name="Test User", email="test@example.com", metadata={})
    user_repo.get_by_id.return_value = user

    # Mock workspace_repo.list_by_owner to return empty list (no existing workspaces)
    workspace_repo.list_by_owner.return_value = []

    # Mock workspace_repo.create to return the created workspace
    async def mock_create(workspace):
        return workspace
    workspace_repo.create.side_effect = mock_create

    # Create service with mocked repositories
    service = WorkspaceService()
    service._get_user_repository = lambda: user_repo
    service._get_workspace_repository = lambda: workspace_repo

    # Call service method
    workspace = await service.create_workspace(
        name="Test Workspace",
        description="Test description",
        owner_id=user_id,
        metadata={"key": "value"}
    )

    # Verify user_repo.get_by_id was called with correct user_id
    user_repo.get_by_id.assert_called_once_with(user_id)

    # Verify workspace_repo.list_by_owner was called with correct user_id
    workspace_repo.list_by_owner.assert_called_once_with(user_id)

    # Verify workspace_repo.create was called with correct workspace
    workspace_repo.create.assert_called_once()
    created_workspace = workspace_repo.create.call_args[0][0]
    assert created_workspace.name == "Test Workspace"
    assert created_workspace.description == "Test description"
    assert created_workspace.owner_id == user_id
    assert created_workspace.metadata == {"key": "value"}

    # Verify returned workspace
    assert workspace.name == "Test Workspace"
    assert workspace.description == "Test description"
    assert workspace.owner_id == user_id
    assert workspace.metadata == {"key": "value"}

@pytest.mark.asyncio
async def test_workspace_service_create_workspace_user_not_found():
    """Test creating a workspace with non-existent user."""
    # Mock repositories
    user_repo = AsyncMock()
    workspace_repo = AsyncMock()

    # Mock user_repo.get_by_id to return None (user not found)
    user_repo.get_by_id.return_value = None

    # Create service with mocked repositories
    service = WorkspaceService()
    service._get_user_repository = lambda: user_repo
    service._get_workspace_repository = lambda: workspace_repo

    # Verify EntityNotFoundError is raised
    user_id = str(uuid.uuid4())
    with pytest.raises(EntityNotFoundError) as excinfo:
        await service.create_workspace(
            name="Test Workspace",
            description="Test description",
            owner_id=user_id,
            metadata={}
        )

    assert "User" in str(excinfo.value)
    assert user_id in str(excinfo.value)

    # Verify user_repo.get_by_id was called with correct user_id
    user_repo.get_by_id.assert_called_once_with(user_id)

    # Verify workspace_repo methods were not called
    workspace_repo.list_by_owner.assert_not_called()
    workspace_repo.create.assert_not_called()
```

## Test Database Strategy

Tests that interact with the database require special consideration.

### Using SQLite for Testing

SQLite in-memory databases provide fast, isolated test databases:

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database.models import Base

# SQLite in-memory database URL for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db():
    """Create a test database."""
    # Create async engine
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create session
    async with async_session() as session:
        yield session

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Dispose engine
    await engine.dispose()
```

### Database Isolation

Ensure tests don't interfere with each other:

- **Use Separate Database Session**: Each test gets its own session
- **Rollback After Tests**: Roll back transactions after tests
- **Create Fresh Data**: Create test data for each test

### SQLite vs. PostgreSQL Differences

Be aware of differences between SQLite and PostgreSQL:

- **JSON Handling**: SQLite stores JSON as text
- **Case Sensitivity**: SQLite string comparisons are case-sensitive
- **Concurrency**: SQLite has limited concurrency
- **Foreign Keys**: SQLite requires foreign key support to be enabled

For most tests, SQLite is sufficient, but you may need PostgreSQL-specific tests for certain features.

### DatabaseCleaner Fixture

Create a fixture to clean the database between tests:

```python
@pytest.fixture
async def db_cleaner(test_db):
    """Clean database between tests."""
    yield test_db

    # Delete all data from tables
    for table in reversed(Base.metadata.sorted_tables):
        await test_db.execute(table.delete())

    await test_db.commit()
```

## Error Handling Testing

Testing error handling ensures the system behaves correctly in exceptional cases.

### What to Test

- **Validation Errors**: Verify validation errors are raised and handled
- **Not Found Errors**: Verify not found errors are raised and handled
- **Authorization Errors**: Verify authorization errors are raised and handled
- **Database Errors**: Verify database errors are handled properly
- **HTTP Error Responses**: Verify API endpoints return correct error responses

### Error Testing Approach

1. **Force Error Conditions**: Deliberately create conditions that cause errors
2. **Verify Error Response**: Verify the error response format and status code
3. **Check Error Logging**: Verify errors are logged correctly
4. **Test Recovery**: Verify the system recovers properly after errors

### Example: Testing Error Handling

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch

client = TestClient(app)

def test_workspace_not_found(auth_headers):
    """Test response when workspace is not found."""
    response = client.get(
        "/config/workspace/non-existent-id",
        headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert "Workspace" in response.json()["error"]["message"]

def test_database_error(auth_headers):
    """Test response when database error occurs."""
    # Patch the repository to raise a database error
    with patch("app.database.repositories.WorkspaceRepository.get_by_id") as mock_get:
        mock_get.side_effect = Exception("Database error")

        response = client.get(
            "/config/workspace/some-id",
            headers=auth_headers
        )

        assert response.status_code == 500
        assert response.json()["error"]["code"] == "internal_error"
```

## Authentication Testing

Testing authentication ensures the system's security mechanisms work correctly.

### What to Test

- **Token Generation**: Verify JWT tokens are generated correctly
- **Token Validation**: Verify tokens are validated correctly
- **Protected Endpoints**: Verify protected endpoints require authentication
- **Invalid Tokens**: Verify invalid or expired tokens are rejected
- **Authorization Rules**: Verify users can only access their own resources

### Authentication Testing Approach

1. **Test Token Creation**: Verify tokens are created with correct claims
2. **Test Token Validation**: Verify token validation with valid and invalid tokens
3. **Test Protected Endpoints**: Verify endpoints require valid tokens
4. **Test Authorization Rules**: Verify access control rules

### Example: Testing Authentication

```python
import pytest
import jwt
from app.utils.auth import create_access_token, get_current_user
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import AsyncMock

client = TestClient(app)

def test_create_access_token():
    """Test creating access token."""
    # Create token with test data
    token_data = {
        "sub": "test@example.com",
        "oid": "test-user-id",
        "name": "Test User",
        "email": "test@example.com"
    }

    token = create_access_token(token_data)

    # Decode token and verify claims
    decoded = jwt.decode(
        token,
        "devsecretkey",  # Test secret key
        algorithms=["HS256"],
        options={"verify_signature": True}
    )

    assert decoded["sub"] == token_data["sub"]
    assert decoded["oid"] == token_data["oid"]
    assert decoded["name"] == token_data["name"]
    assert decoded["email"] == token_data["email"]
    assert "exp" in decoded  # Expiration time

def test_protected_endpoint_with_valid_token(auth_headers):
    """Test protected endpoint with valid token."""
    response = client.get(
        "/config/workspace",
        headers=auth_headers
    )

    assert response.status_code != 401  # Not unauthorized

def test_protected_endpoint_without_token():
    """Test protected endpoint without token."""
    response = client.get("/config/workspace")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"

def test_protected_endpoint_with_invalid_token():
    """Test protected endpoint with invalid token."""
    headers = {"Authorization": "Bearer invalid-token"}

    response = client.get(
        "/config/workspace",
        headers=headers
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
```

## Test Data Management

Managing test data effectively is crucial for reliable tests.

### Test Data Generation

Use factories or fixtures to generate test data:

```python
import uuid
import pytest
from app.models.domain import User, Workspace, Conversation

@pytest.fixture
def create_test_user():
    """Create a test user."""
    def _create(user_id=None, name="Test User", email="test@example.com"):
        return User(
            user_id=user_id or str(uuid.uuid4()),
            name=name,
            email=email,
            metadata={}
        )
    return _create

@pytest.fixture
def create_test_workspace():
    """Create a test workspace."""
    def _create(workspace_id=None, name="Test Workspace", owner_id=None):
        return Workspace(
            id=workspace_id or str(uuid.uuid4()),
            name=name,
            description="Test description",
            owner_id=owner_id or str(uuid.uuid4()),
            metadata={}
        )
    return _create

@pytest.fixture
def create_test_conversation():
    """Create a test conversation."""
    def _create(conversation_id=None, workspace_id=None, topic="Test Topic", participant_ids=None):
        return Conversation(
            id=conversation_id or str(uuid.uuid4()),
            workspace_id=workspace_id or str(uuid.uuid4()),
            topic=topic,
            participant_ids=participant_ids or [str(uuid.uuid4())],
            metadata={}
        )
    return _create
```

### Database Seeding

Seed test database with known data:

```python
@pytest.fixture
async def seed_database(test_db, create_test_user, create_test_workspace):
    """Seed database with test data."""
    # Create user
    user_id = str(uuid.uuid4())
    user = create_test_user(user_id=user_id)

    # Convert to database model
    from app.database.models import User as DbUser
    db_user = DbUser(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        metadata_json="{}"
    )

    test_db.add(db_user)
    await test_db.commit()

    # Create workspace
    workspace = create_test_workspace(owner_id=user_id)

    # Convert to database model
    from app.database.models import Workspace as DbWorkspace
    db_workspace = DbWorkspace(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        owner_id=workspace.owner_id,
        metadata_json="{}"
    )

    test_db.add(db_workspace)
    await test_db.commit()

    # Return created entities
    return {
        "user": user,
        "workspace": workspace
    }
```

### Test Data Isolation

Ensure tests don't interfere with each other:

- **Use Unique IDs**: Generate unique IDs for test entities
- **Avoid Global State**: Don't use global variables for test data
- **Clean Up After Tests**: Clean up any created data

## Mocking Strategy

Mocking allows testing components in isolation by replacing dependencies.

### When to Mock

- **External Dependencies**: APIs, databases, or other services
- **Complex Dependencies**: Components that are difficult to set up
- **Slow Dependencies**: Components that slow down tests
- **Error Scenarios**: To simulate error conditions

### What Not to Mock

- **The Code Under Test**: Never mock the code you're testing
- **Simple Value Objects**: No need to mock simple data structures
- **Core Libraries**: Avoid mocking standard library functions

### Mocking Tools

Use `unittest.mock` for most mocking needs:

- **MagicMock**: For general-purpose mocking
- **AsyncMock**: For mocking async functions
- **patch**: For temporarily replacing objects
- **patch.object**: For replacing object attributes or methods

### Example: Mocking Repositories

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services import WorkspaceService
from app.models.domain import Workspace, User
import uuid

@pytest.mark.asyncio
async def test_get_workspace_service():
    """Test getting a workspace with service."""
    # Create mocks
    workspace_repo = AsyncMock()

    # Mock get_by_id to return a workspace
    workspace_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())
    workspace = Workspace(
        id=workspace_id,
        name="Test Workspace",
        description="Test description",
        owner_id=owner_id,
        metadata={}
    )
    workspace_repo.get_by_id.return_value = workspace

    # Create service with mocked repository
    service = WorkspaceService()
    service._get_workspace_repository = lambda: workspace_repo

    # Call service method
    result = await service.get_workspace(workspace_id, owner_id)

    # Verify repository method was called
    workspace_repo.get_by_id.assert_called_once_with(workspace_id)

    # Verify result
    assert result == workspace
```

### Example: Mocking the Database Session

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories import WorkspaceRepository
from app.models.domain import Workspace
import uuid

@pytest.mark.asyncio
async def test_workspace_repository_with_mocked_session():
    """Test workspace repository with mocked session."""
    # Create mock session
    session = AsyncMock(spec=AsyncSession)

    # Mock execute method
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalars.return_value.first.return_value = None

    # Create repository with mock session
    repo = WorkspaceRepository(session)

    # Call repository method
    workspace = await repo.get_by_id(str(uuid.uuid4()))

    # Verify session method was called
    session.execute.assert_called_once()

    # Verify result
    assert workspace is None
```

## Async Testing Techniques

Testing asynchronous code requires special techniques.

### Using pytest-asyncio

Use pytest-asyncio to test async functions:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test an async function."""
    result = await my_async_function()
    assert result == expected_result
```

### Testing AsyncClient

For testing async HTTP endpoints:

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_async_endpoint():
    """Test an async endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/some/endpoint")
        assert response.status_code == 200
```

### Testing Event Loops

When testing code that creates tasks or uses event loops:

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_with_event_loop():
    """Test code that uses the event loop."""
    # Get the current event loop
    loop = asyncio.get_event_loop()

    # Create a future
    future = loop.create_future()

    # Schedule a task to set the future result
    loop.call_soon(lambda: future.set_result("done"))

    # Wait for the future
    result = await future

    assert result == "done"
```

## Test Isolation

Ensuring tests are isolated prevents interference between tests.

### Function-Level Isolation

Each test function should be independent:

- **No Shared State**: Don't use module-level variables for test state
- **Reset State**: Reset any global state before and after tests
- **Independent Setup**: Each test should set up its own test data

### Database Isolation

Ensure database tests don't interfere:

- **Separate Test Database**: Use a separate database for testing
- **Transaction Rollback**: Roll back transactions after tests
- **Clean State**: Start with a clean state for each test

### Mocking Isolation

When using mocks, ensure they are reset:

- **Reset Mocks**: Reset mocks between tests
- **Clear Mock Calls**: Clear recorded mock calls between tests
- **Restore Patched Objects**: Restore patched objects after tests

## Test Naming and Structure

Good test naming and structure improves readability and maintainability.

### Test Naming Convention

Follow a consistent naming convention:

```python
def test_function_name_scenario_expected_result():
    """Test that function_name with scenario results in expected_result."""
    # Test code
```

Examples:

- `test_create_workspace_valid_data_returns_workspace()`
- `test_get_workspace_not_found_raises_error()`
- `test_authenticate_invalid_credentials_returns_error()`

### Test Structure

Structure tests with arrange-act-assert:

```python
def test_example():
    """Test example."""
    # Arrange (set up test data and dependencies)
    data = {"key": "value"}
    mock_dependency = MagicMock()

    # Act (call the code under test)
    result = function_under_test(data, mock_dependency)

    # Assert (verify the result)
    assert result == expected_result
    mock_dependency.method.assert_called_once_with(data)
```

### Test Documentation

Document tests with docstrings:

```python
def test_get_workspace_by_id():
    """
    Test getting a workspace by ID.

    This test verifies that:
    1. The repository can get a workspace by ID
    2. The workspace data is correctly mapped
    3. The metadata is properly deserialized
    """
    # Test code
```

## Test Coverage Requirements

Define minimum test coverage requirements for the project.

### Coverage Targets

- **Overall Coverage**: 80% code coverage
- **Business Logic**: 90% coverage
- **API Endpoints**: 100% coverage
- **Repository Methods**: 90% coverage
- **Error Handling**: 85% coverage

### Measuring Coverage

Use pytest-cov to measure coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

### Coverage Report

Generate a coverage report:

```bash
pytest --cov=app --cov-report=html
```

### Coverage Configuration

Create a `.coveragerc` file to configure coverage:

```ini
[run]
source = app
omit =
    app/main.py
    app/__init__.py
    app/utils/__init__.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == .__main__.:
    pass
    raise ImportError
```

## Running Tests

Define how to run tests consistently.

### Running All Tests

```bash
pytest
```

### Running Specific Tests

```bash
# Run a specific test file
pytest tests/unit/test_models.py

# Run a specific test function
pytest tests/unit/test_models.py::test_workspace_model_valid

# Run tests matching a pattern
pytest -k "workspace"

# Run tests with a specific marker
pytest -m "unit"
```

### Running with Verbosity

```bash
pytest -v
```

### Running with Coverage

```bash
pytest --cov=app
```

### Running in Parallel

For faster test execution:

```bash
pytest -xvs -n auto
```

(Requires `pytest-xdist`)

## Common Testing Patterns

### Testing Pagination

```python
@pytest.mark.asyncio
async def test_list_with_pagination(test_db):
    """Test listing with pagination."""
    # Create repository
    repo = WorkspaceRepository(test_db)

    # Create 20 workspaces
    owner_id = str(uuid.uuid4())
    for i in range(20):
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name=f"Workspace {i}",
            description=f"Description {i}",
            owner_id=owner_id,
            metadata={}
        )
        await repo.create(workspace)

    # List with pagination (page 1)
    workspaces_page1 = await repo.list_by_owner(owner_id, limit=10, offset=0)
    assert len(workspaces_page1) == 10

    # List with pagination (page 2)
    workspaces_page2 = await repo.list_by_owner(owner_id, limit=10, offset=10)
    assert len(workspaces_page2) == 10

    # Verify pages are different
    assert all(ws1.id != ws2.id for ws1 in workspaces_page1 for ws2 in workspaces_page2)
```

### Testing Transactions

```python
@pytest.mark.asyncio
async def test_transaction_commit_and_rollback(test_db):
    """Test transaction commit and rollback."""
    # Create test entities
    workspace_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())

    # Start a transaction
    async with test_db.begin():
        # Add a workspace
        from app.database.models import Workspace as DbWorkspace
        db_workspace = DbWorkspace(
            id=workspace_id,
            name="Test Workspace",
            description="Test description",
            owner_id=owner_id,
            metadata_json="{}"
        )

        test_db.add(db_workspace)

    # Verify workspace was committed
    result = await test_db.execute(
        select(DbWorkspace).where(DbWorkspace.id == workspace_id)
    )
    assert result.scalars().first() is not None

    # Start another transaction that will be rolled back
    try:
        async with test_db.begin():
            # Delete the workspace
            await test_db.execute(
                delete(DbWorkspace).where(DbWorkspace.id == workspace_id)
            )

            # Verify it's deleted within the transaction
            result = await test_db.execute(
                select(DbWorkspace).where(DbWorkspace.id == workspace_id)
            )
            assert result.scalars().first() is None

            # Raise an exception to trigger rollback
            raise ValueError("Trigger rollback")
    except ValueError:
        pass

    # Verify workspace still exists (rollback occurred)
    result = await test_db.execute(
        select(DbWorkspace).where(DbWorkspace.id == workspace_id)
    )
    assert result.scalars().first() is not None
```

### Testing Authorization

```python
@pytest.mark.asyncio
async def test_get_workspace_authorization(test_db):
    """Test workspace authorization."""
    # Create repository
    repo = WorkspaceRepository(test_db)

    # Create two users
    owner_id = str(uuid.uuid4())
    other_user_id = str(uuid.uuid4())

    # Create a workspace
    workspace = Workspace(
        id=str(uuid.uuid4()),
        name="Test Workspace",
        description="Test description",
        owner_id=owner_id,
        metadata={}
    )

    created_workspace = await repo.create(workspace)

    # Owner can access the workspace
    owner_view = await repo.get_by_id(created_workspace.id, owner_id=owner_id)
    assert owner_view is not None
    assert owner_view.id == created_workspace.id

    # Other user cannot access the workspace
    other_view = await repo.get_by_id(created_workspace.id, owner_id=other_user_id)
    assert other_view is None
```

## Implementation Examples

### Complete Unit Test Example

```python
import pytest
from app.models.domain import Workspace, User
from app.services import WorkspaceService
from app.core.exceptions import EntityNotFoundError, ValidationError
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

@pytest.mark.unit
class TestWorkspaceService:
    """Tests for WorkspaceService."""

    @pytest.fixture
    def service(self):
        """Create a WorkspaceService with mocked repositories."""
        service = WorkspaceService()

        # Mock repositories
        service._get_user_repository = AsyncMock()
        service._get_workspace_repository = AsyncMock()

        return service

    @pytest.mark.asyncio
    async def test_create_workspace_valid_data(self, service):
        """Test creating a workspace with valid data."""
        # Arrange
        user_id = str(uuid.uuid4())
        workspace_id = str(uuid.uuid4())

        # Mock user repository to return a user
        user = User(user_id=user_id, name="Test User", email="test@example.com", metadata={})
        service._get_user_repository.return_value.get_by_id.return_value = user

        # Mock workspace repository
        service._get_workspace_repository.return_value.list_by_owner.return_value = []
        service._get_workspace_repository.return_value.create.side_effect = \
            lambda ws: Workspace(
                id=workspace_id,
                name=ws.name,
                description=ws.description,
                owner_id=ws.owner_id,
                metadata=ws.metadata
            )

        # Act
        workspace = await service.create_workspace(
            name="Test Workspace",
            description="Test description",
            owner_id=user_id,
            metadata={"key": "value"}
        )

        # Assert
        assert workspace.id == workspace_id
        assert workspace.name == "Test Workspace"
        assert workspace.description == "Test description"
        assert workspace.owner_id == user_id
        assert workspace.metadata == {"key": "value"}

        # Verify repository calls
        service._get_user_repository.return_value.get_by_id.assert_called_once_with(user_id)
        service._get_workspace_repository.return_value.list_by_owner.assert_called_once_with(user_id)
        service._get_workspace_repository.return_value.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_workspace_user_not_found(self, service):
        """Test creating a workspace with non-existent user."""
        # Arrange
        user_id = str(uuid.uuid4())

        # Mock user repository to return None (user not found)
        service._get_user_repository.return_value.get_by_id.return_value = None

        # Act and Assert
        with pytest.raises(EntityNotFoundError) as excinfo:
            await service.create_workspace(
                name="Test Workspace",
                description="Test description",
                owner_id=user_id,
                metadata={}
            )

        assert "User" in str(excinfo.value)
        assert user_id in str(excinfo.value)

        # Verify repository calls
        service._get_user_repository.return_value.get_by_id.assert_called_once_with(user_id)
        service._get_workspace_repository.return_value.list_by_owner.assert_not_called()
        service._get_workspace_repository.return_value.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_workspace_invalid_data(self, service):
        """Test creating a workspace with invalid data."""
        # Arrange
        user_id = str(uuid.uuid4())

        # Act and Assert
        with pytest.raises(ValidationError) as excinfo:
            await service.create_workspace(
                name="",  # Empty name (invalid)
                description="Test description",
                owner_id=user_id,
                metadata={}
            )

        assert "name" in excinfo.value.errors

        # Verify repository calls
        service._get_user_repository.return_value.get_by_id.assert_not_called()
        service._get_workspace_repository.return_value.list_by_owner.assert_not_called()
        service._get_workspace_repository.return_value.create.assert_not_called()
```

### Complete Integration Test Example

```python
import pytest
from sqlalchemy import select
from app.database.repositories import WorkspaceRepository
from app.database.models import Workspace as DbWorkspace
from app.models.domain import Workspace
from app.database.exceptions import EntityNotFoundError, DuplicateEntityError
import uuid

@pytest.mark.integration
class TestWorkspaceRepository:
    """Integration tests for WorkspaceRepository."""

    @pytest.fixture
    async def repository(self, test_db):
        """Create a WorkspaceRepository with test database."""
        return WorkspaceRepository(test_db)

    @pytest.mark.asyncio
    async def test_create_and_get_workspace(self, repository, test_db):
        """Test creating and getting a workspace."""
        # Create test data
        workspace_id = str(uuid.uuid4())
        owner_id = str(uuid.uuid4())

        # Create user in database (for foreign key constraint)
        from app.database.models import User as DbUser
        db_user = DbUser(
            user_id=owner_id,
            name="Test User",
            email="test@example.com",
            metadata_json="{}"
        )

        test_db.add(db_user)
        await test_db.commit()

        # Create workspace domain model
        workspace = Workspace(
            id=workspace_id,
            name="Test Workspace",
            description="Test description",
            owner_id=owner_id,
            metadata={"key": "value"}
        )

        # Create workspace using repository
        created_workspace = await repository.create(workspace)

        # Verify created workspace
        assert created_workspace.id == workspace_id
        assert created_workspace.name == "Test Workspace"
        assert created_workspace.description == "Test description"
        assert created_workspace.owner_id == owner_id
        assert created_workspace.metadata == {"key": "value"}

        # Get workspace using repository
        retrieved_workspace = await repository.get_by_id(workspace_id)

        # Verify retrieved workspace
        assert retrieved_workspace is not None
        assert retrieved_workspace.id == workspace_id
        assert retrieved_workspace.name == "Test Workspace"
        assert retrieved_workspace.description == "Test description"
        assert retrieved_workspace.owner_id == owner_id
        assert retrieved_workspace.metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_create_duplicate_workspace(self, repository, test_db):
        """Test creating a workspace with duplicate name."""
        # Create user in database (for foreign key constraint)
        owner_id = str(uuid.uuid4())
        from app.database.models import User as DbUser
        db_user = DbUser(
            user_id=owner_id,
            name="Test User",
            email="test@example.com",
            metadata_json="{}"
        )

        test_db.add(db_user)
        await test_db.commit()

        # Create first workspace
        workspace1 = Workspace(
            id=str(uuid.uuid4()),
            name="Test Workspace",
            description="Test description",
            owner_id=owner_id,
            metadata={}
        )

        await repository.create(workspace1)

        # Create second workspace with same name
        workspace2 = Workspace(
            id=str(uuid.uuid4()),
            name="Test Workspace",  # Same name
            description="Another description",
            owner_id=owner_id,
            metadata={}
        )

        # Verify duplicate error is raised
        with pytest.raises(DuplicateEntityError) as excinfo:
            await repository.create(workspace2)

        assert "Workspace" in str(excinfo.value)
        assert "name" in str(excinfo.value)
        assert "Test Workspace" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_update_workspace(self, repository, test_db):
        """Test updating a workspace."""
        # Create user in database (for foreign key constraint)
        owner_id = str(uuid.uuid4())
        from app.database.models import User as DbUser
        db_user = DbUser(
            user_id=owner_id,
            name="Test User",
            email="test@example.com",
            metadata_json="{}"
        )

        test_db.add(db_user)
        await test_db.commit()

        # Create workspace
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name="Test Workspace",
            description="Test description",
            owner_id=owner_id,
            metadata={"key": "value"}
        )

        created_workspace = await repository.create(workspace)

        # Update workspace
        created_workspace.name = "Updated Workspace"
        created_workspace.description = "Updated description"
        created_workspace.metadata = {"key": "updated"}

        updated_workspace = await repository.update(created_workspace)

        # Verify updated workspace
        assert updated_workspace.id == created_workspace.id
        assert updated_workspace.name == "Updated Workspace"
        assert updated_workspace.description == "Updated description"
        assert updated_workspace.metadata == {"key": "updated"}

        # Verify in database
        result = await test_db.execute(
            select(DbWorkspace).where(DbWorkspace.id == created_workspace.id)
        )
        db_workspace = result.scalars().first()

        assert db_workspace is not None
        assert db_workspace.name == "Updated Workspace"
        assert db_workspace.description == "Updated description"
        import json
        assert json.loads(db_workspace.metadata_json) == {"key": "updated"}
```

### Complete API Test Example

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
import uuid

@pytest.mark.api
class TestWorkspaceApi:
    """API tests for workspace endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_create_workspace(self, client, auth_headers):
        """Test creating a workspace."""
        # Create request data
        request_data = {
            "name": "Test Workspace",
            "description": "Test description",
            "metadata": {"key": "value"}
        }

        # Send request
        response = client.post(
            "/config/workspace",
            json=request_data,
            headers=auth_headers
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "workspace created"
        assert data["workspace"]["name"] == "Test Workspace"
        assert data["workspace"]["description"] == "Test description"
        assert data["workspace"]["metadata"] == {"key": "value"}
        assert "id" in data["workspace"]
        assert "owner_id" in data["workspace"]

    def test_create_workspace_validation_error(self, client, auth_headers):
        """Test creating a workspace with validation error."""
        # Create invalid request data
        request_data = {
            "name": "",  # Empty name (invalid)
            "description": "Test description"
        }

        # Send request
        response = client.post(
            "/config/workspace",
            json=request_data,
            headers=auth_headers
        )

        # Verify response
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "validation_error"
        assert "name" in data["error"]["details"]

    def test_get_workspace(self, client, auth_headers):
        """Test getting a workspace."""
        # Create a workspace first
        create_response = client.post(
            "/config/workspace",
            json={
                "name": "Test Workspace",
                "description": "Test description"
            },
            headers=auth_headers
        )

        workspace_id = create_response.json()["workspace"]["id"]

        # Get the workspace
        response = client.get(
            f"/config/workspace/{workspace_id}",
            headers=auth_headers
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["workspace"]["id"] == workspace_id
        assert data["workspace"]["name"] == "Test Workspace"
        assert data["workspace"]["description"] == "Test description"

    def test_list_workspaces(self, client, auth_headers):
        """Test listing workspaces."""
        # Create workspaces
        for i in range(3):
            client.post(
                "/config/workspace",
                json={
                    "name": f"Workspace {i}",
                    "description": f"Description {i}"
                },
                headers=auth_headers
            )

        # List workspaces
        response = client.get(
            "/config/workspace",
            headers=auth_headers
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "workspaces" in data
        assert len(data["workspaces"]) >= 3

    def test_update_workspace(self, client, auth_headers):
        """Test updating a workspace."""
        # Create a workspace first
        create_response = client.post(
            "/config/workspace",
            json={
                "name": "Test Workspace",
                "description": "Test description"
            },
            headers=auth_headers
        )

        workspace_id = create_response.json()["workspace"]["id"]

        # Update the workspace
        update_data = {
            "name": "Updated Workspace",
            "description": "Updated description",
            "metadata": {"updated": True}
        }

        response = client.put(
            f"/config/workspace/{workspace_id}",
            json=update_data,
            headers=auth_headers
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["workspace"]["id"] == workspace_id
        assert data["workspace"]["name"] == "Updated Workspace"
        assert data["workspace"]["description"] == "Updated description"
        assert data["workspace"]["metadata"] == {"updated": True}
```

This testing strategy provides a comprehensive approach to testing the Cortex Core system in Phase 2. By following these guidelines, you'll create a robust test suite that gives confidence in the system's behavior while facilitating future changes.
