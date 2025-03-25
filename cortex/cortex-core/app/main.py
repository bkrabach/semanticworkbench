import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import USERS
from app.api.auth import router as auth_router
from app.api.cognition import router as cognition_router
from app.api.config import router as config_router
from app.api.input import router as input_router
from app.api.output import router as output_router
from app.core.event_bus import event_bus
from app.core.exceptions import CortexException
from app.core.mcp.factory import close_mcp_client, get_mcp_client
from app.core.mcp.registry import registry as mcp_registry
from app.core.repository import RepositoryManager
from app.database.unit_of_work import UnitOfWork
from app.models import User
from app.services.cognition import CognitionService
from app.services.memory import MemoryService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def ensure_test_users_exist() -> None:
    """
    Development-only function that ensures test users from auth.py exist in the database.

    This is needed because the login endpoint authenticates against static users in the USERS dictionary,
    but these users need to exist in the database to satisfy foreign key constraints when
    creating workspaces and other resources that reference users via foreign keys.

    In a production environment, this would be replaced by proper user management
    with Azure B2C integration where users are created in the database upon first login
    or through user management endpoints.
    """
    async with UnitOfWork.for_transaction() as uow:
        user_repo = uow.repositories.get_user_repository()

        for email, user_data in USERS.items():
            # Check if user already exists
            user_id = user_data["oid"]
            existing_user = await user_repo.get_by_id(user_id)

            if not existing_user:
                logger.info(f"Creating test user: {email} with ID: {user_id}")
                # Create user in database
                new_user = User(user_id=user_id, name=user_data["name"], email=email, metadata={"is_test_user": True})
                await user_repo.create(new_user)
            else:
                logger.info(f"Test user already exists: {email}")

        # Also ensure the 'assistant' system user exists for messages from the AI
        assistant_id = "assistant"
        assistant_email = "assistant@system.local"
        existing_assistant = await user_repo.get_by_id(assistant_id)

        if not existing_assistant:
            logger.info(f"Creating system assistant user with ID: {assistant_id}")
            assistant_user = User(
                user_id=assistant_id, name="AI Assistant", email=assistant_email, metadata={"is_system": True}
            )
            await user_repo.create(assistant_user)
        else:
            logger.info("System assistant user already exists")

        # Commit all changes
        await uow.commit()
        logger.info("Test user setup complete")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Initializing database...")
    from app.database.connection import init_db

    await init_db()
    logger.info("Database initialized")

    # Ensure test users exist in the database
    logger.info("Setting up test users...")
    await ensure_test_users_exist()

    # Set default environment variables for LLM if not present
    if not os.getenv("LLM_PROVIDER"):
        os.environ["LLM_PROVIDER"] = "openai"  # Default provider

    # For development environment, we can set a default OpenAI key if not present
    # This is just to prevent errors during development, not for production use
    if os.getenv("ENVIRONMENT", "").lower() == "development" and not os.getenv("OPENAI_API_KEY"):
        logger.warning("Running in development environment without API keys. Set proper API keys for production use.")
        os.environ["OPENAI_API_KEY"] = "sk-demo-key-for-development"
        os.environ["OPENAI_MODEL"] = "gpt-3.5-turbo"
    else:
        # Using LLM with configured API keys
        logger.info("Using LLM with configured API keys")

    # Initialize LLM adapter
    try:
        logger.info(f"Initializing LLM adapter with provider: {os.getenv('LLM_PROVIDER')}")
        # llm_adapter is already initialized when imported, but we log it here
    except Exception as e:
        logger.warning(f"Failed to initialize LLM adapter: {str(e)}. Will use mock responses.")

    # Check if we're in distributed mode
    distributed_mode = os.getenv("CORTEX_DISTRIBUTED_MODE", "false").lower() in ("true", "1", "yes")

    if distributed_mode:
        # Distributed mode - use network MCP client
        logger.info("Running in distributed mode - using network MCP client")
        # Initialize MCP client that will connect to remote services
        logger.info("Initializing network MCP client...")
        await get_mcp_client()
        logger.info("Network MCP client initialized")
    else:
        # In-process mode - register local MCP services
        logger.info("Running in in-process mode - registering local MCP services")

        # Create repository manager
        repository_manager = RepositoryManager()
        await repository_manager.initialize()

        # Create and register Memory Service
        memory_service = MemoryService(repository_manager)
        await memory_service.initialize()
        await mcp_registry.register_service("memory", memory_service)
        logger.info("Memory Service registered with MCP registry")

        # Create and register Cognition Service
        cognition_service = CognitionService(memory_service=memory_service)
        await cognition_service.initialize()
        await mcp_registry.register_service("cognition", cognition_service)
        logger.info("Cognition Service registered with MCP registry")

    yield

    # Shutdown
    logger.info("Application shutting down")

    if distributed_mode:
        # Close network MCP client
        logger.info("Closing network MCP client...")
        await close_mcp_client()
    else:
        # Shutdown in-process MCP services
        logger.info("Shutting down MCP services...")

        # Get services from registry and shut them down
        try:
            cognition_def = mcp_registry.get_service("cognition")
            if cognition_def:
                await cognition_def.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down cognition service: {e}")
            
        try:
            memory_def = mcp_registry.get_service("memory")
            if memory_def:
                await memory_def.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down memory service: {e}")

    # Shutdown event bus
    await event_bus.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Cortex Core",
    description="Cortex Core API for input and output processing",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(CortexException)
