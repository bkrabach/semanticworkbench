"""
Event System Implementation
Provides a message bus for decoupled communication between components
"""

import asyncio
import uuid
import re
import time
import logging
from typing import Dict, List, Any, Optional, ClassVar

from app.interfaces.router import EventSystemInterface, EventCallback
from pydantic import BaseModel, Field, ConfigDict


class EventPayload(BaseModel):
    """
    Standardized structure for all events in the system

    Attributes:
        event_type: Type of the event (e.g., 'conversation.message.created')
        data: Event-specific data payload
        source: Component that generated the event
        timestamp: Unix timestamp of when the event was created
        trace_id: ID for tracing event chains (automatically generated if not provided)
        correlation_id: Optional ID to correlate related events
    """
    event_type: str
    data: Dict[str, Any]
    source: str
    timestamp: float = Field(default_factory=time.time)
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "event_type": "conversation.message.created",
                "data": {"conversation_id": "123", "message_id": "456"},
                "source": "conversation_processor",
                "timestamp": 1625097600.0
            }
        }
    )


class EventSystem(EventSystemInterface):
    """
    Enhanced implementation of the Event System

    Features:
    - Structured event payloads
    - Event tracing and correlation
    - Stats collection
    - Pattern-based subscription
    - Error isolation between subscribers
    """

    def __init__(self):
        """Initialize the event system"""
        self.subscriptions: Dict[str, Dict[str, EventCallback]] = {}
        self.logger = logging.getLogger(__name__)
        self.stats = {
            "events_published": 0,
            "events_delivered": 0,
            "subscriber_count": 0,
            "event_types": {},
            "errors": 0,
            "start_time": time.time()
        }

    async def publish(self, event_type: str, data: Dict[str, Any], source: str,
                    trace_id: Optional[str] = None,
                    correlation_id: Optional[str] = None) -> None:
        """
        Publish an event to all subscribers

        Args:
            event_type: Type of the event (e.g., 'conversation.message.created')
            data: Event data
            source: Component that generated the event
            trace_id: Optional ID for tracing event chains
            correlation_id: Optional ID to correlate related events
        """
        # Create a standardized event payload
        payload = EventPayload(
            event_type=event_type,
            data=data,
            source=source,
            timestamp=time.time(),
            trace_id=trace_id or str(uuid.uuid4()),
            correlation_id=correlation_id
        )

        # Update stats
        self.stats["events_published"] += 1
        if event_type not in self.stats["event_types"]:
            self.stats["event_types"][event_type] = 0
        self.stats["event_types"][event_type] += 1

        self.logger.debug(f"Publishing event: {event_type} from {source}, total published: {self.stats['events_published']}")

        # Gather all matching callbacks
        callbacks: List[EventCallback] = []
        for pattern, subscribers in self.subscriptions.items():
            if self._match_pattern(pattern, event_type):
                callbacks.extend(subscribers.values())

        # Execute callbacks concurrently
        delivered_count = 0
        if callbacks:
            tasks = [self._execute_callback(callback, event_type, payload) for callback in callbacks]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successful deliveries and errors
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(f"Error in event callback: {str(result)}")
                    self.stats["errors"] += 1
                else:
                    delivered_count += 1

        self.stats["events_delivered"] += delivered_count

    async def _execute_callback(self, callback: EventCallback, event_type: str, payload: EventPayload) -> Optional[Exception]:
        """
        Execute a single callback with error handling

        Args:
            callback: The callback function to execute
            event_type: The event type
            payload: The event payload

        Returns:
            None if successful, Exception if an error occurred
        """
        try:
            await callback(event_type, payload)
            return None
        except Exception as e:
            self.logger.error(f"Error in event callback: {str(e)}")
            return e

    async def subscribe(self, event_pattern: str, callback: EventCallback) -> str:
        """
        Subscribe to events matching a pattern

        Args:
            event_pattern: Pattern to match event types (can use wildcards)
            callback: Async function to call when matching events occur

        Returns:
            Subscription ID that can be used to unsubscribe
        """
        # Generate a unique subscription ID
        subscription_id = str(uuid.uuid4())

        # Ensure the pattern exists in our dictionary
        if event_pattern not in self.subscriptions:
            self.subscriptions[event_pattern] = {}

        # Add the callback
        self.subscriptions[event_pattern][subscription_id] = callback

        # Update stats
        self.stats["subscriber_count"] += 1

        self.logger.debug(f"Added subscription {subscription_id} for pattern {event_pattern}")
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events

        Args:
            subscription_id: ID returned from subscribe

        Returns:
            Boolean indicating success
        """
        # Look for the subscription ID in all patterns
        for pattern in list(self.subscriptions.keys()):
            if subscription_id in self.subscriptions[pattern]:
                del self.subscriptions[pattern][subscription_id]
                self.logger.debug(f"Removed subscription {subscription_id}")

                # Update stats
                self.stats["subscriber_count"] -= 1

                # Clean up empty patterns
                if not self.subscriptions[pattern]:
                    del self.subscriptions[pattern]

                return True

        return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about event processing

        Returns:
            Dictionary with event statistics
        """
        # Calculate uptime
        uptime = time.time() - self.stats["start_time"]

        # Create a copy of stats with additional derived metrics
        stats = dict(self.stats)
        stats["uptime_seconds"] = uptime

        # Calculate events per second if uptime > 0
        if uptime > 0:
            stats["events_per_second"] = stats["events_published"] / uptime
        else:
            stats["events_per_second"] = 0

        return stats
        
    async def get_subscribers(self, event_type: str) -> List[str]:
        """
        Get all subscription IDs that would match a specific event type
        
        Args:
            event_type: The event type to check against all patterns
            
        Returns:
            List of subscription IDs that would receive this event
        """
        matching_subscriptions: List[str] = []
        
        for pattern, subscribers in self.subscriptions.items():
            if self._match_pattern(pattern, event_type):
                matching_subscriptions.extend(subscribers.keys())
                
        self.logger.debug(f"Found {len(matching_subscriptions)} matching subscribers for {event_type}")
        return matching_subscriptions

    def _match_pattern(self, pattern: str, event_type: str) -> bool:
        """
        Check if an event type matches a pattern

        Args:
            pattern: Pattern with wildcards (e.g., "conversation.*.message")
            event_type: Type to check

        Returns:
            True if the type matches the pattern
        """
        # Convert wildcard pattern to regex
        if pattern == "*":
            return True

        regex_pattern = pattern.replace(".", r"\.").replace("*", r"[^.]*")
        return bool(re.match(f"^{regex_pattern}$", event_type))


# Global event system instance
event_system = EventSystem()

def get_event_system() -> EventSystemInterface:
    """Get the global event system instance"""
    return event_system