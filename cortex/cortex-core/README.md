# Cortex Core

Cortex Core is a centralized API service that manages communication between input clients and output clients, providing a clean, reliable channel for message flow with proper data isolation between users.

## Overview

Cortex Core provides the foundation for the Semantic Workbench platform, enabling:

- Input processing from multiple client types
- Real-time output streaming via Server-Sent Events (SSE)
- User authentication and data partitioning
- Workspace and conversation management
- Event-driven architecture for internal communication

This implementation delivers a complete Phase 1 system with in-memory storage, allowing immediate client application development while establishing a solid foundation for future enhancements.

## Key Features

- **FastAPI Application**: High-performance async framework with automatic OpenAPI documentation
- **JWT Authentication**: Secure token-based authentication
- **Server-Sent Events**: Real-time streaming of output to clients
- **Event Bus System**: Loose coupling between components with pub/sub pattern
- **In-Memory Storage**: Ephemeral storage with proper user partitioning
- **Workspace Management**: Basic organization of conversations
- **Conversation Management**: Grouping related messages together
- **Type Safety**: Comprehensive type annotations throughout the codebase
- **Comprehensive Testing**: Unit and integration tests for all components

## API Endpoints

### Authentication
- `POST /auth/login`: Authenticate and receive JWT token
- `GET /auth/verify`: Verify JWT token validity

### Input/Output
- `POST /input`: Receive input from clients
- `GET /output/stream`: Stream output to clients via SSE

### Configuration
- `POST /config/workspace`: Create a new workspace
- `GET /config/workspace`: List user's workspaces
- `POST /config/conversation`: Create a new conversation
- `GET /config/conversation`: List conversations in a workspace

## Getting Started

### Prerequisites

- Python 3.10+
- UV package manager

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd cortex-core
   ```

2. Set up the environment using the Makefile:
   ```bash
   make
   ```
   This will:
   - Create a virtual environment
   - Install all dependencies
   - Set up development tools

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

### Running the Server

Start the development server with:

```bash
make dev
```

Or directly with:

```bash
uv run uvicorn app.main:app
```

The server will be available at http://localhost:8000.

## Development

### Core Commands

- Run server: `make dev`
- Run tests: `python -m pytest`
- Run linting: `ruff check app tests`
- Run type checking: `mypy app tests`
- Run database migrations: `make migrate`
- Create new migration: `make revision MSG="description"`

### Adding New Features

1. Add appropriate test cases
2. Implement the feature
3. Run tests and type checking
4. Update documentation if necessary

## Client Integration

Integrating clients with Cortex Core involves two primary patterns:

1. **Input Clients**: Send data via HTTP POST to `/input` endpoint
2. **Output Clients**: Connect to `/output/stream` for Server-Sent Events

See [CLIENT_INTEGRATION.md](docs/CLIENT_INTEGRATION.md) for detailed examples and code samples.

## Documentation

- [Architecture Overview](docs/ARCHITECTURE_OVERVIEW.md): High-level system architecture
- [API Reference](docs/API_REFERENCE.md): Detailed API documentation
- [Development Guide](docs/DEVELOPMENT_GUIDE.md): Guide for developers
- [Testing Guide](docs/TESTING_GUIDE.md): Testing approach and examples
- [Client Integration](docs/CLIENT_INTEGRATION.md): Guide for client developers
- [Event Bus](docs/EVENT_BUS.md): Detailed documentation of the event system
- [Implementation Philosophy](docs/IMPLEMENTATION_PHILOSOPHY.md): Core design principles

## Testing

Run the test suite with:

```bash
python -m pytest
```

For more detailed output:

```bash
python -m pytest -v
```

For specific test modules:

```bash
python -m pytest tests/test_event_bus.py
```

## Project Structure

```
cortex-core/
├── app/                    # Main application code
│   ├── __init__.py
│   ├── main.py             # FastAPI app and startup
│   ├── api/                # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py         # Authentication endpoints
│   │   ├── input.py        # Input endpoint
│   │   ├── output.py       # Output streaming endpoint
│   │   └── config.py       # Configuration endpoints
│   ├── core/               # Core components
│   │   ├── __init__.py
│   │   ├── event_bus.py    # Event bus implementation
│   │   └── storage.py      # In-memory storage
│   ├── models/             # Data models
│   │   ├── __init__.py
│   │   ├── base.py         # Base models
│   │   ├── domain.py       # Domain models
│   │   └── api/            # API models
│   │       ├── __init__.py
│   │       ├── request.py  # Request models
│   │       └── response.py # Response models
│   └── utils/              # Utilities
│       ├── __init__.py
│       └── auth.py         # Authentication utilities
├── docs/                   # Documentation
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── test_api.py         # API tests
│   ├── test_event_bus.py   # Event bus tests
│   └── test_integration.py # Integration tests
├── Makefile                # Build and development commands
├── pyproject.toml          # Project configuration
└── requirements.txt        # Project dependencies
```

## Future Development

Phase 1 focuses on a functional input/output system with in-memory storage. Future phases will add:

1. **Phase 2**: Persistent storage (SQL database) and enhanced configuration API
2. **Phase 3**: MCP Protocol and service architecture
3. **Phase 4**: Distributed services
4. **Phase 5**: Production hardening

## License

[License Information]

## Contact

[Contact Information]