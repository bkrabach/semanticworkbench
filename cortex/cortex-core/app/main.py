import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Import routers from the API submodules
from app.api import auth, config, input, output
from app.core.event_bus import event_bus
from app.core.response_handler import create_response_handler
from app.utils.exceptions import CortexException

# Store response handler reference
response_handler = None

app = FastAPI(title="Cortex Core MVP")


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


@app.get("/", tags=["system"])
async def root():
    """Root endpoint returning basic service information."""
    return {"status": "online", "service": "Cortex Core"}


@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint to verify that the service is running."""
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    """Initialize components on application startup."""
    global response_handler

    # Create and start the response handler with our global event bus
    response_handler = await create_response_handler(event_bus)

    print("Cortex Core started and response handler initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    global response_handler

    # Stop the response handler if it's running
    if response_handler:
        await response_handler.stop()

    print("Cortex Core shutting down, resources cleaned up")


if __name__ == "__main__":
    # This block allows running the app directly for testing/development.
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
