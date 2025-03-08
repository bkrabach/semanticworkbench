"""
Authentication API endpoints for Cortex Core
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.components.auth_schemes import oauth2_scheme, oauth2_scheme_optional
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import uuid
from json import JSONEncoder

from app.database.connection import get_db
from app.database.models import User, ApiKey
from app.config import settings
from app.utils.logger import logger
from app.components.security_manager import SecurityManager
from app.components.tokens import TokenData, generate_jwt_token, verify_jwt_token

# Create router
router = APIRouter()

# Initialize security manager
security_manager = SecurityManager()

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

# Request and response models
class UserCredentials(BaseModel):
    """User credentials model"""

    type: str = "password"  # "password", "api_key", "oauth", "msal"
    identifier: str
    secret: Optional[str] = None
    provider: Optional[str] = None


class AuthResponse(BaseModel):
    """Authentication response model"""

    success: bool
    user_id: Optional[str] = None
    token: Optional[str] = None
    expires_at_utc: Optional[datetime] = None
    error: Optional[str] = None
    
    class Config:
        json_encoders = {
            # Ensure datetime is serialized to ISO format
            datetime: lambda dt: dt.isoformat()
        }


class ApiKeyRequest(BaseModel):
    """API key request model"""

    scopes: List[str] = ["*"]
    expiry_days: Optional[int] = None


class ApiKeyResponse(BaseModel):
    """API key response model"""

    key: str
    expires_at_utc: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            # Ensure datetime is serialized to ISO format
            datetime: lambda dt: dt.isoformat()
        }


# Authentication dependency
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from token

    Args:
        token: JWT token
        db: Database session

    Returns:
        Authenticated user

    Raises:
        HTTPException: If token is invalid or user doesn't exist
    """
    token_data = verify_jwt_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


# Routes
@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserCredentials, db: Session = Depends(get_db)):
    """
    Authenticate user and create a session token
    """
    try:
        logger.info(
            f"Authentication attempt for {credentials.identifier} using {credentials.type}"
        )

        # Authenticate based on credential type
        if credentials.type == "password":
            # Get user from database
            user = db.query(User).filter(
                User.email == credentials.identifier).first()

            # For development: auto-create test user if it doesn't exist
            if (
                not user
                and settings.server.host == "localhost"
                and credentials.identifier == "test@example.com"
                and credentials.secret == "password"
            ):
                import hashlib

                # Create password hash
                password_hash = hashlib.sha256(
                    credentials.secret.encode()).hexdigest()

                # Create test user
                user = User(
                    id=str(uuid.uuid4()),
                    email=credentials.identifier,
                    name="Test User",
                    password_hash=password_hash,
                    created_at_utc=datetime.now(timezone.utc),
                    updated_at_utc=datetime.now(timezone.utc),
                )
                db.add(user)

                # Commit to get the user ID
                db.commit()
                db.refresh(user)

                logger.info(f"Created test user: {credentials.identifier}")

                # Create default workspace for test user
                from app.database.models import Workspace
                now = datetime.now(timezone.utc)
                default_workspace = Workspace(
                    id=str(uuid.uuid4()),
                    name="My Workspace",
                    user_id=user.id,
                    created_at_utc=now,
                    last_active_at_utc=now,
                    config="{}",
                    meta_data="{}"
                )
                db.add(default_workspace)
                db.commit()
                logger.info(f"Created default workspace for test user: {user.id}")

            if not user:
                logger.warning(f"User not found: {credentials.identifier}")
                return AuthResponse(success=False, error="Invalid email or password")

            # Verify password
            import hashlib

            password_hash = hashlib.sha256(
                credentials.secret.encode()).hexdigest()

            if password_hash != user.password_hash:
                logger.warning(
                    f"Invalid password for user: {credentials.identifier}")
                return AuthResponse(success=False, error="Invalid email or password")

            # Update last login time
            user.last_login_at = datetime.utcnow()
            db.commit()
            
            # Check if user has any workspaces, create a default one if not
            from app.database.models import Workspace
            workspace_count = db.query(Workspace).filter(Workspace.user_id == user.id).count()
            if workspace_count == 0:
                # Create default workspace for existing user
                now = datetime.utcnow()
                default_workspace = Workspace(
                    id=str(uuid.uuid4()),
                    name="My Workspace",
                    user_id=user.id,
                    created_at=now,
                    last_active_at=now,
                    config="{}",
                    meta_data="{}"
                )
                db.add(default_workspace)
                db.commit()
                logger.info(f"Created default workspace for existing user: {user.id}")

        elif credentials.type == "api_key":
            # TODO: Implement API key authentication
            return AuthResponse(
                success=False, error="API key authentication not implemented yet"
            )

        elif credentials.type == "oauth" or credentials.type == "msal":
            # TODO: Implement OAuth/MSAL authentication
            return AuthResponse(
                success=False,
                error=f"{credentials.type.upper()} authentication not implemented yet",
            )

        else:
            return AuthResponse(
                success=False,
                error=f"Unsupported authentication type: {credentials.type}",
            )

        # Generate JWT token
        token_expires = datetime.utcnow() + timedelta(
            seconds=settings.security.token_expiry_seconds
        )
        token = generate_jwt_token(
            TokenData(user_id=user.id),
            expires_delta=timedelta(
                seconds=settings.security.token_expiry_seconds),
        )

        logger.info(f"User {user.id} authenticated successfully")

        return AuthResponse(
            success=True, user_id=user.id, token=token, expires_at=token_expires
        )

    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}", exc_info=True)
        return AuthResponse(success=False, error="Authentication failed")


@router.post("/refresh")
async def refresh_token():
    """Refresh an authentication token"""
    # TODO: Implement token refresh
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented"
    )


@router.post("/logout")
async def logout():
    """Log out and invalidate token"""
    # TODO: Implement token invalidation
    return {"message": "Logged out successfully"}


@router.post("/key/generate", response_model=ApiKeyResponse)
async def generate_api_key(
    request: ApiKeyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate an API key for programmatic access
    """
    try:
        # Calculate expiry date if provided
        expiry = None
        if request.expiry_days:
            expiry = datetime.utcnow() + timedelta(days=request.expiry_days)

        # Generate random key
        import secrets

        key = f"sk-{secrets.token_urlsafe(32)}"

        # Encrypt key for storage
        encrypted_key = security_manager.encrypt(key)

        # Create API key in database
        api_key = ApiKey(
            id=str(uuid.uuid4()),
            key=encrypted_key,
            user_id=user.id,
            scopes_json=security_manager.stringify_json(request.scopes),
            created_at=datetime.utcnow(),
            expires_at=expiry,
        )

        db.add(api_key)
        db.commit()

        logger.info(f"Generated API key for user {user.id}")

        return ApiKeyResponse(key=key, expires_at=expiry)

    except Exception as e:
        logger.error(f"Failed to generate API key: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate API key",
        )
