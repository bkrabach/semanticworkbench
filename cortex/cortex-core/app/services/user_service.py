"""User service for business logic."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.config import settings
from app.database.repositories import UserRepository
from app.models.domain.user import UserCreate, UserInfo, UserUpdate, UserWithWorkspaces, WorkspaceAccess
from app.services.base import BaseService
from app.exceptions import ResourceNotFoundError, AuthenticationError


class UserService(BaseService[UserRepository, UserInfo]):
    """Service for user operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the service.
        
        Args:
            db: The database session
        """
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        repository = UserRepository(db)
        super().__init__(repository, db)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash.
        
        Args:
            plain_password: The plain text password
            hashed_password: The hashed password
            
        Returns:
            True if the password matches the hash, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password.
        
        Args:
            password: The plain text password
            
        Returns:
            The hashed password
        """
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token.
        
        Args:
            data: The data to encode in the token
            expires_delta: Optional expiration timedelta
            
        Returns:
            The encoded JWT token
        """
        to_encode = data.copy()
        
        # Set expiration time
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire})
        
        # Encode the JWT token
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.JWT_ALGORITHM
        )
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[str]:
        """Verify a JWT access token.
        
        Args:
            token: The JWT token to verify
            
        Returns:
            The user ID extracted from the token if valid, None otherwise
        """
        try:
            # Decode the JWT token
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Extract the user ID
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
                
            return user_id
        except JWTError:
            return None
    
    async def authenticate_user(self, email: str, password: str) -> Optional[UserInfo]:
        """Authenticate a user.
        
        Args:
            email: The user's email
            password: The user's password
            
        Returns:
            The user if authentication succeeds, None otherwise
        """
        user_db = await self.repository.get_by_email(email)
        
        if not user_db:
            return None
            
        if not self.verify_password(password, user_db.hashed_password):
            return None
            
        if not user_db.is_active:
            return None
            
        return UserInfo(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            is_active=user_db.is_active,
            created_at=user_db.created_at,
            updated_at=user_db.updated_at,
            metadata=user_db.metadata
        )
    
    async def create_user(self, user_in: UserCreate) -> UserInfo:
        """Create a new user.
        
        Args:
            user_in: The user creation model
            
        Returns:
            The created user
        """
        # Check if user with this email already exists
        existing_user = await self.repository.get_by_email(user_in.email)
        if existing_user:
            raise ValueError(f"User with email {user_in.email} already exists")
        
        # Hash the password
        hashed_password = self.get_password_hash(user_in.password)
        
        # Create user dict for the repository
        user_data = user_in.model_dump()
        user_data.pop("password")  # Remove plain text password
        user_data["hashed_password"] = hashed_password
        
        # Create user model for repository
        create_data = UserCreate(**user_data)
        
        # Create the user in the database
        user_db = await self.repository.create(obj_in=create_data)
        await self.commit()
        
        # Return user info
        return UserInfo(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            is_active=user_db.is_active,
            created_at=user_db.created_at,
            updated_at=user_db.updated_at,
            metadata=user_db.metadata
        )
    
    async def update_user(self, user_id: UUID, user_in: UserUpdate) -> UserInfo:
        """Update a user.
        
        Args:
            user_id: The user ID
            user_in: The user update model
            
        Returns:
            The updated user
        """
        user_db = await self.repository.get_or_404(user_id)
        
        # If we're updating the email, check it doesn't already exist
        if user_in.email and user_in.email != user_db.email:
            existing_user = await self.repository.get_by_email(user_in.email)
            if existing_user:
                raise ValueError(f"User with email {user_in.email} already exists")
        
        # Update the user
        user_db = await self.repository.update(db_obj=user_db, obj_in=user_in)
        await self.commit()
        
        # Return user info
        return UserInfo(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            is_active=user_db.is_active,
            created_at=user_db.created_at,
            updated_at=user_db.updated_at,
            metadata=user_db.metadata
        )
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserInfo]:
        """Get a user by ID string.
        
        Args:
            user_id: The user ID string
            
        Returns:
            The user if found, None otherwise
        """
        try:
            uuid_id = UUID(user_id)
            return await self.get_user(uuid_id)
        except (ValueError, ResourceNotFoundError):
            return None
    
    async def get_user(self, user_id: UUID) -> UserInfo:
        """Get a user by ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            The user
            
        Raises:
            ResourceNotFoundError: If the user is not found
        """
        user_db = await self.repository.get_or_404(user_id)
        
        return UserInfo(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            is_active=user_db.is_active,
            created_at=user_db.created_at,
            updated_at=user_db.updated_at,
            metadata=user_db.metadata
        )
    
    async def get_user_with_workspaces(self, user_id: UUID) -> UserWithWorkspaces:
        """Get a user with their workspace access.
        
        Args:
            user_id: The user ID
            
        Returns:
            The user with workspace access
            
        Raises:
            ResourceNotFoundError: If the user is not found
        """
        user_db = await self.repository.get_or_404(user_id)
        workspace_access_list = await self.repository.get_user_workspaces(user_id)
        
        # Create the user with workspaces model
        workspace_access = [
            WorkspaceAccess(workspace_id=access.workspace_id, role=access.role)
            for access in workspace_access_list
        ]
        
        return UserWithWorkspaces(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            is_active=user_db.is_active,
            created_at=user_db.created_at,
            updated_at=user_db.updated_at,
            metadata=user_db.metadata,
            workspaces=workspace_access
        )
    
    async def deactivate_user(self, user_id: UUID) -> UserInfo:
        """Deactivate a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            The deactivated user
        """
        user_db = await self.repository.get_or_404(user_id)
        user_update = UserUpdate(is_active=False)
        
        user_db = await self.repository.update(db_obj=user_db, obj_in=user_update)
        await self.commit()
        
        return UserInfo(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            is_active=user_db.is_active,
            created_at=user_db.created_at,
            updated_at=user_db.updated_at,
            metadata=user_db.metadata
        )