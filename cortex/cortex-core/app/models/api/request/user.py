"""API request models for user endpoints."""

from pydantic import BaseModel, EmailStr

from app.models.domain.user import UserCreate, UserUpdate


class CreateUserRequest(UserCreate):
    """API request model for creating a user."""
    pass


class UpdateUserRequest(UserUpdate):
    """API request model for updating a user."""
    pass


class UserLogin(BaseModel):
    """API request model for user login."""
    
    email: EmailStr
    password: str