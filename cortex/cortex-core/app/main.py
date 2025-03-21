import logging
import os
import uuid
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from app.api.auth import router as auth_router
from app.api.input import router as input_router
from app.api.output import router as output_router
from app.api.config import router as config_router
from app.core.event_bus import event_bus
from app.core.exceptions import CortexException

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
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
            "details": exc.details
        }
    )
    
    # Log the exception with its built-in method
    exc.log()
    
    error_response = exc.to_dict()
    error_response["request_id"] = request_id
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
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
            "type": error.get("type", "")
        })
    
    logger.warning(
        f"Request {request_id} validation error",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "validation_errors": validation_errors
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Validation error in request data",
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "details": {"validation_errors": validation_errors}
            },
            "request_id": request_id
        }
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
            "client_host": request.client.host if request.client else None
        }
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
                "details": {"error": error_detail} if is_debug else {}
            },
            "request_id": request_id
        }
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