"""
Event System Interface for Cortex Core.

This module defines the interface for the event system that enables loosely coupled
communication between components. The event system follows a simple topic-based
publish/subscribe pattern without complex pattern matching.
"""

from typing import Dict, Any, Optional, Callable, Protocol, Awaitable, List


# Type for event callback functions
EventCallback = Callable[[str, Dict[str, Any]], Awaitable[None]]


class EventSystemInterface(Protocol):
    """
    Interface for the event system that enables communication between components.
    
    The event system follows a simple topic-based publish/subscribe pattern.
    Components can publish events to specific topics, and other components can
    subscribe to those topics to receive events.
    """
    
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
        ...
    
    async def subscribe(self, topic: str, callback: EventCallback) -> str:
        """
        Subscribe to events on a specific topic.
        
        Args:
            topic: The topic to subscribe to
            callback: The function to call when an event is published to the topic
            
        Returns:
            A subscription ID that can be used to unsubscribe
        """
        ...
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscription_id: The ID returned from subscribe
            
        Returns:
            True if the subscription was found and removed, False otherwise
        """
        ...
    
    async def get_subscriber_count(self, topic: Optional[str] = None) -> int:
        """
        Get the number of subscribers for a topic.
        
        Args:
            topic: The topic to get the subscriber count for, or None for all topics
            
        Returns:
            The number of subscribers
        """
        ...
    
    async def get_topics(self) -> List[str]:
        """
        Get a list of all active topics.
        
        Returns:
            A list of all topics with active subscribers
        """
        ...