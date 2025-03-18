"""
Cortex Core FastAPI Application Entry Point

This module initializes the FastAPI application and includes all routers.
It also handles startup and shutdown events for the application.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.conversations import router as conversations_router
from app.api.workspaces import router as workspaces_router
from app.api.sse import router as sse_router
from app.components.event_system import get_event_manager
from app.components.io import get_io_manager
from app.components.mcp import get_mcp_client
from app.components.memory import get_memory_manager
from app.components.router import get_router
from app.components.sse.manager import get_sse_manager
from app.config import settings
from app.database.connection import close_db_connection, init_db
from app.interfaces.event_system import EventSystemInterface
from app.interfaces.mcp_client import McpClientInterface
from app.interfaces.memory_system import MemorySystemInterface
from app.interfaces.router import RouterInterface
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Dependency injection functions

def get_event_system() -> EventSystemInterface:
    """Get the event system singleton instance."""
    return get_event_manager()


def get_io_system(event_system: EventSystemInterface = Depends(get_event_system)):
    """Get the I/O manager singleton instance."""
    return get_io_manager(event_system)


def get_mcp(service_name: str = "default") -> McpClientInterface:
    """Get an MCP client for the specified service."""
    return get_mcp_client(service_name)


def get_memory_system() -> MemorySystemInterface:
    """Get the memory system singleton instance."""
    return get_memory_manager()


def get_message_router(event_system: EventSystemInterface = Depends(get_event_system)) -> RouterInterface:
    """Get the message router singleton instance."""
    return get_router(event_system)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Context manager for FastAPI app lifespan.
    Controls startup and shutdown events.
    
    Args:
        app: The FastAPI application
    """
    # Startup
    logger.info("Starting Cortex Core API")
    await init_db()
    
    # Initialize component managers
    event_system = get_event_manager()
    # Initialize each manager to set up the singletons
    io_manager = get_io_manager(event_system)
    _ = get_memory_manager()
    message_router = get_router(event_system)
    sse_manager = get_sse_manager()
    
    # Initialize MCP clients
    default_mcp = get_mcp_client()
    try:
        await default_mcp.connect()
        logger.info("Connected to default MCP service")
    except ConnectionError as e:
        logger.warning(f"Could not connect to default MCP service: {str(e)}")
    
    domain_experts_mcp = get_mcp_client("domain_experts")
    try:
        await domain_experts_mcp.connect()
        logger.info("Connected to domain experts MCP service")
    except ConnectionError as e:
        logger.warning(f"Could not connect to domain experts MCP service: {str(e)}")
    
    # Register message handlers
    from app.components.router.message_handlers import register_handlers
    register_handlers(message_router)
    logger.info("Registered message handlers")
    
    # Initialize default input receiver for conversations
    from app.components.io import create_conversation_input_receiver
    conversation_input = create_conversation_input_receiver(message_router)
    io_manager.register_input_receiver(conversation_input)
    logger.info(f"Registered conversation input receiver: {conversation_input.get_channel_id()}")
    
    # TODO: In a future implementation, we could retrieve existing conversations
    # from the database and register output publishers for each one
    # For now, publishers will be created dynamically when a conversation is created
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cortex Core API")
    
    # Cleanup SSE manager
    logger.info("Cleaning up SSE manager")
    await sse_manager.cleanup()
    
    # Shutdown message router
    logger.info("Shutting down message router")
    await message_router.shutdown()
    
    # Close MCP connections
    logger.info("Closing MCP connections")
    await default_mcp.close()
    await domain_experts_mcp.close()
    
    # Close database connection
    await close_db_connection()


app = FastAPI(
    title="Cortex Core API",
    description="API for Cortex Core platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api", tags=["Authentication"])
app.include_router(workspaces_router, prefix="/api", tags=["Workspaces"])
app.include_router(conversations_router, prefix="/api", tags=["Conversations"])
app.include_router(sse_router, prefix="/api", tags=["SSE"])


@app.get("/", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint for the API.
    
    Returns:
        dict: Health status response
    """
    return {
        "status": "ok",
        "message": "Cortex Core API is running",
        "version": app.version,
    }


@app.get("/api/ping", tags=["Health"])
async def ping() -> dict:
    """
    Simple ping endpoint to verify the API is responding.
    
    Returns:
        dict: Pong response
    """
    return {"message": "pong"}


# Advanced health check endpoint that includes component statuses
@app.get("/api/health", tags=["Health"])
async def detailed_health(
    router: RouterInterface = Depends(get_message_router),
    memory: MemorySystemInterface = Depends(get_memory_system),
    mcp: McpClientInterface = Depends(get_mcp)
) -> dict:
    """
    Detailed health check endpoint that reports status of system components.
    
    Args:
        router: The message router instance
        memory: The memory system instance
        mcp: The MCP client instance
        
    Returns:
        dict: Detailed health status of all components
    """
    queue_status = await router.get_queue_status()
    
    # Check MCP connection
    mcp_status = "connected" if mcp.is_connected else "disconnected"
    
    return {
        "status": "ok",
        "version": app.version,
        "components": {
            "router": {
                "status": "ok",
                "queue_size": queue_status.get("queue_size", 0),
                "messages_processed": queue_status.get("messages_processed", 0)
            },
            "memory": {
                "status": "ok"
            },
            "mcp": {
                "status": mcp_status
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )