"""API request models for user endpoints."""

from typing import Dict, Any, Optional, ClassVar
from pydantic import BaseModel, Field, EmailStr, field_validator

class UserLoginRequest(BaseModel):
    """Request model for user login"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserRegisterRequest(BaseModel):
    """Request model for user registration"""
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., description="User name")
    password: str = Field(..., description="User password")
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserUpdateRequest(BaseModel):
    """Request model for updating user profile"""
    name: Optional[str] = Field(None, description="User name")
    metadata: Optional[Dict[str, Any]] = Field(None, description="User metadata")