import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Import routers from the API submodules
from app.api import auth, config, health, input, management, output
from app.core.event_bus import event_bus
from app.core.response_handler import create_response_handler
from app.utils.exceptions import CortexException

# Store response handler reference
response_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    global response_handler

    # Get service URLs from environment variables or use defaults
    memory_url = os.environ.get("MEMORY_SERVICE_URL", "http://localhost:5001/sse")
    cognition_url = os.environ.get("COGNITION_SERVICE_URL", "http://localhost:5000/sse")
    
    # Initialize components on application startup
    response_handler = await create_response_handler(
        event_bus=event_bus,
        memory_url=memory_url,
        cognition_url=cognition_url
    )
    
    # Store response handler in app state for access by health checks
    app.state.response_handler = response_handler
    
    print("Cortex Core started with services:")
    print(f"- Memory service: {memory_url}")
    print(f"- Cognition service: {cognition_url}")

    yield

    # Clean up resources on application shutdown
    if response_handler:
        await response_handler.stop()
    app.state.response_handler = None
    print("Cortex Core shutting down, resources cleaned up")


app = FastAPI(title="Cortex Core MVP", lifespan=lifespan)


@app.exception_handler(CortexException)
async def cortex_exception_handler(request: Request, exc: CortexException):
    """Handle custom Cortex exceptions."""
    # Create a copy of the detail dictionary
    response = dict(exc.detail) if isinstance(exc.detail, dict) else {"error": str(exc.detail)}
    # Add a request ID for tracking
    response["request_id"] = str(uuid.uuid4())
    return JSONResponse(status_code=exc.status_code, content=response)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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


# Include API routers (stubs) into the main app
app.include_router(auth.router)
app.include_router(input.router)
app.include_router(output.router)
app.include_router(config.router)
app.include_router(health.router)
app.include_router(management.router)


@app.get("/", tags=["system"])
async def root():
    """Root endpoint returning basic service information."""
    return {"status": "online", "service": "Cortex Core"}


@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint to verify that the service is running."""
    return {"status": "ok"}


if __name__ == "__main__":
    # This block allows running the app directly for testing/development.
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)