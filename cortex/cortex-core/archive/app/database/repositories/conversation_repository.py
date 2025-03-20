"""Conversation repository for database operations."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Conversation, Message
from app.database.repositories.base import BaseRepository
from app.models.domain.conversation import ConversationCreate, ConversationUpdate


class ConversationRepository(BaseRepository[Conversation, ConversationCreate, ConversationUpdate]):
    """Repository for conversation operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the repository.
        
        Args:
            db: The database session
        """
        super().__init__(Conversation, db)
    
    async def get_by_workspace(self, workspace_id: UUID, *, skip: int = 0, limit: int = 100) -> List[Conversation]:
        """Get conversations by workspace ID.
        
        Args:
            workspace_id: The workspace ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of conversations
        """
        query = (
            select(Conversation)
            .where(Conversation.workspace_id == workspace_id)
            .order_by(desc(Conversation.last_active_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_messages(
        self, conversation_id: UUID, *, skip: int = 0, limit: int = 100
    ) -> List[Message]:
        """Get messages for a conversation.
        
        Args:
            conversation_id: The conversation ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of messages
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def add_message(
        self, 
        conversation_id: UUID, 
        role: str, 
        content: str, 
        user_id: Optional[UUID] = None
    ) -> Message:
        """Add a message to a conversation.
        
        Args:
            conversation_id: The conversation ID
            role: The message role (user, assistant, system)
            content: The message content
            user_id: Optional user ID for user messages
            
        Returns:
            The created message
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            user_id=user_id
        )
        self.db.add(message)
        
        # Update the conversation's last_active_at timestamp
        query = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(query)
        conversation = result.scalar_one()
        conversation.last_active_at = func.now()
        
        await self.db.flush()
        await self.db.refresh(message)
        return message