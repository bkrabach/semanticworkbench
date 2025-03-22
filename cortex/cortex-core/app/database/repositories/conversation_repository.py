import json
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ...models.domain import Conversation
from ..models import Conversation as DbConversation

class ConversationRepository(BaseRepository[Conversation, DbConversation]):
    """Repository for conversation operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize conversation repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, Conversation, DbConversation)

    async def list_by_workspace(self, workspace_id: str,
                              limit: int = 100, offset: int = 0) -> List[Conversation]:
        """
        List conversations in a specific workspace.

        Args:
            workspace_id: Workspace ID
            limit: Maximum number of conversations to return
            offset: Pagination offset

        Returns:
            List of conversations
        """
        try:
            result = await self.session.execute(
                select(DbConversation)
                .where(DbConversation.workspace_id == workspace_id)
                .limit(limit)
                .offset(offset)
            )
            db_conversations = result.scalars().all()
            # Filter out None values to satisfy type checker
            conversations = [conv for conv in [self._to_domain(db) for db in db_conversations] if conv is not None]
            return conversations
        except Exception as e:
            self._handle_db_error(e, f"Error listing conversations for workspace {workspace_id}")
            return []  # Return empty list on error

    async def count_by_workspace(self, workspace_id: str) -> int:
        """
        Count conversations in a specific workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            Count of conversations
        """
        try:
            result = await self.session.execute(
                select(func.count())
                .select_from(DbConversation)
                .where(DbConversation.workspace_id == workspace_id)
            )
            return result.scalar() or 0
        except Exception as e:
            self._handle_db_error(e, f"Error counting conversations for workspace {workspace_id}")
            return 0  # Return 0 count on error

    def _to_domain(self, db_entity: Optional[DbConversation]) -> Optional[Conversation]:
        """
        Convert database conversation to domain conversation.

        Args:
            db_entity: Database conversation

        Returns:
            Domain conversation
        """
        if not db_entity:
            return None

        # Parse metadata JSON
        metadata = {}
        # Use getattr to avoid SQLAlchemy Column type issues
        metadata_json = getattr(db_entity, 'metadata_json', None)
        if metadata_json is not None:
            try:
                metadata_str = str(metadata_json)
                metadata = json.loads(metadata_str)
            except (json.JSONDecodeError, TypeError):
                pass

        # Parse participant IDs JSON
        participant_ids = []
        # Use getattr to avoid SQLAlchemy Column type issues
        participant_ids_json = getattr(db_entity, 'participant_ids_json', None)
        if participant_ids_json is not None:
            try:
                participant_ids_str = str(participant_ids_json)
                participant_ids = json.loads(participant_ids_str)
            except (json.JSONDecodeError, TypeError):
                pass

        return Conversation(
            id=str(getattr(db_entity, 'id')),
            workspace_id=str(getattr(db_entity, 'workspace_id')),
            topic=str(getattr(db_entity, 'topic')),
            participant_ids=participant_ids,
            metadata=metadata
        )

    def _to_db(self, entity: Conversation) -> DbConversation:
        """
        Convert domain conversation to database conversation.

        Args:
            entity: Domain conversation

        Returns:
            Database conversation
        """
        metadata_json = "{}"
        if entity.metadata:
            metadata_json = json.dumps(entity.metadata)

        participant_ids_json = "[]"
        if entity.participant_ids:
            participant_ids_json = json.dumps(entity.participant_ids)

        return DbConversation(
            id=entity.id,
            workspace_id=entity.workspace_id,
            topic=entity.topic,
            participant_ids_json=participant_ids_json,
            metadata_json=metadata_json
        )

    def _update_db_entity(self, db_entity: DbConversation,
                         entity: Conversation) -> DbConversation:
        """
        Update database conversation from domain conversation.

        Args:
            db_entity: Database conversation to update
            entity: Domain conversation with new values

        Returns:
            Updated database conversation
        """
        # Use setattr to avoid SQLAlchemy Column type issues
        setattr(db_entity, 'workspace_id', entity.workspace_id)
        setattr(db_entity, 'topic', entity.topic)

        # Update participant IDs
        if entity.participant_ids:
            setattr(db_entity, 'participant_ids_json', json.dumps(entity.participant_ids))
        else:
            setattr(db_entity, 'participant_ids_json', "[]")

        # Update metadata
        if entity.metadata:
            setattr(db_entity, 'metadata_json', json.dumps(entity.metadata))
        else:
            setattr(db_entity, 'metadata_json', "{}")

        return db_entity