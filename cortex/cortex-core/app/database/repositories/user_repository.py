"""User repository for accessing user data."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
import uuid
import json
from app.utils.json_helpers import parse_datetime

from sqlalchemy.orm import Session

from app.database.models import User as UserDB
from app.models.domain.user import User, UserInfo
from app.database.repositories.base import Repository

class UserRepository(Repository[User, UserDB]):
    """Repository for user data access"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        user_db = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user_db:
            return None
        return self._to_domain(user_db)
        
    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        user_db = self.db.query(UserDB).filter(UserDB.email == email).first()
        if not user_db:
            return None
        return self._to_domain(user_db)
    
    def get_user_info(self, user_id: str) -> Optional[UserInfo]:
        """Get limited user information by ID"""
        user_db = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user_db:
            return None
        return self._to_user_info(user_db)
        
    def create(self, email: str, name: str, password_hash: str) -> User:
        """Create a new user"""
        now = datetime.now(timezone.utc)
        
        # Extract metadata if provided
        metadata: Dict[str, Any] = {}
        
        # Convert metadata to JSON
        metadata_json = json.dumps(metadata) if metadata else "{}"
        
        user_db = UserDB(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            password_hash=password_hash,
            created_at_utc=now,
            updated_at_utc=now,
            meta_data=metadata_json,
            last_login_at_utc=None,
            roles="[]"  # Default empty array
        )
        
        self.db.add(user_db)
        self.db.commit()
        self.db.refresh(user_db)
        
        return self._to_domain(user_db)
        
    def update_last_login(self, user_id: str) -> Optional[User]:
        """Update user's last login timestamp"""
        user_db = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user_db:
            return None
            
        now = datetime.now(timezone.utc)
        # Convert from SQLAlchemy Column to plain python type
        setattr(user_db, 'last_login_at_utc', now)
        setattr(user_db, 'updated_at_utc', now)
        
        self.db.commit()
        self.db.refresh(user_db)
        
        return self._to_domain(user_db)
        
    def _to_domain(self, db_model: UserDB) -> User:
        """Convert DB model to domain model"""
        # Parse metadata
        try:
            metadata = json.loads(db_model.meta_data) if db_model.meta_data is not None else {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}
            
        # Parse roles
        try:
            roles = json.loads(db_model.roles) if db_model.roles is not None else []
        except (json.JSONDecodeError, TypeError):
            roles = []
        
        # Extract the values from SQLAlchemy Column objects
        # Use parse_datetime that handles various formats safely
        created_at = parse_datetime(db_model.created_at_utc) if db_model.created_at_utc is not None else datetime.now(timezone.utc)
        updated_at = parse_datetime(db_model.updated_at_utc) if db_model.updated_at_utc is not None else None
        last_login_at = parse_datetime(db_model.last_login_at_utc) if db_model.last_login_at_utc is not None else None
            
        return User(
            id=str(db_model.id),
            email=str(db_model.email),
            name=str(db_model.name) if db_model.name is not None else None,
            created_at=created_at,
            updated_at=updated_at,
            last_login_at=last_login_at,
            metadata=metadata,
            roles=roles,
            password_hash=str(db_model.password_hash)
        )
        
    def _to_user_info(self, db_model: UserDB) -> UserInfo:
        """Convert DB model to UserInfo domain model"""
        # Parse roles
        try:
            roles = json.loads(db_model.roles) if db_model.roles is not None else []
        except (json.JSONDecodeError, TypeError):
            roles = []
        
        # Extract the value from SQLAlchemy Column object and convert to Python type
        # Use parse_datetime that handles various formats safely
        created_at = parse_datetime(db_model.created_at_utc) if db_model.created_at_utc is not None else datetime.now(timezone.utc)
            
        return UserInfo(
            id=str(db_model.id),
            email=str(db_model.email),
            name=str(db_model.name) if db_model.name is not None else None,
            created_at=created_at,
            roles=roles
        )
        
    def _to_db_model(self, domain_model: User) -> UserDB:
        """Convert domain model to DB model"""
        # This is used for update operations
        metadata_json = json.dumps(domain_model.metadata) if domain_model.metadata else "{}"
        roles_json = json.dumps(domain_model.roles) if domain_model.roles else "[]"
        
        return UserDB(
            id=domain_model.id,
            email=domain_model.email,
            name=domain_model.name,
            password_hash=domain_model.password_hash,
            created_at_utc=domain_model.created_at,
            updated_at_utc=domain_model.updated_at or datetime.now(timezone.utc),
            last_login_at_utc=domain_model.last_login_at,
            meta_data=metadata_json,
            roles=roles_json
        )

# Factory function for dependency injection
def get_user_repository(db_session: Session) -> UserRepository:
    """Get a user repository instance"""
    return UserRepository(db_session)