# Event Bus Specification

## Overview

The Event Bus is a central communication mechanism within the Cortex Core that enables loose coupling between components. It implements a publish-subscribe pattern where components can publish events and subscribe to receive them. This document provides a comprehensive specification of the Event Bus design, implementation details, and usage patterns.

## Core Principles

The Event Bus follows these core design principles:

1. **Simplicity**: Minimal API with only essential operations
2. **Asynchronous**: All operations are non-blocking
3. **User-partitioned**: Events include user information for filtering
4. **In-process**: Phase 1 uses an in-memory implementation
5. **No persistence**: Events exist only in memory and are not stored

## Interface Definition

### EventBus Class

```python
class EventBus:
    def __init__(self):
        """Initialize the event bus."""

    def subscribe(self, queue: asyncio.Queue) -> None:
        """
        Register a queue to receive events.

        Args:
            queue: An asyncio.Queue to receive events
        """

    async def publish(self, event: Dict[str, Any]) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: The event to publish
        """

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """
        Unregister a queue from receiving events.

        Args:
            queue: The queue to unregister
        """

    def create_background_task(self, coroutine) -> asyncio.Task:
        """
        Create a tracked background task.

        Args:
            coroutine: The coroutine to run as a task

        Returns:
            The created task
        """

    async def shutdown(self) -> None:
        """
        Shutdown the event bus.
        Cancel all active tasks and clear subscribers.
        """
```

## Event Schema

### Standard Event Format

Every event must include the following fields:

```json
{
  "type": "event_type",           // Required: String identifying the event type
  "data": { ... },                // Required: Event-specific payload
  "user_id": "user-id",           // Required: ID of the user the event relates to
  "timestamp": "ISO-timestamp",   // Required: When the event was created
  "metadata": { ... }             // Optional: Additional contextual information
}
```

### Required Fields

| Field       | Type   | Description           | Validation Rules                         |
| ----------- | ------ | --------------------- | ---------------------------------------- |
| `type`      | String | Event type identifier | Non-empty string                         |
| `data`      | Object | Event payload         | Valid JSON object                        |
| `user_id`   | String | User identifier       | Non-empty string, must match UUID format |
| `timestamp` | String | Event creation time   | ISO-8601 format (YYYY-MM-DDTHH:MM:SSZ)   |

### Optional Fields

| Field      | Type   | Description            |
| ---------- | ------ | ---------------------- |
| `metadata` | Object | Additional information |

### Standard Event Types

| Event Type               | Description                 | Data Fields                                 |
| ------------------------ | --------------------------- | ------------------------------------------- |
| `input`                  | Input received from client  | `content`, `conversation_id`, `timestamp`   |
| `output`                 | Output to be sent to client | `content`, `conversation_id`, `timestamp`   |
| `typing`                 | Typing indicator            | `is_typing`, `conversation_id`, `timestamp` |
| `heartbeat`              | Connection keepalive        | `timestamp`                                 |
| `error`                  | Error notification          | `message`, `code`, `timestamp`              |
| `connection_established` | SSE connection established  | `timestamp`                                 |

### Example Events

#### Input Event

```json
{
  "type": "input",
  "data": {
    "content": "Hello, Cortex!",
    "conversation_id": "850e8400-e29b-41d4-a716-446655440333",
    "timestamp": "2025-03-20T10:15:30Z"
  },
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-03-20T10:15:30Z",
  "metadata": {
    "client_id": "web-chat-client",
    "client_version": "1.0.0"
  }
}
```

#### Output Event

```json
{
  "type": "output",
  "data": {
    "content": "I'm processing your request.",
    "conversation_id": "850e8400-e29b-41d4-a716-446655440333",
    "timestamp": "2025-03-20T10:15:32Z"
  },
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-03-20T10:15:32Z",
  "metadata": {}
}
```

#### Typing Event

```json
{
  "type": "typing",
  "data": {
    "is_typing": true,
    "conversation_id": "850e8400-e29b-41d4-a716-446655440333",
    "timestamp": "2025-03-20T10:15:31Z"
  },
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-03-20T10:15:31Z",
  "metadata": {}
}
```

