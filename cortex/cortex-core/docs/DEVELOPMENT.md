# Development Guide

This document contains information for developers contributing to Cortex Core.

## Project Structure

```
cortex_core/
├── alembic/              # Database migrations
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration
│   ├── components/       # Core components
│   │   ├── __init__.py
│   │   └── security_manager.py
│   ├── interfaces/       # Interface definitions
│   │   ├── __init__.py
│   │   └── memory_system.py
│   ├── api/              # API endpoints
│   │   ├── __init__.py
│   │   └── auth.py
│   ├── modalities/       # Input/output modalities
│   │   └── __init__.py
│   ├── database/         # Database models and connection
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── models.py
│   ├── cache/            # Redis cache
│   │   ├── __init__.py
│   │   └── redis_client.py
│   └── utils/            # Utility functions
│       ├── __init__.py
│       ├── json_helpers.py
│       └── logger.py
├── logs/                 # Log files
├── tests/                # Test cases
├── .env                  # Environment variables
└── pyproject.toml        # Project metadata and dependencies
```

## Key Components

### Session Manager

Handles user sessions and the association of sessions with specific workspaces, ensuring continuity and security across user interactions.

### Dispatcher

Routes incoming requests to the appropriate handlers, managing task delegation and coordination between different processing pathways.

### Context Manager

Interfaces with the memory system to retrieve, update, and maintain context across user interactions.

### Integration Hub

Facilitates communication with external services and tools, managing MCP client/server interactions.

### Workspace Manager

Handles the creation, retrieval, and organization of workspaces and associated conversations.

### Security Manager

Handles authentication, data encryption, and authorization processes to ensure all interactions are secure.

## Development Workflow

### Setting Up Development Environment

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/cortex-core.git
   cd cortex-core
   ```

2. Create and activate a virtual environment:

   ```bash
   uv venv
   # On Unix/macOS
   source .venv/bin/activate
   # On Windows
   .venv\Scripts\activate
   ```

3. Install dependencies in development mode:

   ```bash
   uv pip install -e ".[dev]"
   ```

4. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run specific tests
pytest tests/test_auth.py

# Run with coverage report
pytest --cov=app tests/

# Run only the event system tests
pytest tests/components/test_event_system.py
```

### Testing Best Practices

#### FastAPI Endpoint Testing

When testing FastAPI endpoints, use dependency overrides rather than patching:

```python
# BAD APPROACH (patching)
def test_login(test_client, mock_db):
    with patch("app.api.auth.get_db", return_value=mock_db):
        response = test_client.post("/auth/login", json={"username": "test"})
        assert response.status_code == 200

# GOOD APPROACH (dependency overrides)
@pytest.fixture
def client_with_db_override(mock_db):
    """Create a test client with DB dependency override"""
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}

def test_login(client_with_db_override):
    response = client_with_db_override.post("/auth/login", json={"username": "test"})
    assert response.status_code == 200
```

Key principles for effective API testing:

1. **Use dependency overrides**: Override FastAPI's dependency injection system rather than patching functions.
2. **Create specific fixtures**: Create fixtures that set up dependencies and clean up after tests.
3. **Handle async properly**: Use `@pytest.mark.asyncio` for async functions and properly await results.
4. **Clean up after tests**: Use `try/finally` or fixture yield patterns to clean up overrides.
5. **Mock at the right level**: Mock database sessions, not individual queries when possible.

#### Testing Async Components

For async components, always use the `asyncio` pytest plugin:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

#### Testing the Event System

When testing the event system, consider these scenarios:

1. **Basic Pub/Sub Testing**:
   - Test publishing events and receiving them through subscribers
   - Verify that event payloads are correctly delivered

2. **Pattern Matching Testing**:
   - Test wildcard patterns like "domain.*" and "*"
   - Test exact matches and multi-level patterns

3. **Error Handling Testing**:
   - Verify that errors in one subscriber don't affect others
   - Test error counting in statistics

