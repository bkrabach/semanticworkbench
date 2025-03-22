import asyncio
from typing import Any, Dict, Set


class EventBus:
    """In-memory publish/subscribe event bus for internal communication."""

    def __init__(self) -> None:
        """Initialize the event bus with no subscribers."""
        # Set of subscriber queues
        self.subscribers: Set[asyncio.Queue] = set()

    def subscribe(self, queue: asyncio.Queue) -> None:
        """Subscribe a queue to all events."""
        self.subscribers.add(queue)

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe a queue from all events."""
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    async def publish(self, event: Dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        # Put the event in all subscriber queues
        for queue in self.subscribers:
            await queue.put(event)


# Create a singleton instance for global use
event_bus = EventBus()
