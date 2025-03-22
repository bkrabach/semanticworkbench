from typing import Callable, Dict, List, Set
import asyncio

class EventBus:
    """In-memory publish/subscribe event bus for internal communication."""
    def __init__(self):
        """Initialize the event bus with no subscribers."""
        # Set of subscriber queues
        self.subscribers: Set[asyncio.Queue] = set()
        
        # For backward compatibility with original implementation
        self.type_subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, queue: asyncio.Queue):
        """Subscribe a queue to all events."""
        self.subscribers.add(queue)
        
    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe a queue from all events."""
        if queue in self.subscribers:
            self.subscribers.remove(queue)
    
    # For backward compatibility
    def subscribe_to_type(self, event_type: str, handler: Callable):
        """Subscribe a handler function to a given event type."""
        if event_type not in self.type_subscribers:
            self.type_subscribers[event_type] = []
        self.type_subscribers[event_type].append(handler)

    async def publish(self, event: dict):
        """Publish an event to all subscribers."""
        # Put the event in all subscriber queues
        for queue in self.subscribers:
            await queue.put(event)
        
        # For backward compatibility
        event_type = event.get("type")
        if event_type and event_type in self.type_subscribers:
            for handler in self.type_subscribers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    # In a real implementation, log the error and continue
                    print(f"Error in event handler for {event_type}: {e}")
