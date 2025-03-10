# AI Assistant Guide for Cortex Chat

This document provides essential information for AI assistants helping with this codebase. It contains development guidelines, architecture information, and best practices to follow when assisting with the Cortex Chat project.

> **CRITICAL: PRE-PRODUCTION STATUS**
>
> This codebase is currently in **pre-production development**. Therefore:
>
> - **NO BACKWARD COMPATIBILITY REQUIRED**: When refactoring or redesigning, do not maintain backward compatibility
> - **NO MIGRATION PATHS NEEDED**: Since the codebase is not in production use, do not implement migration paths
> - **PRIORITIZE CLEAN DESIGN**: Focus on creating clean, well-designed components without preserving old patterns
> - **REMOVE LEGACY CODE**: If you find code that seems focused on backward compatibility or migrations, suggest removing it
> - **ALWAYS CONFIRM**: If ever in doubt about backward compatibility needs, explicitly confirm with the human user
>
> The goal is a clean, well-architected codebase without technical debt from compatibility concerns.

## Conversation Workflow

Every time you (the AI assistant) begin a new conversation with a user about this codebase:

1. **Initial Message**:

   - Acknowledge that you've read and will follow this guide
   - Briefly mention that you understand the pre-production nature of the codebase
   - Ask the user what they want to work on today

2. **Read Documentation First**:

   - Review `docs/ARCHITECTURE.md` for system design principles
   - Review `docs/DEVELOPMENT.md` for development practices
   - Check for any ADRs (Architecture Decision Records) in `docs/adr/` that might be relevant
   - For deeper context on SSE implementation, review `docs/API_INTEGRATION.md`
   - Examine vision documents in `/cortex/cortex-platform/ai-context/` for broader platform context

3. **Understand the Current Context**:

   - Check git status to understand what files are being modified
   - Look for a pre-existing work context or current task focus
   - When specific files are mentioned, examine their imports and dependencies

4. **Respect Architectural Boundaries**:
   - The project follows a layered architecture (UI, Application Core, Communication Layer)
   - Services should be responsible for business logic
   - Components should be focused on UI concerns
   - Respect the event-driven architecture for real-time updates

## Common Commands

### Development

- Install dependencies: `pnpm install`
- Start development server: `pnpm start`
- Format code: `pnpm format`
- Lint: `pnpm lint`
- Type-check: `pnpm typecheck`

### Testing

- Run unit tests: `pnpm test`
- Run tests in watch mode: `pnpm test:watch`
- Run E2E tests: `pnpm cy:run`
- Open Cypress test runner: `pnpm cy:open`

### Building

- Build for production: `pnpm build`
- Analyze bundle size: `pnpm analyze`

## Codebase Philosophy and Goals

### Fast-Moving Innovation Environment

This codebase is designed for a **fast-moving team that needs to explore new ideas quickly**. Therefore:

- **Simplicity is paramount**: Code should be easy to understand and navigate
- **Modularity over monoliths**: Components should be well-isolated with clean interfaces
- **Reduced complexity**: Prefer straightforward implementations over clever or complex ones
- **Lower cognitive load**: New team members should be able to contribute quickly
- **Safe experimentation**: Changes in one area should have minimal risk to others

The overall modular design of the client supports these goals by allowing:

- Independent development of different UI components
- Parallel exploration of multiple approaches
- Easier reasoning about the system's behavior
- Faster iteration cycles
- Better team collaboration

### Dead Code Elimination

The codebase has accumulated some **dead/abandoned code** over time. Actively look for and remove:

- **Unused functions or components**: Code that is never called or rendered
- **Commented-out code blocks**: Old implementations left as comments
- **Deprecated features**: Code marked as deprecated or obsolete
- **Duplicate implementations**: Multiple ways to do the same thing
- **Experimental code**: Proof-of-concept code that was never completed
- **Empty or stub implementations**: Functions with TODO comments or pass statements

When you identify potential dead code, verify it's unused by:

1. Searching for references across the codebase
2. Checking import statements in other files
3. Looking for indirect usage through dynamic imports or lazy loading

## Core Development Principles

### Architecture

