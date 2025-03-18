"""API response models for user endpoints."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class UserInfoResponse(BaseModel):
    """Response model for user information"""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="User name")
    roles: List[str] = Field(default_factory=list, description="User roles")


class UserDetailResponse(UserInfoResponse):
    """Response model for detailed user information"""
    created_at: datetime = Field(..., description="User creation timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="User metadata")


class LoginResponse(BaseModel):
    """Response model for login endpoint"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    user: UserInfoResponse = Field(..., description="User information")


class RegisterResponse(BaseModel):
    """Response model for register endpoint"""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    message: str = Field("User registered successfully", description="Success message")