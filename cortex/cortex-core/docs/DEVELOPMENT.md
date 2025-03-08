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
