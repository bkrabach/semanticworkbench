# Cortex Chat Client

A modern, modular client implementation for the Cortex Core platform. This client provides a streamlined interface for conversational AI interactions using Cortex Core's API and Server-Sent Events system.

## Overview

Cortex Chat Client provides:
- Real-time communication with Cortex Core via SSE
- Multi-modal conversation support
- Workspace and conversation management
- Enterprise-grade authentication
- Extensible architecture for custom integrations

## Current Implementation Status

The project is currently in the initial scaffolding phase. We have implemented:

- Project structure and configuration
- Core services (API, Authentication, SSE)
- Type definitions and interfaces
- Basic UI with FluentUI React Components
- Authentication flow

See the [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) for details on current status and upcoming work.

## Getting Started

### Prerequisites
- Node.js v18+
- pnpm v8+
- Modern web browser
- Cortex Core instance running (default: http://localhost:8000)

### Quick Start
1. Clone this repository
2. Install dependencies:
   ```bash
   pnpm install
   ```
3. Start the development server:
   ```bash
   pnpm dev
   ```
4. Open http://localhost:5000 in your browser

## Development Commands

- **Development**: `pnpm dev`
- **Build**: `pnpm build`
- **Lint**: `pnpm lint`
- **Format**: `pnpm format`
- **Type Check**: `pnpm typecheck`
- **Test**: `pnpm test`

## Project Structure

```
src/
├── components/    # UI components
├── services/      # Service layer (API, Auth, SSE)
├── store/         # State management
├── hooks/         # Custom React hooks
├── utils/         # Utility functions
├── types/         # TypeScript type definitions
└── styles/        # Global styles
```

## Documentation

Comprehensive documentation is available in the `docs` directory:

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [API Integration](docs/API_INTEGRATION.md)
- [Component Reference](docs/COMPONENTS.md)
- [Testing Guide](docs/TESTING.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [Architecture Decisions](docs/adr/)

## Current Status

This project is in active development and considered pre-production. Breaking changes may occur between versions as we refine the architecture and feature set.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.