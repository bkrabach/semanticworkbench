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

- Node.js 16+
- PostgreSQL 13+
- Redis 6+

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/cortex-core.git
   cd cortex-core
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env` file with your configuration:
   ```
   # Database
   DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cortex?schema=public"
   
   # Redis
   REDIS_HOST="localhost"
   REDIS_PORT=6379
   
   # Security
   JWT_SECRET="your-jwt-secret"
   ENCRYPTION_KEY="your-encryption-key"
   
   # Server
   PORT=4000
   HOST="localhost"
   LOG_LEVEL="info"
   ```

4. Run database migrations:
   ```bash
   npm run migrate
   ```

5. Start the server:
   ```bash
   npm run dev
   ```

## Key Features

### Workspace & Conversation Management

Cortex Core organizes all user interactions within workspaces, which contain multiple conversations. Each conversation represents a specific thread of interactions within a particular modality (chat, voice, etc.).

### Memory System

The initial implementation uses a "whiteboard" memory system that captures and synthesizes context from user interactions. This will later be replaced with the more sophisticated JAKE memory system, but the interface remains consistent.

### Domain Expert Delegation

Cortex Core can delegate specialized tasks to Domain Expert entities - autonomous modules with deep expertise in specific domains like code assistance or research. The system handles delegation, monitoring, and result integration.

### Multi-Modal Support

Users can interact with Cortex through various modalities:

- **Chat**: Text-based conversations
- **Voice**: Speech-based interactions
- **Canvas**: Visual inputs and outputs
- **App Integrations**: Direct integration with applications like VS Code or Word

### MCP Integration

The Model Context Protocol (MCP) is used to connect the Cortex Core with external tools and services, providing a standardized way to exchange context and execute commands.

## Development

### Project Structure

```
src/
├── components/    # Core components
├── interfaces/    # Interface definitions
├── utils/         # Utility functions
├── database/      # Database access
├── cache/         # Redis cache
├── api/           # API endpoints
├── modalities/    # Input/output modalities
├── config.ts      # Configuration
└── index.ts       # Main entry point
```

### Running Tests

```bash
npm test
```

### Linting

```bash
npm run lint
```

### Building for Production

```bash
npm run build
```

## API Documentation

When running in development mode, API documentation is available at http://localhost:4000/docs.

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
