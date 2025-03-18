# Cortex Core

The central orchestration engine for the Cortex Platform, designed to be modular, extensible, and adaptive.

## Overview

Cortex Core is the central AI orchestration system that coordinates interactions between users, memory systems, domain expert entities, and external integrations. It's designed as a modular platform where specialized AI components can be integrated through well-defined interfaces.

The Cortex Core is responsible for:

- **Session Management**: Handling user sessions and workspaces
- **Unified Context**: Maintaining and enriching contextual understanding across all interactions
- **Task Orchestration**: Routing incoming requests and delegating specialized tasks
- **LLM Integration**: Processing messages with language models from various providers
- **Multi-Modal Interactions**: Supporting various input/output modalities including chat, voice, and more
- **External Integrations**: Connecting with other tools and services using the MCP protocol

## Current Scope

The current implementation includes:

- **REST API** for standard request/response interactions with clients
- **SSE System** for real-time, server-to-client communication
- **CortexRouter** for message processing and routing
- **LLM Integration** using LiteLLM for multiple providers
- **MCP Framework** for domain expert integration
- **Whiteboard Memory** implementation
- **Domain-Driven Repository Architecture** with clean separation of concerns

See the [Implementation Status](./docs/IMPLEMENTATION_STATUS.md) document for a detailed breakdown of implemented and planned components.

## Architecture

The Cortex Core follows a modular architecture with these key components:

```mermaid
graph TD
    subgraph "Clients"
        Web[Web Applications]
        Mobile[Mobile Apps]
        Desktop[Desktop Apps]
    end

    subgraph "API Layer"
        REST[REST API]
        SSE[Server-Sent Events]
    end

    subgraph "Cortex Core"
        API[API Gateway]
        SM[Session Manager]
        DI[Dispatcher]
        CM[Context Manager]
        IH[Integration Hub]
        WM[Workspace Manager]
        SEC[Security Manager]
    end

    subgraph "Inter-Service Communication"
        MCP[Model Context Protocol]
    end

    subgraph "External Services"
        Domain[Domain Experts]
        Tools[External Tools]
    end

    Web --> REST & SSE
    Mobile --> REST & SSE
    Desktop --> REST & SSE

    REST & SSE --> API
    API --> SM & DI & CM & IH & WM & SEC

    IH --> MCP
    MCP --> Domain & Tools
    
    %% Style to show implemented vs planned components
    style Domain stroke-dasharray: 5 5
    style Tools stroke-dasharray: 5 5
    style CM stroke-dasharray: 5 5
```

Cortex Core uses:

- **REST API** for standard request/response interactions with clients
- **Server-Sent Events (SSE)** for real-time, server-to-client communication
- **LiteLLM** for unified access to multiple LLM providers
- **Model Context Protocol (MCP)** for internal communication between Cortex Core and specialized services or domain experts

## Real-time Communication

Cortex Core uses Server-Sent Events (SSE) for real-time communication with client applications. This enables:

- Instant notifications of new messages
- Live updates for conversation and workspace changes
- Typing indicators and other real-time status updates

See the [CLIENT_INTEGRATION_GUIDE.md](./docs/CLIENT_INTEGRATION_GUIDE.md) for details on implementing SSE in client applications.

## Roadmap

Our development roadmap currently focuses on:

1. Implementing advanced memory systems (JAKE or equivalent)
2. Building domain expert integrations
3. Enhancing context management and synthesis
4. Adding tool calling for LLM interactions
5. Supporting additional modalities

See the [Implementation Status](./docs/IMPLEMENTATION_STATUS.md) document for a detailed timeline and priorities.

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
   
   # LLM Configuration
   LLM_DEFAULT_MODEL="openai/gpt-3.5-turbo"
   # LLM_USE_MOCK=true  # Uncomment for mock mode
   # Provider API keys
   OPENAI_API_KEY="your-openai-api-key"
   # ANTHROPIC_API_KEY="your-anthropic-api-key"
   ```

4. Run database migrations:

   ```bash
   uv run alembic upgrade head
   ```

5. Start the server:
   ```bash
   uv run uvicorn app.main:app
   ```

## Development

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific tests
python -m pytest tests/api/test_auth.py

# Check architecture integrity
python -m pytest tests/architecture/test_layer_integrity.py
```

### Architecture Validation

To check for architecture boundary violations:

```bash
./check_imports.sh
```

This script validates that SQLAlchemy models are properly confined to repositories and don't leak into services, API endpoints, or components.

## Documentation

For more detailed information, refer to:

- [Implementation Status](./docs/IMPLEMENTATION_STATUS.md) - Current implementation status and roadmap
- [Development Guide](./docs/DEVELOPMENT.md) - For contributors and developers
- [Architecture](./docs/ARCHITECTURE.md) - System design and principles
- [Domain Experts](./docs/DOMAIN_EXPERTS.md) - Domain expert entities documentation
- [SSE System](./docs/SSE.md) - Server-Sent Events implementation
- [Router](./docs/ROUTER.md) - CortexRouter documentation
- [Memory System](./docs/MEMORY_SYSTEM.md) - Memory system architecture
- [API Reference](./docs/API_REFERENCE.md) - API endpoint documentation
- [Configuration](./docs/CONFIGURATION.md) - Detailed configuration options
- [Client Integration Guide](./docs/CLIENT_INTEGRATION_GUIDE.md) - Guide for client application developers
- [Testing Guide](./docs/TESTING.md) - Best practices for testing
- [LLM Integration](./docs/LLM_INTEGRATION.md) - Guide to LLM integration with LiteLLM
- [Terminology](./docs/TERMINOLOGY.md) - Consistent terminology reference
- [AI Assistant Guide](./docs/AI_ASSISTANT_GUIDE.md) - Guide for AI code assistants working with this codebase