"""
Authentication API Routes

This module defines authentication-related endpoints including user registration,
login, token refresh, and user profile management.
"""

from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.security_manager import (
    security_manager,
    get_current_active_user,
    get_current_user,
)
from app.database.connection import get_db_session
from app.database.models import User, UserRole
from app.schemas.base import (
    Token,
    RefreshToken,
    UserCreate,
    UserRead,
    UserUpdate,
    ChangePasswordRequest,
    BaseResponse,
)
from app.utils.logger import get_contextual_logger, log_execution_time

# Configure router
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)

# Configure logger
logger = get_contextual_logger("api.auth")


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account with the provided details",
    response_description="The created user details",
)
@log_execution_time
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Register a new user

    Creates a new user account with the provided email, password, and full name.
    """
    logger.info(f"Registering new user with email: {user_data.email}")

    try:
        # Check if user already exists
        query = select(User).where(User.email == user_data.email)
        result = await db.execute(query)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.warning(
                f"Registration failed: Email {user_data.email} already in use"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        # Hash password
        hashed_password = security_manager.get_password_hash(user_data.password)

        # Create new user
        user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=UserRole.USER,  # Default role
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"User registered successfully: {user.id}")

        return user

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Database error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User registration failed due to a database constraint",
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Error during user registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration",
        )


@router.post(
    "/login",
    response_model=Token,
    summary="Login user",
    description="Authenticate user and return access token",
    response_description="Authentication tokens",
)
@log_execution_time
async def login(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Login user

    Authenticates a user with email/username and password, returning JWT tokens.
    """
    logger.info(f"Login attempt for user: {form_data.username}")

    # Authenticate user
    user = await security_manager.authenticate_user(
        email=form_data.username,
        password=form_data.password,
        db=db,
    )

    if not user:
        logger.warning(f"Login failed for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(
        minutes=security_manager.access_token_expire_minutes
    )
    access_token = security_manager.create_access_token(
        subject=user.id,
        role=user.role,
        expires_delta=access_token_expires,
    )

    # Create refresh token
    user_agent = request.headers.get("User-Agent")
    client_host = request.client.host if request.client else None

    refresh_token = await security_manager.create_refresh_token(
        user_id=user.id,
        db=db,
        user_agent=user_agent,
        ip_address=client_host,
    )

    await db.commit()

    logger.info(f"User logged in successfully: {user.id}")

    # Return tokens
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": security_manager.access_token_expire_minutes * 60,
    }


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh token",
    description="Get a new access token using a refresh token",
    response_description="New authentication tokens",
)
@log_execution_time
async def refresh_token(
    token_data: RefreshToken,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Refresh token

    Gets a new access token using a refresh token.
    """
    logger.info("Token refresh request")

    # Refresh token
    tokens = await security_manager.refresh_access_token(
        refresh_token=token_data.refresh_token,
        db=db,
    )

    if not tokens:
        logger.warning("Token refresh failed: Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await db.commit()

    logger.info("Token refreshed successfully")

    return tokens


@router.post(
    "/logout",
    response_model=BaseResponse,
    summary="Logout user",
    description="Revoke refresh token to logout user",
    response_description="Success response",
)
@log_execution_time
async def logout(
    token_data: RefreshToken,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Logout user

    Revokes the refresh token to logout the user.
    """
    logger.info(f"Logout request for user: {current_user.id}")

    # Revoke refresh token
    result = await security_manager.revoke_refresh_token(
        refresh_token=token_data.refresh_token,
        db=db,
    )

    if not result:
        logger.warning(f"Logout failed for user: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token",
        )

    await db.commit()

    logger.info(f"User logged out successfully: {current_user.id}")

    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user",
    description="Retrieve the authenticated user's profile information",
    response_description="Current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current user

    Returns the authenticated user's profile information.
    """
    return current_user


@router.put(
    "/me",
    response_model=UserRead,
    summary="Update current user",
    description="Update the authenticated user's profile information",
    response_description="Updated user profile",
)
@log_execution_time
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Update current user

    Updates the authenticated user's profile information.
    """
    logger.info(f"Updating user profile: {current_user.id}")

    try:
        # Update user fields if provided
        if user_data.full_name is not None:
            current_user.full_name = user_data.full_name

        if user_data.email is not None and user_data.email != current_user.email:
            # Check if email is already in use
            query = select(User).where(User.email == user_data.email)
            result = await db.execute(query)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                logger.warning(f"Update failed: Email {user_data.email} already in use")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered",
                )

            current_user.email = user_data.email

        if user_data.password is not None:
            current_user.hashed_password = security_manager.get_password_hash(
                user_data.password
            )

        # Normal users cannot update their own active status
        # This is handled by admins

        await db.commit()
        await db.refresh(current_user)

        logger.info(f"User profile updated successfully: {current_user.id}")

        return current_user

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Database error during profile update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile update failed due to a database constraint",
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Error during profile update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during profile update",
        )


@router.post(
    "/change-password",
    response_model=BaseResponse,
    summary="Change password",
    description="Change the authenticated user's password",
    response_description="Success response",
)
@log_execution_time
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, str]:
    """
    Change password

    Changes the authenticated user's password.
    """
    logger.info(f"Password change request for user: {current_user.id}")

    # Verify current password
    if not security_manager.verify_password(
        password_data.current_password, current_user.hashed_password
    ):
        logger.warning(
            f"Password change failed for user {current_user.id}: Invalid current password"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.hashed_password = security_manager.get_password_hash(
        password_data.new_password
    )

    await db.commit()

    logger.info(f"Password changed successfully for user: {current_user.id}")

    return {"message": "Password changed successfully"}
