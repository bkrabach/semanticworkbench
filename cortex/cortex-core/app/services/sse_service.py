"""
SSE (Server-Sent Events) service implementation for Cortex Core.

This module provides a service layer for SSE functionality, following the
domain-driven repository architecture pattern.
"""

from typing import Tuple
import asyncio
from sqlalchemy.orm import Session

from app.components.sse.starlette_manager import SSEStarletteManager
from app.components.sse.events import SSEEventSubscriber
from app.components.event_system import get_event_system
from app.database.repositories.resource_access_repository import ResourceAccessRepository
from app.database.connection import get_db
from app.models.domain.user import UserInfo
from app.models.domain.sse import SSEConnectionStats
from app.utils.logger import logger
import jwt
from app.config import settings
from fastapi import Depends


class SSEService:
    """
    Server-Sent Events service.

    Provides a unified interface to all SSE operations including
    authentication, authorization, message broadcasting, and connection
    management.
    
    This service implements the domain-driven repository pattern by:
    1. Using domain models for all business logic and communications
    2. Isolating data access in repositories
    3. Providing an interface over internal components
    4. Handling conversions between domain and API models
    5. Maintaining clear separation of concerns
    
    The service acts as the orchestrator for SSE functionality, bringing together
    the connection manager, event subscriber, and repository components while
    maintaining a clean architecture with well-defined responsibilities.
    """

    def __init__(self, db_session: Session, repository: ResourceAccessRepository):
        """
        Initialize the SSE service and its components.

        Args:
            db_session: SQLAlchemy database session
            repository: Resource access repository for authorization checks
        """
        self.db = db_session
        self.repository = repository
        self.connection_manager = SSEStarletteManager()
        self.event_subscriber = SSEEventSubscriber(get_event_system(), self.connection_manager)

    async def initialize(self):
        """
        Initialize the service components.

        This method should be called at application startup to set up any
        required event subscriptions or background tasks.
        """
        await self.event_subscriber.initialize()

    async def cleanup(self):
        """
        Clean up resources.

        This method should be called at application shutdown to properly
        release resources and cancel any background tasks.
        """
        await self.event_subscriber.cleanup()

    async def authenticate_token(self, token: str) -> UserInfo:
        """
        Authenticate a token and return user info.

        Args:
            token: JWT token to authenticate

        Returns:
            UserInfo: Domain model with authenticated user information

        Raises:
            HTTPException: If token is invalid
        """
        from fastapi import HTTPException

        try:
            # Verify the token
            payload = jwt.decode(token, settings.security.jwt_secret, algorithms=["HS256"])

            user_id = payload.get("user_id")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token format: missing user_id")

            # Create and return UserInfo domain model
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)

            return UserInfo(
                id=user_id,
                email=payload.get("email", ""),
                name=payload.get("name"),
                roles=payload.get("roles", []),
                created_at=now,
            )

        except jwt.InvalidTokenError as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(status_code=401, detail="Invalid authentication token")

    async def verify_resource_access(self, user_info: UserInfo, resource_type: str, resource_id: str) -> bool:
        """
        Verify a user's access to a resource.

        Args:
            user_info: UserInfo domain model
            resource_type: Type of resource (user, workspace, conversation)
            resource_id: ID of the resource

        Returns:
            Boolean indicating whether user has access
        """
        # Users can only access their own user events
        if resource_type == "user":
            return user_info.id == resource_id

        # For workspace access, check ownership and sharing
        if resource_type == "workspace":
            # First check if user is the owner
            if self.repository.is_workspace_owner(resource_id, user_info.id):
                return True

            # Then check if workspace is shared with the user
            return self.repository.has_workspace_sharing_access(resource_id, user_info.id)

        # For conversation access, check workspace access
        if resource_type == "conversation":
            # Get the workspace for this conversation
            workspace_id = self.repository.get_conversation_workspace_id(resource_id)

            if not workspace_id:
                return False

            # Check access to the workspace
            return await self.verify_resource_access(user_info, "workspace", workspace_id)

        # Default deny for unsupported resource types
        logger.warning(f"Unsupported resource type: {resource_type}")
        return False

    async def register_connection(self, channel_type: str, resource_id: str, user_id: str) -> Tuple[asyncio.Queue, str]:
        """
        Register a new SSE connection.

        Args:
            channel_type: Type of events to subscribe to
            resource_id: ID of the resource to subscribe to
            user_id: ID of the user making the connection

        Returns:
            Tuple containing the event queue and connection ID
        """
        return await self.connection_manager.register_connection(channel_type, resource_id, user_id)

    async def remove_connection(self, channel_type: str, resource_id: str, connection_id: str):
        """
        Remove an SSE connection.

        Args:
            channel_type: Type of events the connection is subscribed to
            resource_id: ID of the resource the connection is subscribed to
            connection_id: ID of the connection to remove
        """
        await self.connection_manager.remove_connection(channel_type, resource_id, connection_id)

    async def generate_sse_events(self, queue: asyncio.Queue):
        """
        Generate SSE events from a queue.

        Args:
            queue: Asyncio queue containing events

        Returns:
            Generator yielding SSE event strings
        """
        return self.connection_manager.generate_sse_events(queue)

    async def create_sse_stream(self, channel_type: str, resource_id: str, token: str, request):
        """
        Create an SSE stream for a specific channel type and resource.
        
        This method encapsulates all the logic needed to set up an SSE stream,
        including authentication, authorization, and connection registration.
        It follows the domain-driven repository pattern by:
        
        1. Handling all business logic in the service layer
        2. Isolating the API layer from implementation details
        3. Using domain models for all operations
        4. Managing component life cycles internally
        
        Args:
            channel_type: Type of events to subscribe to
            resource_id: ID of the resource to subscribe to
            token: Authentication token
            request: The FastAPI request object from the API endpoint
            
        Returns:
            EventSourceResponse from sse-starlette with SSE stream
        """
        from fastapi import HTTPException
        
        # Authenticate user
        user_info = await self.authenticate_token(token)
        
        # For non-global channels, verify resource access
        if channel_type != "global":
            has_access = await self.verify_resource_access(user_info, channel_type, resource_id)
            
            if not has_access:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Not authorized to access {channel_type} events for {resource_id}"
                )
        
        # Log connection status for debugging
        logger.info(f"SSE Connection requested - type: {channel_type}, resource: {resource_id}, user: {user_info.id}")
        
        # Debug the connection manager state before creating the connection
        stats = self.get_connection_stats()
        logger.info(f"Current active connections: {stats.total_connections}")
        if channel_type == "conversation":
            conv_key = f"conversation:{resource_id}"
            logger.info(f"Current conversation connections: {stats.connections_by_channel.get(conv_key, 0)}")
        
        # Handle special case for conversation channel - start publisher
        if channel_type == "conversation":
            try:
                from app.components.conversation_channels import get_conversation_publisher
                
                # Start the publisher, but await it directly instead of creating a task
                publisher = await get_conversation_publisher(resource_id)
                logger.info(f"Created conversation publisher for {resource_id}: {publisher}")
            except Exception as e:
                logger.error(f"Error initializing conversation publisher: {e}")
                import traceback
                logger.error(f"Publisher error details: {traceback.format_exc()}")
        
        # Use the actual request from the API endpoint
        # This ensures that the client disconnect detection works properly
        logger.info(f"Creating SSE response through connection manager for {channel_type}/{resource_id}")
        try:
            response = await self.connection_manager.create_sse_response(
                channel_type=channel_type,
                resource_id=resource_id,
                user_id=user_info.id,
                request=request
            )
            logger.info(f"Successfully created SSE response for {channel_type}/{resource_id}")
            
            # Debug state after creating connection
            stats = self.get_connection_stats() 
            logger.info(f"After creating connection - total active: {stats.total_connections}")
            if channel_type == "conversation":
                conv_key = f"conversation:{resource_id}"
                logger.info(f"After creating connection - conversation connections: {stats.connections_by_channel.get(conv_key, 0)}")
            
            return response
        except Exception as e:
            logger.error(f"Error creating SSE response: {e}")
            import traceback
            logger.error(f"SSE response error details: {traceback.format_exc()}")
            raise
    
    def get_connection_stats(self) -> SSEConnectionStats:
        """
        Get statistics about active SSE connections.
        
        This method demonstrates the domain-driven repository pattern by:
        1. Retrieving raw data from the component layer
        2. Converting this data to a proper domain model
        3. Ensuring type safety through Pydantic validation
        4. Returning a domain model to the caller
        
        The service layer is responsible for these transformations, shielding
        both the API layer and the component layer from each other's implementation
        details.

        Returns:
            SSEConnectionStats domain model with connection statistics
        """
        # Get raw statistics from the connection manager
        stats_dict = self.connection_manager.get_stats()

        # Transform the raw data into a properly typed domain model
        # This provides validation and ensures consistent structure
        return SSEConnectionStats(
            id="stats",
            total_connections=stats_dict["total_connections"],
            connections_by_channel=stats_dict["connections_by_channel"],
            connections_by_user=stats_dict["connections_by_user"],
            generated_at=stats_dict["generated_at"]
        )


# Singleton instance for backward compatibility during migration
_sse_service = None


# Factory function for dependency injection
def get_sse_service(db: Session = Depends(get_db)) -> SSEService:
    """
    Factory function to create an SSE service.

    Args:
        db: SQLAlchemy database session

    Returns:
        SSEService instance
    """
    # For testing we need a hack to allow overriding the service
    if hasattr(get_sse_service, "override"):
        override = getattr(get_sse_service, "override")
        if override is not None:
            return override  # type: ignore

    # For production use, create a real service
    from app.database.repositories.resource_access_repository import get_resource_access_repository
    
    repository = get_resource_access_repository(db)
    return SSEService(db, repository)


# Create an attribute for testing overrides
setattr(get_sse_service, "override", None)
