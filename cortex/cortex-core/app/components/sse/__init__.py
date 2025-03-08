"""
Server-Sent Events (SSE) module for Cortex Core.

This module provides components for managing SSE connections, authentication,
and event broadcasting for real-time client updates.
"""

from app.components.sse.manager import SSEConnectionManager
from app.components.sse.auth import SSEAuthService
from app.components.sse.events import SSEEventSubscriber
from app.components.event_system import get_event_system

# Singleton instance for the SSE service
_sse_service = None

class SSEService:
    """
    Central service for SSE functionality.
    Provides a unified interface to all SSE operations.
    """
    
    def __init__(self):
        """Initialize the SSE service and its components"""
        self.connection_manager = SSEConnectionManager()
        self.auth_service = SSEAuthService()
        self.event_subscriber = SSEEventSubscriber(
            get_event_system(), self.connection_manager
        )
        
    async def initialize(self):
        """Initialize the service components"""
        await self.event_subscriber.initialize()
        
    async def cleanup(self):
        """Clean up resources"""
        await self.event_subscriber.cleanup()
        
    async def authenticate_token(self, token: str) -> dict:
        """Authenticate a token and return user info"""
        return await self.auth_service.authenticate_token(token)
        
    async def verify_resource_access(self, user_info: dict, resource_type: str, resource_id: str, db=None) -> bool:
        """Verify a user's access to a resource"""
        return await self.auth_service.verify_resource_access(
            user_info, resource_type, resource_id, db
        )

def get_sse_service():
    """Get the global SSE service instance"""
    global _sse_service
    if _sse_service is None:
        _sse_service = SSEService()
    return _sse_service