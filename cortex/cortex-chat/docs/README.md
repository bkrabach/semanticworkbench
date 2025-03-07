# Cortex Chat Documentation

_Date: 2025-03-07_

This directory contains technical documentation for the Cortex Chat frontend application, which is part of the broader Cortex Platform ecosystem.

## Documentation Index

### Architecture & Design

- [Architecture Overview](./ARCHITECTURE_OVERVIEW.md) - High-level overview of the application architecture
- [Component Relationships](./COMPONENT_RELATIONSHIPS.md) - Detailed component relationships and data flow
- [API Integration](./API_INTEGRATION.md) - How the frontend integrates with the backend API

### Developer Resources

- [Development Guide](./DEVELOPMENT.md) - Detailed technical information for developers

## Related Documentation

### Cortex Core Backend

For documentation about the backend API that this frontend integrates with, see the Cortex Core documentation:

- [Client API Reference](../../cortex-core/docs/CLIENT_API_REFERENCE.md)
- [Client Integration Guide](../../cortex-core/docs/CLIENT_INTEGRATION_GUIDE.md)
- [Client Quickstart](../../cortex-core/docs/CLIENT_QUICKSTART.md)

### Platform Architecture

For broader context on the Cortex Platform architecture and vision, see:

- [Platform Overview](../../cortex-platform/docs/PLATFORM_OVERVIEW.md)
- [Codebase Structure](../../cortex-platform/docs/CODEBASE_STRUCTURE.md)

## Development Quickstart

Cortex Chat is a React application built with:

- React 19
- TypeScript
- Vite
- Fluent UI
- React Query
- React Router

To start the development server:

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev
```

To build for production:

```bash
pnpm build
```

To run linting:

```bash
pnpm lint
```

To type-check:

```bash
pnpm type-check
```

For more detailed development information, see the [project README](../README.md) and the [Contributing Guide](../CONTRIBUTING.md).