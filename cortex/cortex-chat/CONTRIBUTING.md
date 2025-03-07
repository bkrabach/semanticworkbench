# Contributing to Cortex Chat

_Date: 2025-03-07_

This document provides guidelines and instructions for contributing to the Cortex Chat frontend project.

## Getting Started

### Prerequisites

- Node.js (v18 or later)
- pnpm
- A running Cortex Core backend instance

### Development Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd cortex/cortex-chat
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

3. Start the development server:
   ```bash
   pnpm dev
   ```

## Project Structure

The Cortex Chat project follows a feature-based structure:

```
/src
  /api                 # API client and types
    /hooks             # React Query hooks
  /components          # React components organized by feature
    /auth              # Authentication components
    /common            # Shared components
    /conversation      # Conversation UI components
    /layout            # Layout components
    /workspace         # Workspace management
  /context             # React context providers
  /hooks               # Custom React hooks
  /utils               # Utility functions
```

## Development Guidelines

### Code Style

- Use consistent formatting with ESLint and Prettier
- Follow TypeScript best practices with proper type definitions
- Use React hooks for state and effects
- Prefer functional components over class components

### Component Best Practices

- Create small, focused components with single responsibilities
- Use Fluent UI components for consistent look and feel
- Follow the component naming conventions:
  - Component files: PascalCase (e.g., `MessageInput.tsx`)
  - Hook files: camelCase with 'use' prefix (e.g., `useMessages.ts`)
  - Utility files: camelCase (e.g., `formatDate.ts`)

### State Management

- Use React Query for server state (API data)
- Use React Context for global application state
- Use local component state for UI-specific state
- Minimize prop drilling by using context appropriately

### Adding New Features

1. **Plan**: Understand how your feature fits within the existing architecture
2. **Components**: Create or modify components needed for the feature
3. **API Integration**: Update or add API hooks if needed
4. **Connect**: Integrate with the appropriate parts of the application
5. **Test**: Ensure your feature works as expected
6. **Document**: Update documentation to reflect your changes

## Testing

While we work on implementing a formal testing framework, please manually test your changes thoroughly before submitting.

Future test implementation will include:
- Unit tests with Jest
- Component tests with React Testing Library
- End-to-end tests

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes and commit them
3. Ensure your code passes linting and type checking:
   ```bash
   pnpm lint
   pnpm type-check
   ```
4. Submit a pull request with a clear description of your changes
5. Address any feedback from reviewers

## Documentation

When making significant changes, please update the relevant documentation:

- Update component documentation if you change component behavior
- Add or update API documentation if you modify API integration
- Update architecture documentation for structural changes

For more detailed documentation about the project, see the [docs](./docs/) directory.

## Questions and Support

If you have questions or need help with your contributions, please:

1. Check the existing documentation
2. Reach out to the project maintainers

Thank you for contributing to Cortex Chat!