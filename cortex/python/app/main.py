"""
Main Application Entry Point

This module serves as the entry point for the FastAPI application.
It configures the API routes, middleware, and initializes all required components.
"""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from typing import Callable, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import health, auth, memory, message
from app.components.context_manager import initialize_context_manager
from app.components.dispatcher import initialize_dispatcher
from app.components.integration_hub import initialize_integration_hub
from app.components.message_handler import message_handler
from app.components.security_manager import initialize_security_manager
from app.components.session_manager import initialize_session_manager
from app.components.whiteboard_memory import initialize_whiteboard_memory
from app.components.workspace_manager import initialize_workspace_manager
from app.config import settings
from app.interfaces.domain_expert_interface import DomainExpertInterface
from app.utils.logger import get_contextual_logger, configure_logging

# Configure logging
configure_logging()

# Get logger for this module
logger = get_contextual_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI

    This handles startup and shutdown events for the application.
    It initializes and properly closes all necessary components.

    Args:
        app: The FastAPI application

    Yields:
        None
    """
    # Log startup
    logger.info(f"Starting application with environment: {settings.environment}")

    # Initialize components
    try:
        # Initialize security manager first for early protection
        security_mgr = initialize_security_manager()
        logger.info("Security manager initialized")

        # Initialize session manager
        session_mgr = initialize_session_manager()
        logger.info("Session manager initialized")

        # Initialize workspace manager
        workspace_mgr = initialize_workspace_manager()
        logger.info("Workspace manager initialized")

        # Initialize memory system
        whiteboard = initialize_whiteboard_memory()
        logger.info("Whiteboard memory initialized")

        # Initialize context manager
        context_mgr = initialize_context_manager(whiteboard)
        logger.info("Context manager initialized")

        # Initialize integration hub
        integration_hub = initialize_integration_hub()
        await integration_hub.initialize()
        logger.info("Integration hub initialized")

        # Initialize domain expert interface
        # For now, we'll use a simple implementation
        domain_expert = DomainExpertInterface()
        logger.info("Domain expert interface initialized")

        # Initialize dispatcher (needs other components)
        dispatcher = initialize_dispatcher(
            context_manager=context_mgr,
            session_manager=session_mgr,
            domain_expert_interface=domain_expert,
        )

        # Register message handler with dispatcher
        dispatcher.register_handler("message", message_handler)
        logger.info("Dispatcher initialized")

        logger.info("All components initialized successfully")

    except Exception as e:
        logger.error(f"Error during component initialization: {str(e)}", exc_info=True)
        # Even if we encounter an error, we'll yield to allow graceful shutdown

    # Yield control back to FastAPI
    yield

    # Shutdown logic
    logger.info("Shutting down application")

    # Close integration hub connections
    try:
        if "integration_hub" in locals():
            await integration_hub.shutdown()
            logger.info("Integration hub shut down")
    except Exception as e:
        logger.error(f"Error shutting down integration hub: {str(e)}", exc_info=True)

    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Cortex Core",
    description="Cortex Core API for AI-powered assistance",
    version="1.0.0",
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url="/api/redoc" if settings.environment != "production" else None,
    lifespan=lifespan,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add a unique request ID to each request for tracing"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Call next middleware or route handler
    try:
        response = await call_next(request)
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "request_id": request_id},
        )


# Register API routes
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(message.router, prefix="/api")

# Serve web client if available
web_client_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "web-client.html"
)
if os.path.exists(web_client_path):
    # Get directory containing the file
    web_client_dir = os.path.dirname(web_client_path)
    app.mount("/", StaticFiles(directory=web_client_dir, html=True), name="web_client")


# Custom error handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Generic exception handler to log errors and return appropriate responses"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    # Get request ID for tracking
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
            "type": exc.__class__.__name__,
            "message": str(exc)
            if settings.environment != "production"
            else "An error occurred",
        },
    )


if __name__ == "__main__":
    """Run the application with uvicorn when script is executed directly"""
    # Configure uvicorn
    host = settings.host
    port = settings.port

    logger.info(f"Starting uvicorn server on {host}:{port}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=settings.environment == "development",
        workers=settings.workers,
        log_level="info",
    )
