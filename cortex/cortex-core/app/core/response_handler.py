import logging
from typing import Optional

from app.backend.cognition_client import CognitionClient
from app.backend.memory_client import MemoryClient
from app.core.event_bus import EventBus
from app.core.llm_orchestrator import LLMOrchestrator, create_llm_orchestrator

# Set up logger for the response handler
logger = logging.getLogger(__name__)


class ResponseHandler:
    """
    Response handler that processes input events and produces output events.
    Orchestrates interactions between event bus, memory client, cognition client,
    and the LLM orchestrator.
    """

    def __init__(self, event_bus: EventBus, memory_client: MemoryClient, cognition_client: CognitionClient) -> None:
        """
        Initialize the response handler with required dependencies.

        Args:
            event_bus: Event bus for publishing and subscribing to events
            memory_client: Client for interacting with the memory service
            cognition_client: Client for interacting with the cognition service
        """
        self.event_bus = event_bus
        self.memory_client = memory_client
        self.cognition_client = cognition_client
        self.running = False
        self.llm_orchestrator: Optional[LLMOrchestrator] = None

    async def start(self) -> None:
        """
        Start the response handler.
        Initializes and starts the LLM orchestrator for processing messages.
        """
        self.running = True
        
        # Initialize the LLM orchestrator
        self.llm_orchestrator = await create_llm_orchestrator(self.event_bus)
        
        logger.info("Response handler started with LLM orchestrator")

    async def stop(self) -> None:
        """
        Stop the response handler and clean up resources.
        Stops the LLM orchestrator and closes client connections.
        """
        self.running = False
        
        # Stop the LLM orchestrator if it's running
        if self.llm_orchestrator:
            await self.llm_orchestrator.stop()

        # Close client connections
        await self.memory_client.close()
        await self.cognition_client.close()
        
        logger.info("Response handler stopped")


async def create_response_handler(
    event_bus: EventBus,
    memory_url: str = "http://localhost:5001/sse",
    cognition_url: str = "http://localhost:5000/sse",
) -> ResponseHandler:
    """
    Factory function to create and start a response handler.

    Args:
        event_bus: The event bus instance to use.
        memory_url: URL for the memory service SSE endpoint
        cognition_url: URL for the cognition service SSE endpoint

    Returns:
        An initialized and started ResponseHandler instance
    """
    memory_client = MemoryClient(service_url=memory_url)
    cognition_client = CognitionClient(service_url=cognition_url)

    handler = ResponseHandler(event_bus=event_bus, memory_client=memory_client, cognition_client=cognition_client)

    # Start the handler in the background
    await handler.start()

    return handler