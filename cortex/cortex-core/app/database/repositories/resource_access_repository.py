"""
Resource access repository for authorization checks.

This module defines the repository interface and implementation for
authorization and resource access checks.
"""

from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.orm import Session

from app.database.models import Workspace, WorkspaceSharing, Conversation
from app.models.domain.workspace import Workspace as WorkspaceDomain
from app.database.repositories.base import Repository


class ResourceAccessRepository(ABC):
    """
    Interface for resource access verification operations.
    
    This repository is responsible for determining whether a user
    has access to specific resources.
    """
    
    @abstractmethod
    def is_workspace_owner(self, workspace_id: str, user_id: str) -> bool:
        """
        Check if user is the owner of a workspace.
        
        Args:
            workspace_id: ID of the workspace
            user_id: ID of the user
            
        Returns:
            True if user is the owner, False otherwise
        """
        pass
        
    @abstractmethod
    def has_workspace_sharing_access(self, workspace_id: str, user_id: str) -> bool:
        """
        Check if workspace is shared with the user.
        
        Args:
            workspace_id: ID of the workspace
            user_id: ID of the user
            
        Returns:
            True if workspace is shared with user, False otherwise
        """
        pass
        
    @abstractmethod
    def get_conversation_workspace_id(self, conversation_id: str) -> Optional[str]:
        """
        Get the workspace ID for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Workspace ID if found, None otherwise
        """
        pass


class SQLAlchemyResourceAccessRepository(ResourceAccessRepository):
    """
    SQLAlchemy implementation of ResourceAccessRepository.
    
    Implements the resource access verification operations using
    SQLAlchemy ORM models.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        
    def is_workspace_owner(self, workspace_id: str, user_id: str) -> bool:
        """
        Check if user is the owner of a workspace.
        
        Args:
            workspace_id: ID of the workspace
            user_id: ID of the user
            
        Returns:
            True if user is the owner, False otherwise
        """
        workspace = self.db.query(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.user_id == user_id
        ).first()
        return workspace is not None
        
    def has_workspace_sharing_access(self, workspace_id: str, user_id: str) -> bool:
        """
        Check if workspace is shared with the user.
        
        Args:
            workspace_id: ID of the workspace
            user_id: ID of the user
            
        Returns:
            True if workspace is shared with user, False otherwise
        """
        sharing = self.db.query(WorkspaceSharing).filter(
            WorkspaceSharing.workspace_id == workspace_id,
            WorkspaceSharing.user_id == user_id
        ).first()
        return sharing is not None
        
    def get_conversation_workspace_id(self, conversation_id: str) -> Optional[str]:
        """
        Get the workspace ID for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Workspace ID if found, None otherwise
        """
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conversation:
            return str(conversation.workspace_id)
        return None


def get_resource_access_repository(db_session: Session) -> ResourceAccessRepository:
    """
    Factory function for ResourceAccessRepository.
    
    Args:
        db_session: SQLAlchemy database session
        
    Returns:
        ResourceAccessRepository instance
    """
    return SQLAlchemyResourceAccessRepository(db_session)