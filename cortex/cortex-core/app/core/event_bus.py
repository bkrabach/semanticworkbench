import asyncio
import logging
from typing import Any, Dict, List, Optional


# Set up logger for the event bus
logger = logging.getLogger(__name__)


class EventBus:
    """
    Simple in-memory pub/sub event bus for internal communication.
    
    This implements a minimalist event system that allows components to communicate
    without direct coupling. Components can subscribe to specific event types and
    filter on user_id or conversation_id.
    
    Standard event types include:
    - "input": User messages entering the system
    - "output": Assistant responses being delivered to clients
    - "error": Error events for client notification
    """

    def __init__(self) -> None:
        """Initialize the event bus with no subscribers."""
        self._subscriptions: List[Dict[str, Any]] = []

    def subscribe(
        self, event_type: Optional[str] = None, conversation_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> asyncio.Queue:
        """
        Subscribe to events on the bus, optionally filtering by event_type, conversation_id, and/or user_id.
        
        Returns an asyncio.Queue that will receive matching events.
        The caller is responsible for reading from the queue and eventually unsubscribing.

        Args:
            event_type: Optional event type to filter (e.g., "input", "output")
            conversation_id: Optional conversation ID to filter
            user_id: Optional user ID to filter

        Returns:
            An asyncio.Queue that will receive matching events
        """
        # Create a new queue for this subscriber
        queue: asyncio.Queue = asyncio.Queue()

        # Register the subscription with the specified filters
        sub_record = {
            "queue": queue,
            "event_type": event_type,
            "conversation_id": conversation_id,
            "user_id": user_id,
        }
        self._subscriptions.append(sub_record)
        return queue

    async def publish(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Publish a new event to the bus. All subscribers with matching filters will receive it.
        
        This is an async method that awaits delivery to all subscribers.

        Args:
            event_type: The type/name of the event (e.g., "input", "output", "error")
            event_data: Event payload dict, may contain conversation_id and user_id for filtering
        """
        # Make a copy of event_data to avoid modifying the original
        event_data_copy = dict(event_data)
        
        # Ensure the event data includes its type
        event_data_copy["type"] = event_type

        # Create a copy of subscriptions for safe iteration
        subs_copy = list(self._subscriptions)

        # Deliver the event to matching subscribers
        for sub in subs_copy:
            if not self._matches_subscription(sub, event_type, event_data_copy):
                continue

            # Deliver the event to this subscriber
            try:
                await sub["queue"].put(event_data_copy)
            except Exception as e:
                # If delivery fails, remove the subscription
                logger.error(f"Error delivering event to subscriber: {e}")
                if sub in self._subscriptions:
                    self._subscriptions.remove(sub)

    def _matches_subscription(
        self, sub: Dict[str, Any], event_type: str, event_data: Dict[str, Any]
    ) -> bool:
        """
        Check if an event matches a subscription's filters.
        
        Args:
            sub: The subscription record to check against
            event_type: Type of the event
            event_data: Event data containing potential filter fields
            
        Returns:
            True if the event should be delivered to this subscription
        """
        # Check event_type filter
        if sub["event_type"] is not None and sub["event_type"] != event_type:
            return False

        # Check conversation_id filter
        if sub["conversation_id"] is not None:
            if "conversation_id" not in event_data or event_data.get("conversation_id") != sub["conversation_id"]:
                return False

        # Check user_id filter
        if sub["user_id"] is not None:
            if "user_id" not in event_data or event_data.get("user_id") != sub["user_id"]:
                return False
                
        return True

    def unsubscribe(self, queue: asyncio.Queue, event_type: Optional[str] = None) -> None:
        """
        Unsubscribe a previously subscribed queue from the bus.
        
        This will stop delivering events to that queue and allow it to be garbage-collected.
        
        Args:
            queue: The queue to unsubscribe
            event_type: If provided, only unsubscribe from this specific event type
        """
        if event_type is not None:
            # Remove subscriptions with this queue and event type
            self._subscriptions = [
                sub for sub in self._subscriptions 
                if not (sub["queue"] is queue and sub["event_type"] == event_type)
            ]
        else:
            # Remove all subscriptions with this queue
            self._subscriptions = [sub for sub in self._subscriptions if sub["queue"] is not queue]
