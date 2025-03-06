# Cortex Core

A modern and extensible AI routing and conversation platform built to facilitate complex AI interactions with real-time capabilities, tool usage, and memory management.

## Overview

Cortex Core serves as a central hub for AI interactions, providing:

- **Conversation Management**: Process and manage multi-turn conversations with advanced AI models
- **Tool Integration**: Seamless integration with external tools via MCP servers
- **Real-time Updates**: Server-Sent Events (SSE) for immediate updates to clients
- **Memory System**: Contextual awareness and recall across conversation sessions
- **Multi-user Support**: Clean isolation between different users' data and conversations

## Architecture

Cortex Core follows a modular design with clear component separation:

```
cortex_core/
├── api/              # FastAPI routes and endpoints
├── core/             # Core components
│   ├── auth.py       # Authentication and session management
│   ├── config.py     # Configuration management
│   ├── conversation.py # Conversation handling
│   ├── llm.py        # LLM integration
│   ├── mcp_client.py # MCP client for tool execution
│   ├── memory.py     # Memory integration
│   ├── router.py     # Message routing
│   └── sse.py        # Real-time updates via SSE
├── db/               # Database models and connection
│   ├── database.py   # Database setup
│   └── models.py     # SQLAlchemy models
├── models/           # Pydantic models
│   └── schemas.py    # Data schemas
├── utils/            # Utility functions
└── main.py           # Application entry point
```

## Installation

```bash
# Install uv if not already installed
pip install uv

# Create and activate a virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package with development dependencies
uv pip install -e ".[dev]"
```

> **Note:** This project uses `uv` for dependency management. Do not use pip directly.

## Configuration

Create a `.env` file in the project root with the following variables:

```
# Application settings
APP_NAME=Cortex Core
APP_VERSION=0.1.0
DEBUG=true
HOST=127.0.0.1
PORT=8000

# Database settings
DATABASE_URL=sqlite:///cortex.db

# LLM API settings
OPENAI_API_KEY=your_openai_api_key
DEFAULT_MODEL=gpt-4o

# Authentication settings
AUTH_SECRET_KEY=generate_a_secure_random_key
```

## Running the Application

```bash
# Run the development server
uv run uvicorn cortex_core.main:app --reload

# Or use the built-in command
uv run python -m cortex_core
```

The API will be available at http://127.0.0.1:8000 and the interactive documentation at http://127.0.0.1:8000/docs.

## Development

### Code Quality

```bash
# Run formatter
uv run black .

# Sort imports
uv run isort .

# Run linter
uv run flake8

# Type checking
uv run mypy
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=cortex_core --cov-report=term-missing
```

## API Endpoints

### Authentication

- `POST /api/validate-session` - Validate a session token

### Conversations

- `GET /api/conversations` - List all conversations for a user
- `POST /api/conversations` - Create a new conversation
- `GET /api/conversations/{conversation_id}` - Get a specific conversation
- `DELETE /api/conversations/{conversation_id}` - Delete a conversation

### Messages

- `GET /api/conversations/{conversation_id}/messages` - Get messages in a conversation
- `POST /api/conversations/{conversation_id}/messages` - Add a message to a conversation

### Real-time Updates

- `GET /api/sse/conversations/{conversation_id}` - SSE connection for conversation updates

## MCP Integration

Cortex Core integrates with MCP servers for tool execution. To register a new MCP server:

```python
from cortex_core.models.schemas import MCPServer
server = MCPServer(
    name="Example MCP Server",
    url="http://localhost:8001"
)
await mcp_client.register_server(server)
```

## License

MIT
