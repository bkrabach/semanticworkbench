"""
Event System Implementation for Cortex Core.

This module provides a simple, topic-based event system for decoupled communication
between components. It follows the implementation philosophy of ruthless simplicity
while maintaining the core architectural pattern.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional

from app.utils.logger import get_logger
from app.interfaces.event_system import EventSystemInterface, EventCallback

logger = get_logger(__name__)


class EventPayload:
    """
    Standard payload for events.
    
    This class provides a consistent structure for all events in the system.
    """
    
    def __init__(
        self,
        topic: str,
        data: Dict[str, Any],
        source: str,
        correlation_id: Optional[str] = None
    ):
        """
        Initialize an event payload.
        
        Args:
            topic: The topic the event was published to
            data: The event data
            source: The component that generated the event
            correlation_id: Optional ID to correlate related events
        """
        self.topic = topic
        self.data = data
        self.source = source
        self.timestamp = time.time()
        self.id = str(uuid.uuid4())
        self.correlation_id = correlation_id


class EventManager(EventSystemInterface):
    """
    Simple topic-based event system implementation.
    
    This class provides a publish/subscribe mechanism for loosely coupled
    communication between components. It follows a simple topic-based approach
    without complex pattern matching.
    """
    
    def __init__(self):
        """Initialize the event system."""
        self.subscriptions: Dict[str, Dict[str, EventCallback]] = {}
        self.stats = {
            "events_published": 0,
            "events_delivered": 0,
            "subscriber_count": 0,
            "topics": {},
            "errors": 0,
            "start_time": time.time()
        }
    
    async def publish(
        self, 
        topic: str, 
        data: Dict[str, Any], 
        source: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Publish an event to all subscribers of a topic.
        
        Args:
            topic: The topic to publish to
            data: The event data
            source: The component that generated the event
            correlation_id: Optional ID to correlate related events
        """
        # Create the event payload
        payload = EventPayload(
            topic=topic,
            data=data,
            source=source,
            correlation_id=correlation_id
        )
        
        # Update stats
        self.stats["events_published"] += 1
        if topic not in self.stats["topics"]:
            self.stats["topics"][topic] = 0
        self.stats["topics"][topic] += 1
        
        logger.debug(f"Publishing event to topic '{topic}' from {source}")
        
        # Get subscribers for this topic
        subscribers = self.subscriptions.get(topic, {})
        if not subscribers:
            logger.debug(f"No subscribers for topic '{topic}'")
            return
        
        # Execute callbacks concurrently
        delivered_count = 0
        if subscribers:
            tasks = [
                self._execute_callback(callback, topic, payload) 
                for callback in subscribers.values()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful deliveries and errors
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error in event callback: {str(result)}")
                    self.stats["errors"] += 1
                else:
                    delivered_count += 1
        
        self.stats["events_delivered"] += delivered_count
    
    async def _execute_callback(
        self, 
        callback: EventCallback, 
        topic: str, 
        payload: EventPayload
    ) -> Optional[Exception]:
        """
        Execute a single callback with error handling.
        
        Args:
            callback: The callback function to execute
            topic: The topic the event was published to
            payload: The event payload
            
        Returns:
            None if successful, Exception if an error occurred
        """
        try:
            await callback(topic, payload.__dict__)
            return None
        except Exception as e:
            logger.error(f"Error in event callback: {str(e)}")
            return e
    
    async def subscribe(self, topic: str, callback: EventCallback) -> str:
        """
        Subscribe to events on a specific topic.
        
        Args:
            topic: The topic to subscribe to
            callback: The function to call when an event is published to the topic
            
        Returns:
            A subscription ID that can be used to unsubscribe
        """
        # Generate a unique subscription ID
        subscription_id = str(uuid.uuid4())
        
        # Ensure the topic exists in our dictionary
        if topic not in self.subscriptions:
            self.subscriptions[topic] = {}
        
        # Add the callback
        self.subscriptions[topic][subscription_id] = callback
        
        # Update stats
        self.stats["subscriber_count"] += 1
        
        logger.debug(f"Added subscription {subscription_id} for topic '{topic}'")
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscription_id: The ID returned from subscribe
            
        Returns:
            True if the subscription was found and removed, False otherwise
        """
        # Look for the subscription ID in all topics
        for topic in list(self.subscriptions.keys()):
            if subscription_id in self.subscriptions[topic]:
                del self.subscriptions[topic][subscription_id]
                logger.debug(f"Removed subscription {subscription_id}")
                
                # Update stats
                self.stats["subscriber_count"] -= 1
                
                # Clean up empty topics
                if not self.subscriptions[topic]:
                    del self.subscriptions[topic]
                
                return True
        
        return False
    
    async def get_subscriber_count(self, topic: Optional[str] = None) -> int:
        """
        Get the number of subscribers for a topic.
        
        Args:
            topic: The topic to get the subscriber count for, or None for all topics
            
        Returns:
            The number of subscribers
        """
        if topic:
            return len(self.subscriptions.get(topic, {}))
        else:
            return sum(len(subscribers) for subscribers in self.subscriptions.values())
    
    async def get_topics(self) -> List[str]:
        """
        Get a list of all active topics.
        
        Returns:
            A list of all topics with active subscribers
        """
        return list(self.subscriptions.keys())


# Global event manager instance
_event_manager: Optional[EventManager] = None


def get_event_manager() -> EventManager:
    """
    Get the global event manager instance.
    
    Returns:
        The event manager instance
    """
    global _event_manager
    if _event_manager is None:
        _event_manager = EventManager()
    return _event_manager