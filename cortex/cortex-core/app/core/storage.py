import logging
from typing import Dict, List, Any, Optional

from ..models import User, Workspace, Conversation, Message

logger = logging.getLogger(__name__)

class InMemoryStorage:
    """
    Simple in-memory storage for development use.
    """
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.workspaces: Dict[str, Dict[str, Any]] = {}
        self.conversations: Dict[str, Dict[str, Any]] = {}
        self.messages: Dict[str, Dict[str, Any]] = {}

    # User operations

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return self.users.get(user_id)

    def create_user(self, user: User) -> Dict[str, Any]:
        """Create a new user."""
        user_dict = user.model_dump()
        self.users[user.user_id] = user_dict
        return user_dict

    # Workspace operations

    def create_workspace(self, workspace: Workspace) -> Dict[str, Any]:
        """Create a new workspace."""
        workspace_dict = workspace.model_dump()
        self.workspaces[workspace.id] = workspace_dict
        return workspace_dict

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get workspace by ID."""
        return self.workspaces.get(workspace_id)

    def list_workspaces(self, owner_id: str) -> List[Dict[str, Any]]:
        """List workspaces by owner ID."""
        return [
            workspace for workspace in self.workspaces.values()
            if workspace["owner_id"] == owner_id
        ]

    # Conversation operations

    def create_conversation(self, conversation: Conversation) -> Dict[str, Any]:
        """Create a new conversation."""
        conversation_dict = conversation.model_dump()
        self.conversations[conversation.id] = conversation_dict
        return conversation_dict

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        return self.conversations.get(conversation_id)

    def list_conversations(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List conversations by workspace ID."""
        return [
            conversation for conversation in self.conversations.values()
            if conversation["workspace_id"] == workspace_id
        ]

    # Message operations

    def create_message(self, message: Message) -> Dict[str, Any]:
        """Create a new message."""
        message_dict = message.model_dump()
        self.messages[message.id] = message_dict
        return message_dict

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get message by ID."""
        return self.messages.get(message_id)

    def list_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """List messages by conversation ID."""
        return [
            message for message in self.messages.values()
            if message["conversation_id"] == conversation_id
        ]

# Singleton instance
storage = InMemoryStorage()