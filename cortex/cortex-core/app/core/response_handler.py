import asyncio
from typing import Optional

from app.backend.cognition_client import CognitionClient
from app.backend.memory_client import MemoryClient
from app.core.event_bus import EventBus


class ResponseHandler:
    """
    Response handler that processes input events and produces output events.
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
        self.event_bus.subscribe(self.input_queue)
        await self.process_events()

    async def stop(self):
        """Stop the response handler."""
        self.running = False
        self.event_bus.unsubscribe(self.input_queue)

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

    async def handle_input_event(self, event: dict):
        """
        Handle an input event by orchestrating calls to memory and cognition services.
        """
        # Extract needed info from the event
        user_id = event.get("user_id")
        conversation_id = event.get("conversation_id")
        message_content = event.get("data", {}).get("content", "")

        if not user_id or not conversation_id or not message_content:
            print("Missing required fields in event")
            return

        try:
            # 1. Retrieve conversation context from memory
            _ = await self.memory_client.get_recent_messages(user_id=user_id, conversation_id=conversation_id)

            # 2. Generate a response
            response = await self.cognition_client.generate_reply(
                user_id=user_id, conversation_id=conversation_id, message=message_content
            )

            # 3. Store the response in memory (would happen in real implementation)
            # await self.memory_client.store_message(...)

            # 4. Publish output event with the response
            await self.event_bus.publish({
                "type": "output",
                "user_id": user_id,
                "conversation_id": conversation_id,
                "data": {"content": response, "role": "assistant"},
            })

        except Exception as e:
            print(f"Error handling input event: {e}")
            # Publish error event
            await self.event_bus.publish({
                "type": "error",
                "user_id": user_id,
                "conversation_id": conversation_id,
                "data": {"message": f"Error processing message: {str(e)}"},
            })


async def create_response_handler(event_bus: Optional[EventBus] = None):
    """
    Factory function to create and start a response handler.
    """
    if event_bus is None:
        event_bus = EventBus()

    memory_client = MemoryClient()
    cognition_client = CognitionClient()

    handler = ResponseHandler(event_bus=event_bus, memory_client=memory_client, cognition_client=cognition_client)

    # Start the handler in the background
    asyncio.create_task(handler.start())

    return handler