4. **Tracing and Correlation Testing**:
   - Test that trace IDs are properly generated and propagated
   - Verify correlation IDs link related events

5. **Performance Testing**:
   - Test with many subscribers
   - Test concurrent event publishing
   
Example test for the event system:

```python
@pytest.mark.asyncio
async def test_publish_subscribe(event_system):
    # Setup
    received_events = []
    
    async def callback(event_type, payload):
        received_events.append(payload)
    
    # Subscribe to events
    subscription_id = await event_system.subscribe("test.*", callback)
    
    # Publish an event
    await event_system.publish(
        event_type="test.event",
        data={"key": "value"},
        source="test_component"
    )
    
    # Verify
    assert len(received_events) == 1
    assert received_events[0].event_type == "test.event"
    assert received_events[0].data == {"key": "value"}
```

### Linting and Formatting

The project uses several tools to ensure code quality:

```bash
# Format code with Black
black app tests

# Sort imports with isort
isort app tests

# Run Ruff linter
ruff check app tests

# Run mypy type checking
mypy app tests
```

### Database Migrations

When you make changes to the database models, you need to create a new migration:

```bash
# Create a migration using the Makefile
make revision MSG="description of changes"

# Or directly with Alembic
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head
```

## Adding New Features

### Adding a New API Endpoint

1. Create a new file in the `app/api/` directory or add to an existing one:

   ```python
   # app/api/workspaces.py
   from fastapi import APIRouter, Depends, HTTPException
   from typing import List
   from app.database.connection import get_db
   from app.database.models import Workspace
   from app.components.security_manager import get_current_user

   router = APIRouter()

   @router.get("/")
   async def list_workspaces(user = Depends(get_current_user), db = Depends(get_db)):
       """List workspaces for the current user"""
       workspaces = db.query(Workspace).filter(Workspace.user_id == user.id).all()
       return {"workspaces": workspaces}
   ```

2. Include the router in the main application (`app/main.py`):

   ```python
   from app.api import workspaces

   app.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
   ```

### Implementing a New Domain Expert Interface

1. Define the interface in `app/interfaces/`:

   ```python
   # app/interfaces/code_assistant.py
   from abc import ABC, abstractmethod
   from typing import Dict, Any, List

   class CodeAssistantInterface(ABC):
       @abstractmethod
       async def generate_code(self, prompt: str, language: str) -> str:
           """Generate code based on a prompt"""
           pass

       @abstractmethod
       async def review_code(self, code: str, language: str) -> List[Dict[str, Any]]:
           """Review code and provide suggestions"""
           pass
   ```

2. Implement the interface in `app/components/`:

   ```python
   # app/components/code_assistant.py
   from app.interfaces.code_assistant import CodeAssistantInterface

   class CodeAssistant(CodeAssistantInterface):
       async def generate_code(self, prompt: str, language: str) -> str:
           # Implementation
           pass

       async def review_code(self, code: str, language: str) -> List[Dict[str, Any]]:
           # Implementation
           pass
   ```

## Deployment

### Building Docker Images

```bash
# Build using the provided Dockerfile
docker build -f docker/Dockerfile.non_root -t cortex-core:latest .

# Run the container
docker run -p 4000:4000 \
    -v $(pwd)/proxy_config.yaml:/app/config.yaml \
    -e DATABASE_URL="postgresql://username:password@host:port/dbname" \
    -e SECURITY_JWT_SECRET="your-jwt-secret" \
    -e SECURITY_ENCRYPTION_KEY="your-encryption-key" \
    cortex-core:latest
```

### Using Docker Compose

A `docker-compose.yml` file is provided for local development:

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Continuous Integration

The project uses CircleCI for continuous integration. The configuration is defined in `.circleci/config.yml`.

The CI pipeline runs:

1. Linting checks (black, isort, ruff)
2. Type checking (mypy)
3. Unit tests
4. Integration tests

