"""
SSE Event Subscriber implementation for Cortex Core.

Subscribes to relevant events in the event system and broadcasts them 
to the appropriate SSE connections.
"""

from typing import Dict, Any, List
import logging

from app.utils.logger import logger
from app.interfaces.router import EventSystemInterface
from app.components.sse.manager import SSEConnectionManager

class SSEEventSubscriber:
    """
    Subscribes to relevant events in the event system and broadcasts them
    to the appropriate SSE connections.
    """
    
    def __init__(self, event_system: EventSystemInterface, connection_manager: SSEConnectionManager):
        """
        Initialize the event subscriber
        
        Args:
            event_system: Event system to subscribe to
            connection_manager: SSE connection manager to send events to
        """
        self.event_system = event_system
        self.connection_manager = connection_manager
        self.subscriptions: List[str] = []
        
    async def initialize(self):
        """Subscribe to all relevant events"""
        # Subscribe to conversation events
        sub_id = await self.event_system.subscribe(
            "conversation.*", self._handle_conversation_event
        )
        self.subscriptions.append(sub_id)
        
        # Subscribe to workspace events
        sub_id = await self.event_system.subscribe(
            "workspace.*", self._handle_workspace_event
        )
        self.subscriptions.append(sub_id)
        
        # Subscribe to user events
        sub_id = await self.event_system.subscribe(
            "user.*", self._handle_user_event
        )
        self.subscriptions.append(sub_id)
        
        # Subscribe to global events
        sub_id = await self.event_system.subscribe(
            "global.*", self._handle_global_event
        )
        self.subscriptions.append(sub_id)
        
        logger.info("SSE Event Subscriber initialized and subscribed to event patterns")
        
    async def _handle_conversation_event(self, event_type: str, payload):
        """
        Handle events related to conversations
        
        Args:
            event_type: Type of the event
            payload: Event payload with full event data
        """
        conversation_id = payload.data.get("conversation_id")
        if conversation_id:
            await self.connection_manager.send_event(
                "conversation",
                conversation_id,
                event_type,
                payload.data
            )
            
    async def _handle_workspace_event(self, event_type: str, payload):
        """
        Handle events related to workspaces
        
        Args:
            event_type: Type of the event
            payload: Event payload with full event data
        """
        workspace_id = payload.data.get("workspace_id")
        if workspace_id:
            await self.connection_manager.send_event(
                "workspace",
                workspace_id,
                event_type,
                payload.data
            )
            
    async def _handle_user_event(self, event_type: str, payload):
        """
        Handle events related to users
        
        Args:
            event_type: Type of the event
            payload: Event payload with full event data
        """
        user_id = payload.data.get("user_id")
        if user_id:
            await self.connection_manager.send_event(
                "user",
                user_id,
                event_type,
                payload.data
            )
            
    async def _handle_global_event(self, event_type: str, payload):
        """
        Handle global events
        
        Args:
            event_type: Type of the event
            payload: Event payload with full event data
        """
        await self.connection_manager.send_event(
            "global",
            "global",
            event_type,
            payload.data
        )
        
    async def cleanup(self):
        """Unsubscribe from all events"""
        for sub_id in self.subscriptions:
            try:
                await self.event_system.unsubscribe(sub_id)
            except Exception as e:
                logger.error(f"Error unsubscribing from event {sub_id}: {e}")
                
        self.subscriptions = []
        logger.info("SSE Event Subscriber cleaned up and unsubscribed from all events")