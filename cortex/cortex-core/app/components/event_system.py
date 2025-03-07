"""
Event System Implementation
Provides a message bus for decoupled communication between components
"""

import asyncio
import uuid
import re
from typing import Dict, List, Any, Callable, Optional
import logging

from app.interfaces.router import EventSystemInterface, EventCallback


class SimpleEventSystem(EventSystemInterface):
    """
    Simple in-memory implementation of the Event System
    
    This implementation uses a dictionary of event patterns and callbacks
    to route events to subscribers. It supports wildcard patterns using
    regular expressions.
    """
    
    def __init__(self):
        """Initialize the event system"""
        self.subscriptions: Dict[str, Dict[str, EventCallback]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def publish(self, event_name: str, data: Any) -> None:
        """
        Publish an event to all subscribers
        
        Args:
            event_name: Name of the event
            data: Event data
        """
        self.logger.debug(f"Publishing event: {event_name}")
        
        # Gather all matching callbacks
        callbacks = []
        for pattern, subscribers in self.subscriptions.items():
            if self._match_pattern(pattern, event_name):
                callbacks.extend(subscribers.values())
        
        # Execute callbacks concurrently
        tasks = [callback(event_name, data) for callback in callbacks]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def subscribe(self, event_pattern: str, callback: EventCallback) -> str:
        """
        Subscribe to events matching a pattern
        
        Args:
            event_pattern: Pattern to match event names (can use wildcards)
            callback: Async function to call when matching events occur
            
        Returns:
            Subscription ID
        """
        # Generate a unique subscription ID
        subscription_id = str(uuid.uuid4())
        
        # Ensure the pattern exists in our dictionary
        if event_pattern not in self.subscriptions:
            self.subscriptions[event_pattern] = {}
        
        # Add the callback
        self.subscriptions[event_pattern][subscription_id] = callback
        
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
        for pattern in self.subscriptions:
            if subscription_id in self.subscriptions[pattern]:
                del self.subscriptions[pattern][subscription_id]
                self.logger.debug(f"Removed subscription {subscription_id}")
                
                # Clean up empty patterns
                if not self.subscriptions[pattern]:
                    del self.subscriptions[pattern]
                
                return True
        
        return False
    
    def _match_pattern(self, pattern: str, event_name: str) -> bool:
        """
        Check if an event name matches a pattern
        
        Args:
            pattern: Pattern with wildcards (e.g., "channel.*.message")
            event_name: Name to check
            
        Returns:
            True if the name matches the pattern
        """
        # Convert wildcard pattern to regex
        if pattern == "*":
            return True
        
        regex_pattern = pattern.replace(".", r"\.").replace("*", r"[^.]*")
        return bool(re.match(f"^{regex_pattern}$", event_name))


# Global event system instance
event_system = SimpleEventSystem()

def get_event_system() -> EventSystemInterface:
    """Get the global event system instance"""
    return event_system