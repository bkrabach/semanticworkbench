# ADR-006: Messaging Architecture

## Status

Accepted

## Context

The Cortex Core platform requires a robust messaging architecture that supports real-time communication between clients and the system. Key requirements include:

1. Fire-and-forget API endpoints that return quickly to clients
2. Asynchronous message processing
3. Real-time status updates via SSE (Server-Sent Events)
4. Reliable handling of typing indicators
5. Proper resource management including clean shutdown
6. Type-safe message handling

## Decision

We have decided to implement a messaging architecture with the following characteristics:

1. **Asyncio-based processing queue** in the CortexRouter for handling messages
2. **Direct communication paths** between components where appropriate
3. **Required conversation_id** field in the InputMessage class
4. **Proper cleanup methods** for all components with background tasks
5. **Clear sequence of operations** for message processing:
   - Show typing indicator
   - Process message
   - Save response to database
   - Hide typing indicator
   - Send response via SSE

## Consequences

### Positive

- **Performance**: Asyncio-based tasks are more efficient than threads for IO-bound operations
- **Type Safety**: Required fields eliminate unnecessary null checks and improve type checking
- **Resource Management**: Proper cleanup methods prevent resource leaks
- **Testing**: Clean separation of concerns makes testing easier and more reliable
- **Maintenance**: Direct communication paths are easier to understand and debug

### Negative

- **Flexibility**: Direct paths may require more changes for advanced routing scenarios
- **Complexity for some use cases**: Some complex routing scenarios may require additional implementation work

### Neutral

- **Event System**: The event system remains available for scenarios requiring decoupled communication
- **Repository Pattern**: The existing repository pattern is maintained for data access

## Implementation Notes

When implementing components following this architecture:

1. **Asyncio for background processing**:
   ```python
   class CortexRouter(RouterInterface):
       def __init__(self):
           self.message_queue = asyncio.Queue()
           self.processing_task = asyncio.create_task(self._process_messages())
   ```

2. **Required conversation_id**:
   ```python
   class InputMessage(CortexMessage):
       # Required field - no Optional[] wrapper
       conversation_id: str
   ```

3. **Proper cleanup methods**:
   ```python
   async def cleanup(self):
       self.running = False
       if self.processing_task and not self.processing_task.done():
           self.processing_task.cancel()
           try:
               await asyncio.wait_for(asyncio.shield(self.processing_task), timeout=0.5)
           except (asyncio.CancelledError, asyncio.TimeoutError):
               pass
   ```

4. **Direct SSE communication**:
   ```python
   async def _send_typing_indicator(self, conversation_id: str, is_typing: bool):
       """Send typing indicator directly via SSE"""
       sse_service = get_sse_service()
       await sse_service.connection_manager.send_event(
           "conversation",
           conversation_id,
           "typing_indicator",
           {
               "conversation_id": conversation_id,
               "isTyping": is_typing,
               "timestamp_utc": datetime.now(timezone.utc).isoformat(),
           }
       )
   ```

## Related ADRs

- [ADR-002: Domain-Driven Repository Architecture](adr-002-domain-driven-repository-architecture.md)
- [ADR-003: SSE Starlette Implementation](adr-003-sse-starlette-implementation.md)
- [ADR-005: Service Layer Pattern](adr-005-service-layer-pattern.md)