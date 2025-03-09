"""
Authentication API endpoints for Cortex Core
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.components.auth_schemes import oauth2_scheme
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import uuid
import hashlib

from app.database.connection import get_db
from app.database.models import ApiKey
from app.database.repositories.user_repository import get_user_repository, UserRepository
from app.database.repositories.workspace_repository import get_workspace_repository, WorkspaceRepository
from app.services.user_service import get_user_service, UserService
from app.models.domain.user import User, UserInfo
from app.models.api.request.user import UserLoginRequest, UserRegisterRequest
from app.models.api.response.user import LoginResponse, RegisterResponse, UserInfoResponse
from app.config import settings
from app.utils.logger import logger
from app.components.security_manager import SecurityManager
from app.components.tokens import TokenData, generate_jwt_token, verify_jwt_token
from app.components.event_system import get_event_system, EventSystem

# Create router
router = APIRouter()

# Initialize security manager
security_manager = SecurityManager()

# API key models (to be moved to domain models later)
class ApiKeyRequest(BaseModel):
    """API key request model"""
    scopes: List[str] = ["*"]
    expiry_days: Optional[int] = None


class ApiKeyResponse(BaseModel):
    """API key response model"""
    key: str
    expires_at_utc: Optional[datetime] = None
    
    model_config = {
        "json_encoders": {
            # Ensure datetime is serialized to ISO format
            datetime: lambda dt: dt.isoformat()
        }
    }

# Factory functions for dependency injection
def get_user_service_with_events() -> UserService:
    """Get a user service instance with event system"""
    db = get_db()
    repository = get_user_repository(db)
    event_system = get_event_system()
    return get_user_service(db, repository, event_system)

# Authentication dependency
async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    user_service: UserService = Depends(get_user_service_with_events)
) -> User:
    """
    Get current authenticated user from token

    Args:
        token: JWT token
        user_service: User service

    Returns:
        Authenticated user (domain model)

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

    user = user_service.get_user(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


# Routes
@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: UserLoginRequest
) -> LoginResponse:
    """
    Authenticate user and create a session token
    """
    user_service = get_user_service_with_events()
    workspace_repo = get_workspace_repository(get_db())
    try:
        logger.info(f"Authentication attempt for {credentials.email}")

        # Get user from database
        user = user_service.get_user_by_email(credentials.email)

        # For development: auto-create test user if it doesn't exist
        if (
            not user
            and settings.server.host == "localhost"
            and credentials.email == "test@example.com"
            and credentials.password == "password"
        ):
            # Create password hash
            password_hash = hashlib.sha256(credentials.password.encode()).hexdigest()

            # Create test user
            user = user_service.create_user(
                email=credentials.email,
                name="Test User",
                password_hash=password_hash
            )

            logger.info(f"Created test user: {credentials.email}")

            # Create default workspace for test user
            default_workspace = workspace_repo.create_workspace(
                user_id=user.id,
                name="My Workspace"
            )
            
            logger.info(f"Created default workspace for test user: {user.id}")

        if not user:
            logger.warning(f"User not found: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Verify password
        password_hash = hashlib.sha256(credentials.password.encode()).hexdigest()

        if password_hash != user.password_hash:
            logger.warning(f"Invalid password for user: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Update last login time
        user = user_service.update_last_login(user.id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user has any workspaces, create a default one if not
        workspaces = workspace_repo.get_user_workspaces(user.id, limit=1)
        if not workspaces:
            # Create default workspace for existing user
            default_workspace = workspace_repo.create_workspace(
                user_id=user.id,
                name="My Workspace"
            )
            
            logger.info(f"Created default workspace for existing user: {user.id}")

        # Generate JWT token
        token_expires = datetime.now(timezone.utc) + timedelta(
            seconds=settings.security.token_expiry_seconds
        )
        token = generate_jwt_token(
            TokenData(user_id=user.id),
            expires_delta=timedelta(seconds=settings.security.token_expiry_seconds),
        )

        logger.info(f"User {user.id} authenticated successfully")

        # Create response with user info
        user_info = UserInfoResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            roles=user.roles
        )

        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user=user_info
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


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
    # TODO: Implement token invalidation via user service
    return {"message": "Logged out successfully"}


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: UserRegisterRequest
):
    """Register a new user account"""
    user_service = get_user_service_with_events()
    workspace_repo = get_workspace_repository(get_db())
    try:
        # Check if user already exists
        existing_user = user_service.get_user_by_email(request.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists"
            )
            
        # Create password hash
        password_hash = hashlib.sha256(request.password.encode()).hexdigest()
        
        # Create new user
        user = user_service.create_user(
            email=request.email,
            name=request.name,
            password_hash=password_hash
        )
        
        # Create default workspace
        default_workspace = workspace_repo.create_workspace(
            user_id=user.id,
            name="My Workspace"
        )
        
        logger.info(f"Registered new user: {user.id} ({request.email})")
        
        # Return success response
        return RegisterResponse(
            id=user.id,
            email=user.email,
            message="User registered successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    token: str = Depends(oauth2_scheme)
):
    """Get the current authenticated user's information"""
    user_service = get_user_service_with_events()
    user = await get_current_user(token, user_service)
    return UserInfoResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        roles=user.roles
    )


@router.post("/key/generate", response_model=ApiKeyResponse)
async def generate_api_key(
    request: ApiKeyRequest,
    token: str = Depends(oauth2_scheme)
):
    """
    Generate an API key for programmatic access
    """
    db = get_db()
    user_service = get_user_service_with_events()
    user = await get_current_user(token, user_service)
    try:
        # Calculate expiry date if provided
        expiry = None
        if request.expiry_days:
            expiry = datetime.now(timezone.utc) + timedelta(days=request.expiry_days)

        # Generate random key
        import secrets

        key = f"sk-{secrets.token_urlsafe(32)}"

        # Encrypt key for storage
        encrypted_key = security_manager.encrypt(key)

        # Create API key in database
        api_key = ApiKey(
            id=str(uuid.uuid4()),
            key=encrypted_key,
            user_id=str(user.id),
            scopes_json=security_manager.stringify_json(request.scopes),
            created_at_utc=datetime.now(timezone.utc),
            expires_at_utc=expiry,
        )

        db.add(api_key)
        db.commit()

        logger.info(f"Generated API key for user {user.id}")

        return ApiKeyResponse(key=key, expires_at_utc=expiry)

    except Exception as e:
        logger.error(f"Failed to generate API key: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate API key",
        )