- Follow the layered architecture outlined in `docs/ARCHITECTURE.md`
- Maintain separation between:
  - UI Components (presentation)
  - Application Core (business logic)
  - Communication Layer (API and SSE)
- Use services for business logic, components for UI concerns
- Follow the SSE implementation guidelines in ADR-001

### Code Quality

- Always add proper TypeScript type annotations
- Follow code style guidelines (4 spaces, 80-120 char line length)
- Use JSDoc or TSDoc comments for public APIs
- Implement proper error handling and loading states
- Ensure proper resource cleanup to prevent memory leaks

### State Management

- Use appropriate state management based on scope:
  - Local component state for UI-specific concerns
  - Context API or state management library for shared state
  - Custom hooks for reusable stateful logic
- Be mindful of unnecessary re-renders
- Implement proper data fetching patterns (loading/error/success states)

### Testing

- Write tests for all new functionality
- Unit test components and utilities
- Integration test key user flows
- Mock API and SSE interactions appropriately
- For SSE testing, follow the guidelines in `docs/TESTING.md`

## Context and Background Information

The Cortex Chat client interacts with the Cortex Core platform, which provides a modular architecture for AI assistants. Several background documents are essential for understanding the overall vision and platform structure.

### Vision and Platform Documentation

- Review these documents to understand the larger vision and architecture:
  - `/cortex/cortex-platform/ai-context/vision/` - High-level architectural vision
  - `/cortex/cortex-platform/ai-context/cortex/` - Cortex platform design concepts

These documents provide critical context about the overall platform architecture that the chat client is part of. They should be referenced when making architectural decisions or implementing features that need to align with the broader platform vision.

### Cortex Platform Architecture

- **Workspaces**: Containers for conversations and resources
- **Conversations**: Threads of interaction between users and AI
- **Messages**: Individual interactions within a conversation
- **Modalities**: Different forms of input/output (text, voice, canvas, etc.)
- **SSE (Server-Sent Events)**: Real-time updates from the server

### Key Technical Decisions

The implementation of real-time updates via SSE is a core architectural decision:

- **Unified SSE Channels**: Global, workspace, and conversation-level events
- **Event-Driven Architecture**: Components react to events rather than polling
- **Connection Management**: Robust reconnection strategies and resource cleanup
- **Token Authentication**: Secure authentication for all SSE connections

## Handling Documentation and Architecture

### Plan of Record (PoR)

When encountering apparent contradictions with the established plan of record:

1. **Identify the Contradiction**:

   - Highlight exactly which part of the plan (e.g., ARCHITECTURE.md, DEVELOPMENT.md, ADRs) is being contradicted
   - Explain the nature of the contradiction

2. **Get Explicit Confirmation**:

   - Present the contradiction to the user
   - Explain the implications of deviating from the plan
   - Get clear confirmation before proceeding with changes

3. **Update Documentation**:
   - If a change is approved, update all affected documentation
   - Create or update ADRs to document significant architectural decisions
   - Ensure README and other guides reflect the new approach

### Documentation Practices

- Always update documentation when completing work
- Keep ADRs current with architectural decisions
- Add examples to clarify complex patterns
- Create new documentation when introducing new concepts

## Problem-Solving Approach

### Continuous Codebase Improvement

The codebase is already quite large and complex in some areas. Actively work to improve it by:

- **Breaking Down Components**: Split large components into smaller, focused ones
- **Extracting Custom Hooks**: Move complex logic into reusable hooks
- **Improving Type Definitions**: Enhance type safety and developer experience
- **Enhancing Error Handling**: Implement consistent error handling patterns
- **Optimizing Performance**: Identify and fix performance bottlenecks
- **Improving Accessibility**: Ensure UI components follow accessibility best practices

### Technical Debt Reduction

- Identify and remove redundant code
- Remove compatibility layers and migration paths (codebase is pre-production)
- Eliminate dead/abandoned code as described in the Codebase Philosophy section
- Improve type safety and error handling
- Refactor to align with architectural principles
- Create automated tools to enforce good practices
- Look for opportunities to simplify by removing unused or overly-complex code

### Testing First

