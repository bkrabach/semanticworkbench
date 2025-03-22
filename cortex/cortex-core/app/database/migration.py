import logging
from typing import Any, Dict

from ..core.storage import storage
from ..models import Conversation, Message, User, Workspace
from .unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


async def migrate_to_sqlite() -> Dict[str, Any]:
    """
    Migrate data from in-memory storage to SQLite database.

    This function should be called once during the transition from in-memory storage
    to SQLite persistence. It copies all data from the in-memory storage to the database.

    Returns:
        Dictionary with migration statistics
    """
    stats = {"users": 0, "workspaces": 0, "conversations": 0, "messages": 0, "errors": 0}

    try:
        async with UnitOfWork.for_transaction() as uow:
            # Migrate users
            for user_id, user_data in storage.users.items():
                try:
                    user = User(**user_data)
                    await uow.repositories.get_user_repository().create(user)
                    stats["users"] += 1
                except Exception as e:
                    logger.error(f"Error migrating user {user_id}: {str(e)}")
                    stats["errors"] += 1

            # Migrate workspaces
            for workspace_id, workspace_data in storage.workspaces.items():
                try:
                    workspace = Workspace(**workspace_data)
                    await uow.repositories.get_workspace_repository().create(workspace)
                    stats["workspaces"] += 1
                except Exception as e:
                    logger.error(f"Error migrating workspace {workspace_id}: {str(e)}")
                    stats["errors"] += 1

            # Migrate conversations
            for conversation_id, conversation_data in storage.conversations.items():
                try:
                    conversation = Conversation(**conversation_data)
                    await uow.repositories.get_conversation_repository().create(conversation)
                    stats["conversations"] += 1
                except Exception as e:
                    logger.error(f"Error migrating conversation {conversation_id}: {str(e)}")
                    stats["errors"] += 1

            # Migrate messages
            for message_id, message_data in storage.messages.items():
                try:
                    message = Message(**message_data)
                    await uow.repositories.get_message_repository().create(message)
                    stats["messages"] += 1
                except Exception as e:
                    logger.error(f"Error migrating message {message_id}: {str(e)}")
                    stats["errors"] += 1

            # Commit all changes
            await uow.commit()

            logger.info(f"Migration completed: {stats}")

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        stats["errors"] += 1

    return stats
