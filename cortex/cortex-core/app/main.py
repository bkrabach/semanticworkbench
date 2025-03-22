import logging
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import USERS
from app.api.auth import router as auth_router
from app.api.config import router as config_router
from app.api.input import router as input_router
from app.api.output import router as output_router
from app.core.event_bus import event_bus
from app.core.exceptions import CortexException
from app.database.unit_of_work import UnitOfWork
from app.models import User

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def ensure_test_users_exist():
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
async def lifespan(app: FastAPI):
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

    # Check if we're using mock or real LLM
    use_mock = os.getenv("USE_MOCK_LLM", "").lower() == "true"

    # Only set fake key if we're using mock and don't have real keys configured
    if use_mock and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "sk-demo-key-will-fail"
        os.environ["OPENAI_MODEL"] = "gpt-3.5-turbo"
        logger.info("Using mock LLM with dummy API key")
    else:
        # Using real LLM with keys from .env
        logger.info("Using real LLM with configured API keys")

    # Initialize LLM adapter
    try:
        logger.info(f"Initializing LLM adapter with provider: {os.getenv('LLM_PROVIDER')}")
        # llm_adapter is already initialized when imported, but we log it here
    except Exception as e:
        logger.warning(f"Failed to initialize LLM adapter: {str(e)}. Will use mock responses.")

    yield

    # Shutdown
    logger.info("Application shutting down")
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
async def cortex_exception_handler(request: Request, exc: CortexException):
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
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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
async def general_exception_handler(request: Request, exc: Exception):
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
async def root():
    """API status endpoint."""
    return {"status": "online", "service": "Cortex Core"}


# Include routers
app.include_router(auth_router)
app.include_router(input_router)
app.include_router(output_router)
app.include_router(config_router)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
