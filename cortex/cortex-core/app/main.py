"""
Main entry point for Cortex Core FastAPI application
"""

import asyncio
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import time
from contextlib import asynccontextmanager

from app.config import settings
from app.utils.logger import logger, request_logger
from app.database.connection import db
from app.cache.redis_client import connect_redis, disconnect_redis

# Import routers (to be implemented)
# from app.api import auth, workspaces, conversations, integrations, mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events handler for FastAPI
    - Startup: Connect to database, cache
    - Shutdown: Cleanup resources
    """
    # Startup
    logger.info("Starting Cortex Core")

    # Connect to database
    await db.connect()

    # Connect to Redis
    await connect_redis()

    # Additional startup initialization could be added here

    yield

    # Shutdown
    logger.info("Shutting down Cortex Core")

    # Disconnect from Redis
    await disconnect_redis()

    # Disconnect from database
    await db.disconnect()

    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Cortex Core",
    description="Central orchestration engine for the Cortex Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log request information and execution time"""
    start_time = time.time()
    method = request.method
    path = request.url.path
    query_params = str(request.query_params)

    # Log the request
    request_logger.info(f"{method} {path} {query_params}")

    # Process the request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        status_code = response.status_code

        # Log the response
        request_logger.info(
            f"{method} {path} {status_code} {process_time:.3f}s")

        # Add X-Process-Time header
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        # Log the error
        logger.error(f"Request failed: {method} {path}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


# TODO: Include routers
# app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# app.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
# app.include_router(conversations.router, tags=["Conversations"])
# app.include_router(integrations.router, prefix="/integrations", tags=["Integrations"])
# app.include_router(mcp.router, prefix="/mcp", tags=["MCP"])

# Define entry point for running the application
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=True,
    )
