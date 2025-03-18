# Cortex Core

Cortex Core is the central orchestration engine for the Cortex Platform. It provides a FastAPI-based backend with authentication, real-time updates via SSE, and integration with AI services.

## Features

- User authentication with JWT
- Workspace management with role-based access control
- Conversation and message handling
- Real-time updates via Server-Sent Events (SSE)
- Integration with LLMs via LiteLLM
- Domain experts via MCP protocol
- Memory system for context management

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL

### Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd cortex-core
```

2. Set up a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your settings
```

5. Run database migrations:

```bash
uv run alembic upgrade head
```

### Running the Server

```bash
uv run -m app.main
```

The server will be available at http://localhost:8000.

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Running Tests

```bash
python -m pytest
```

### Linting and Type Checking

```bash
ruff check app tests
mypy app tests
```

### Creating Database Migrations

```bash
make revision MSG="description"
```

## Architecture

Cortex Core follows a domain-driven repository architecture with:

1. **API Layer**: FastAPI endpoints
2. **Service Layer**: Business logic
3. **Repository Layer**: Data access
4. **Model Layer**: Data models (Domain, API)
5. **Component Layer**: Core system components

For detailed architecture information, see the [documentation](./docs/).

## License

[License details]