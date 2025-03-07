"""
API Routes Package

This package contains all API route modules for the application.
Each module defines a FastAPI router with endpoints for a specific resource.
"""

# Import all API routers here for easy access from main application
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.memory import router as memory_router

# Export routers for use in main application
__all__ = [
    "health_router",
    "auth_router",
    "memory_router",
]
