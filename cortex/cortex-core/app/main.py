"""
Cortex Core FastAPI Application Entry Point

This module initializes the FastAPI application and includes all routers.
It also handles startup and shutdown events for the application.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.conversations import router as conversations_router
from app.api.workspaces import router as workspaces_router
from app.api.sse import router as sse_router
from app.components.sse.manager import get_sse_manager
from app.config import settings
from app.database.connection import close_db_connection, get_db, init_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


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
    
    # Initialize SSE manager
    sse_manager = get_sse_manager()
    
    # TODO: Initialize event system
    # TODO: Initialize other services
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cortex Core API")
    
    # Cleanup SSE manager
    logger.info("Cleaning up SSE manager")
    await sse_manager.cleanup()
    
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


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )