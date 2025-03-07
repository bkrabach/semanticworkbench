# Cortex Core

Cortex Core is an AI-powered assistance framework built with Python, FastAPI, and modern asynchronous programming patterns.

## Features

- 🚀 **Modular Architecture**: Component-based design for easy extension and customization
- 🔄 **Asynchronous Processing**: Built with Python's asyncio for high performance
- 🧠 **Context Awareness**: Sophisticated context management system
- 🔒 **Security First**: Robust security policies and authentication
- 💾 **Flexible Storage**: Support for multiple storage backends
- 🌐 **API-Driven**: RESTful API with OpenAPI documentation
- 🔌 **Integration Hub**: Connect to external services and APIs

## Requirements

- Python 3.9+
- Redis (for caching)
- SQLite or PostgreSQL

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/example/cortex-core.git
cd cortex-core/python

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Or for development:
pip install -e ".[dev,test]"
```

### Using pip

```bash
pip install cortex-core
```

## Configuration

Cortex Core uses environment variables for configuration. Copy the example environment file and adjust as needed:

```bash
cp .env.example .env
```

Key configuration options:

| Variable       | Description                                      | Default                                |
| -------------- | ------------------------------------------------ | -------------------------------------- |
| `ENVIRONMENT`  | Deployment environment (development, production) | `development`                          |
| `DEBUG`        | Enable debug mode                                | `False`                                |
| `LOG_LEVEL`    | Logging level                                    | `INFO`                                 |
| `HOST`         | Server host                                      | `0.0.0.0`                              |
| `PORT`         | Server port                                      | `8000`                                 |
| `DATABASE_URL` | Database connection string                       | `sqlite+aiosqlite:///./data/cortex.db` |
| `REDIS_URL`    | Redis connection string                          | `redis://localhost:6379/0`             |
| `SECRET_KEY`   | Secret key for token signing                     | `None` (must be set)                   |
| `CORS_ORIGINS` | Allowed CORS origins                             | `["http://localhost:3000"]`            |

## Running the Application

```bash
# Using the CLI
cortex-core

# Or directly with uvicorn
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000 with OpenAPI documentation at http://localhost:8000/api/docs.

## Architecture

Cortex Core is built around a modular component architecture:

```
app/
├── api/              # FastAPI routes
├── components/       # Core components
├── database/         # Database models and connection
├── interfaces/       # Abstract interfaces
├── modalities/       # Modality implementations
├── schemas/          # Pydantic schemas
└── utils/            # Utility functions
```

### Key Components

- **Context Manager**: Manages conversation context and memory
- **Dispatcher**: Routes messages to appropriate handlers
- **Integration Hub**: Manages external service integrations
- **Security Manager**: Enforces security policies
- **Session Manager**: Handles user sessions
- **Workspace Manager**: Manages user workspaces
- **Whiteboard Memory**: Implements memory system

## API Endpoints

The API provides several endpoints for interaction:

- **Authentication**: `/api/auth/*`
- **Health Checks**: `/api/health`
- **Messages**: `/api/messages`
- **Memory**: `/api/memory`

## Development

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app
```

### Code Formatting

```bash
# Format code
black app tests

# Sort imports
isort app tests

# Lint code
ruff app tests
```

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality:

```bash
pre-commit install
```

## Database Migrations

We use Alembic for database migrations:

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Run migrations
alembic upgrade head
```

## Extending Cortex Core

### Adding a New Component

1. Create a new file in `app/components/`
2. Implement the component using the established patterns
3. Register the component in `app/main.py`

### Adding a New API Endpoint

1. Create a new router in `app/api/`
2. Implement the endpoint handlers
3. Include the router in `app/main.py`

## License

[MIT License](LICENSE)
