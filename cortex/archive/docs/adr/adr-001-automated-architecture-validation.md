# ADR-001: Automated Architecture Validation

## Status

Accepted

## Context

As the Cortex Core codebase grows, maintaining clean architectural boundaries becomes increasingly challenging. We've established a domain-driven repository architecture that strictly separates:

1. **Database models (SQLAlchemy)**: Represent database schema
2. **Domain models (Pydantic)**: Represent business entities
3. **API models (Pydantic)**: Handle HTTP request/response concerns

A core principle is that database models must never leak into service or API layers. However, enforcing this principle has been challenging:

- Subtle import statements can violate architectural boundaries
- SQLAlchemy models have type characteristics that cause issues when they cross boundaries
- Code reviews alone have proven insufficient to catch all boundary violations

We've observed several production issues stemming from SQLAlchemy models leaking across layer boundaries, including:
- Type errors with SQLAlchemy Column objects in conditional evaluations
- JSON serialization failures when passing SQLAlchemy objects to `json.loads()`
- Testing difficulties when mocking domain models but receiving database models

## Decision

We will implement automated validation of architectural boundaries through:

1. **Automated Test Suite**: Create `tests/architecture/test_layer_integrity.py` to validate import patterns
2. **Shell Script**: Implement `check_imports.sh` for quick validation in development and CI
3. **Enhanced Documentation**: Add explicit warnings, examples, and guidance in DEVELOPMENT.md

The architectural boundaries we will enforce are:
- API layer (app/api/): Must not import SQLAlchemy models
- Service layer (app/services/): Must not import SQLAlchemy models
- Components (app/components/): Must not import SQLAlchemy models

## Consequences

### Positive

- Architectural violations are caught automatically before they reach production
- Developers receive immediate feedback when boundary violations occur
- The codebase maintains its clean separation of concerns
- New team members can more easily understand the expected architecture
- Reduced cognitive load when writing code, as architectural rules are systematically enforced
- Type safety is improved across the codebase

### Negative

- Additional test burden (though the tests are simple and fast)
- Learning curve for new developers to understand and respect the boundaries
- Potential friction for quick prototyping (though maintaining architecture is worth this trade-off)

## Alternatives Considered

### Manual Code Reviews Only

We considered relying solely on code reviews to catch architectural violations. While this approach requires no additional tooling, experience has shown that:
- Violations are easily missed in complex PRs
- Reviewers may not consistently check import statements
- New team members may not understand the architecture sufficiently to identify violations

### Linting Rules

We considered creating custom rules for linting tools like ruff or pylint. While this would integrate well with existing tooling, it would require:
- Creating and maintaining custom linting rules
- Ensuring consistent tool usage across the team
- More complex setup and configuration

Our simpler approach of a dedicated test module and shell script provides the necessary validation with minimal overhead.

### Type Checking with mypy

We considered relying on mypy's type checking to catch most issues. While mypy does catch many problems when SQLAlchemy models leak, it doesn't always identify the architectural violation itself, just the resulting type errors. Our approach focuses on preventing the underlying architectural issues.

## References

- [Domain-Driven Design principles](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Cortex Core Development Guide](../DEVELOPMENT.md)