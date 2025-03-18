"""User service for handling user-related business logic."""

from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session

from app.database.repositories.user_repository import UserRepository
from app.models.domain.user import User, UserInfo, ApiKey
from app.services.base import Service
from app.components.event_system import EventSystem

class UserService(Service[User, UserRepository]):
    """Service for user-related operations"""
    
    def __init__(self, db_session: Session, repository: UserRepository, event_system: Optional[EventSystem] = None):
        self.db = db_session
        self.repository = repository
        self.event_system = event_system
        
    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        return self.repository.get_by_id(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        return self.repository.get_by_email(email)
    
    def get_user_info(self, user_id: str) -> Optional[UserInfo]:
        """Get limited user information by ID"""
        return self.repository.get_user_info(user_id)
        
    async def create_user(self, email: str, name: str, password_hash: str) -> User:
        """Create a new user"""
        # Business logic - pre-creation validations can go here
        
        # Call repository to create user
        user = self.repository.create(
            email=email,
            name=name,
            password_hash=password_hash
        )
        
        # Post-creation logic (e.g., publish events)
        if self.event_system:
            await self._publish_user_created_event(user)
            
        return user
        
    async def update_last_login(self, user_id: str) -> Optional[User]:
        """Update user's last login timestamp"""
        # Update user
        user = self.repository.update_last_login(user_id)
        
        # Publish event
        if user and self.event_system:
            await self._publish_user_login_event(user)
            
        return user
    
    async def _publish_user_created_event(self, user: User) -> None:
        """Publish user created event"""
        if not self.event_system:
            return
            
        await self.event_system.publish(
            event_type="user.created",
            data={
                "user_id": user.id,
                "email": user.email,
                "name": user.name
            },
            source="user_service"
        )
        
    async def _publish_user_login_event(self, user: User) -> None:
        """Publish user login event"""
        if not self.event_system:
            return
            
        await self.event_system.publish(
            event_type="user.login",
            data={
                "user_id": user.id,
                "email": user.email,
                "login_at": user.last_login_at.isoformat() if user.last_login_at else None
            },
            source="user_service"
        )
        
    def create_api_key(self, user_id: str, encrypted_key: str, scopes: List[str], 
                      expires_at: Optional[datetime] = None) -> ApiKey:
        """Create a new API key for a user."""
        # Use repository to create the key
        return self.repository.create_api_key(
            user_id=user_id,
            encrypted_key=encrypted_key,
            scopes=scopes,
            expires_at=expires_at
        )

# Factory function for dependency injection
def get_user_service(
    db: Session,
    repository: UserRepository,
    event_system: Optional[EventSystem] = None
) -> UserService:
    """Get a user service instance"""
    return UserService(db, repository, event_system)