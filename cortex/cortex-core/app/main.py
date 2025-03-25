import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Import routers from the API submodules
from app.api import auth, config, health, input, management, output
from app.core.event_bus import EventBus
from app.core.response_handler import create_response_handler
from app.backend.memory_client import MemoryClient
from app.backend.cognition_client import CognitionClient
from app.core.config import (
    MEMORY_SERVICE_URL, 
    COGNITION_SERVICE_URL, 
    SERVER_HOST,
    SERVER_PORT, 
    ENVIRONMENT,
    APP_VERSION,
    LOG_LEVEL,
    ALLOWED_CORS_ORIGINS,
    validate_config
)
from app.utils.exceptions import CortexException
from app.utils.auth import get_current_user

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    # Validate configuration - fail fast for critical errors
    config_error = validate_config()
    if config_error and "required" in config_error.lower():
        raise RuntimeError(f"Critical configuration error: {config_error}")
    elif config_error:
        logger.error(f"Configuration warning: {config_error}")
    
    # Initialize event bus for internal pub/sub
    app.state.event_bus = EventBus()
    logger.info("Event bus initialized")
    
    # Initialize service clients explicitly
    app.state.memory_client = MemoryClient(MEMORY_SERVICE_URL)
    app.state.cognition_client = CognitionClient(COGNITION_SERVICE_URL)
    
    # Add client factory functions to app state for components that need to create their own clients
    async def get_memory_client():
        return MemoryClient(MEMORY_SERVICE_URL)
    
    async def get_cognition_client():
        return CognitionClient(COGNITION_SERVICE_URL)
    
    app.state.get_memory_client = get_memory_client
    app.state.get_cognition_client = get_cognition_client
    
    # Connect to services
    try:
        memory_connected, memory_error = await app.state.memory_client.connect()
        cognition_connected, cognition_error = await app.state.cognition_client.connect()
        
        if not memory_connected:
            logger.error(f"Failed to connect to memory service: {memory_error}")
        
        if not cognition_connected:
            logger.error(f"Failed to connect to cognition service: {cognition_error}")
            
    except Exception as e:
        logger.error(f"Error connecting to services: {e}")
        # Log but continue - health check will show degraded status
    
    # Initialize and start response handler
    app.state.response_handler = await create_response_handler(
        event_bus=app.state.event_bus,
        memory_url=MEMORY_SERVICE_URL,
        cognition_url=COGNITION_SERVICE_URL
    )

    # Start embedded services if requested (development convenience)
    if os.getenv("START_EMBEDDED_SERVICES") == "true":
        logger.info("Starting embedded services (development mode)")
        # TODO: Implement embedded service startup if needed

    logger.info(f"Cortex Core {APP_VERSION} started in {ENVIRONMENT} environment with services:")
    logger.info(f"- Memory service: {MEMORY_SERVICE_URL}")
    logger.info(f"- Cognition service: {COGNITION_SERVICE_URL}")

    yield

    # Clean up resources on application shutdown in reverse order
    logger.info("Shutting down Cortex Core...")
    
    # Stop response handler
    if hasattr(app.state, "response_handler") and app.state.response_handler:
        logger.info("Stopping response handler...")
        await app.state.response_handler.stop()
        app.state.response_handler = None
    
    # Close service clients
    if hasattr(app.state, "memory_client") and app.state.memory_client:
        logger.info("Closing memory client connection...")
        await app.state.memory_client.close()
        app.state.memory_client = None
        
    if hasattr(app.state, "cognition_client") and app.state.cognition_client:
        logger.info("Closing cognition client connection...")
        await app.state.cognition_client.close()
        app.state.cognition_client = None
        
    logger.info("Cortex Core shutdown complete, all resources cleaned up")


app = FastAPI(title="Cortex Core MVP", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(CortexException)
async def cortex_exception_handler(request: Request, exc: CortexException) -> JSONResponse:
    """Handle custom Cortex exceptions."""
    # Create a copy of the detail dictionary
    response = dict(exc.detail) if isinstance(exc.detail, dict) else {"error": str(exc.detail)}
    # Add a request ID for tracking
    response["request_id"] = str(uuid.uuid4())
    return JSONResponse(status_code=exc.status_code, content=response)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation errors."""
    # Extract error messages
    validation_errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        validation_errors.append(f"{field}: {error['msg']}")

    # Build custom response format
    response = {
        "error": {
            "code": "validation_error",
            "message": "Validation error",
            "details": {"validation_errors": validation_errors},
        },
        "request_id": str(uuid.uuid4()),
    }

    return JSONResponse(status_code=422, content=response)


# Include API routers with proper authentication
# Public routes (no authentication required)
app.include_router(auth.router)
app.include_router(health.router)

# Protected routes (require authentication)
app.include_router(input.router, dependencies=[Depends(get_current_user)])
app.include_router(output.router, dependencies=[Depends(get_current_user)])
app.include_router(config.router, dependencies=[Depends(get_current_user)])
app.include_router(management.router, dependencies=[Depends(get_current_user)])


@app.get("/", tags=["system"])
async def root() -> Dict[str, str]:
    """Root endpoint returning basic service information."""
    return {"status": "online", "service": "Cortex Core"}


if __name__ == "__main__":
    # This block allows running the app directly for testing/development.
    import uvicorn

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level=LOG_LEVEL.lower())
