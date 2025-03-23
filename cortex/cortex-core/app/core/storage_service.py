import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.exceptions import PermissionDeniedException, ResourceNotFoundException

# Set up logger
logger = logging.getLogger(__name__)


class StorageService:
    """
    Service class for managing in-memory storage of workspaces and conversations.
    In a production environment, this would be replaced with a database service.
    """

    def __init__(self):
        """Initialize empty storage containers."""
        self._workspaces: Dict[str, Dict[str, Any]] = {}
        self._conversations: Dict[str, Dict[str, Any]] = {}

    # Workspace operations
    def create_workspace(self, name: str, description: str, owner_id: str, 
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new workspace for a user.
        
        Args:
            name: The name of the workspace
            description: The description of the workspace
            owner_id: The ID of the user who owns the workspace
            metadata: Optional metadata for the workspace
            
        Returns:
            The created workspace as a dictionary
        """
        workspace_id = str(uuid.uuid4())
        
        # Create workspace record
        workspace = {
            "id": workspace_id,
            "name": name,
            "description": description or "",
            "metadata": metadata or {},
            "owner_id": owner_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        # Store in memory
        self._workspaces[workspace_id] = workspace
        logger.info(f"Created new workspace: {workspace_id} for user: {owner_id}")
        return workspace

    def get_workspaces_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all workspaces owned by a specific user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            A list of workspace dictionaries owned by the user
        """
        return [ws for ws in self._workspaces.values() if ws.get("owner_id") == user_id]

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific workspace by ID.
        
        Args:
            workspace_id: The ID of the workspace to retrieve
            
        Returns:
            The workspace dictionary or None if not found
        """
        return self._workspaces.get(workspace_id)

    def verify_workspace_access(self, workspace_id: str, user_id: str) -> Dict[str, Any]:
        """
        Verify that a user has access to a workspace and return the workspace.
        
        Args:
            workspace_id: The ID of the workspace to verify access to
            user_id: The ID of the user requesting access
            
        Returns:
            The workspace dictionary if access is allowed
            
        Raises:
            ResourceNotFoundException: If the workspace doesn't exist
            PermissionDeniedException: If the user doesn't own the workspace
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            logger.warning(f"Workspace not found: {workspace_id}")
            raise ResourceNotFoundException(resource_id=workspace_id, resource_type="workspace")
            
        if workspace.get("owner_id") != user_id:
            logger.warning(f"Permission denied for user: {user_id} accessing workspace: {workspace_id}")
            raise PermissionDeniedException(
                resource_id=workspace_id, 
                message="You don't have permission to access this workspace"
            )
            
        return workspace

    # Conversation operations
    def create_conversation(self, workspace_id: str, topic: str, owner_id: str,
                           metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new conversation in a workspace.
        
        Args:
            workspace_id: The ID of the workspace to create the conversation in
            topic: The topic/title of the conversation
            owner_id: The ID of the user who owns the conversation
            metadata: Optional metadata for the conversation
            
        Returns:
            The created conversation as a dictionary
        """
        conversation_id = str(uuid.uuid4())
        
        # Create conversation record
        conversation = {
            "id": conversation_id,
            "workspace_id": workspace_id,
            "topic": topic or "New Conversation",
            "metadata": metadata or {},
            "owner_id": owner_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        # Store in memory
        self._conversations[conversation_id] = conversation
        logger.info(f"Created new conversation: {conversation_id} in workspace: {workspace_id} for user: {owner_id}")
        return conversation

    def get_conversations_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """
        Get all conversations in a specific workspace.
        
        Args:
            workspace_id: The ID of the workspace
            
        Returns:
            A list of conversation dictionaries in the workspace
        """
        return [
            conv for conv in self._conversations.values() 
            if conv.get("workspace_id") == workspace_id
        ]

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific conversation by ID.
        
        Args:
            conversation_id: The ID of the conversation to retrieve
            
        Returns:
            The conversation dictionary or None if not found
        """
        return self._conversations.get(conversation_id)

    def verify_conversation_access(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        """
        Verify that a user has access to a conversation and return the conversation.
        
        Args:
            conversation_id: The ID of the conversation to verify access to
            user_id: The ID of the user requesting access
            
        Returns:
            The conversation dictionary if access is allowed
            
        Raises:
            ResourceNotFoundException: If the conversation doesn't exist
            PermissionDeniedException: If the user doesn't own the conversation
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation not found: {conversation_id}")
            raise ResourceNotFoundException(resource_id=conversation_id, resource_type="conversation")
            
        if conversation.get("owner_id") != user_id:
            logger.warning(f"Permission denied for user: {user_id} accessing conversation: {conversation_id}")
            raise PermissionDeniedException(
                resource_id=conversation_id, 
                message="You don't have permission to access this conversation"
            )
            
        return conversation


# Create a singleton instance for global use
storage_service = StorageService()