import os
import platform
import time
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.backend.cognition_client import CognitionClient
from app.backend.memory_client import MemoryClient

router = APIRouter(prefix="/health", tags=["health"])

# Store the application start time for uptime calculation
APP_START_TIME = time.time()


class HealthServiceStatus(BaseModel):
    """Status information for a dependent service."""

    status: str
    latency_ms: float = 0
    error: str = ""


class SystemInfo(BaseModel):
    """System information for the health check."""

    hostname: str
    platform: str
    python_version: str
    uptime_seconds: float
    environment: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: float
    version: str
    system: SystemInfo
    services: Dict[str, Dict[str, Any]]


@router.get("", response_model=HealthResponse)
async def health_check(request: Request):
    """
    Health check endpoint for the Cortex API.
    Returns the status of the API, system information, and the status of its dependencies.
    """
    # Access response handler from application state
    app = request.app
    response_handler = app.state.response_handler if hasattr(app.state, "response_handler") else None
    
    # Get version from environment or default
    version = os.environ.get("APP_VERSION", "1.0.0")
    
    # Calculate uptime
    uptime_seconds = time.time() - APP_START_TIME
    
    # Get system information
    system_info = SystemInfo(
        hostname=platform.node(),
        platform=f"{platform.system()} {platform.release()}",
        python_version=platform.python_version(),
        uptime_seconds=uptime_seconds,
        environment=os.environ.get("ENVIRONMENT", "development")
    )
    
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
            "tools": [t.name for t in tools_response.tools],
            "last_checked": datetime.now().isoformat()
        }
    except Exception as e:
        services["cognition"] = {
            "status": "unhealthy", 
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }

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
        
        services["memory"] = {
            "status": "healthy", 
            "latency_ms": latency_ms,
            "last_checked": datetime.now().isoformat()
        }
    except Exception as e:
        services["memory"] = {
            "status": "unhealthy", 
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }

    # Determine overall status based on dependent services
    overall_status = "healthy"
    if any(service["status"] != "healthy" for service in services.values()):
        overall_status = "degraded"

    # Return the health response
    return HealthResponse(
        status=overall_status,
        timestamp=time.time(),
        version=version,
        system=system_info,
        services=services,
    )


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint for basic availability checks.
    """
    return {"ping": "pong", "timestamp": time.time()}