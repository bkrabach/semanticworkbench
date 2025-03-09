"""
User domain models for the Cortex Core application.

This module defines the domain models related to users, including
authentication and authorization concepts.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import EmailStr, Field

from app.models.domain.base import TimestampedModel, MetadataModel


class User(TimestampedModel, MetadataModel):
    """
    Domain model for a user in the system.
    
    Represents a user account with core identity information.
    """
    email: EmailStr
    name: Optional[str] = None
    last_login_at: Optional[datetime] = None
    roles: List[str] = Field(default_factory=list)


class UserInfo(TimestampedModel):
    """
    Domain model for limited user information.
    
    Used for scenarios where full user details aren't needed,
    such as in authentication responses.
    """
    id: str
    email: str  # We use str instead of EmailStr to avoid validation errors during auth
    name: Optional[str] = None
    roles: List[str] = Field(default_factory=list)