"""
SSE Event Subscriber implementation for Cortex Core.

Subscribes to relevant events in the event system and broadcasts them 
to the appropriate SSE connections. Uses domain models for events.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime, timezone

from app.utils.logger import logger
from app.interfaces.router import EventSystemInterface
from app.components.sse.manager import SSEConnectionManager
from app.models.domain.sse import SSEEvent

class SSEEventSubscriber:
    """
    Subscribes to relevant events in the event system and broadcasts them
    to the appropriate SSE connections.
    
    Uses domain models for events internally and in communications with
    the SSE connection manager, following the domain-driven repository architecture.
    
    This implementation demonstrates several key principles:
    1. Creation and use of proper domain models (SSEEvent) for event data
    2. Clear separation between event handling and connection management
    3. Type safety through Pydantic domain models
    4. Consistent patterns for event creation and processing
    
    By using domain models throughout the event flow, we ensure consistency
    and maintain a clear separation between different layers of the system.
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
        
        # Define event patterns and corresponding resource ID extractors
        self.event_patterns = {
            "conversation.*": ("conversation_id", "conversation"),
            "workspace.*": ("workspace_id", "workspace"),
            "user.*": ("user_id", "user"),
            "global.*": (None, "global")  # Special case for global events
        }
        
    async def initialize(self):
        """Subscribe to all relevant events"""
        # Subscribe to all event patterns
        for pattern, (id_key, channel_type) in self.event_patterns.items():
            sub_id = await self.event_system.subscribe(
                pattern, self._create_event_handler(id_key, channel_type)
            )
            self.subscriptions.append(sub_id)
            logger.debug(f"Subscribed to {pattern} events with subscription ID {sub_id}")
        
        logger.info(f"SSE Event Subscriber initialized with {len(self.subscriptions)} event pattern subscriptions")
    
    def _create_event_handler(self, 
                             resource_id_key: Optional[str], 
                             channel_type: str) -> Callable[[str, Any], Awaitable[None]]:
        """
        Create an event handler function for a specific channel type.
        
        This factory method creates specialized event handlers for different
        channel types, with common handling logic but specific resource ID extraction.
        
        Args:
            resource_id_key: Key to extract resource ID from event payload (None for global)
            channel_type: Type of channel (conversation, workspace, user, global)
            
        Returns:
            Async function that handles events for the specified channel type
        """
        async def event_handler(event_type: str, payload):
            """
            Handle events for a specific channel type
            
            Args:
                event_type: Type of the event
                payload: Event payload with full event data
            """
            # For global events, resource ID is always "global"
            if channel_type == "global":
                resource_id = "global"
            else:
                # Extract resource ID from payload
                resource_id = payload.data.get(resource_id_key)
                if not resource_id:
                    logger.warning(
                        f"Missing {resource_id_key} in {event_type} event payload: {payload.data}"
                    )
                    return
            
            # Create domain model for the event
            event = self._create_sse_event(
                event_type=event_type,
                data=payload.data,
                channel_type=channel_type,
                resource_id=resource_id
            )
            
            # Send event to connection manager
            await self.connection_manager.send_event(
                event.channel_type,
                event.resource_id,
                event.event_type,
                event.data
            )
        
        return event_handler
        
    def _create_sse_event(self, event_type: str, data: Dict[str, Any],
                         channel_type: str, resource_id: str) -> SSEEvent:
        """
        Create a domain model for an SSE event.
        
        This method demonstrates the domain-driven repository pattern by creating
        and returning a proper domain model object rather than using raw dictionaries.
        The domain model provides validation, consistent structure, and type safety.
        
        Args:
            event_type: Type of the event
            data: Event data payload
            channel_type: Type of channel (user, workspace, conversation, global)
            resource_id: ID of the resource
            
        Returns:
            SSEEvent domain model with all required fields properly initialized
        """
        # Generate a unique ID that includes relevant metadata
        event_id = f"{channel_type}:{resource_id}:{event_type}:{datetime.now(timezone.utc).isoformat()}"
        
        # Create a properly initialized domain model
        return SSEEvent(
            id=event_id,
            event_type=event_type,
            data=data,
            channel_type=channel_type,
            resource_id=resource_id,
            created_at=datetime.now(timezone.utc),
            metadata={}
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