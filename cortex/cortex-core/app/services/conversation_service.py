"""Conversation service for business logic."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories import ConversationRepository, WorkspaceRepository
from app.models.domain.conversation import (
    ConversationCreate, ConversationInfo, ConversationUpdate,
    MessageCreate, MessageInfo
)
from app.services.base import BaseService
from app.exceptions import ResourceNotFoundError, PermissionDeniedError


class ConversationService(BaseService[ConversationRepository, ConversationInfo]):
    """Service for conversation operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the service.
        
        Args:
            db: The database session
        """
        self.workspace_repository = WorkspaceRepository(db)
        repository = ConversationRepository(db)
        super().__init__(repository, db)
    
    async def create_conversation(
        self, conversation_in: ConversationCreate, user_id: UUID
    ) -> ConversationInfo:
        """Create a new conversation.
        
        Args:
            conversation_in: The conversation creation model
            user_id: The user ID creating the conversation
            
        Returns:
            The created conversation
            
        Raises:
            PermissionDeniedError: If the user doesn't have access to the workspace
            ResourceNotFoundError: If the workspace doesn't exist
        """
        # Check if the user has access to the workspace
        workspace_id = conversation_in.workspace_id
        has_access = await self.workspace_repository.has_access(
            user_id, workspace_id, required_role="viewer"
        )
        
        if not has_access:
            raise PermissionDeniedError("You don't have access to this workspace")
        
        # Create the conversation
        conversation_db = await self.repository.create(obj_in=conversation_in)
        await self.commit()
        
        return ConversationInfo(
            id=conversation_db.id,
            workspace_id=conversation_db.workspace_id,
            title=conversation_db.title,
            modality=conversation_db.modality,
            created_at=conversation_db.created_at,
            updated_at=conversation_db.updated_at,
            last_active_at=conversation_db.last_active_at,
            metadata=conversation_db.metadata
        )
    
    async def get_conversation(
        self, conversation_id: UUID, user_id: UUID
    ) -> ConversationInfo:
        """Get a conversation.
        
        Args:
            conversation_id: The conversation ID
            user_id: The user ID accessing the conversation
            
        Returns:
            The conversation
            
        Raises:
            ResourceNotFoundError: If the conversation is not found
            PermissionDeniedError: If the user doesn't have access
        """
        # Get the conversation
        conversation_db = await self.repository.get_or_404(conversation_id)
        
        # Check if the user has access to the workspace
        has_access = await self.workspace_repository.has_access(
            user_id, conversation_db.workspace_id, required_role="viewer"
        )
        
        if not has_access:
            raise PermissionDeniedError("You don't have access to this conversation")
        
        return ConversationInfo(
            id=conversation_db.id,
            workspace_id=conversation_db.workspace_id,
            title=conversation_db.title,
            modality=conversation_db.modality,
            created_at=conversation_db.created_at,
            updated_at=conversation_db.updated_at,
            last_active_at=conversation_db.last_active_at,
            metadata=conversation_db.metadata
        )
    
    async def get_workspace_conversations(
        self, workspace_id: UUID, user_id: UUID, *, skip: int = 0, limit: int = 100
    ) -> List[ConversationInfo]:
        """Get conversations in a workspace.
        
        Args:
            workspace_id: The workspace ID
            user_id: The user ID accessing the conversations
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of conversations
            
        Raises:
            PermissionDeniedError: If the user doesn't have access to the workspace
        """
        # Check if the user has access to the workspace
        has_access = await self.workspace_repository.has_access(
            user_id, workspace_id, required_role="viewer"
        )
        
        if not has_access:
            raise PermissionDeniedError("You don't have access to this workspace")
        
        # Get the conversations
        conversations = await self.repository.get_by_workspace(
            workspace_id, skip=skip, limit=limit
        )
        
        return [
            ConversationInfo(
                id=conv.id,
                workspace_id=conv.workspace_id,
                title=conv.title,
                modality=conv.modality,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                last_active_at=conv.last_active_at,
                metadata=conv.metadata
            )
            for conv in conversations
        ]
    
    async def update_conversation(
        self, conversation_id: UUID, conversation_in: ConversationUpdate, user_id: UUID
    ) -> ConversationInfo:
        """Update a conversation.
        
        Args:
            conversation_id: The conversation ID
            conversation_in: The conversation update model
            user_id: The user ID performing the update
            
        Returns:
            The updated conversation
            
        Raises:
            ResourceNotFoundError: If the conversation is not found
            PermissionDeniedError: If the user doesn't have access
        """
        # Get the conversation
        conversation_db = await self.repository.get_or_404(conversation_id)
        
        # Check if the user has access to the workspace
        has_access = await self.workspace_repository.has_access(
            user_id, conversation_db.workspace_id, required_role="editor"
        )
        
        if not has_access:
            raise PermissionDeniedError("You don't have permission to update this conversation")
        
        # Update the conversation
        conversation_db = await self.repository.update(
            db_obj=conversation_db, obj_in=conversation_in
        )
        await self.commit()
        
        return ConversationInfo(
            id=conversation_db.id,
            workspace_id=conversation_db.workspace_id,
            title=conversation_db.title,
            modality=conversation_db.modality,
            created_at=conversation_db.created_at,
            updated_at=conversation_db.updated_at,
            last_active_at=conversation_db.last_active_at,
            metadata=conversation_db.metadata
        )
    
    async def delete_conversation(self, conversation_id: UUID, user_id: UUID) -> bool:
        """Delete a conversation.
        
        Args:
            conversation_id: The conversation ID
            user_id: The user ID performing the deletion
            
        Returns:
            True if the conversation was deleted, False otherwise
            
        Raises:
            ResourceNotFoundError: If the conversation is not found
            PermissionDeniedError: If the user doesn't have access
        """
        # Get the conversation
        conversation_db = await self.repository.get_or_404(conversation_id)
        
        # Check if the user has access to the workspace
        has_access = await self.workspace_repository.has_access(
            user_id, conversation_db.workspace_id, required_role="editor"
        )
        
        if not has_access:
            raise PermissionDeniedError("You don't have permission to delete this conversation")
        
        # Delete the conversation
        result = await self.repository.delete(id=conversation_id)
        
        if result:
            await self.commit()
            
        return result
    
    async def get_messages(
        self, conversation_id: UUID, user_id: UUID, *, skip: int = 0, limit: int = 100
    ) -> List[MessageInfo]:
        """Get messages in a conversation.
        
        Args:
            conversation_id: The conversation ID
            user_id: The user ID accessing the messages
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of messages
            
        Raises:
            ResourceNotFoundError: If the conversation is not found
            PermissionDeniedError: If the user doesn't have access
        """
        # Get the conversation
        conversation_db = await self.repository.get_or_404(conversation_id)
        
        # Check if the user has access to the workspace
        has_access = await self.workspace_repository.has_access(
            user_id, conversation_db.workspace_id, required_role="viewer"
        )
        
        if not has_access:
            raise PermissionDeniedError("You don't have access to this conversation")
        
        # Get the messages
        messages = await self.repository.get_messages(
            conversation_id, skip=skip, limit=limit
        )
        
        return [
            MessageInfo(
                id=msg.id,
                conversation_id=msg.conversation_id,
                user_id=msg.user_id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                metadata=msg.metadata
            )
            for msg in messages
        ]
    
    async def add_message(
        self, conversation_id: UUID, message_in: MessageCreate, user_id: UUID
    ) -> MessageInfo:
        """Add a message to a conversation.
        
        Args:
            conversation_id: The conversation ID
            message_in: The message creation model
            user_id: The user ID adding the message
            
        Returns:
            The created message
            
        Raises:
            ResourceNotFoundError: If the conversation is not found
            PermissionDeniedError: If the user doesn't have access
        """
        # Get the conversation
        conversation_db = await self.repository.get_or_404(conversation_id)
        
        # Check if the user has access to the workspace
        has_access = await self.workspace_repository.has_access(
            user_id, conversation_db.workspace_id, required_role="viewer"
        )
        
        if not has_access:
            raise PermissionDeniedError("You don't have access to this conversation")
        
        # Add the message
        message_user_id = user_id if message_in.role == "user" else None
        message_db = await self.repository.add_message(
            conversation_id=conversation_id,
            role=message_in.role,
            content=message_in.content,
            user_id=message_user_id
        )
        await self.commit()
        
        return MessageInfo(
            id=message_db.id,
            conversation_id=message_db.conversation_id,
            user_id=message_db.user_id,
            role=message_db.role,
            content=message_db.content,
            created_at=message_db.created_at,
            metadata=message_db.metadata
        )