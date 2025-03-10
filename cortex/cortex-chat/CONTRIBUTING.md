# Contributing to Cortex Chat

This document provides guidelines and instructions for contributing to the Cortex Chat client project.

## Development Environment

### Prerequisites

- Node.js (v18+ recommended)
- pnpm (v8+ recommended)
- A modern IDE (VS Code recommended)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/cortex-chat.git
   cd cortex-chat
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

3. Start the development server:
   ```bash
   pnpm dev
   ```

## Development Workflow

### Branching Strategy

- `main` - Production-ready code
- `develop` - Integration branch
- Feature branches - `feature/name-of-feature`

Always branch from `develop` for new features:

```bash
git checkout develop
git pull
git checkout -b feature/my-new-feature
```

### Code Style

We use ESLint and Prettier to maintain consistent code style:

- 4 spaces for indentation
- 80-120 character line length
- Single quotes for strings
- Semicolons at the end of statements

To check and fix your code:

```bash
pnpm lint      # Check for linting issues
pnpm format    # Fix formatting issues
```

### Testing

We use Vitest for unit tests and Cypress for integration tests:

```bash
pnpm test          # Run all tests
pnpm test:watch    # Run tests in watch mode
pnpm cy:run        # Run Cypress tests
pnpm cy:open       # Open Cypress test runner
```

## Project Structure

```
src/
├── components/      # UI components
│   ├── chat/        # Chat-specific components
│   ├── workspace/   # Workspace components
│   └── shared/      # Shared UI components
├── services/        # Service layer
│   ├── api/         # API communication
│   ├── auth/        # Authentication
│   └── sse/         # Server-Sent Events
├── store/           # State management
├── utils/           # Utility functions
├── hooks/           # Custom React hooks
├── types/           # TypeScript type definitions
└── styles/          # Global styles
```

## Commit Guidelines

Follow conventional commits format for commit messages:

- `feat: add new feature`
- `fix: resolve issue with X`
- `docs: update documentation`
- `chore: update dependencies`
- `refactor: improve code structure`
- `test: add tests for feature X`

## Pull Request Process

1. Ensure your code passes all tests and linting
2. Update documentation if necessary
3. Create a pull request to the `develop` branch
4. Request review from at least one team member
5. Address any feedback from reviewers
6. Once approved, your PR will be merged

## Additional Resources

- [Architecture Documentation](docs/ARCHITECTURE.md)
- [API Integration Guide](docs/API_INTEGRATION.md)
- [Testing Guide](docs/TESTING.md)