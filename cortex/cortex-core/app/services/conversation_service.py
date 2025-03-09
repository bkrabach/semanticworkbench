"""
Conversation service implementation for Cortex Core.

This module provides a service layer for conversation functionality, following the
domain-driven repository architecture pattern.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException

from app.database.connection import get_db
from app.database.repositories.conversation_repository import ConversationRepository, get_conversation_repository
from app.models.domain.conversation import Conversation, Message
from app.models.domain.user import UserInfo
from app.services.base import Service
from app.utils.logger import logger
from app.components.event_system import get_event_system


class ConversationService(Service):
    """
    Conversation service.

    Provides a unified interface to all conversation operations including
    creation, retrieval, message handling, and updates.
    
    This service implements the domain-driven repository pattern by:
    1. Using domain models for all business logic
    2. Isolating data access in repositories
    3. Handling business logic and validation
    4. Managing events related to conversations
    """

    def __init__(self, db_session: Session, repository: ConversationRepository):
        """
        Initialize the conversation service.

        Args:
            db_session: SQLAlchemy database session
            repository: Conversation repository
        """
        super().__init__(db_session, repository)
        self.repository = repository
        self.event_system = get_event_system()

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get a conversation by ID.

        Args:
            conversation_id: ID of the conversation to retrieve

        Returns:
            Conversation domain model or None if not found
        """
        # Explicit return type to address mypy no-any-return error
        result: Optional[Conversation] = self.repository.get_by_id(conversation_id)
        
        if result:
            # You might perform additional processing here, such as:
            # - Filtering messages based on user permissions
            # - Enriching the conversation with additional data
            # - Logging access for analytics
            pass
            
        return result

    async def get_workspace_conversations(self, workspace_id: str) -> List[Conversation]:
        """
        Get all conversations for a workspace.

        Args:
            workspace_id: ID of the workspace

        Returns:
            List of Conversation domain models
        """
        # Explicit return type to address mypy no-any-return error
        result: List[Conversation] = self.repository.get_by_workspace(workspace_id)
        return result

    async def create_conversation(
        self, 
        workspace_id: str, 
        title: str, 
        modality: str, 
        user_info: UserInfo,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            workspace_id: ID of the workspace for the conversation
            title: Conversation title
            modality: Conversation modality (e.g., "text", "voice")
            user_info: Information about the user creating the conversation
            metadata: Optional metadata dictionary

        Returns:
            The created Conversation domain model
        """
        # Add creation metadata
        if metadata is None:
            metadata = {}
            
        # Track the creator in the metadata
        metadata["created_by"] = user_info.id
        
        # Create the conversation
        conversation: Conversation = self.repository.create(
            workspace_id=workspace_id,
            title=title,
            modality=modality,
            metadata=metadata
        )
        
        # Publish event for the new conversation
        await self.event_system.publish(
            event_type="conversation.created",
            data={
                "conversation_id": conversation.id,
                "workspace_id": conversation.workspace_id,
                "title": conversation.title,
                "modality": conversation.modality
            },
            source="conversation_service"
        )
        
        return conversation

    async def add_message(
        self, 
        conversation_id: str, 
        content: str, 
        role: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """
        Add a message to a conversation.

        Args:
            conversation_id: ID of the conversation
            content: Message content
            role: Role of the message sender (e.g., "user", "assistant")
            metadata: Optional message metadata

        Returns:
            The created Message domain model or None if conversation not found
        """
        # Add the message
        message: Optional[Message] = self.repository.add_message(
            conversation_id=conversation_id,
            content=content,
            role=role,
            metadata=metadata
        )
        
        if not message:
            return None
            
        # Get the conversation for event publishing
        conversation = self.repository.get_by_id(conversation_id)
        
        # Publish event for the new message
        await self.event_system.publish(
            event_type="conversation.message_added",
            data={
                "conversation_id": conversation_id,
                "workspace_id": conversation.workspace_id if conversation else None,
                "message_id": message.id,
                "role": message.role
            },
            source="conversation_service"
        )
        
        return message

    async def update_title(self, conversation_id: str, title: str) -> Optional[Conversation]:
        """
        Update a conversation's title.

        Args:
            conversation_id: ID of the conversation
            title: New title

        Returns:
            Updated Conversation domain model or None if not found
        """
        conversation: Optional[Conversation] = self.repository.update_title(conversation_id, title)
        
        if conversation:
            # Publish event for title update
            await self.event_system.publish(
                event_type="conversation.updated",
                data={
                    "conversation_id": conversation.id,
                    "workspace_id": conversation.workspace_id,
                    "title": conversation.title,
                    "updated_field": "title"
                },
                source="conversation_service"
            )
            
        return conversation

    async def update_metadata(self, conversation_id: str, metadata: Dict[str, Any]) -> Optional[Conversation]:
        """
        Update a conversation's metadata.

        Args:
            conversation_id: ID of the conversation
            metadata: New metadata dictionary

        Returns:
            Updated Conversation domain model or None if not found
        """
        conversation: Optional[Conversation] = self.repository.update_metadata(conversation_id, metadata)
        
        if conversation:
            # Publish event for metadata update
            await self.event_system.publish(
                event_type="conversation.updated",
                data={
                    "conversation_id": conversation.id,
                    "workspace_id": conversation.workspace_id,
                    "updated_field": "metadata"
                },
                source="conversation_service"
            )
            
        return conversation

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: ID of the conversation to delete

        Returns:
            Boolean indicating success
        """
        # Get the conversation first for event data
        conversation = self.repository.get_by_id(conversation_id)
        
        if not conversation:
            return False
            
        # Delete the conversation
        success: bool = self.repository.delete(conversation_id)
        
        if success:
            # Publish event for deletion
            await self.event_system.publish(
                event_type="conversation.deleted",
                data={
                    "conversation_id": conversation_id,
                    "workspace_id": conversation.workspace_id
                },
                source="conversation_service"
            )
            
        return success


# Factory function for dependency injection
def get_conversation_service(
    db: Session = Depends(get_db)
) -> ConversationService:
    """
    Get a conversation service instance.

    Args:
        db: SQLAlchemy database session

    Returns:
        ConversationService instance
    """
    # If a test is providing a mock, return it directly
    if hasattr(get_conversation_service, "override") and getattr(get_conversation_service, "override") is not None:
        # Explicit typing to help mypy
        result: ConversationService = getattr(get_conversation_service, "override")
        return result

    # Create repository inside function to avoid FastAPI dependency issues
    repository = get_conversation_repository(db)
    
    # Explicit return type to help mypy
    service: ConversationService = ConversationService(db, repository)
    return service


# Set up the override attribute for testing
# We need to use setattr because mypy can't infer the attribute on a function
setattr(get_conversation_service, "override", None)