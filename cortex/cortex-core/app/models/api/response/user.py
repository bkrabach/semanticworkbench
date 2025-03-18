"""API response models for user endpoints."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.domain.user import UserInfo, UserWithWorkspaces


class UserResponse(UserInfo):
    """API response model for user information."""
    pass


class UserWithWorkspacesResponse(UserWithWorkspaces):
    """API response model for user with workspaces."""
    pass


class Token(BaseModel):
    """Simple token response model for OAuth-compatible endpoints."""
    
    access_token: str
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    """API response model for authentication token with user info."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse


class UsersResponse(BaseModel):
    """API response model for a list of users."""
    
    users: List[UserResponse]
    count: int
    total: int