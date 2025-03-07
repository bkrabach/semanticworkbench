# Cortex Chat

Cortex Chat is a modern React-based chat interface for interacting with the Cortex Core backend. It provides a real-time, conversational user interface with support for streaming responses, tool executions, and markdown rendering.

## Features

- Real-time chat interface with streaming responses
- Markdown rendering with syntax highlighting
- Tool execution result display
- Authentication with token-based system
- Workspace and conversation management
- Server-Sent Events (SSE) for real-time updates

## Technology Stack

- **Frontend Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **UI Library**: Fluent UI (@fluentui/react-components)
- **Data Fetching**: TanStack React Query 
- **Real-time Communication**: Server-Sent Events (SSE)
- **Routing**: React Router
- **Package Management**: pnpm

## Getting Started

### Prerequisites

- Node.js (v18 or later)
- pnpm
- Running Cortex Core backend service

### Installation

```bash
# Install dependencies
pnpm install
```

### Development

```bash
# Start development server
pnpm dev
```

The development server will start at `http://localhost:5173` by default.

### Build

```bash
# Build for production
pnpm build
```

### Lint

```bash
# Run ESLint
pnpm lint
```

### Type Check

```bash
# Run TypeScript type checking
pnpm type-check
```

## Project Structure

```
/src
  /api                 # API client and types
    /hooks             # React Query hooks
    client.ts          # Base API client
    types.ts           # TypeScript interfaces
  /components          # React components
    /auth              # Authentication components
    /common            # Shared components
    /conversation      # Conversation UI
    /layout            # Layout components
    /workspace         # Workspace management
  /context             # React context providers
  /hooks               # Custom React hooks
  /utils               # Utility functions
  App.tsx              # Main application component
  main.tsx             # Application entry point
```

## Documentation

For more detailed documentation, see the [docs](./docs/) directory:

- [Architecture Overview](./docs/ARCHITECTURE_OVERVIEW.md)
- [Component Relationships](./docs/COMPONENT_RELATIONSHIPS.md)
- [API Integration](./docs/API_INTEGRATION.md)
- [Development Guide](./docs/DEVELOPMENT.md)
- [Contributing Guide](./CONTRIBUTING.md)

## Backend Integration

Cortex Chat connects to the Cortex Core backend service which runs on `http://127.0.0.1:8000` by default. For details on the backend API, see:

- [Client API Reference](../cortex-core/docs/CLIENT_API_REFERENCE.md)
- [Client Integration Guide](../cortex-core/docs/CLIENT_INTEGRATION_GUIDE.md)
- [Client Quickstart](../cortex-core/docs/CLIENT_QUICKSTART.md)

## Platform Architecture

Cortex Chat is part of the broader Cortex Platform, which follows a central AI core with adaptive ecosystem model. The chat interface represents one of multiple potential input/output modalities in the platform's ecosystem. For more details on the platform architecture, see:

- [Platform Overview](../cortex-platform/docs/PLATFORM_OVERVIEW.md)
- [Codebase Structure](../cortex-platform/docs/CODEBASE_STRUCTURE.md)