# AI Assistant Guide for Cortex Core

This document provides essential information for AI assistants helping with this codebase. It contains development guidelines, architecture information, and best practices to follow when assisting with the Cortex Core project.

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

   - Review the files mentioned in [Context and Background Information](#context-and-background-information)
   - Check for any ADRs (Architecture Decision Records) in `docs/adr/` that might be relevant
   - For deeper context, explore the vision and technology documents (more details below)

3. **Understand the Current Context**:

   - Check git status to understand what files are being modified
   - Look for a pre-existing work context or current task focus
   - When specific files are mentioned, examine their imports and dependencies

4. **Respect Architectural Boundaries**:
   - The project follows a strict domain-driven repository architecture
   - SQLAlchemy models must never leak outside repository layer
   - Use the testing tools and scripts (e.g., `check_imports.sh`) to verify architectural integrity

## Common Commands

### Development

- Build/Install: `uv pip install -e .`
- Start Server: `uv run -m app.main`
- Format: `ruff format`
- Lint: `ruff check`
- Type-check: `mypy`

### Database

- Run Migrations: `uv run alembic upgrade head`
- Create Migration: `make revision MSG="description"`

### Testing

- Run All Tests: `python -m pytest`
- Run Single Test: `python -m pytest tests/test_file.py::test_function -v`
- Run Architecture Tests: `python -m pytest tests/architecture/test_layer_integrity.py`
- Check Architecture Boundaries: `./check_imports.sh`

### Dependencies

- Install Dev Dependencies: `uv add --dev <package>`
- Install Type Stubs: `uv add --dev types-<package>`

## Codebase Philosophy and Goals

### Fast-Moving Innovation Environment

This codebase is designed for a **fast-moving team that needs to explore new ideas quickly**. Therefore:

- **Ruthless Simplicity**: Keep everything as simple as possible, but no simpler
- **Minimize abstractions**: Every layer of abstraction must justify its existence
- **Start minimal, grow as needed**: Begin with the simplest implementation that meets current needs
- **Avoid future-proofing**: Don't build for hypothetical future requirements
- **Direct over indirect**: Favor direct communication paths over complex event chains
- **Lower cognitive load**: New team members should be able to contribute quickly
- **Safe experimentation**: Changes in one area should have minimal risk to others

The focus on simplicity supports these goals by allowing:

- Clearer understanding of the system behavior
- Faster iteration cycles
- Less cognitive load for developers
- Easier debugging and maintenance
- Better team collaboration

### Dead Code Elimination

The codebase has accumulated some **dead/abandoned code** over time. Actively look for and remove:

- **Unused functions or classes**: Code that is never called or instantiated
- **Commented-out code blocks**: Old implementations left as comments
- **Deprecated features**: Code marked as deprecated or obsolete
- **Duplicate implementations**: Multiple ways to do the same thing
- **Experimental code**: Proof-of-concept code that was never completed
- **Empty or stub implementations**: Functions with TODO comments or pass statements

When you identify potential dead code, verify it's unused by:

1. Searching for references across the codebase
2. Checking import statements in other files
3. Looking for indirect usage through reflection or dependency injection

## Core Development Principles

### Architecture

- Follow the domain-driven repository architecture
- Maintain separation between:
  - Database Models (SQLAlchemy)
  - Domain Models (Pydantic)
  - API Models (Pydantic)
- Use services for business logic, repositories for data access
- Remember architectural integrity with minimal implementation:
  - Preserve key architectural patterns but simplify implementations
  - Focus on complete flows rather than perfect components
  - Maintain pattern benefits with dramatically simpler code

### Code Quality

- Always add proper type annotations
- Handle SQLAlchemy Column objects properly
- Follow code style guidelines (4 spaces, 100 char line length, etc.)
- Use docstrings with Args/Returns sections

### Testing

- Write tests for all new functionality
- Use dependency overrides, not patching, for FastAPI tests
- Test each layer (API, service, repository) separately

### Message Processing Flow

- **Async over threading**: Use asyncio-based tasks for background processing instead of threads
- **Make appropriate fields required**: Don't make fields optional when they're always needed (e.g., conversation_id)
- **Direct communication**: Prefer direct calls to services over complex event chains when appropriate
- **Clean resource management**: Always provide proper cleanup methods for background tasks
- **Minimize conditional checks**: Remove redundant null checks when fields are required

## Context and Background Information

The Cortex Platform has several context directories containing architectural vision and technical information that should be referenced based on the task at hand:

### Vision and Architecture

- `/cortex/cortex-platform/ai-context/vision/` - High-level architectural vision
  - Review these files to understand the overall architectural approach and philosophy
  - Essential when making decisions that affect the overall system architecture
  - Key files: `Central AI Core with Adaptive Ecosystem.md`, `Domain Expert Entities.md`

### Platform Design

- `/cortex/cortex-platform/ai-context/cortex/` - Cortex platform design and concepts
  - Includes detailed information about the platform's design and values
  - Reference when implementing features that should align with the platform's vision
  - Key files: `Cortex_Platform-Technical_Architecture.md`, `Cortex_Platform-Vision_and_Values.md`

### Technical Documentation

- `/cortex/cortex-platform/ai-context/mcp/` - Model Context Protocol (MCP) documentation

  - Review when working on MCP integrations or domain expert services
  - Contains SDK documentation for both Python and TypeScript
  - Reference when implementing tools or services that communicate via MCP
  - Key files: `python-sdk-README.md`, `llms-concepts.txt`

- `/cortex/cortex-platform/ai-context/misc/` - Miscellaneous technologies
  - Contains information about supporting technologies like LiteLLM
  - Reference when working with specific third-party integrations
  - Key files: `litellm-README.md`

**When to Reference**:

- When starting work on a new major feature
- When making architectural decisions
- When implementing integrations with external services
- When clarifying the overall vision or philosophy guiding implementation

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

- Focus on essential documentation that delivers immediate value
- Keep ADRs current with significant architectural decisions
- Use simple examples to clarify patterns
- Create minimal but sufficient documentation for new concepts
- Remember: code that is simple and clear requires less documentation

## Problem-Solving Approach

### Continuous Codebase Improvement

The codebase is already quite large and complex in some areas. Actively work to improve it by:

- **Eliminating Unnecessary Code**: Remove code that isn't providing clear value
- **Simplifying Functions**: Break down complex functions into smaller, focused ones
- **Clarifying Logic**: Replace clever/complex code with more straightforward implementations
- **Improving Naming**: Ensure functions, variables, and classes have clear, descriptive names
- **Reducing Abstractions**: Question every layer of abstraction and remove unnecessary ones
- **Enhancing Discoverability**: Make important code paths easier to find and understand
- **Streamlining Interfaces**: Prefer simple, clear interfaces over complex, flexible ones
- **Standardizing Patterns**: Use consistent patterns for common operations
- **Avoid Over-modularization**: Don't split files unnecessarily - this can increase complexity

### Technical Debt Reduction

- Identify and remove redundant code
- Remove compatibility layers and migration paths (codebase is pre-production)
- Eliminate dead/abandoned code as described in the Codebase Philosophy section
- Remove unnecessary abstractions and indirection
- Minimize wrappers around external libraries
- Improve type safety and error handling
- Convert optional fields to required when they're always needed
- Replace threading with asyncio for background tasks
- Simplify complex event chains with direct service calls where appropriate
- Ensure all background tasks have proper cleanup methods
- Refactor to align with architectural principles while maintaining simplicity
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

## Proposed File Organization (update as needed, remove "Proposed" once decided)

```
cortex-core/
├── app/                    # Main application code
│   ├── api/                # API endpoints
│   ├── components/         # Core components
│   ├── database/           # Database connection and models
│   │   └── repositories/   # Repository implementations
│   ├── interfaces/         # Interface definitions
│   ├── models/             # Data models
│   │   ├── api/            # API models
│   │   │   ├── request/    # Request models
│   │   │   └── response/   # Response models
│   │   └── domain/         # Domain models
│   └── services/           # Service implementations
├── docs/                   # Documentation
│   └── adr/                # Architecture Decision Records
└── tests/                  # Test suite
    ├── api/                # API tests
    ├── components/         # Component tests
    ├── database/           # Database tests
    ├── services/           # Service tests
    └── architecture/       # Architecture validation tests
```

## Engineering Excellence Guidelines

### Core Engineering Mindset

The most successful contributions to this codebase share these engineering attributes:

1. **Ruthless Simplicity**: Question everything and keep everything as simple as possible. Ask "do we actually need this right now?" before adding anything.

2. **First Principles Thinking**: Start with the core purpose of the component rather than incrementally modifying existing patterns. Ask "what is this actually trying to achieve?" before diving into implementation.

3. **Start Minimal, Grow as Needed**: Begin with the simplest implementation that meets current needs. Don't build for hypothetical future requirements.

4. **Follow Direct Paths**: Prefer direct communication between components over complex event chains or multiple layers of indirection. Each additional hop is a potential failure point.

5. **Visualize End-to-End Flow**: Think in terms of complete paths from request to response. Focus on complete flows rather than perfect components.

6. **Resource Lifecycle Awareness**: Consider the full lifecycle of components including cleanup and shutdown. Any component that manages background tasks or resources must implement proper cleanup methods.

7. **Type Safety as Default**: Make fields required unless they truly are optional. Eliminate unnecessary null checks by designing with proper type constraints from the start.

8. **Code as Communication**: Write code primarily for human understanding, not just machine execution. Choose clarity over cleverness, even if it means a few more lines of code.

9. **Iterative Simplification**: After implementing a solution, look for further opportunities to simplify. Ask "can I remove this layer?" or "is this abstraction necessary?"

10. **Library Direct Usage**: Use libraries as intended with minimal wrappers. Avoid unnecessary adapter layers.

### Best Practices for Assisting with This Project

1. **Start with Current Status**: Always check git status to understand the current state of the project
2. **Understand Architecture First**: Review architecture documentation before making changes
3. **Verify Boundary Compliance**: Run architecture tests to verify changes maintain architectural integrity
4. **Test Rigorously**: Write and run comprehensive tests for all changes
5. **Document Changes**: Update or create documentation for any significant changes
6. **Propose Improvements**: Suggest better approaches when you see opportunities for improvement
7. **Provide Context**: Explain why certain approaches are recommended or required
8. **Fix Forward**: When encountering issues, address root causes rather than symptoms
9. **Prioritize Clean Design**: As this is pre-production code, prioritize clean architecture over backward compatibility
10. **Remove Technical Debt**: Actively look for and suggest removing code that adds complexity without value

Remember that this project prioritizes architectural integrity, type safety, and maintainability over quick solutions. Always aim to leave the codebase better than you found it.

## Self-Improvement and Maintenance

As an AI assistant, you should:

1. **Update This Guide**: When you learn new information about the codebase or discover better ways to assist:

   - Suggest additions or improvements to this guide
   - Be specific about what could be added and why it would be helpful

2. **Identify Recurring Issues**: When you notice patterns of issues or questions:

   - Propose automated solutions (like the architecture validation tools)
   - Suggest documentation or guide updates to prevent future problems

3. **Record Common Commands**: When you or the user find useful commands:

   - Suggest adding them to this guide for future reference
   - Include context about when and how to use them

4. **Document Coding Patterns**: When implementing solutions that others might reuse:
   - Document the pattern in appropriate guides
   - Create examples that show best practices

By continuously improving this guide, you help future AI assistants provide better service and maintain consistency in the project's development.