async def cortex_exception_handler(request: Request, exc: CortexException) -> JSONResponse:
    """
    Global exception handler for CortexException.
    Returns a standardized error response.
    """
    request_id = str(uuid.uuid4())
    logger.error(
        f"Request {request_id} failed: {exc.message}",
        extra={
            "request_id": request_id,
            "error_code": exc.code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "client_host": request.client.host if request.client else None,
            "details": exc.details,
        },
    )

    # Log the exception with its built-in method
    exc.log()

    # Format the error response to match expected structure in tests
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details if hasattr(exc, "details") else {},
            },
            "request_id": request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Exception handler for Pydantic validation errors.
    Converts validation errors into a standardized format.
    """
    request_id = str(uuid.uuid4())
    errors = exc.errors()

    validation_errors = []
    for error in errors:
        validation_errors.append({
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        })

    logger.warning(
        f"Request {request_id} validation error",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "validation_errors": validation_errors,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Validation error in request data",
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "details": {"validation_errors": validation_errors},
            },
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all exception handler for unhandled exceptions.
    Provides a standardized response for unexpected errors.
    """
    request_id = str(uuid.uuid4())

    # Log detailed error information
    logger.exception(
        f"Unhandled exception in request {request_id}: {str(exc)}",
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
            "client_host": request.client.host if request.client else None,
        },
    )

    # In production, we don't want to expose internal error details
    is_debug = os.getenv("DEBUG", "False").lower() == "true"
    error_detail = str(exc) if is_debug else "An unexpected error occurred"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": error_detail} if is_debug else {},
            },
            "request_id": request_id,
        },
    )


# Root endpoint for health checks
@app.get("/", tags=["status"])
async def root() -> dict[str, str]:
    """API status endpoint."""
    return {"status": "online", "service": "Cortex Core"}


# Health check endpoint for service discovery
@app.get("/health", tags=["status"])
async def health() -> dict[str, str]:
    """Health check endpoint for service discovery."""
    return {"status": "healthy"}


# Enhanced health check endpoint with system information
@app.get("/v1/health", tags=["status"])
async def v1_health() -> dict:
    """
    Enhanced health check endpoint with system information.
    Returns detailed system status information.
    """
    import os
    import platform
    import sys
    import psutil
    
    # Get basic system information
    system_info = {
        "status": "healthy",
        "service": "Cortex Core",
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "python_version": sys.version,
        "platform": platform.platform(),
        "resources": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    }
    
    return system_info


