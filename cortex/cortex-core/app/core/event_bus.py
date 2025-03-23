import asyncio
import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


class EventBus:
    """
    Simple in-memory event bus for internal communication.
    """

    def __init__(self) -> None:
        self.subscribers: List[asyncio.Queue[Dict[str, Any]]] = []
        self._active_tasks: Set[asyncio.Task[Any]] = set()

    def subscribe(self, queue: asyncio.Queue[Dict[str, Any]]) -> None:
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

    def unsubscribe(self, queue: asyncio.Queue[Dict[str, Any]]) -> None:
        """
        Unregister a queue from receiving events.

        Args:
            queue: The queue to unregister
        """
        if queue in self.subscribers:
            self.subscribers.remove(queue)
            logger.debug(f"Unsubscribed queue. Remaining subscribers: {len(self.subscribers)}")

    def create_background_task(self, coroutine: Any) -> asyncio.Task[Any]:
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
