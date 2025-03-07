"""
Health API Routes

This module defines health check endpoints to monitor the application status.
These endpoints provide information about the application and its dependencies.
"""

import time
from typing import Dict, Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis import redis_cache
from app.config import settings
from app.database.connection import get_db_session
from app.utils.logger import get_contextual_logger, log_execution_time

# Configure router
router = APIRouter(
    prefix="/health",
    tags=["health"],
)

# Configure logger
logger = get_contextual_logger("api.health")


@router.get(
    "/",
    summary="Basic health check",
    description="Returns a simple status indicating the application is running",
    response_description="Health status",
)
async def health() -> Dict[str, Any]:
    """
    Basic health check endpoint

    Returns basic application status and metadata.
    """
    return {
        "status": "healthy",
        "name": settings.app_name,
        "version": settings.version,
        "environment": settings.env,
    }


@router.get(
    "/detailed",
    summary="Detailed health check",
    description="Returns detailed health information including database and cache status",
    response_description="Detailed health status",
)
@log_execution_time
async def detailed_health(
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Detailed health check endpoint

    Returns detailed information about the application and its dependencies.
    """
    start_time = time.time()
    status_ok = True
    components = {}

    # Check database
    try:
        # Execute a simple query
        query_result = await db.execute("SELECT 1")
        await query_result.fetchone()
        components["database"] = {
            "status": "healthy",
            "type": "SQL",
            "url": settings.database_url.split("@")[-1]
            if "@" in settings.database_url
            else "***",
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        components["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        status_ok = False

    # Check Redis cache
    if settings.redis_url:
        try:
            # Test Redis connection
            redis_ok = await redis_cache.exists("health-check-key")
            components["cache"] = {
                "status": "healthy" if redis_ok is not None else "unhealthy",
                "type": "Redis",
                "enabled": True,
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            components["cache"] = {
                "status": "unhealthy",
                "error": str(e),
                "enabled": True,
            }
            status_ok = False
    else:
        components["cache"] = {
            "status": "disabled",
            "enabled": False,
        }

    # Set appropriate status code
    if not status_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    # Calculate response time
    response_time = time.time() - start_time

    return {
        "status": "healthy" if status_ok else "unhealthy",
        "name": settings.app_name,
        "version": settings.version,
        "environment": settings.env,
        "components": components,
        "response_time_ms": round(response_time * 1000, 2),
    }


@router.get(
    "/ping",
    summary="Ping check",
    description="Simple ping endpoint for load balancers",
    response_description="Ping response",
)
async def ping() -> Dict[str, str]:
    """
    Ping endpoint

    Returns a simple ping response for load balancers.
    """
    return {"ping": "pong"}
