import json
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Message
from ..models import Message as DbMessage
from .base import BaseRepository


class MessageRepository(BaseRepository[Message, DbMessage]):
    """Repository for message operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize message repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, Message, DbMessage)

    async def list_by_conversation(self, conversation_id: str, limit: int = 100, offset: int = 0) -> List[Message]:
        """
        List messages in a specific conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return
            offset: Pagination offset

        Returns:
            List of messages
        """
        try:
            result = await self.session.execute(
                select(DbMessage)
                .where(DbMessage.conversation_id == conversation_id)
                .order_by(DbMessage.timestamp)
                .limit(limit)
                .offset(offset)
            )
            db_messages = result.scalars().all()
            # Filter out None values to satisfy type checker
            messages = [msg for msg in [self._to_domain(db) for db in db_messages] if msg is not None]
            return messages
        except Exception as e:
            self._handle_db_error(e, f"Error listing messages for conversation {conversation_id}")
            return []  # Return empty list on error

    async def count_by_conversation(self, conversation_id: str) -> int:
        """
        Count messages in a specific conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Count of messages
        """
        try:
            result = await self.session.execute(
                select(func.count()).select_from(DbMessage).where(DbMessage.conversation_id == conversation_id)
            )
            return result.scalar() or 0
        except Exception as e:
            self._handle_db_error(e, f"Error counting messages for conversation {conversation_id}")
            return 0  # Return 0 count on error
    
    async def list_by_sender(self, sender_id: str, limit: int = 100, offset: int = 0) -> List[Message]:
        """
        List messages from a specific sender.

        Args:
            sender_id: Sender ID
            limit: Maximum number of messages to return
            offset: Pagination offset

        Returns:
            List of messages
        """
        try:
            result = await self.session.execute(
                select(DbMessage)
                .where(DbMessage.sender_id == sender_id)
                .order_by(DbMessage.timestamp.desc())
                .limit(limit)
                .offset(offset)
            )
            db_messages = result.scalars().all()
            # Filter out None values to satisfy type checker
            messages = [msg for msg in [self._to_domain(db) for db in db_messages] if msg is not None]
            return messages
        except Exception as e:
            self._handle_db_error(e, f"Error listing messages for sender {sender_id}")
            return []  # Return empty list on error

    def _to_domain(self, db_entity: Optional[DbMessage]) -> Optional[Message]:
        """
        Convert database message to domain message.

        Args:
            db_entity: Database message

        Returns:
            Domain message
        """
        if not db_entity:
            return None

        # Parse metadata JSON
        metadata = {}
        # Use getattr to avoid SQLAlchemy Column type issues
        metadata_json = getattr(db_entity, "metadata_json", None)
        if metadata_json is not None:
            try:
                metadata_str = str(metadata_json)
                metadata = json.loads(metadata_str)
            except (json.JSONDecodeError, TypeError):
                pass

        return Message(
            id=str(getattr(db_entity, "id")),
            conversation_id=str(getattr(db_entity, "conversation_id")),
            sender_id=str(getattr(db_entity, "sender_id")),
            content=str(getattr(db_entity, "content")),
            timestamp=str(getattr(db_entity, "timestamp")),
            metadata=metadata,
        )

    def _to_db(self, entity: Message) -> DbMessage:
        """
        Convert domain message to database message.

        Args:
            entity: Domain message

        Returns:
            Database message
        """
        metadata_json = "{}"
        if entity.metadata:
            metadata_json = json.dumps(entity.metadata)

        return DbMessage(
            id=entity.id,
            conversation_id=entity.conversation_id,
            sender_id=entity.sender_id,
            content=entity.content,
            timestamp=entity.timestamp,
            metadata_json=metadata_json,
        )

    def _update_db_entity(self, db_entity: DbMessage, entity: Message) -> DbMessage:
        """
        Update database message from domain message.

        Args:
            db_entity: Database message to update
            entity: Domain message with new values

        Returns:
            Updated database message
        """
        # Use setattr to avoid SQLAlchemy Column type issues
        setattr(db_entity, "conversation_id", entity.conversation_id)
        setattr(db_entity, "sender_id", entity.sender_id)
        setattr(db_entity, "content", entity.content)
        setattr(db_entity, "timestamp", entity.timestamp)

        # Update metadata
        if entity.metadata:
            setattr(db_entity, "metadata_json", json.dumps(entity.metadata))
        else:
            setattr(db_entity, "metadata_json", "{}")

        return db_entity
