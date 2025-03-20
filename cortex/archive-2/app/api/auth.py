"""
Authentication API endpoints for the Cortex application.

This module handles user registration, login, token refresh, and other auth-related endpoints.
"""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.config import settings
from app.database.connection import get_db
from app.models.api.request.user import UserCreate, UserLogin
from app.models.api.response.user import Token, UserResponse
from app.services.user_service import UserService

router = APIRouter(tags=["auth"])

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """
    Dependency to get the current authenticated user from a JWT token.
    
    Args:
        token: The JWT token from the request
        user_service: The user service instance
        
    Returns:
        The authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        user_id = user_service.verify_token(token)
        if not user_id:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    
    return user


async def get_user_service() -> UserService:
    """
    Dependency to get a UserService instance.
    
    Returns:
        A UserService instance
    """
    db = await get_db()
    return UserService(db=db)


@router.post("/auth/register", response_model=UserResponse)
async def register(
    user_data: UserCreate, 
    user_service: Annotated[UserService, Depends(get_user_service)]
) -> UserResponse:
    """
    Register a new user.
    
    Args:
        user_data: The user registration data
        user_service: The user service instance
        
    Returns:
        The newly created user
        
    Raises:
        HTTPException: If registration fails
    """
    try:
        user = await user_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/auth/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> Token:
    """
    OAuth2 compatible token login endpoint.
    
    Args:
        form_data: The OAuth2 form data
        user_service: The user service instance
        
    Returns:
        An access token
        
    Raises:
        HTTPException: If authentication fails
    """
    user = await user_service.authenticate_user(
        email=form_data.username,  # OAuth2 form uses username field
        password=form_data.password,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = user_service.create_access_token(
        data={"sub": user.id},
        expires_delta=access_token_expires,
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/auth/login", response_model=Token)
async def login(
    login_data: UserLogin,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> Token:
    """
    Login using email and password to get an access token.
    
    Args:
        login_data: The user login data
        user_service: The user service instance
        
    Returns:
        An access token
        
    Raises:
        HTTPException: If authentication fails
    """
    user = await user_service.authenticate_user(
        email=login_data.email,
        password=login_data.password,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = user_service.create_access_token(
        data={"sub": user.id},
        expires_delta=access_token_expires,
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/auth/me", response_model=UserResponse)
async def read_users_me(
    current_user: Annotated[UserResponse, Depends(get_current_user)]
) -> UserResponse:
    """
    Get the current authenticated user.
    
    Args:
        current_user: The current authenticated user
        
    Returns:
        The current user's info
    """
    return current_user