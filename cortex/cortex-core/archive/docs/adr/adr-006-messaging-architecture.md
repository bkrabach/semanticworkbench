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

Key requirements for our platform include:
1. Fire-and-forget API endpoints that return quickly to clients
2. Asynchronous message processing
3. Real-time status updates via SSE (Server-Sent Events)
4. Reliable handling of typing indicators
5. Proper resource management including clean shutdown
6. Type-safe message handling

## Decision

We have decided to simplify the messaging architecture by:

1. **Asyncio-based processing queue** in the CortexRouter instead of threads
2. **Direct communication paths** between components where appropriate
3. **Required conversation_id** field in the InputMessage class
4. **Proper cleanup methods** for all components with background tasks
5. **Clear sequence of operations** for message processing:
   - Show typing indicator
   - Process message
   - Save response to database
   - Hide typing indicator
   - Send response via SSE
6. **Removing unnecessary null checks** for required fields
7. **Clearly documenting the message flow** in architecture documentation

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

4. **Direct SSE communication with fallback to event system**:
   ```python
   async def _send_message_to_client(self, conversation_id: str, message_id: str,
                                    content: str, role: str, metadata: dict):
       """Send message directly to client via SSE"""
       # Create payload
       payload = {
           "id": message_id,
           "content": content,
           "role": role,
           "created_at": datetime.now(timezone.utc).isoformat(),
           "metadata": metadata,
           "conversation_id": conversation_id
       }
       
       # First publish through event system for broader distribution
       event_system = get_event_system()
       await event_system.publish(
           "conversation.message_received",
           payload,
           source="cortex_router"
       )
       
       # Also try direct SSE path for active connections
       sse_service = get_sse_service()
       await sse_service.connection_manager.send_event(
           "conversation",
           conversation_id,
           "message_received",
           payload,
           republish=False  # Already published through event system
       )
   ```

## Design Process

The successful simplification of the messaging architecture followed this process:

1. **End-to-End Flow Analysis**: Rather than trying to fix individual components, we traced the entire message path from client request to response delivery, identifying all the steps involved.

2. **First Principles Reassessment**: We went back to the core purpose of message routing - receiving a message, processing it, and delivering a response - and questioned whether each layer of indirection was necessary.

3. **Complexity Reduction**: We identified that the event system created an unnecessary layer of indirection for the core messaging flow, while the thread-based router added complexity without benefits over asyncio.

4. **Essential vs. Optional Requirements**: We distinguished between essential requirements (message routing, typing indicators, response delivery) and optional flexibility (complex event routing), prioritizing the essential functionality.

5. **Resource Lifecycle Management**: We added proper cleanup methods to all components with background tasks, ensuring clean shutdown of the application.

6. **Data Model Refinement**: We recognized that conversation_id was always required in the messaging flow, making it a required field and eliminating unnecessary null checks.

7. **Visual Design**: We created clear, simple diagrams of the new flow to validate its simplicity and clarity.

8. **Documentation as Design Tool**: The process of documenting the new architecture in COMPONENTS.md and this ADR helped refine and validate the design choices.

## Implementation Example

The simplified messaging architecture is implemented in the CortexRouter:

```python
class CortexRouter(RouterInterface):
    """
    Implementation of the Cortex Router
    
    The Router processes input messages, makes routing decisions,
    and optionally produces outputs. It maintains a queue of
    messages and processes them asynchronously.
    """
    
    def __init__(self):
        """Initialize the router"""
        self.event_system = get_event_system()
        self.message_queue = asyncio.Queue()
        self.logger = logging.getLogger(__name__)
        self.running = True
        
        # Start async task to process messages
        self.processing_task = asyncio.create_task(self._process_messages())
    
    async def process_input(self, message: InputMessage) -> bool:
        """Process an input message"""
        try:
            # Queue the message for asynchronous processing
            await self.message_queue.put(message)
            self.logger.info(f"Queued message {message.message_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error queuing message: {e}")
            return False
    
    async def _process_messages(self):
        """Process messages from the queue asynchronously"""
        while self.running:
            try:
                # Get message from queue (with timeout for clean shutdown)
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                
                # Process the message
                await self._handle_message(message)
                
                # Mark task as done
                self.message_queue.task_done()
            except asyncio.TimeoutError:
                # This is expected when the queue is empty
                pass
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
```

## Current Status

The simplified messaging architecture has been implemented in the following components:

- **CortexRouter**: Fully implemented with asyncio queue
- **SSE Service**: Updated to support direct event sending
- **Message Processing**: Implemented with proper typing indicators and LLM integration
- **Resource Cleanup**: All components have proper cleanup methods

## Related Documentation

- [ROUTER.md](../ROUTER.md): Comprehensive documentation of the CortexRouter
- [SSE.md](../SSE.md): Documentation of the SSE system
- [ARCHITECTURE.md](../ARCHITECTURE.md): Overall system architecture

## Related ADRs

- [ADR-002: Domain-Driven Repository Architecture](adr-002-domain-driven-repository-architecture.md)
- [ADR-003: SSE Starlette Implementation](adr-003-sse-starlette-implementation.md)
- [ADR-005: Service Layer Pattern](adr-005-service-layer-pattern.md)