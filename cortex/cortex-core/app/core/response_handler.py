import asyncio
from typing import Optional, Dict, Any

from app.backend.cognition_client import CognitionClient
from app.backend.memory_client import MemoryClient
from app.core.event_bus import EventBus


class ResponseHandler:
    """
    Response handler that processes input events and produces output events.
    Orchestrates interactions between event bus, memory client, and cognition client.
    """

    def __init__(self, event_bus: EventBus, memory_client: MemoryClient, cognition_client: CognitionClient):
        """Initialize with required dependencies."""
        self.event_bus = event_bus
        self.memory_client = memory_client
        self.cognition_client = cognition_client
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.running = False

    async def start(self):
        """Start the response handler."""
        self.running = True
        self.input_queue = self.event_bus.subscribe(event_type="user_message")
        await self.process_events()

    async def stop(self):
        """Stop the response handler and clean up resources."""
        self.running = False
        self.event_bus.unsubscribe(self.input_queue)
        
        # Close client connections
        await self.memory_client.close()
        await self.cognition_client.close()

    async def process_events(self):
        """
        Process events from the input queue.
        This is the core orchestration loop that handles user messages.
        """
        while self.running:
            try:
                # Get the next event with a timeout (allows checking if we should stop)
                try:
                    event = await asyncio.wait_for(self.input_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Process the event
                await self.handle_input_event(event)

                # Mark the task as done
                self.input_queue.task_done()

            except Exception as e:
                print(f"Error processing event: {e}")

    async def handle_input_event(self, event: Dict[str, Any]):
        """
        Handle an input event by orchestrating calls to memory and cognition services.
        This implements the processing pipeline:
        1. Retrieve relevant memory
        2. Evaluate context with the cognition service
        3. Store the response in memory
        4. Publish response as an event
        """
        # Extract needed info from the event
        user_id = event.get("user_id")
        conversation_id = event.get("conversation_id")
        message_data = event.get("data", {})
        message_content = message_data.get("content", "")

        if not user_id or not conversation_id or not message_content:
            print("Missing required fields in event")
            return

        try:
            # 1. Store the user message in memory
            await self.memory_client.store_message(
                user_id=user_id,
                conversation_id=conversation_id,
                content=message_content,
                role="user",
                metadata=message_data.get("metadata", {})
            )

            # 2. Retrieve conversation context from memory
            memory_snippets = await self.memory_client.get_recent_messages(
                user_id=user_id,
                conversation_id=conversation_id,
                limit=10
            )

            # 3. Generate a response by evaluating context
            response = await self.cognition_client.evaluate_context(
                user_id=user_id,
                conversation_id=conversation_id,
                message=message_content,
                memory_snippets=memory_snippets,
                expert_insights=[]  # Will add domain expert results here when implemented
            )

            # 4. Store the assistant response in memory
            await self.memory_client.store_message(
                user_id=user_id,
                conversation_id=conversation_id,
                content=response,
                role="assistant"
            )

            # 5. Publish output event with the response
            output_event = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "data": {"content": response, "role": "assistant"},
            }
            await self.event_bus.publish_async("assistant_response", output_event)

        except Exception as e:
            print(f"Error handling input event: {e}")
            # Publish error event
            error_event = {
                "type": "error",
                "user_id": user_id,
                "conversation_id": conversation_id,
                "data": {"message": f"Error processing message: {str(e)}"},
            }
            await self.event_bus.publish_async("error", error_event)


async def create_response_handler(
    event_bus: Optional[EventBus] = None,
    memory_url: str = "http://localhost:5001/sse",
    cognition_url: str = "http://localhost:5000/sse"
) -> ResponseHandler:
    """
    Factory function to create and start a response handler.
    
    Args:
        event_bus: Optional event bus instance. If None, a new one will be created.
        memory_url: URL for the memory service SSE endpoint
        cognition_url: URL for the cognition service SSE endpoint
    
    Returns:
        An initialized and started ResponseHandler instance
    """
    from app.core.event_bus import event_bus as global_event_bus
    
    if event_bus is None:
        event_bus = global_event_bus

    memory_client = MemoryClient(service_url=memory_url)
    cognition_client = CognitionClient(service_url=cognition_url)

    handler = ResponseHandler(
        event_bus=event_bus,
        memory_client=memory_client,
        cognition_client=cognition_client
    )

    # Start the handler in the background
    asyncio.create_task(handler.start())

    return handler