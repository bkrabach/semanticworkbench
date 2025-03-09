"""
SSE Authentication Service implementation for Cortex Core.

Provides authentication and authorization for SSE endpoints.
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
import jwt

from app.utils.logger import logger
from app.config import settings
from app.database.repositories import ResourceAccessRepository

class SSEAuthService:
    """
    Authentication and authorization for SSE endpoints.
    """
    
    def __init__(self, resource_access_repo: Optional[ResourceAccessRepository] = None):
        """
        Initialize the SSE authentication service
        
        Args:
            resource_access_repo: Optional repository for resource access checks
        """
        self.resource_access_repo = resource_access_repo
    
    async def authenticate_token(self, token: str) -> Dict[str, Any]:
        """
        Authenticate a token and return user info
        
        Args:
            token: JWT token to authenticate
            
        Returns:
            Dictionary with user information
            
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
                
            return {
                "id": user_id,
                "roles": payload.get("roles", [])
            }
            
        except jwt.InvalidTokenError as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(
                status_code=401, 
                detail="Invalid authentication token"
            )
            
    async def verify_resource_access(self, 
                                  user_info: Dict[str, Any],
                                  resource_type: str,
                                  resource_id: str,
                                  db: Optional[Session] = None) -> bool:
        """
        Verify a user's access to a resource
        
        Args:
            user_info: User information dictionary
            resource_type: Type of resource (user, workspace, conversation)
            resource_id: ID of the resource
            db: Optional database session for access checks
            
        Returns:
            Boolean indicating whether user has access
        """
        # Users can only access their own user events
        if resource_type == "user":
            return bool(user_info["id"] == resource_id)
            
        # If we have a repository, use it for permissions checks
        if self.resource_access_repo:
            # For workspace access, check ownership and sharing
            if resource_type == "workspace":
                # First check if user is the owner
                if self.resource_access_repo.is_workspace_owner(resource_id, user_info["id"]):
                    return True
                    
                # Then check if workspace is shared with the user
                return self.resource_access_repo.has_workspace_sharing_access(resource_id, user_info["id"])
                
            # For conversation access, check workspace access
            if resource_type == "conversation":
                # Get the workspace for this conversation
                workspace_id = self.resource_access_repo.get_conversation_workspace_id(resource_id)
                
                if not workspace_id:
                    return False
                    
                # Check access to the workspace
                return await self.verify_resource_access(
                    user_info, "workspace", workspace_id, db
                )
        
        # Fallback to direct DB queries if no repository is available
        elif db:
            # For workspace access, check ownership and sharing
            if resource_type == "workspace":
                from app.database.models import Workspace, WorkspaceSharing
                
                # First check if user is the owner
                workspace = db.query(Workspace).filter(
                    Workspace.id == resource_id,
                    Workspace.user_id == user_info["id"]
                ).first()
                
                if workspace:
                    return True
                    
                # Then check if workspace is shared with the user
                sharing = db.query(WorkspaceSharing).filter(
                    WorkspaceSharing.workspace_id == resource_id,
                    WorkspaceSharing.user_id == user_info["id"]
                ).first()
                
                return sharing is not None
                
            # For conversation access, check workspace membership
            if resource_type == "conversation":
                from app.database.models import Conversation
                
                # Get the workspace for this conversation
                conversation = db.query(Conversation).filter(
                    Conversation.id == resource_id
                ).first()
                
                if not conversation:
                    return False
                    
                # Check access to the workspace
                return await self.verify_resource_access(
                    user_info, "workspace", str(conversation.workspace_id), db
                )
        
        # If no repository or db session, log warning and restrict access
        logger.warning(
            f"No resource access repository or database session for {resource_type} {resource_id} access check - "
            "denying access by default"
        )
        return False