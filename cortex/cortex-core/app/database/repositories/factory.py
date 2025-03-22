from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, cast

from .user_repository import UserRepository
from .workspace_repository import WorkspaceRepository 
from .conversation_repository import ConversationRepository
from .message_repository import MessageRepository

class RepositoryFactory:
    """Factory for creating repositories with the same database session."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository factory.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self._repositories: Dict[str, Any] = {}
    
    def get_user_repository(self) -> UserRepository:
        """
        Get user repository.
        
        Returns:
            User repository
        """
        # Get or create user repository
        repo_key = "user_repository"
        if repo_key not in self._repositories:
            self._repositories[repo_key] = UserRepository(self.session)
        return cast(UserRepository, self._repositories[repo_key])
    
    def get_workspace_repository(self) -> WorkspaceRepository:
        """
        Get workspace repository.
        
        Returns:
            Workspace repository
        """
        # Get or create workspace repository
        repo_key = "workspace_repository"
        if repo_key not in self._repositories:
            self._repositories[repo_key] = WorkspaceRepository(self.session)
        return cast(WorkspaceRepository, self._repositories[repo_key])
    
    def get_conversation_repository(self) -> ConversationRepository:
        """
        Get conversation repository.
        
        Returns:
            Conversation repository
        """
        # Get or create conversation repository
        repo_key = "conversation_repository"
        if repo_key not in self._repositories:
            self._repositories[repo_key] = ConversationRepository(self.session)
        return cast(ConversationRepository, self._repositories[repo_key])
    
    def get_message_repository(self) -> MessageRepository:
        """
        Get message repository.
        
        Returns:
            Message repository
        """
        # Get or create message repository
        repo_key = "message_repository"
        if repo_key not in self._repositories:
            self._repositories[repo_key] = MessageRepository(self.session)
        return cast(MessageRepository, self._repositories[repo_key])