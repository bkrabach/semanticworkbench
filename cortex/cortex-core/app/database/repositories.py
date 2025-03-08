"""
Repository pattern implementation for data access
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json
import uuid
from sqlalchemy.orm import Session

from app.database.models import Conversation, Workspace
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
    def create_conversation(self, workspace_id: str, title: str, modality: str, metadata: Dict) -> Conversation:
        """Create a new conversation"""
        pass
        
    @abstractmethod
    def update_conversation(self, conversation_id: str, title: Optional[str] = None, metadata: Optional[Dict] = None) -> Conversation:
        """Update a conversation"""
        pass
        
    @abstractmethod
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        pass
        
    @abstractmethod
    def get_messages(self, conversation_id: str, limit: int, offset: int) -> List[Dict]:
        """Get messages from a conversation with pagination"""
        pass
        
    @abstractmethod
    def add_message(self, conversation_id: str, content: str, role: str, metadata: Optional[Dict] = None) -> Dict:
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
        
    def create_conversation(self, workspace_id: str, title: str, modality: str, metadata: Dict = None) -> Conversation:
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
        
    def update_conversation(self, conversation_id: str, title: Optional[str] = None, metadata: Optional[Dict] = None) -> Conversation:
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
        
    def get_messages(self, conversation_id: str, limit: int, offset: int) -> List[Dict]:
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
        
        return paginated_entries
        
    def add_message(self, conversation_id: str, content: str, role: str, metadata: Optional[Dict] = None) -> Dict:
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