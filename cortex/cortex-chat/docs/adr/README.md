# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for the Cortex Chat project.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences.

## Why use ADRs?

ADRs are used to document significant decisions that shape the architecture and design of the system. They help:

- Provide context and rationale for decisions
- Communicate design decisions to team members
- Preserve knowledge for future team members and iterations
- Create a historical record of how and why the architecture evolved

## ADR Format

Each ADR follows this structure:

1. **Title**: A descriptive title that includes the ADR number and a brief summary
2. **Status**: Current status (Proposed, Accepted, Deprecated, Superseded)
3. **Context**: The problem being addressed and relevant factors
4. **Decision**: The decision that was made
5. **Consequences**: The resulting context after applying the decision
6. **References**: Additional information, related decisions, or relevant documentation

## ADR List

1. [ADR-001: Server-Sent Events (SSE) Implementation](adr-001-sse-implementation.md) - Describes the approach for implementing real-time updates using SSE

## Creating a New ADR

When creating a new ADR:

1. Copy the template from `adr-template.md`
2. Name it following the pattern `adr-NNN-title.md` where NNN is the next available number
3. Fill in the sections according to the template
4. Add a link to the new ADR in this README file

## Changing an ADR

ADRs are intended to be immutable once they reach "Accepted" status. If a decision needs to be revised:

1. Create a new ADR that references the old one
2. Change the status of the old ADR to "Superseded" and reference the new ADR
3. Document the context for why the original decision is being revised

## References

- [Michael Nygard's article on ADRs](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ADR GitHub organization](https://adr.github.io/)
- [Sustainable Architectural Decisions](https://www.infoq.com/articles/sustainable-architectural-design-decisions/)