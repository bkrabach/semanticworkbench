"""
Security Manager Component

This module provides security-related functionality including:
- User authentication
- Password hashing and verification
- JWT token generation and validation
- Session management
"""

import base64
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Union

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.connection import get_db_session
from app.database.models import Session, User, UserRole
from app.utils.logger import get_contextual_logger

# Configure logger
logger = get_contextual_logger("components.security_manager")

# OAuth2 scheme for token extraction from request
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_prefix.rstrip('/')}/auth/login",
    auto_error=False,
)


class SecurityManager:
    """
    Security Manager Component

    Handles user authentication, password hashing, JWT token
    generation and validation, and session management.
    """

    def __init__(self):
        """Initialize the security manager"""
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.jwt_algorithm = settings.jwt_algorithm
        self.secret_key = settings.secret_key
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = settings.refresh_token_expire_days

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches hash, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Get password hash

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)

    async def authenticate_user(
        self,
        email: str,
        password: str,
        db: AsyncSession,
    ) -> Optional[User]:
        """
        Authenticate a user with email and password

        Args:
            email: User email
            password: Plain text password
            db: Database session

        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            # Find user by email
            query = select(User).where(User.email == email)
            result = await db.execute(query)
            user = result.scalar_one_or_none()

            # Check if user exists and password is correct
            if not user or not self.verify_password(password, user.hashed_password):
                return None

            # Check if user is active
            if not user.is_active:
                logger.warning(f"Authentication attempt for inactive user: {email}")
                return None

            return user

        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            return None

    def create_access_token(
        self,
        subject: Union[str, uuid.UUID],
        role: UserRole,
        expires_delta: Optional[timedelta] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new access token

        Args:
            subject: Token subject (usually user ID)
            role: User role
            expires_delta: Optional custom expiration time
            extra_data: Optional extra data to include in the token

        Returns:
            JWT access token
        """
        # Set expiration time
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        # Create token payload
        to_encode = {
            "exp": expire,
            "iat": datetime.utcnow(),
            "sub": str(subject),
            "role": role.value if isinstance(role, UserRole) else role,
            "type": "access",
        }

        # Add extra data if provided
        if extra_data:
            for key, value in extra_data.items():
                # Don't overwrite reserved keys
                if key not in to_encode:
                    to_encode[key] = value

        # Encode token
        encoded_jwt = jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.jwt_algorithm,
        )

        return encoded_jwt

    async def create_refresh_token(
        self,
        user_id: Union[str, uuid.UUID],
        db: AsyncSession,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> str:
        """
        Create a new refresh token

        Args:
            user_id: User ID
            db: Database session
            user_agent: Optional user agent string
            ip_address: Optional IP address

        Returns:
            Refresh token string
        """
        # Generate random token
        token_bytes = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b"=")
        refresh_token = token_bytes.decode("ascii")

        # Set expiration time
        expires_at = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        # Create session record
        session = Session(
            user_id=user_id,
            refresh_token=refresh_token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        db.add(session)

        return refresh_token

    async def revoke_refresh_token(
        self,
        refresh_token: str,
        db: AsyncSession,
    ) -> bool:
        """
        Revoke a refresh token

        Args:
            refresh_token: Refresh token to revoke
            db: Database session

        Returns:
            True if token was revoked, False otherwise
        """
        try:
            # Find token
            query = select(Session).where(Session.refresh_token == refresh_token)
            result = await db.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                return False

            # Delete session
            await db.delete(session)

            return True

        except Exception as e:
            logger.error(f"Error revoking refresh token: {str(e)}")
            return False

    async def refresh_access_token(
        self,
        refresh_token: str,
        db: AsyncSession,
    ) -> Optional[Dict[str, str]]:
        """
        Refresh an access token

        Args:
            refresh_token: Refresh token
            db: Database session

        Returns:
            Dict with new access and refresh tokens, or None if invalid
        """
        try:
            # Find token
            query = select(Session).where(Session.refresh_token == refresh_token)
            result = await db.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                logger.warning("Refresh token not found")
                return None

            # Check if token is expired
            if session.expires_at < datetime.utcnow():
                logger.warning(f"Expired refresh token for user {session.user_id}")
                await db.delete(session)
                return None

            # Get user
            user_query = select(User).where(User.id == session.user_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()

            if not user or not user.is_active:
                logger.warning(f"User inactive or deleted: {session.user_id}")
                await db.delete(session)
                return None

            # Create new access token
            access_token = self.create_access_token(
                subject=user.id,
                role=user.role,
            )

            # Create new refresh token
            new_refresh_token = await self.create_refresh_token(
                user_id=user.id,
                db=db,
                user_agent=session.user_agent,
                ip_address=session.ip_address,
            )

            # Delete old session
            await db.delete(session)

            # Return new tokens
            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
            }

        except Exception as e:
            logger.error(f"Error refreshing access token: {str(e)}")
            return None

    def decode_token(
        self,
        token: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token

        Args:
            token: JWT token

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.jwt_algorithm],
            )

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None

        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None

        except Exception as e:
            logger.error(f"Error decoding token: {str(e)}")
            return None


# Create global instance
security_manager = SecurityManager()


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """
    Get current user from token

    This dependency extracts the user from a JWT token.

    Args:
        token: JWT token
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If authentication fails
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = security_manager.decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error",
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user

    This dependency checks if the authenticated user is active.

    Args:
        current_user: Authenticated user

    Returns:
        Active user

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get admin user

    This dependency checks if the authenticated user is an admin.

    Args:
        current_user: Authenticated user

    Returns:
        Admin user

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        logger.warning(f"Non-admin user attempted admin action: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return current_user


# Export public symbols
__all__ = [
    "SecurityManager",
    "security_manager",
    "get_current_user",
    "get_current_active_user",
    "get_admin_user",
]