#### Heartbeat Event

```json
{
  "type": "heartbeat",
  "data": {},
  "timestamp": "2025-03-20T10:16:00Z"
}
```

#### Error Event

```json
{
  "type": "error",
  "data": {
    "message": "Failed to process request",
    "code": "processing_error",
    "timestamp": "2025-03-20T10:15:35Z"
  },
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-03-20T10:15:35Z",
  "metadata": {
    "request_id": "req-123456"
  }
}
```

## Implementation Details

### In-Memory Implementation

The Phase 1 implementation uses a simple in-memory approach with the following characteristics:

1. **Storage**: A list of asyncio.Queue objects
2. **Subscription**: Adding a queue to the list
3. **Publishing**: Sending the event to each queue
4. **Unsubscription**: Removing a queue from the list
5. **Background Tasks**: Tracked with a set of asyncio.Task objects

```python
import asyncio
import logging
from typing import Dict, List, Any, Set

logger = logging.getLogger(__name__)

class EventBus:
    """
    Simple in-memory event bus for internal communication.
    """
    def __init__(self):
        self.subscribers: List[asyncio.Queue] = []
        self._active_tasks: Set[asyncio.Task] = set()

    def subscribe(self, queue: asyncio.Queue) -> None:
        """
        Register a queue to receive events.

        Args:
            queue: An asyncio.Queue to receive events
        """
        self.subscribers.append(queue)
        logger.debug(f"Subscribed new queue. Total subscribers: {len(self.subscribers)}")

    async def publish(self, event: Dict[str, Any]) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: The event to publish
        """
        for queue in self.subscribers:
            try:
                await queue.put(event)
            except Exception as e:
                logger.error(f"Failed to publish event to subscriber: {e}")

        logger.debug(f"Published event: {event.get('type')} to {len(self.subscribers)} subscribers")

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """
        Unregister a queue from receiving events.

        Args:
            queue: The queue to unregister
        """
        if queue in self.subscribers:
            self.subscribers.remove(queue)
            logger.debug(f"Unsubscribed queue. Remaining subscribers: {len(self.subscribers)}")

    def create_background_task(self, coroutine) -> asyncio.Task:
        """
        Create a tracked background task.

        Args:
            coroutine: The coroutine to run as a task

        Returns:
            The created task
        """
        task = asyncio.create_task(coroutine)
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
        return task

    async def shutdown(self) -> None:
        """
        Shutdown the event bus.
        Cancel all active tasks and clear subscribers.
        """
        # Cancel all active tasks
        for task in self._active_tasks:
            task.cancel()

        # Wait for all tasks to complete
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        # Clear subscribers
        self.subscribers.clear()
        logger.info("Event bus shut down")

# Global event bus instance
event_bus = EventBus()
```

### Key Implementation Notes

1. **No Filtering at Source**: All subscribers receive all events
2. **Filtering at Consumption**: Subscribers filter events based on user_id
3. **Exception Handling**: Errors in one subscriber don't affect others
4. **Task Tracking**: Background tasks are tracked for proper cleanup
5. **Graceful Shutdown**: Includes cancellation of tasks and clearing subscribers

## Subscription and Publishing Patterns

### Subscription Lifecycle

1. **Creation**: Create an asyncio.Queue for the subscription
2. **Registration**: Call `event_bus.subscribe(queue)` with the queue
3. **Consumption**: Await events from the queue
4. **Filtering**: Filter events based on user_id or other criteria
5. **Cleanup**: Call `event_bus.unsubscribe(queue)` when done

### Publishing Patterns

1. **Event Creation**: Construct an event dictionary with required fields
2. **Validation**: Ensure the event has all required fields
3. **Publication**: Call `await event_bus.publish(event)`
4. **Error Handling**: Handle any exceptions during publishing

### SSE Integration Pattern

The most common use case is integrating the Event Bus with Server-Sent Events (SSE):

