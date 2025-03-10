# ADR-006: Simplified Messaging Architecture

## Status

Accepted

## Context

The original Cortex Core messaging architecture used a complex event system with multiple layers of indirection between components:

1. The API layer would add a message to the database via service
2. The message would be passed to a queue in a thread-based router
3. The router would make a decision and publish events to an event system
4. Output publishers would subscribe to events and republish them
5. Publishers would save messages to the database again
6. Publishers would emit SSE events to connected clients

This architecture had several issues:
- Complex event chains were difficult to trace and debug
- Threading model caused resource management issues
- Multiple event publishing/subscribing created many possible failure points
- Inconsistent null-checking for fields that were always present
- Unclear ownership of database operations

Additionally, the previous architecture lacked proper cleanup mechanisms for background tasks, leading to potential resource leaks during application shutdown.

## Decision

We have decided to simplify the messaging architecture by:

1. Converting from a threading-based to an asyncio-based router
2. Establishing direct communication paths between components where appropriate
3. Making conversation_id a required field in the InputMessage class
4. Adding proper cleanup methods to all components with background tasks
5. Removing unnecessary null checks for required fields
6. Clearly documenting the message flow in architecture documentation

## Consequences

### Positive

- **Improved Readability**: Direct communication paths are easier to understand and debug
- **Better Type Safety**: Required fields eliminate unnecessary null checks
- **Resource Management**: Proper cleanup methods prevent resource leaks
- **Simplified Testing**: Fewer components and simpler interfaces make testing easier
- **Performance**: Asyncio-based tasks are more efficient than threads for IO-bound operations
- **Reduced Complexity**: Fewer layers of indirection reduce cognitive load

### Negative

- **Reduced Flexibility**: Direct paths may be less flexible for complex routing scenarios
- **Migration Effort**: Existing code may need updates to align with the new architecture

### Neutral

- **Event System**: The event system is still available for scenarios where decoupled communication is appropriate
- **Repository Pattern**: The existing repository pattern is maintained for data access

## Implementation Notes

When implementing components following this architecture:

1. Use asyncio for background processing instead of threads
2. Make fields required when they are logically required
3. Implement cleanup methods for all components with background tasks
4. Prefer direct service calls over event chains when it simplifies the code
5. Document the flow clearly in tests and documentation

## Design Process

The successful simplification of the messaging architecture followed this process:

1. **End-to-End Flow Analysis**: Rather than trying to fix individual components, we traced the entire message path from client request to response delivery, identifying all the steps involved.

2. **First Principles Reassessment**: We went back to the core purpose of message routing - receiving a message, processing it, and delivering a response - and questioned whether each layer of indirection was necessary.

3. **Complexity Reduction**: We identified that the event system created an unnecessary layer of indirection for the core messaging flow, while the thread-based router added complexity without benefits over asyncio.

4. **Essential vs. Optional Requirements**: We distinguished between essential requirements (message routing, typing indicators, response delivery) and optional flexibility (complex event routing), prioritizing the essential functionality.

5. **Resource Lifecycle Management**: We added proper cleanup methods to all components with background tasks, ensuring clean shutdown of the application.

6. **Data Model Refinement**: We recognized that conversation_id was always required in the messaging flow, making it a required field and eliminating unnecessary null checks.

7. **Visual Design**: We created clear, simple diagrams of the new flow to validate its simplicity and clarity.

8. **Documentation as Design Tool**: The process of documenting the new architecture in COMPONENTS.md and ADR-006 helped refine and validate the design choices.

This design approach prioritized simplicity, directness, and maintainability over flexibility that wasn't immediately needed. By focusing on the core requirements and removing unnecessary complexity, we created a more reliable and easier-to-understand system.

## Related ADRs

- [ADR-002: Domain-Driven Repository Architecture](adr-002-domain-driven-repository-architecture.md)
- [ADR-003: SSE Starlette Implementation](adr-003-sse-starlette-implementation.md)
- [ADR-005: Service Layer Pattern](adr-005-service-layer-pattern.md)