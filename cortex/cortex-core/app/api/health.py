import time
from typing import Any, Dict

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.backend.cognition_client import CognitionClient
from app.backend.memory_client import MemoryClient

router = APIRouter(prefix="/health", tags=["health"])


class HealthServiceStatus(BaseModel):
    """Status information for a dependent service."""

    status: str
    latency_ms: float = 0
    error: str = ""


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: float
    version: str
    services: Dict[str, Dict[str, Any]]


@router.get("", response_model=HealthResponse)
async def health_check(request: Request):
    """
    Health check endpoint for the Cortex API.
    Returns the status of the API and its dependencies.
    """
    # Access response handler from application state
    app = request.app
    response_handler = app.state.response_handler if hasattr(app.state, "response_handler") else None
    
    # Collect service health checks
    services = {}

    # Check cognition service health
    try:
        cognition_client = None
        if response_handler:
            # Use existing client from response handler if available
            cognition_client = response_handler.cognition_client
        else:
            # Create temporary client for health check only
            cognition_client = CognitionClient()
            
        # Measure latency
        start_time = time.time()
        if cognition_client.session is None:
            await cognition_client.connect()
        # Just verify connection is active
        # Ensure session is available after connect
        if cognition_client.session is None:
            raise RuntimeError("Failed to establish cognition session")
        tools_response = await cognition_client.session.list_tools()
        latency_ms = (time.time() - start_time) * 1000
        
        services["cognition"] = {
            "status": "healthy", 
            "latency_ms": latency_ms,
            "tools": [t.name for t in tools_response.tools]
        }
    except Exception as e:
        services["cognition"] = {"status": "unhealthy", "error": str(e)}

    # Check memory service health
    try:
        memory_client = None
        if response_handler:
            # Use existing client from response handler if available
            memory_client = response_handler.memory_client
        else:
            # Create temporary client for health check only
            memory_client = MemoryClient()
            
        # Measure latency
        start_time = time.time()
        if memory_client.session is None:
            await memory_client.connect()
        # Just ping the connection
        # Ensure session is available after connect
        if memory_client.session is None:
            raise RuntimeError("Failed to establish memory session")
        await memory_client.session.initialize()
        latency_ms = (time.time() - start_time) * 1000
        
        services["memory"] = {"status": "healthy", "latency_ms": latency_ms}
    except Exception as e:
        services["memory"] = {"status": "unhealthy", "error": str(e)}

    # Determine overall status based on dependent services
    overall_status = "healthy"
    if any(service["status"] != "healthy" for service in services.values()):
        overall_status = "degraded"

    # Return the health response
    return HealthResponse(
        status=overall_status,
        timestamp=time.time(),
        version="1.0.0",  # This should ideally come from a version file or environment variable
        services=services,
    )


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint for basic availability checks.
    """
    return {"ping": "pong", "timestamp": time.time()}