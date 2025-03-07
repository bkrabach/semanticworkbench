"""
Base Schema Models

This module defines Pydantic models used throughout the application
for data validation, serialization, and documentation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator, root_validator, constr

# Define generic type variable for pagination models
T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response model with a message field"""

    message: str


class Token(BaseModel):
    """Token model for authentication responses"""

    access_token: str
    refresh_token: str
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Expiration time in seconds")


class RefreshToken(BaseModel):
    """Refresh token model for token refresh requests"""

    refresh_token: str


class UserRole(str, Enum):
    """User role enumeration"""

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class UserBase(BaseModel):
    """Base user model with common fields"""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """User creation model"""

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User password (min 8 chars)",
    )

    @validator("password")
    def password_strength(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        # Check for at least one number
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one number")

        # Check for at least one uppercase letter
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")

        return v


class UserRead(UserBase):
    """User read model (response model)"""

    id: UUID
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    """User update model"""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=100,
        description="User password (min 8 chars)",
    )

    @validator("password")
    def password_strength(cls, v: Optional[str]) -> Optional[str]:
        """Validate password strength if provided"""
        if v is None:
            return None

        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        # Check for at least one number
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one number")

        # Check for at least one uppercase letter
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")

        return v


class ChangePasswordRequest(BaseModel):
    """Change password request model"""

    current_password: str
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (min 8 chars)",
    )

    @validator("new_password")
    def password_strength(cls, v: str) -> str:
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        # Check for at least one number
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one number")

        # Check for at least one uppercase letter
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")

        return v


class MemoryItemType(str, Enum):
    """Memory item type enumeration"""

    CONVERSATION = "conversation"
    DOCUMENT = "document"
    IMAGE = "image"
    CODE = "code"
    THOUGHT = "thought"
    NOTE = "note"
    SUMMARY = "summary"
    REFERENCE = "reference"
    CUSTOM = "custom"


class MemoryItemBase(BaseModel):
    """Base memory item model"""

    type: MemoryItemType
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    parent_id: Optional[UUID] = None


class MemoryItemCreate(MemoryItemBase):
    """Memory item creation model"""

    workspace_id: UUID
    parent_id: Optional[UUID] = None
    ttl: Optional[int] = None


class MemoryItemRead(MemoryItemBase):
    """Memory item read model (response model)"""

    id: UUID
    workspace_id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class MemoryItemUpdate(BaseModel):
    """Memory item update model"""

    content: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    ttl: Optional[int] = None


class MemoryItemSearch(BaseModel):
    """Memory item search request model"""

    query: str = Field(..., min_length=1)
    types: Optional[List[MemoryItemType]] = None
    limit: int = Field(20, ge=1, le=100)


class PaginationParams(BaseModel):
    """Common pagination parameters"""

    limit: int = Field(
        100, ge=1, le=1000, description="Maximum number of items to return"
    )
    offset: int = Field(0, ge=0, description="Number of items to skip")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model"""

    items: List[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        """Check if there are more items available"""
        return self.offset + len(self.items) < self.total


class FilterParams(BaseModel):
    """Common filter parameters for memory items"""

    types: Optional[List[MemoryItemType]] = None
    owner_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkspaceRole(str, Enum):
    """Workspace role enumeration"""

    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class WorkspaceBase(BaseModel):
    """Base workspace model"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)


class WorkspaceCreate(WorkspaceBase):
    """Workspace creation model"""

    pass


class WorkspaceRead(WorkspaceBase):
    """Workspace read model (response model)"""

    id: UUID
    owner_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class WorkspaceUpdate(BaseModel):
    """Workspace update model"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class WorkspaceUserRead(BaseModel):
    """Workspace user read model (response model)"""

    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class WorkspaceUserCreate(BaseModel):
    """Workspace user creation/update model"""

    user_id: UUID
    role: WorkspaceRole = WorkspaceRole.VIEWER


# Export public symbols
__all__ = [
    "BaseResponse",
    "Token",
    "RefreshToken",
    "UserRole",
    "UserBase",
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "ChangePasswordRequest",
    "MemoryItemType",
    "MemoryItemBase",
    "MemoryItemCreate",
    "MemoryItemRead",
    "MemoryItemUpdate",
    "MemoryItemSearch",
    "PaginationParams",
    "PaginatedResponse",
    "FilterParams",
    "WorkspaceRole",
    "WorkspaceBase",
    "WorkspaceCreate",
    "WorkspaceRead",
    "WorkspaceUpdate",
    "WorkspaceUserRead",
    "WorkspaceUserCreate",
]
