import time
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

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
async def health_check():
    """
    Health check endpoint for the Cortex API.
    Returns the status of the API and its dependencies.
    """
    # Collect service health checks
    services = {}

    # Check cognition service health
    try:
        # In a real implementation, this would call a health check method
        # on the cognition client that returns actual status
        # For now, we simulate a successful check
        services["cognition"] = {"status": "healthy", "latency_ms": 10.5}
    except Exception as e:
        services["cognition"] = {"status": "unhealthy", "error": str(e)}

    # Check memory service health
    try:
        # Similarly, this would call a real health check in production
        services["memory"] = {"status": "healthy", "latency_ms": 5.2}
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
