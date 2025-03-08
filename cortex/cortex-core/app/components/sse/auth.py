"""
SSE Authentication Service implementation for Cortex Core.

Provides authentication and authorization for SSE endpoints.
"""

from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import jwt

from app.utils.logger import logger
from app.config import settings

class SSEAuthService:
    """
    Authentication and authorization for SSE endpoints.
    """
    
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
            return user_info["id"] == resource_id
            
        # For workspace access, check membership if db provided
        if db and resource_type == "workspace":
            result = db.execute(
                text("SELECT id FROM workspace_members WHERE workspace_id = :workspace_id AND user_id = :user_id"),
                {"workspace_id": resource_id, "user_id": user_info["id"]}
            ).fetchone()
            return result is not None
            
        # For conversation access, check workspace membership if db provided
        if db and resource_type == "conversation":
            # Get the workspace for this conversation
            result = db.execute(
                text("SELECT workspace_id FROM conversations WHERE id = :conversation_id"),
                {"conversation_id": resource_id}
            ).fetchone()
            
            if not result:
                return False
                
            workspace_id = result[0]
            
            # Check access to the workspace
            return await self.verify_resource_access(
                user_info, "workspace", workspace_id, db
            )
        
        # If no db session or other checks, log warning and restrict access
        logger.warning(
            f"No database session for {resource_type} {resource_id} access check - "
            "denying access by default"
        )
        return False