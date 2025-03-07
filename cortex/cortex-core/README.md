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
```

Cortex Core uses:

- **REST API** for standard request/response interactions with clients
- **Server-Sent Events (SSE)** for real-time, server-to-client communication
- **Model Context Protocol (MCP)** for internal communication between Cortex Core and specialized services or domain experts

## Real-time Communication

Cortex Core uses Server-Sent Events (SSE) for real-time communication with client applications. This enables:

- Instant notifications of new messages
- Live updates for conversation and workspace changes
- Typing indicators and other real-time status updates

See the [CLIENT_INTEGRATION_GUIDE.md](./CLIENT_INTEGRATION_GUIDE.md) for details on implementing SSE in client applications.

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

## Documentation

For more detailed information, refer to:

- [Development Guide](./DEVELOPMENT.md) - For contributors and developers
- [API Reference](./API_REFERENCE.md) - API endpoint documentation
- [Configuration](./CONFIGURATION.md) - Detailed configuration options
- [Client Integration Guide](./CLIENT_INTEGRATION_GUIDE.md) - Guide for client application developers

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
