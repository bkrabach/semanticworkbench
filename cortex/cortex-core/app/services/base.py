"""
Base service classes for Cortex Core.

This module defines base service classes that provide common functionality
and structure for all service implementations.
"""

from typing import TypeVar, Generic
from sqlalchemy.orm import Session

from app.database.repositories.base import Repository
from app.models.domain.base import DomainModel

T = TypeVar('T', bound=DomainModel)  # Domain model type
R = TypeVar('R', bound=Repository)  # Repository type


class Service(Generic[T, R]):
    """
    Base service class.
    
    Provides a consistent interface for services that operate on
    domain models and use repositories for data access.
    
    Type Parameters:
        T: Domain model type
        R: Repository type
    """
    
    def __init__(self, db_session: Session, repository: R):
        """
        Initialize the service with a database session and repository.
        
        Args:
            db_session: SQLAlchemy database session
            repository: Repository instance
        """
        self.db = db_session
        self.repository = repository