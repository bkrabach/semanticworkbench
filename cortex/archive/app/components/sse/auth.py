"""
SSE Authentication Service implementation for Cortex Core.

Provides authentication and authorization for SSE endpoints.
This service is being deprecated in favor of SSEService in app.services.sse_service
which follows the domain-driven repository architecture.
"""

from typing import Optional
from fastapi import HTTPException
import jwt

from app.utils.logger import logger
from app.config import settings
from app.database.repositories.resource_access_repository import ResourceAccessRepository
from app.models.domain.user import UserInfo


class SSEAuthService:
    """
    DEPRECATED: Authentication and authorization for SSE endpoints.
    
    This class is being deprecated in favor of SSEService in app.services.sse_service
    which follows the domain-driven repository architecture.
    
    Handles authentication of tokens and authorization of access to resources
    for Server-Sent Events connections.
    """
    
    def __init__(self, resource_access_repo: Optional[ResourceAccessRepository] = None):
        """
        Initialize the SSE authentication service
        
        Args:
            resource_access_repo: Repository for resource access checks
        """
        self.resource_access_repo = resource_access_repo
        
        # Warn about deprecation
        import warnings
        warnings.warn(
            "SSEAuthService is deprecated. Use SSEService from app.services.sse_service instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
    async def authenticate_token(self, token: str) -> UserInfo:
        """
        Authenticate a token and return user info
        
        Args:
            token: JWT token to authenticate
            
        Returns:
            UserInfo model with authenticated user information
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Verify the token
            payload = jwt.decode(
                token, 
                settings.security.jwt_secret, 
                algorithms=["HS256"]
            )
            
            user_id = payload.get("user_id")
            if not user_id:
                raise HTTPException(
                    status_code=401, 
                    detail="Invalid token format: missing user_id"
                )
            
            # Create and return UserInfo domain model
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            
            return UserInfo(
                id=user_id,
                email=payload.get("email", ""),
                name=payload.get("name", ""),
                roles=payload.get("roles", []),
                created_at=now
            )
            
        except jwt.InvalidTokenError as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(
                status_code=401, 
                detail="Invalid authentication token"
            )
            
    async def verify_resource_access(self, 
                                  user_info: UserInfo,
                                  resource_type: str,
                                  resource_id: str,
                                  **kwargs) -> bool:
        """
        Verify a user's access to a resource
        
        Args:
            user_info: UserInfo domain model
            resource_type: Type of resource (user, workspace, conversation)
            resource_id: ID of the resource
            
        Returns:
            Boolean indicating whether user has access
        """
        # Users can only access their own user events
        if resource_type == "user":
            return bool(user_info.id == resource_id)
            
        # Ensure repository is available
        if not self.resource_access_repo:
            logger.error(
                f"No resource access repository available for {resource_type} {resource_id} access check - "
                "denying access by default"
            )
            return False
            
        # For workspace access, check ownership and sharing
        if resource_type == "workspace":
            # First check if user is the owner
            if self.resource_access_repo.is_workspace_owner(resource_id, user_info.id):
                return True
                
            # Then check if workspace is shared with the user
            return self.resource_access_repo.has_workspace_sharing_access(resource_id, user_info.id)
            
        # For conversation access, check workspace access
        if resource_type == "conversation":
            # Get the workspace for this conversation
            workspace_id = self.resource_access_repo.get_conversation_workspace_id(resource_id)
            
            if not workspace_id:
                return False
                
            # Check access to the workspace
            return await self.verify_resource_access(
                user_info, "workspace", workspace_id
            )
        
        # Unsupported resource type
        logger.warning(f"Unsupported resource type: {resource_type}")
        return False