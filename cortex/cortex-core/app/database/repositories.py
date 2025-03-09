"""
Repository pattern implementation for data access
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json
import uuid
from sqlalchemy.orm import Session

from app.database.models import Conversation, Workspace, WorkspaceSharing, User
from app.utils.json_helpers import DateTimeEncoder


class ConversationRepository(ABC):
    """Interface for conversation data access"""
    
    @abstractmethod
    def get_conversation_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        pass
        
    @abstractmethod
    def get_conversations_by_workspace(self, workspace_id: str, limit: int, offset: int) -> List[Conversation]:
        """Get conversations by workspace ID with pagination"""
        pass
        
    @abstractmethod
    def create_conversation(self, workspace_id: str, title: str, modality: str, metadata: Optional[Dict[str, Any]] = None) -> Conversation:
        """Create a new conversation"""
        pass
        
    @abstractmethod
    def update_conversation(self, conversation_id: str, title: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[Conversation]:
        """Update a conversation"""
        pass
        
    @abstractmethod
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        pass
        
    @abstractmethod
    def get_messages(self, conversation_id: str, limit: int, offset: int) -> List[Dict[str, Any]]:
        """Get messages from a conversation with pagination"""
        pass
        
    @abstractmethod
    def add_message(self, conversation_id: str, content: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Add a message to a conversation"""
        pass


class SQLAlchemyConversationRepository(ConversationRepository):
    """SQLAlchemy implementation of ConversationRepository"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def get_conversation_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        return self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        
    def get_conversations_by_workspace(self, workspace_id: str, limit: int, offset: int) -> List[Conversation]:
        """Get conversations by workspace ID with pagination"""
        return self.db.query(Conversation).filter(
            Conversation.workspace_id == workspace_id
        ).order_by(
            Conversation.last_active_at_utc.desc()
        ).offset(offset).limit(limit).all()
        
    def create_conversation(self, workspace_id: str, title: str, modality: str, metadata: Optional[Dict[str, Any]] = None) -> Conversation:
        """Create a new conversation"""
        now = datetime.now(timezone.utc)
        metadata_json = json.dumps(metadata or {})
        
        new_conversation = Conversation(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            title=title,
            modality=modality,
            created_at_utc=now,
            last_active_at_utc=now,
            entries="[]",
            meta_data=metadata_json
        )
        
        self.db.add(new_conversation)
        self.db.commit()
        self.db.refresh(new_conversation)
        
        # Update workspace last_active_at_utc
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if workspace:
            setattr(workspace, 'last_active_at_utc', now)
            self.db.commit()
            
        return new_conversation
        
    def update_conversation(self, conversation_id: str, title: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[Conversation]:
        """Update a conversation"""
        conversation = self.get_conversation_by_id(conversation_id)
        if not conversation:
            return None
            
        # Update conversation fields
        if title is not None:
            setattr(conversation, 'title', title)
            
        if metadata is not None:
            # Parse existing metadata
            try:
                existing_metadata = json.loads(str(getattr(conversation, 'meta_data')))
            except json.JSONDecodeError:
                existing_metadata = {}
                
            # Update with new metadata
            existing_metadata.update(metadata)
            setattr(conversation, 'meta_data', json.dumps(existing_metadata))
            
        # Update last_active_at_utc
        setattr(conversation, 'last_active_at_utc', datetime.now(timezone.utc))
        
        self.db.commit()
        self.db.refresh(conversation)
        
        return conversation
        
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        conversation = self.get_conversation_by_id(conversation_id)
        if not conversation:
            return False
            
        self.db.delete(conversation)
        self.db.commit()
        
        return True
        
    def get_messages(self, conversation_id: str, limit: int, offset: int) -> List[Dict[str, Any]]:
        """Get messages from a conversation with pagination"""
        conversation = self.get_conversation_by_id(conversation_id)
        if not conversation:
            return []
            
        try:
            entries = json.loads(str(getattr(conversation, 'entries')))
        except json.JSONDecodeError:
            return []
            
        # Apply pagination (reversing to get newest first, then reversing back)
        entries.reverse()
        paginated_entries = entries[offset:offset+limit]
        paginated_entries.reverse()  # Back to chronological order
        
        result: List[Dict[str, Any]] = paginated_entries
        return result
        
    def add_message(self, conversation_id: str, content: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Add a message to a conversation"""
        conversation = self.get_conversation_by_id(conversation_id)
        if not conversation:
            return None
            
        # Create new message with timezone-aware UTC datetime
        message_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Create message entry
        new_entry = {
            "id": message_id,
            "content": content,
            "role": role,
            "created_at_utc": now,
            "metadata": metadata or {}
        }
        
        # Parse and update entries
        try:
            entries = json.loads(str(getattr(conversation, 'entries')))
        except json.JSONDecodeError:
            entries = []
            
        entries.append(new_entry)
        
        # Update conversation - use custom encoder for datetime objects
        setattr(conversation, 'entries', json.dumps(entries, cls=DateTimeEncoder))
        setattr(conversation, 'last_active_at_utc', now)
        
        self.db.commit()
        
        # Return a serializable version of the entry
        serializable_entry = new_entry.copy()
        serializable_entry["created_at_utc"] = now.isoformat()
        
        return serializable_entry
        
        
