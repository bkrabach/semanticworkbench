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
- UV
- PostgreSQL

### Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd cortex-core
```

2. Set up a virtual environment & install dependencies:

```bash
make
```

3. Activate the virtual environment:

```bash
source .venv/bin/activate # Linux, on Windows use .venv\Scripts\activate
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
