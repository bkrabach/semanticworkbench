"""Router components for the Cortex application."""

from app.components.router.message_router import get_router
from app.components.router.message_handlers import register_handlers

__all__ = ["get_router", "register_handlers"]