- Always write and run tests for new functionality
- Update tests when changing existing functionality
- When tests fail, analyze whether the issue is with the tests or the code
- Avoid hacks and quick fixes that bypass failing tests

### When to Seek Human Feedback

- When making significant architectural changes
- When multiple valid approaches exist with different trade-offs
- When encountering ambiguous requirements
- Before implementing solutions that deviate from established patterns

### Proactive Problem Solving

- Suggest automated tools to prevent recurring issues
- Identify and address root causes, not just symptoms
- Propose comprehensive solutions rather than patches
- Look for patterns in issues that might indicate deeper problems

## File Organization

```
cortex-chat/
├── public/                # Static files
├── src/                   # Source code
│   ├── components/        # UI components
│   │   ├── chat/          # Chat-specific components
│   │   ├── workspace/     # Workspace components
│   │   └── shared/        # Shared UI components
│   ├── services/          # Service layer
│   │   ├── api/           # API communication
│   │   ├── auth/          # Authentication
│   │   └── sse/           # Server-Sent Events
│   ├── store/             # State management
│   ├── utils/             # Utility functions
│   ├── hooks/             # Custom React hooks
│   ├── types/             # TypeScript type definitions
│   ├── styles/            # Global styles
│   ├── App.tsx            # Application entry point
│   └── index.tsx          # React rendering entry point
├── docs/                  # Documentation
│   └── adr/               # Architecture Decision Records
├── tests/                 # Test files
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── cypress/               # E2E tests
└── config/                # Configuration files
```

## Best Practices for Assisting with This Project

1. **Start with Current Status**: Always check git status to understand the current state of the project
2. **Understand Architecture First**: Review architecture documentation before making changes
3. **Test Rigorously**: Write and run comprehensive tests for all changes
4. **Document Changes**: Update or create documentation for any significant changes
5. **Propose Improvements**: Suggest better approaches when you see opportunities for improvement
6. **Provide Context**: Explain why certain approaches are recommended or required
7. **Fix Forward**: When encountering issues, address root causes rather than symptoms
8. **Prioritize Clean Design**: As this is pre-production code, prioritize clean architecture over backward compatibility
9. **Remove Technical Debt**: Actively look for and suggest removing code that adds complexity without value
10. **Consider Performance**: Be mindful of performance implications, especially for real-time features

Remember that this project prioritizes component isolation, type safety, and maintainability over quick solutions. Always aim to leave the codebase better than you found it.

## Frontend-Specific Considerations

### UI Component Design

- Design components for reusability and composition
- Implement proper prop validation and default values
- Handle loading, error, and empty states within components
- Follow accessibility best practices (ARIA attributes, keyboard navigation)
- Use semantic HTML elements appropriately

### State Management

- Choose appropriate state management based on complexity and scope
- Avoid prop drilling by using context or state management libraries
- Implement optimistic updates for better user experience
- Consider using immutable data patterns for predictable state updates

### SSE Implementation

- Follow the SSE implementation pattern in ADR-001
- Ensure proper connection lifecycle management
- Implement robust reconnection strategies
- Handle event parsing and error boundaries
- Properly clean up connections when components unmount

### Performance Optimization

- Use React.memo for expensive components
- Implement virtualization for long lists
- Be mindful of unnecessary re-renders
- Optimize bundle size with code splitting
- Use performance profiling tools to identify bottlenecks

## Self-Improvement and Maintenance

As an AI assistant, you should:

1. **Update This Guide**: When you learn new information about the codebase or discover better ways to assist:

   - Suggest additions or improvements to this guide
   - Be specific about what could be added and why it would be helpful

2. **Identify Recurring Issues**: When you notice patterns of issues or questions:

   - Propose automated solutions (like linting rules or type definitions)
   - Suggest documentation or guide updates to prevent future problems

3. **Record Common Commands**: When you or the user find useful commands:

   - Suggest adding them to this guide for future reference
   - Include context about when and how to use them

4. **Document Coding Patterns**: When implementing solutions that others might reuse:
   - Document the pattern in appropriate guides
   - Create examples that show best practices

By continuously improving this guide, you help future AI assistants provide better service and maintain consistency in the project's development.
