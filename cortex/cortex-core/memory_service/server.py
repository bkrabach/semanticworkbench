# server.py for memory service
import datetime
import logging
import sys
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from .config import config
from .memory_store import MemoryStore
from .memory_updater import MemoryUpdater
from .models import MemoryRetrievalRequest, MemoryRetrievalResponse, MemoryUpdateRequest, MemoryUpdateResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("memory_service")

# Create FastMCP instance
mcp = FastMCP("MemoryService")

# Initialize memory store and updater
memory_store = MemoryStore()
memory_updater = MemoryUpdater()


@mcp.tool()
async def get_memory(request: MemoryRetrievalRequest) -> MemoryRetrievalResponse:
    """Retrieve memory for a conversation."""
    logger.info(f"Getting memory for conversation: {request.conversation_id}")
    memory = memory_store.get_memory(request.conversation_id)

    if memory is None:
        return MemoryRetrievalResponse(conversation_id=request.conversation_id, memory_content=None, exists=False)

    return MemoryRetrievalResponse(
        conversation_id=request.conversation_id, memory_content=memory.memory_content, exists=True
    )


@mcp.tool()
async def update_memory(request: MemoryUpdateRequest) -> MemoryUpdateResponse:
    """Update memory for a conversation with new messages."""
    logger.info(
        f"Updating memory for conversation: {request.conversation_id} with {len(request.new_messages)} new messages"
    )
    # Get existing memory or create new one
    memory = memory_store.get_memory(request.conversation_id)

    if memory is None:
        # Create new memory
        logger.info(f"Creating new memory for conversation: {request.conversation_id}")
        memory = await memory_updater.create_memory(
            conversation_id=request.conversation_id, messages=request.new_messages
        )
        success = memory_store.save_memory(memory)
    else:
        # Update existing memory
        logger.info(f"Updating existing memory for conversation: {request.conversation_id}")
        update_result = await memory_updater.update_memory(current_memory=memory, new_messages=request.new_messages)

        if update_result.success:
            memory.memory_content = update_result.updated_memory
            memory.last_updated = datetime.datetime.now().isoformat()
            success = memory_store.save_memory(memory)
        else:
            success = False

    return MemoryUpdateResponse(
        conversation_id=request.conversation_id, updated_memory=memory.memory_content, success=success
    )


@mcp.tool()
async def delete_memory(request: MemoryRetrievalRequest) -> Dict[str, Any]:
    """Delete memory for a conversation."""
    logger.info(f"Deleting memory for conversation: {request.conversation_id}")
    success = memory_store.delete_memory(request.conversation_id)

    return {"conversation_id": request.conversation_id, "success": success}


@mcp.resource("memory://{conversation_id}")
async def memory_resource(conversation_id: str) -> Dict[str, Any]:
    """Resource endpoint for retrieving memory."""
    logger.info(f"Resource request for conversation memory: {conversation_id}")
    memory = memory_store.get_memory(conversation_id)

    if memory is None:
        return {"conversation_id": conversation_id, "exists": False, "memory_content": None}

    return {
        "conversation_id": conversation_id,
        "exists": True,
        "memory_content": memory.memory_content,
        "last_updated": memory.last_updated,
    }


@mcp.tool()
async def health() -> Dict[str, Any]:
    """Health check endpoint to verify service is running."""
    return {
        "status": "healthy",
        "service": "memory",
        "version": "0.1.0",
    }


def run() -> None:
    """Run the Memory Service."""
    logger.info(f"Starting Memory Service on {config.HOST}:{config.PORT}")
    mcp.settings.host = config.HOST
    mcp.settings.port = config.PORT
    mcp.run(transport="sse")


if __name__ == "__main__":
    run()
