"""User repository for accessing user data."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import uuid
import json
from app.utils.json_helpers import parse_datetime

from sqlalchemy.orm import Session

from app.database.models import User as UserDB, ApiKey as ApiKeyDB
from app.models.domain.user import User, UserInfo, ApiKey
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
        
        # No longer needed as meta_data is not a field in User model
        # metadata_json = json.dumps(metadata) if metadata else "{}"
        
        user_db = UserDB(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            password_hash=password_hash,
            created_at_utc=now,
            updated_at_utc=now,
            # meta_data field doesn't exist in the User DB model
            # Removed meta_data parameter
            last_login_at_utc=None,
            # Don't set roles parameter - it's a relationship that defaults to an empty list
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
        # No meta_data field in UserDB model, so use an empty dict
        metadata: Dict[str, Any] = {}
            
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
        # No longer needed as meta_data is not a field in User model
        # metadata_json = json.dumps(domain_model.metadata) if domain_model.metadata else "{}"
        # roles is a relationship, not a string column
        # roles_json = json.dumps(domain_model.roles) if domain_model.roles else "[]"
        
        db_instance = UserDB(
            id=domain_model.id,
            email=domain_model.email,
            name=domain_model.name,
            password_hash=domain_model.password_hash,
            created_at_utc=domain_model.created_at,
            updated_at_utc=domain_model.updated_at or datetime.now(timezone.utc),
            last_login_at_utc=domain_model.last_login_at
            # meta_data field doesn't exist in the User DB model
            # roles field is a relationship, not a column - don't set directly
        )
        
        # Roles needs to be handled through the relationship
        # We would need to query Role objects and add them to the relationship
        # This could be implemented in a separate method if needed
        
        return db_instance
    
    def create_api_key(self, user_id: str, encrypted_key: str, scopes: List[str], 
                       expires_at: Optional[datetime] = None) -> ApiKey:
        """Create a new API key for a user."""
        # Convert scopes to JSON
        scopes_json = json.dumps(scopes)
        
        # Create a new API key
        api_key_db = ApiKeyDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            key=encrypted_key,
            scopes_json=scopes_json,
            created_at_utc=datetime.now(timezone.utc),
            expires_at_utc=expires_at
        )
        
        self.db.add(api_key_db)
        self.db.commit()
        self.db.refresh(api_key_db)
        
        return self._api_key_to_domain(api_key_db)
    
    def _api_key_to_domain(self, db_model: ApiKeyDB) -> ApiKey:
        """Convert API key database model to domain model."""
        # Parse scopes from JSON
        try:
            # Convert SQLAlchemy Column to string first
            scopes_json_str = str(db_model.scopes_json) if db_model.scopes_json is not None else "[]"
            scopes = json.loads(scopes_json_str)
        except (json.JSONDecodeError, TypeError):
            scopes = []
        
        # Extract the values from SQLAlchemy Column objects
        created_at = parse_datetime(db_model.created_at_utc) if db_model.created_at_utc is not None else datetime.now(timezone.utc)
        expires_at = parse_datetime(db_model.expires_at_utc) if db_model.expires_at_utc is not None else None
        
        return ApiKey(
            id=str(db_model.id),
            user_id=str(db_model.user_id),
            key=str(db_model.key),  # Already encrypted
            created_at=created_at,
            scopes=scopes,
            expires_at=expires_at
        )

# Factory function for dependency injection
def get_user_repository(db_session: Session) -> UserRepository:
    """Get a user repository instance"""
    return UserRepository(db_session)