## Contributing Guidelines

1. Fork the repository and create a feature branch
2. Make your changes following the code style guidelines
3. Write tests for your changes
4. Ensure all tests pass and you've added appropriate documentation
5. Submit a pull request with a clear description of your changes

## Best Practices

- Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- Use type hints for all function arguments and return values
- Document all public classes and methods with docstrings
- Write unit tests for new functionality
- Keep components modular and focused on a single responsibility
- Use dependency injection for better testability

## Core Development Principles

### Clean Implementation Over Backward Compatibility

**Important**: This codebase is currently in pre-production development. Therefore:

- **No Backward Compatibility Required**: When refactoring or redesigning components, do not maintain backward compatibility with previous implementations.
- **No Migration Path Needed**: Since the codebase and database are not yet in production use, you don't need to provide migration paths between versions.
- **Focus on Clean Design**: Prioritize creating clean, well-designed APIs and components without worrying about preserving old patterns or interfaces.
- **Delete Unused Code**: Remove deprecated or unused code entirely rather than keeping it around for compatibility.

This principle allows us to move quickly and maintain a clean codebase during initial development.

### Layered Architecture

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

This project follows a layered architecture to maintain separation of concerns:

- **API Layer**: Handles HTTP requests/responses, validation, authentication
- **Service Layer**: Contains business logic, orchestrates operations
- **Repository Layer**: Abstracts data access patterns
- **Data Layer**: ORM models, database connections

### Repository Pattern

We use the Repository Pattern to abstract database access:

```python
# Definition (interfaces)
class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        pass
        
    @abstractmethod
    def create(self, email: str, name: str) -> User:
        pass

# Implementation (concrete classes)
class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
        
    def create(self, email: str, name: str) -> User:
        user = User(email=email, name=name)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

# Factory function for dependency injection
def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return SQLAlchemyUserRepository(db)
```

### Benefits of Repository Pattern

1. **Separation of Concerns**: API endpoints focus on HTTP interaction, while repositories handle data operations
2. **Testability**: Repositories can be mocked for testing API endpoints without complex DB mocking
3. **Flexibility**: Allows for easier DB backend changes in the future
4. **Consistency**: Provides consistent data access patterns across the codebase

### Common Anti-patterns to Avoid

1. **Mixing SQL queries with business logic**: Keep data access contained within repositories
2. **Direct JSON string manipulation in API layer**: Handle serialization consistently
3. **Heavy database logic in API handlers**: Move this to repositories
4. **Complex mocking in tests**: Mock at interface boundaries, not implementation details

### Testing with Repository Pattern

```python
# Create a mock repository
mock_repo = MagicMock(spec=UserRepository)
mock_repo.get_by_id.return_value = User(id="123", name="Test User")

# Patch the repository dependency
with patch('app.api.users.get_user_repository', return_value=mock_repo):
    response = client.get("/users/123")
    assert response.status_code == 200
    assert response.json()["name"] == "Test User"
```

### Code Review Checklist

Before approving a PR, check:

- [ ] Is business logic separate from data access?
- [ ] Are JSON manipulations encapsulated in appropriate layers?
- [ ] Are tests mocking at interface boundaries, not implementation details?
- [ ] Is there proper error handling between layers?
- [ ] Is there clear separation between API handlers and business logic?
- [ ] Are database operations contained within repositories?

### Refactoring Strategy

When refactoring existing code:

1. **Identify better designs**: Think about the cleanest possible implementation without constraints
2. **Make clean breaks**: Don't worry about maintaining backward compatibility 
3. **Extract repositories and services**: Move data access into repository classes and business logic into service classes
4. **Implement interfaces**: Define clear interfaces between components
5. **Update tests**: Rewrite tests to target public interfaces, not implementation details
6. **Remove old implementations**: Delete deprecated code completely rather than leaving it for compatibility

Remember: This is a pre-production codebase, so prioritize clean implementation over compatibility.
