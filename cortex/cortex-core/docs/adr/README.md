# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) documenting significant architectural decisions made in the Cortex Core project.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences. Each ADR describes:

- The architectural decision that was made
- The context and problem statement that motivated the decision
- The options considered and the decision outcome
- The consequences, both positive and negative, of the decision

## ADR Index

- [ADR-001: Automated Architecture Validation](adr-001-automated-architecture-validation.md)
- [ADR-002: Domain-Driven Repository Architecture](adr-002-domain-driven-repository-architecture.md)
- [ADR-003: SSE Implementation with sse-starlette](adr-003-sse-starlette-implementation.md)
- [ADR-004: Type Safety with SQLAlchemy and Pydantic](adr-004-type-safety-sqlalchemy-pydantic.md)
- [ADR-005: Service Layer Pattern](adr-005-service-layer-pattern.md)

## ADR Template

```markdown
# ADR-NNN: Title

## Status

[Proposed | Accepted | Superseded | Deprecated]

## Context

[Description of the problem and context that motivates this decision]

## Decision

[Description of the decision that was made]

## Consequences

[Description of the consequences, both positive and negative, of the decision]

## Alternatives Considered

[Description of alternative solutions that were considered and why they were rejected]

## References

[Links to relevant documentation, issues, or discussions]
```

## How to Create a New ADR

1. Copy the template above into a new file named `adr-NNN-title.md` where NNN is the next ADR number and title is a short, hyphenated description
2. Fill in the sections of the template
3. Add a link to the new ADR in the ADR Index section of this README
4. Commit the new ADR file and updated README

## Further Reading

- [Architectural Decision Records in the Wild](https://github.com/joelparkerhenderson/architecture-decision-record)
- [ADR GitHub Organization](https://adr.github.io/)