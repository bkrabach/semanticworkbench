"""
Main entry point for Cortex Core FastAPI application
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
import time
import uuid
from contextlib import asynccontextmanager

from app.config import settings
from app.utils.logger import logger, request_logger
from app.database.connection import db
from app.cache.redis_client import connect_redis, disconnect_redis
from app.exceptions import CortexException

# Import routers
from app.api import auth, sse, workspaces, conversations, monitoring, integrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events handler for FastAPI
    - Startup: Connect to database, cache, initialize components
    - Shutdown: Cleanup resources
    """
    # Startup
    logger.info("Starting Cortex Core")
    
    # Check debug log settings
    import os
    debug_log_enabled = os.environ.get("DEBUG_LOG_ENABLED", "false").lower() == "true"
    logger.info(f"Debug log enabled: {debug_log_enabled}")
    if debug_log_enabled:
        debug_main_path = os.environ.get("DEBUG_MAIN_LOG_PATH", "logs/cortex.log.debug_current")
        debug_error_path = os.environ.get("DEBUG_ERROR_LOG_PATH", "logs/cortex-error.log.debug_current")
        debug_requests_path = os.environ.get("DEBUG_REQUESTS_LOG_PATH", "logs/cortex-requests.log.debug_current")
        logger.info(f"Debug log paths: main={debug_main_path}, error={debug_error_path}, requests={debug_requests_path}")

    # Connect to database
    await db.connect()

    # Connect to Redis
    await connect_redis()

    # Initialize and store event system in app state
    from app.components.event_system import get_event_system
    app.state.event_system = get_event_system()
    logger.info("Event System initialized")

    # Initialize SSE service
    try:
        # Use the domain-driven service layer implementation
        from app.database.connection import SessionLocal
        from app.database.repositories.resource_access_repository import get_resource_access_repository
        from app.services.sse_service import SSEService
        
        # Create a direct database session (not using async generator)
        db_session = SessionLocal()
        
        try:
            # Create repository and service directly 
            repository = get_resource_access_repository(db_session)
            app.state.sse_service = SSEService(db_session, repository)
            await app.state.sse_service.initialize()
            logger.info("SSE Service initialized")
        finally:
            # Close session even if initialization succeeded
            db_session.close()
    except Exception as e:
        logger.error(f"Error initializing SSE service: {e}")

    # Initialize Integration Hub for MCP connections
    try:
        from app.components.integration_hub import get_integration_hub
        app.state.integration_hub = get_integration_hub()
        await app.state.integration_hub.startup()
        logger.info("Integration Hub initialized")
    except Exception as e:
        logger.error(f"Error initializing Integration Hub: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Cortex Core")

    # Clean up Integration Hub
    try:
        if hasattr(app.state, "integration_hub"):
            await app.state.integration_hub.shutdown()
            logger.info("Integration Hub cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up Integration Hub: {e}")

    # Clean up SSE service
    try:
        if hasattr(app.state, "sse_service"):
            await app.state.sse_service.cleanup()
            logger.info("SSE Service cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up SSE service: {e}")
        
    # Clean up router
    try:
        from app.components.cortex_router import get_router
        router = get_router()
        if hasattr(router, 'cleanup'):
            await router.cleanup()
            logger.info("CortexRouter cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up CortexRouter: {e}")

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

    # Generate trace_id for request
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id

    # Log the request
    request_logger.info(f"{method} {path} {query_params} [trace_id={trace_id}]")

    # Process the request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        status_code = response.status_code

        # Log the response
        request_logger.info(
            f"{method} {path} {status_code} {process_time:.3f}s [trace_id={trace_id}]")

        # Add X-Process-Time and X-Trace-ID headers
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Trace-ID"] = trace_id
        return response
    except Exception:
        # Log the error
        logger.error(f"Request failed: {method} {path} [trace_id={trace_id}]", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "code": "INTERNAL_ERROR",
                "params": {},
                "trace_id": trace_id
            }
        )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


# Exception handlers
@app.exception_handler(CortexException)
async def cortex_exception_handler(request: Request, exc: CortexException):
    """Handle application-specific exceptions"""
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    logger.info(
        f"Handling {exc.__class__.__name__}: {exc.detail} [trace_id={trace_id}]"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": exc.code,
            "params": exc.params,
            "trace_id": trace_id
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions"""
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": "HTTP_ERROR",
            "params": {},
            "trace_id": trace_id
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors from Pydantic models"""
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    errors = exc.errors()
    error_details = []

    for error in errors:
        error_details.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "code": "VALIDATION_FAILED",
            "params": {"errors": error_details},
            "trace_id": trace_id
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    # Log the exception with traceback
    logger.exception(f"Unhandled exception: {str(exc)} [trace_id={trace_id}]")

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "code": "INTERNAL_ERROR",
            "params": {},
            "trace_id": trace_id
        }
    )


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(sse.router, tags=["Events"])  # No prefix - the router already has /v1 prefix
app.include_router(workspaces.router, tags=["Workspaces"])
app.include_router(conversations.router, tags=["Conversations"])
app.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
app.include_router(integrations.router, prefix="/integrations", tags=["Integrations"])


# Define entry point for running the application
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=True,
    )