```python
# Create a queue for this connection
queue = asyncio.Queue()

# Subscribe to event bus
event_bus.subscribe(queue)

async def event_generator():
    """Generate SSE events from the queue."""
    try:
        while True:
            # Get event from queue
            event = await queue.get()

            # Filter events for this user
            if event.get("user_id") == user_id or event.get("type") == "heartbeat":
                # Format as SSE event
                yield f"data: {json.dumps(event)}\n\n"

            # Small delay to prevent CPU hogging
            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        # Client disconnected
        event_bus.unsubscribe(queue)
        raise
```

## Thread Safety and Concurrency

### Thread Safety

The event bus implementation uses asyncio primitives and is designed for use within an asynchronous context. It is **not thread-safe** for use across multiple threads. All interaction with the event bus should happen within the asyncio event loop.

### Concurrency Handling

1. **Queue-based Design**: Uses asyncio.Queue for thread-safe event delivery within asyncio
2. **Task Tracking**: Properly tracks and manages asyncio tasks
3. **Exception Isolation**: Errors in one subscriber don't affect others

### Subscription Concurrency

Multiple components can concurrently subscribe to the event bus. Each subscriber receives all events independently.

### Publishing Concurrency

Multiple components can concurrently publish events to the event bus. Events are processed sequentially per subscriber due to the queue-based design.

## Memory Management

### Potential Memory Leaks

The most common source of memory leaks with the event bus is **forgotten subscriptions**. If a component subscribes but never unsubscribes, the queue will remain in memory forever.

### Prevention Strategies

1. **Always Unsubscribe**: Always call `unsubscribe()` when a subscription is no longer needed
2. **Use try/finally**: Place unsubscribe calls in finally blocks to ensure they run
3. **Handle CancelledError**: Ensure unsubscription happens when coroutines are cancelled
4. **Track Active Tasks**: Use the task tracking mechanism for background processing

### Example: Proper Cleanup

```python
# Create queue and subscribe
queue = asyncio.Queue()
event_bus.subscribe(queue)

try:
    # Use the subscription
    while True:
        event = await queue.get()
        # Process event...
except Exception as e:
    logger.error(f"Error processing events: {e}")
finally:
    # Always unsubscribe to prevent memory leaks
    event_bus.unsubscribe(queue)
```

## Performance Considerations

### Current Limitations

The Phase 1 implementation prioritizes simplicity over performance:

1. **Linear Scaling**: Publishing time scales linearly with the number of subscribers
2. **No Back-pressure Control**: Fast publishers can overwhelm slow consumers
3. **Full Event Delivery**: All subscribers receive all events (no topic-based filtering)
4. **In-Memory Only**: No persistence or replay capability

### Optimization Opportunities

For Phase 1, these limitations are acceptable given the expected scale. Future phases might implement:

1. **Topic-based Routing**: Subscribe to specific event types
2. **Consumer Groups**: Allow multiple consumers to share work
3. **Backpressure Controls**: Prevent overwhelming slow consumers
4. **Persistence**: Store events for replay or recovery

## Testing

### Unit Testing Approaches

1. **Direct Testing**: Create an instance and test subscribe/publish directly

```python
@pytest.mark.asyncio
async def test_event_bus():
    bus = EventBus()
    queue = asyncio.Queue()

    bus.subscribe(queue)

    test_event = {"type": "test", "data": {}, "user_id": "test-user", "timestamp": "2023-01-01T00:00:00Z"}
    await bus.publish(test_event)

    received = await queue.get()
    assert received == test_event
```

2. **Mock Subscribers**: Use mock queues to verify behavior

```python
@pytest.mark.asyncio
async def test_event_bus_multiple_subscribers():
    bus = EventBus()
    queue1 = asyncio.Queue()
    queue2 = asyncio.Queue()

    bus.subscribe(queue1)
    bus.subscribe(queue2)

    test_event = {"type": "test", "data": {}, "user_id": "test-user", "timestamp": "2023-01-01T00:00:00Z"}
    await bus.publish(test_event)

    received1 = await queue1.get()
    received2 = await queue2.get()

    assert received1 == test_event
    assert received2 == test_event
```

