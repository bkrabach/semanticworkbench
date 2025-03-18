"""
Conversation repository implementation for Cortex Core.

This module provides a repository for accessing conversation data,
following the domain-driven repository architecture pattern.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
import uuid
from sqlalchemy.orm import Session

from app.database.models import Conversation as ConversationDB
from app.models.domain.conversation import Conversation, Message
from app.database.repositories.base import Repository
from app.utils.json_helpers import DateTimeEncoder, parse_datetime
from app.utils.logger import logger


class ConversationRepository(Repository):
    """
    Repository for conversation data access.
    
    This repository provides methods to access and manipulate conversation data,
    implementing the domain-driven repository pattern by:
    1. Converting between database models and domain models
    2. Encapsulating all data access logic
    3. Providing a clean interface for the service layer
    """
    
    def __init__(self, db_session: Session):
        """Initialize the repository with a database session."""
        self.db = db_session
        
    def _to_db_model(self, domain_model: Conversation) -> ConversationDB:
        """
        Convert domain model to database model.
        
        This method is required by the Repository interface but not used
        in this implementation yet. It will be fully implemented when
        needed for create/update operations.
        
        Args:
            domain_model: Domain model to convert
            
        Returns:
            Equivalent database model
        """
        # This is a stub implementation to satisfy the interface
        # It will be properly implemented when needed
        db_model = ConversationDB(
            id=domain_model.id,
            workspace_id=domain_model.workspace_id,
            title=domain_model.title,
            modality=domain_model.modality,
            created_at_utc=domain_model.created_at,
            last_active_at_utc=domain_model.last_active_at,
            meta_data=json.dumps(domain_model.metadata, cls=DateTimeEncoder),
            entries=json.dumps([{
                "id": msg.id,
                "content": msg.content,
                "role": msg.role,
                "created_at_utc": msg.created_at.isoformat(),
                "metadata": msg.metadata
            } for msg in domain_model.messages], cls=DateTimeEncoder)
        )
        return db_model
        
    def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get a conversation by ID.
        
        Args:
            conversation_id: The ID of the conversation to retrieve
            
        Returns:
            Conversation domain model or None if not found
        """
        db_model = self.db.query(ConversationDB).filter(
            ConversationDB.id == conversation_id
        ).first()
        
        if db_model is None:
            return None
            
        return self._to_domain(db_model)
    
    def get_by_workspace(self, workspace_id: str) -> List[Conversation]:
        """
        Get all conversations for a workspace.
        
        Args:
            workspace_id: The ID of the workspace
            
        Returns:
            List of Conversation domain models
        """
        db_models = self.db.query(ConversationDB).filter(
            ConversationDB.workspace_id == workspace_id
        ).all()
        
        return [self._to_domain(db_model) for db_model in db_models]
    
    def create(self, workspace_id: str, title: str, modality: str, metadata: Optional[Dict[str, Any]] = None) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            workspace_id: The ID of the workspace for the conversation
            title: The conversation title
            modality: The conversation modality (e.g., "text", "voice")
            metadata: Optional metadata dictionary
            
        Returns:
            The created Conversation domain model
        """
        now = datetime.now(timezone.utc)
        metadata_json = json.dumps(metadata or {}, cls=DateTimeEncoder)
        
        db_model = ConversationDB(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            title=title,
            modality=modality,
            created_at_utc=now,
            last_active_at_utc=now,
            entries="[]",
            meta_data=metadata_json
        )
        
        self.db.add(db_model)
        self.db.commit()
        self.db.refresh(db_model)
        
        return self._to_domain(db_model)
    
    def add_message(self, conversation_id: str, content: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Message]:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: The ID of the conversation
            content: The message content
            role: The role of the message sender (e.g., "user", "assistant")
            metadata: Optional message metadata
            
        Returns:
            The created Message domain model or None if conversation not found
        """
        db_model = self.db.query(ConversationDB).filter(
            ConversationDB.id == conversation_id
        ).first()
        
        if db_model is None:
            return None
        
        # Parse existing entries
        try:
            entries_str = str(db_model.entries) if db_model.entries is not None else "[]"
            entries = json.loads(entries_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error parsing conversation entries: {e}")
            entries = []
        
        # Create new message
        now = datetime.now(timezone.utc)
        message_id = str(uuid.uuid4())
        
        new_message = {
            "id": message_id,
            "content": content,
            "role": role,
            "created_at_utc": now.isoformat(),
            "metadata": metadata or {}
        }
        
        # Add message and update conversation
        entries.append(new_message)
        entries_json = json.dumps(entries, cls=DateTimeEncoder)
        
        # Update with appropriate SQLAlchemy ORM pattern
        setattr(db_model, 'entries', entries_json)
        setattr(db_model, 'last_active_at_utc', now)
        
        self.db.commit()
        
        # Return domain model
        return Message(
            id=message_id,
            content=content,
            role=role,
            created_at=now,
            metadata=metadata or {}
        )
    
    def update_title(self, conversation_id: str, title: str) -> Optional[Conversation]:
        """
        Update a conversation's title.
        
        Args:
            conversation_id: The ID of the conversation
            title: The new title
            
        Returns:
            Updated Conversation domain model or None if not found
        """
        db_model = self.db.query(ConversationDB).filter(
            ConversationDB.id == conversation_id
        ).first()
        
        if db_model is None:
            return None
        
        setattr(db_model, 'title', title)
        self.db.commit()
        
        return self._to_domain(db_model)
    
    def update_metadata(self, conversation_id: str, metadata: Dict[str, Any]) -> Optional[Conversation]:
        """
        Update a conversation's metadata.
        
        Args:
            conversation_id: The ID of the conversation
            metadata: The new metadata dictionary
            
        Returns:
            Updated Conversation domain model or None if not found
        """
        db_model = self.db.query(ConversationDB).filter(
            ConversationDB.id == conversation_id
        ).first()
        
        if db_model is None:
            return None
        
        metadata_json = json.dumps(metadata, cls=DateTimeEncoder)
        setattr(db_model, 'meta_data', metadata_json)
        self.db.commit()
        
        return self._to_domain(db_model)
    
    def delete(self, conversation_id: str) -> bool:
        """
        Delete a conversation.
        
        Args:
            conversation_id: The ID of the conversation to delete
            
        Returns:
            Boolean indicating success
        """
        db_model = self.db.query(ConversationDB).filter(
            ConversationDB.id == conversation_id
        ).first()
        
        if db_model is None:
            return False
        
        self.db.delete(db_model)
        self.db.commit()
        
        return True
    
    def _to_domain(self, db_model: ConversationDB) -> Conversation:
        """
        Convert database model to domain model.
        
        Args:
            db_model: SQLAlchemy Conversation model
            
        Returns:
            Conversation domain model
        """
        # Parse JSON fields
        try:
            meta_data_str = str(db_model.meta_data) if db_model.meta_data is not None else "{}"
            metadata = json.loads(meta_data_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error parsing conversation metadata: {e}")
            metadata = {}
            
        try:
            entries_str = str(db_model.entries) if db_model.entries is not None else "[]"
            entries = json.loads(entries_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error parsing conversation entries: {e}")
            entries = []
            
        # Convert entries to Message objects
        messages = []
        for entry in entries:
            try:
                created_at = parse_datetime(entry.get("created_at_utc"))
                
                message = Message(
                    id=entry.get("id"),
                    content=entry.get("content", ""),
                    role=entry.get("role", "user"),
                    created_at=created_at,
                    metadata=entry.get("metadata", {})
                )
                messages.append(message)
            except (KeyError, ValueError) as e:
                logger.error(f"Error parsing message: {e}")
                # Skip invalid messages
        
        # Create and return domain model
        # Use parse_datetime that handles mock objects and various formats safely
        created_at = parse_datetime(db_model.created_at_utc) if db_model.created_at_utc is not None else datetime.now(timezone.utc)
        last_active_at = parse_datetime(db_model.last_active_at_utc) if db_model.last_active_at_utc is not None else datetime.now(timezone.utc)
        
        updated_at = None
        if hasattr(db_model, "updated_at_utc") and db_model.updated_at_utc is not None:
            updated_at = parse_datetime(db_model.updated_at_utc)
        
        return Conversation(
            id=str(db_model.id),
            workspace_id=str(db_model.workspace_id),
            title=str(db_model.title),
            modality=str(db_model.modality),
            created_at=created_at,
            updated_at=updated_at,
            last_active_at=last_active_at,
            metadata=metadata,
            messages=messages
        )


# Factory function for dependency injection
def get_conversation_repository(db_session: Session) -> ConversationRepository:
    """
    Get a conversation repository instance.
    
    Args:
        db_session: SQLAlchemy database session
        
    Returns:
        ConversationRepository instance
    """
    return ConversationRepository(db_session)


# Set up the override attribute for testing
# We need to use setattr because mypy can't infer the attribute on a function
setattr(get_conversation_repository, "override", None)