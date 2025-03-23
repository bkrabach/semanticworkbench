import asyncio
import logging
from typing import Any, Dict, List, Optional


class EventData(Dict[str, Any]):
    """Type definition for event data passed through the event bus."""

    pass


class SubscriptionRecord(Dict[str, Any]):
    """Type definition for subscription records in the event bus."""

    pass


# Set up logger for the event bus
logger = logging.getLogger(__name__)


class EventBus:
    """In-memory publish/subscribe event bus for internal communication."""

    def __init__(self) -> None:
        """Initialize the event bus with no subscribers."""
        # List of subscriber records
        # List of subscription records with filtering criteria
        self._subscriptions: List[SubscriptionRecord] = []

    def subscribe(
        self, event_type: Optional[str] = None, conversation_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> asyncio.Queue:
        """
        Subscribe to events on the bus, optionally filtering by event_type, conversation_id, and/or user_id.
        Returns an asyncio.Queue that will receive matching events.
        The caller is responsible for reading from the queue and eventually unsubscribing.

        Args:
            event_type: Optional event type to filter
            conversation_id: Optional conversation ID to filter
            user_id: Optional user ID to filter

        Returns:
            An asyncio.Queue that will receive matching events
        """
        # Create a new queue for this subscriber
        queue: asyncio.Queue = asyncio.Queue()

        # Register the subscription with the specified filters
        sub_record = SubscriptionRecord({
            "queue": queue,
            "event_type": event_type,
            "conversation_id": conversation_id,
            "user_id": user_id,
        })
        self._subscriptions.append(sub_record)
        return queue

    def publish(self, event_type: str, event_data: EventData) -> None:
        """
        Publish a new event to the bus.

        Args:
            event_type: The type/name of the event (e.g., "user_message", "assistant_response").
            event_data: Event payload containing event type and optionally conversation_id and
                        user_id for filtering.
        """
        # Ensure the event_data itself knows its type
        event_data.setdefault("type", event_type)

        # Create a copy of subscriptions for safe iteration
        subs_copy = list(self._subscriptions)

        # Deliver the event to matching subscribers
        for sub in subs_copy:
            # Check event_type filter
            if sub["event_type"] is not None and sub["event_type"] != event_type:
                continue

            # Check conversation_id filter
            if sub["conversation_id"] is not None:
                if "conversation_id" not in event_data or event_data.get("conversation_id") != sub["conversation_id"]:
                    continue

            # Check user_id filter
            if sub["user_id"] is not None:
                if "user_id" not in event_data or event_data.get("user_id") != sub["user_id"]:
                    continue

            # Deliver the event to this subscriber
            try:
                sub["queue"].put_nowait(event_data)
            except asyncio.QueueFull:
                # Skip if queue is full (unlikely with default unbounded queues)
                continue
            except Exception as e:
                # If delivery fails, remove the subscription
                logger.error(f"Error delivering event to subscriber: {e}")
                if sub in self._subscriptions:
                    self._subscriptions.remove(sub)

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """
        Unsubscribe a previously subscribed queue from the bus.
        This will stop delivering events to that queue and allow it to be garbage-collected.
        """
        # Remove all subscriptions with this queue
        self._subscriptions = [sub for sub in self._subscriptions if sub["queue"] is not queue]

    async def publish_async(self, event_type: str, event_data: EventData) -> None:
        """
        Async version of publish that awaits queue.put() for each subscriber.
        Use this when you need flow control or when running in an async context.

        Args:
            event_type: The type/name of the event (e.g., "user_message", "assistant_response").
            event_data: Event payload containing event type and optionally conversation_id and
                        user_id for filtering.
        """
        # Ensure the event_data itself knows its type
        event_data.setdefault("type", event_type)

        # Create a copy of subscriptions for safe iteration
        subs_copy = list(self._subscriptions)

        # Deliver the event to matching subscribers
        for sub in subs_copy:
            # Check event_type filter
            if sub["event_type"] is not None and sub["event_type"] != event_type:
                continue

            # Check conversation_id filter
            if sub["conversation_id"] is not None:
                if "conversation_id" not in event_data or event_data.get("conversation_id") != sub["conversation_id"]:
                    continue

            # Check user_id filter
            if sub["user_id"] is not None:
                if "user_id" not in event_data or event_data.get("user_id") != sub["user_id"]:
                    continue

            # Deliver the event to this subscriber
            try:
                await sub["queue"].put(event_data)
            except Exception as e:
                # If delivery fails, remove the subscription
                logger.error(f"Error delivering event to subscriber: {e}")
                if sub in self._subscriptions:
                    self._subscriptions.remove(sub)


# Create a singleton instance for global use
event_bus = EventBus()