### Integration Testing

When testing components that use the event bus:

1. **Use Dependency Injection**: Pass the event bus instance to components
2. **Mock the Event Bus**: Create a mock bus for isolation testing
3. **End-to-End Testing**: Test the complete flow with real event bus

### Test Pattern: Producer-Consumer

```python
@pytest.mark.asyncio
async def test_producer_consumer():
    bus = EventBus()
    queue = asyncio.Queue()
    bus.subscribe(queue)

    # Test producer
    async def producer():
        for i in range(5):
            event = {
                "type": "test",
                "data": {"value": i},
                "user_id": "test-user",
                "timestamp": datetime.now().isoformat()
            }
            await bus.publish(event)

    # Test consumer
    received_events = []
    async def consumer():
        for _ in range(5):
            event = await queue.get()
            received_events.append(event)

    # Run both concurrently
    producer_task = asyncio.create_task(producer())
    consumer_task = asyncio.create_task(consumer())

    await asyncio.gather(producer_task, consumer_task)

    # Verify
    assert len(received_events) == 5
    assert all(e["type"] == "test" for e in received_events)
```

## Best Practices

### Creating Events

1. **Complete Events**: Always include all required fields
2. **ISO-8601 Timestamps**: Use ISO format for all timestamps
3. **Minimal Data**: Include only necessary information in events
4. **Proper User ID**: Always include the correct user_id for partitioning
5. **Descriptive Types**: Use clear, descriptive event types

### Subscribing to Events

1. **Queue Per Consumer**: Create a separate queue for each logical consumer
2. **Always Unsubscribe**: Never forget to unsubscribe when done
3. **Handle Exceptions**: Properly handle exceptions in event processing
4. **Filter Early**: Filter events as early as possible in the processing pipeline
5. **Clean Up Resources**: Release any resources associated with the subscription

### Handling Backpressure

In Phase 1, there's no built-in backpressure control. Consumers should:

1. **Process Quickly**: Keep event processing as fast as possible
2. **Limit Queue Size**: Consider using bounded queues where appropriate
3. **Monitor Queue Growth**: Log warnings if queues grow too large
4. **Graceful Degradation**: Have strategies for handling event overload

### Error Handling

1. **Publish Errors**: The event bus swallows exceptions during publish operations
2. **Consumer Errors**: Consumers are responsible for handling their own errors
3. **Log Errors**: Always log errors for debugging
4. **Don't Block**: Never block the event loop in event handlers

## Common Pitfalls

### Memory Leaks

1. **Forgotten Subscriptions**: Not unsubscribing when done
2. **Orphaned Queues**: Losing references to queues without unsubscribing
3. **Uncancelled Tasks**: Not properly managing background tasks

### Concurrency Issues

1. **Blocking the Event Loop**: Using blocking operations in event handlers
2. **Task Starvation**: Creating too many concurrent tasks
3. **Callback Hell**: Nesting callbacks instead of using async/await

### Event Ordering

1. **No Order Guarantee**: Events aren't guaranteed to be processed in publication order
2. **Cross-Subscriber Timing**: Don't make timing assumptions across subscribers
3. **Race Conditions**: Avoid race conditions in event handlers

## Extensions for Future Phases

The current event bus implementation is deliberately simple for Phase 1. Future phases might extend it with:

1. **Topic-Based Routing**: Subscribe to specific event types
2. **Persistence**: Store events for replay or recovery
3. **Distributed Implementation**: Scale across multiple processes or machines
4. **Delivery Guarantees**: At-least-once or exactly-once delivery
5. **Event Schema Validation**: Validate events against schemas
6. **Monitoring and Metrics**: Track event flow and performance

## Conclusion

The event bus is a critical component of the Cortex Core architecture, enabling loose coupling between components. The Phase 1 implementation focuses on simplicity and reliability, with a minimal API that covers the essential operations for publish-subscribe communication.

By following the patterns and best practices outlined in this document, you can effectively use the event bus for internal communication while avoiding common pitfalls.
