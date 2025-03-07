# Cortex Core

The central orchestration engine for the Cortex Platform, designed to be modular, extensible, and adaptive.

## Overview

Cortex Core is the central AI orchestration system that coordinates interactions between users, memory systems, domain expert entities, and external integrations. It's designed as a modular platform where specialized AI components can be integrated through well-defined interfaces.

The Cortex Core is responsible for:

- **Session Management**: Handling user sessions and workspaces
- **Unified Context**: Maintaining and enriching contextual understanding across all interactions
- **Task Orchestration**: Routing incoming requests and delegating specialized tasks
- **Multi-Modal Interactions**: Supporting various input/output modalities including chat, voice, and more
- **External Integrations**: Connecting with other tools and services using the MCP protocol

## Architecture

The Cortex Core follows a modular architecture with these key components:

- **Session Manager**: Handles user sessions and workspace association
- **Dispatcher**: Routes incoming requests to appropriate processing pathways
- **Context Manager**: Interfaces with the memory system for context retrieval/update
- **Integration Hub**: Facilitates communication with external tools/services
- **Workspace Manager**: Manages workspaces and conversations
- **Security Manager**: Handles authentication, authorization, and data security

These components interact through well-defined interfaces that enable parallel development and future extensibility.

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL 13+ (or SQLite for development)
- Redis 6+ (optional, falls back to in-memory cache)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/cortex-core.git
   cd cortex-core
   ```

2. Install dependencies using uv:

   ```bash
   uv venv
   uv pip install -e .
   ```

3. Create a `.env` file with your configuration:

   ```
   # Database
   DATABASE_URL="sqlite:///./cortex.db"
   # For PostgreSQL
   # DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cortex"

   # Redis
   REDIS_HOST="localhost"
   REDIS_PORT=6379

   # Security
   SECURITY_JWT_SECRET="your-jwt-secret"
   SECURITY_ENCRYPTION_KEY="your-encryption-key"

   # Server
   SERVER_PORT=4000
   SERVER_HOST="localhost"
   SERVER_LOG_LEVEL="info"
   ```

4. Run database migrations:

   ```bash
   uv run alembic upgrade head
   ```

5. Start the server:
   ```bash
   uv run -m app.main
   ```

## Development

### Project Structure

```
cortex_core/
├── alembic/              # Database migrations
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration
│   ├── components/       # Core components
│   ├── interfaces/       # Interface definitions
│   ├── api/              # API endpoints
│   ├── modalities/       # Input/output modalities
│   ├── database/         # Database models and connection
│   ├── cache/            # Redis cache
│   └── utils/            # Utility functions
├── logs/                 # Log files
├── tests/                # Test cases
├── .env                  # Environment variables
└── pyproject.toml        # Project metadata and dependencies
```

### Running Tests

```bash
uv run pytest
```

### Linting and Formatting

```bash
uv run black app tests
uv run isort app tests
uv run ruff check app tests
```

## API Documentation

When running in development mode, API documentation is available at http://localhost:4000/docs.

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