def get_conversation_repository(db_session: Session) -> ConversationRepository:
    """Get a conversation repository instance"""
    return SQLAlchemyConversationRepository(db_session)


class UserRepository(ABC):
    """Interface for user data access"""
    
    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        pass
        
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        pass
        
    @abstractmethod
    def create_user(self, email: str, name: str, password_hash: str) -> User:
        """Create a new user"""
        pass
        
    @abstractmethod
    def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp"""
        pass


class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of UserRepository"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
        
    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        return self.db.query(User).filter(User.email == email).first()
        
    def create_user(self, email: str, name: str, password_hash: str) -> User:
        """Create a new user"""
        now = datetime.now(timezone.utc)
        new_user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            password_hash=password_hash,
            created_at_utc=now,
            updated_at_utc=now
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user
        
    def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp"""
        user = self.get_by_id(user_id)
        if user:
            now = datetime.now(timezone.utc)
            setattr(user, 'last_login_at_utc', now)
            self.db.commit()


def get_user_repository(db_session: Session) -> UserRepository:
    """Factory function for UserRepository"""
    return SQLAlchemyUserRepository(db_session)


class WorkspaceRepository(ABC):
    """Interface for workspace data access"""
    
    @abstractmethod
    def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID"""
        pass
        
    @abstractmethod
    def get_user_workspaces(self, user_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Workspace]:
        """Get workspaces for a user with optional pagination"""
        pass
        
    @abstractmethod
    def create_workspace(self, user_id: str, name: str, config: Optional[Dict[str, Any]] = None) -> Workspace:
        """Create a new workspace"""
        pass
        
    @abstractmethod
    def update_workspace(self, workspace_id: str, name: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Optional[Workspace]:
        """Update a workspace"""
        pass
        
    @abstractmethod
    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace"""
        pass


class SQLAlchemyWorkspaceRepository(WorkspaceRepository):
    """SQLAlchemy implementation of WorkspaceRepository"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID"""
        return self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        
    def get_user_workspaces(self, user_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Workspace]:
        """Get workspaces for a user with optional pagination"""
        query = self.db.query(Workspace).filter(
            Workspace.user_id == user_id
        ).order_by(
            Workspace.last_active_at_utc.desc()
        ).offset(offset)
        
        if limit is not None:
            query = query.limit(limit)
            
        return query.all()
        
    def create_workspace(self, user_id: str, name: str, config: Optional[Dict[str, Any]] = None) -> Workspace:
        """Create a new workspace"""
        now = datetime.now(timezone.utc)
        config_json = json.dumps(config or {}, cls=DateTimeEncoder)
        
        new_workspace = Workspace(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            created_at_utc=now,
            last_active_at_utc=now,
            config=config_json,
            meta_data="{}"
        )
        
        self.db.add(new_workspace)
        self.db.commit()
        self.db.refresh(new_workspace)
        return new_workspace
        
    def update_workspace(self, workspace_id: str, name: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Optional[Workspace]:
        """Update a workspace"""
        workspace = self.get_by_id(workspace_id)
        
        if not workspace:
            return None
            
        if name:
            setattr(workspace, 'name', name)
            
        if config is not None:
            setattr(workspace, 'config', json.dumps(config, cls=DateTimeEncoder))
            
        workspace.updated_at_utc = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(workspace)
        return workspace
        
    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace"""
        workspace = self.get_by_id(workspace_id)
        
        if not workspace:
            return False
            
        self.db.delete(workspace)
        self.db.commit()
        return True


def get_workspace_repository(db_session: Session) -> WorkspaceRepository:
    """Factory function for WorkspaceRepository"""
    return SQLAlchemyWorkspaceRepository(db_session)


class ResourceAccessRepository(ABC):
    """Interface for resource access verification operations"""
    
    @abstractmethod
    def is_workspace_owner(self, workspace_id: str, user_id: str) -> bool:
        """Check if user is the owner of a workspace"""
        pass
        
    @abstractmethod
    def has_workspace_sharing_access(self, workspace_id: str, user_id: str) -> bool:
        """Check if workspace is shared with the user"""
        pass
        
    @abstractmethod
    def get_conversation_workspace_id(self, conversation_id: str) -> Optional[str]:
        """Get the workspace ID for a conversation"""
        pass


class SQLAlchemyResourceAccessRepository(ResourceAccessRepository):
    """SQLAlchemy implementation of ResourceAccessRepository"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def is_workspace_owner(self, workspace_id: str, user_id: str) -> bool:
        """Check if user is the owner of a workspace"""
        workspace = self.db.query(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.user_id == user_id
        ).first()
        return workspace is not None
        
    def has_workspace_sharing_access(self, workspace_id: str, user_id: str) -> bool:
        """Check if workspace is shared with the user"""
        sharing = self.db.query(WorkspaceSharing).filter(
            WorkspaceSharing.workspace_id == workspace_id,
            WorkspaceSharing.user_id == user_id
        ).first()
        return sharing is not None
        
    def get_conversation_workspace_id(self, conversation_id: str) -> Optional[str]:
        """Get the workspace ID for a conversation"""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conversation:
            return str(conversation.workspace_id)
        return None


def get_resource_access_repository(db_session: Session) -> ResourceAccessRepository:
    """Factory function for ResourceAccessRepository"""
    return SQLAlchemyResourceAccessRepository(db_session)