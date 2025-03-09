"""
Base repository interface and implementation.

This module defines the base repository interface that all repository 
implementations should follow.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from sqlalchemy.orm import Session
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)  # Domain model type
M = TypeVar('M')  # Database model type


class Repository(Generic[T, M], ABC):
    """
    Base repository interface.
    
    Defines the common interface for all repositories, providing a standard
    way to convert between database and domain models.
    
    Type Parameters:
        T: Domain model type (Pydantic)
        M: Database model type (SQLAlchemy)
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        
    @abstractmethod
    def _to_domain(self, db_model: M) -> T:
        """
        Convert a database model to a domain model.
        
        Args:
            db_model: SQLAlchemy model instance
            
        Returns:
            Pydantic domain model instance
        """
        pass
        
    @abstractmethod
    def _to_db_model(self, domain_model: T) -> M:
        """
        Convert a domain model to a database model.
        
        Args:
            domain_model: Pydantic domain model instance
            
        Returns:
            SQLAlchemy model instance
        """
        pass