# Detailed health check endpoint with service status
@app.get("/v1/health/details", tags=["status"])
async def v1_health_details() -> dict:
    """
    Detailed health check endpoint with service status.
    Returns comprehensive system and service health information.
    """
    import os
    import platform
    import sys
    import psutil
    import time
    import httpx
    from datetime import datetime
    
    # Start timing the response
    start_time = time.time()
    
    # Get basic system information (same as v1_health)
    health_info = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Cortex Core",
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "request_id": str(uuid.uuid4()),
        "system": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "cpu_usage": psutil.cpu_percent(interval=0.1),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "uptime_seconds": int(time.time() - psutil.boot_time())
        },
        "services": {}
    }
    
    # Check if we're in distributed mode
    distributed_mode = os.getenv("CORTEX_DISTRIBUTED_MODE", "false").lower() in ("true", "1", "yes")
    
    if distributed_mode:
        # Check distributed services
        services_to_check = {
            "memory": os.getenv("MEMORY_SERVICE_URL", "http://localhost:9000"),
            "cognition": os.getenv("COGNITION_SERVICE_URL", "http://localhost:9100")
        }
        
        # Check each service
        service_statuses = {}
        overall_status = "healthy"
        
        async with httpx.AsyncClient(timeout=2.0) as client:
            for service_name, service_url in services_to_check.items():
                service_start_time = time.time()
                try:
                    response = await client.get(f"{service_url}/health")
                    if response.status_code == 200:
                        service_statuses[service_name] = {
                            "status": "healthy",
                            "endpoint": service_url,
                            "response_time_ms": int((time.time() - service_start_time) * 1000)
                        }
                    else:
                        service_statuses[service_name] = {
                            "status": "unhealthy",
                            "endpoint": service_url,
                            "status_code": response.status_code,
                            "response_time_ms": int((time.time() - service_start_time) * 1000)
                        }
                        overall_status = "degraded"
                except Exception as e:
                    service_statuses[service_name] = {
                        "status": "unavailable",
                        "endpoint": service_url,
                        "error": str(e),
                        "response_time_ms": int((time.time() - service_start_time) * 1000)
                    }
                    overall_status = "degraded"
        
        health_info["services"] = service_statuses
        health_info["status"] = overall_status
    else:
        # In-process mode - check local MCP services
        local_services = {
            "memory": mcp_registry.get_service("memory"),
            "cognition": mcp_registry.get_service("cognition")
        }
        
        service_statuses = {}
        for service_name, service in local_services.items():
            if service is not None:
                service_statuses[service_name] = {
                    "status": "healthy",
                    "mode": "in-process",
                    "initialized": getattr(service, "initialized", True)
                }
            else:
                service_statuses[service_name] = {
                    "status": "unavailable",
                    "mode": "in-process"
                }
        
        health_info["services"] = service_statuses
    
    # Check database connectivity
    try:
        async with UnitOfWork.for_transaction() as uow:
            # Simple query to verify database connection
            user_repo = uow.repositories.get_user_repository()
            count = await user_repo.count()
            
            health_info["database"] = {
                "status": "healthy",
                "type": os.getenv("DATABASE_TYPE", "sqlite"),
                "connection_count": 1,
                "record_counts": {
                    "users": count
                }
            }
    except Exception as e:
        health_info["database"] = {
            "status": "unhealthy",
            "type": os.getenv("DATABASE_TYPE", "sqlite"),
            "error": str(e)
        }
        health_info["status"] = "degraded"
    
    # Add response time
    health_info["response_time_ms"] = int((time.time() - start_time) * 1000)
    
    return health_info


# Include routers
app.include_router(auth_router)
app.include_router(input_router)
app.include_router(output_router)
app.include_router(config_router)
app.include_router(cognition_router)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
