from typing import TypeVar, Generic, List, Optional, Dict, Any, Type, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from ...core.exceptions import EntityNotFoundError, DatabaseError
from ..models import Base

T = TypeVar('T', bound=BaseModel)  # Domain model type
DB = TypeVar('DB', bound=Base)  # Database model type - bound to our concrete Base class

class BaseRepository(Generic[T, DB]):
    """Base repository implementation for CRUD operations."""
    
    def __init__(self, session: AsyncSession, model_type: Type[T], db_model_type: Type[DB]):
        """
        Initialize repository.
        
        Args:
            session: SQLAlchemy async session
            model_type: Pydantic model type
            db_model_type: SQLAlchemy model type
        """
        self.session = session
        self.model_type = model_type
        self.db_model_type = db_model_type
    
    async def create(self, entity: T) -> T:
        """
        Create a new entity.
        
        Args:
            entity: Domain entity to create
            
        Returns:
            Created domain entity
        """
        try:
            # Convert domain model to database model
            db_entity = self._to_db(entity)
            
            # Add to session
            self.session.add(db_entity)
            await self.session.flush()
            
            # Convert back to domain model and return
            result = self._to_domain(db_entity)
            assert result is not None, "Created entity should not be None"
            return result
        except Exception as e:
            self._handle_db_error(e, "Error creating entity")
            raise  # Never reached, just to satisfy typechecker
    
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """
        Get entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Domain entity if found, None otherwise
        """
        try:
            # Cast to our concrete Base type to access id
            id_attr_name = "id"
            if hasattr(self.db_model_type, "user_id"):
                id_attr_name = "user_id"
                
            query = select(self.db_model_type).where(
                getattr(self.db_model_type, id_attr_name) == entity_id
            )
            result = await self.session.execute(query)
            db_entity = result.scalars().first()
            
            return self._to_domain(db_entity) if db_entity else None
        except Exception as e:
            self._handle_db_error(e, f"Error getting entity with ID {entity_id}")
            raise  # Never reached, just to satisfy typechecker
    
    async def list(self, filters: Optional[Dict[str, Any]] = None, 
                    limit: int = 100, offset: int = 0) -> List[T]:
        """
        List entities with optional filtering.
        
        Args:
            filters: Optional filters as field-value pairs
            limit: Maximum number of entities to return
            offset: Pagination offset
            
        Returns:
            List of domain entities
        """
        try:
            # Build query
            query = select(self.db_model_type)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.db_model_type, field):
                        query = query.where(getattr(self.db_model_type, field) == value)
            
            # Apply pagination
            query = query.limit(limit).offset(offset)
            
            # Execute query
            result = await self.session.execute(query)
            db_entities = result.scalars().all()
            
            # Convert to domain models and filter out None values
            domain_entities = [
                entity for entity in [self._to_domain(db_entity) for db_entity in db_entities] 
                if entity is not None
            ]
            return cast(List[T], domain_entities)
        except Exception as e:
            self._handle_db_error(e, "Error listing entities")
            raise  # Never reached, just to satisfy typechecker
    
    async def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: Domain entity to update
            
        Returns:
            Updated domain entity
        """
        try:
            # Get entity ID (assumes entity has either 'id' or 'user_id' attribute)
            id_attr_name = 'id'
            db_id_attr_name = 'id'
            
            if hasattr(entity, 'user_id'):
                id_attr_name = 'user_id'
                db_id_attr_name = 'user_id'
                
            entity_id = getattr(entity, id_attr_name)
            
            # Get existing entity
            query = select(self.db_model_type).where(
                getattr(self.db_model_type, db_id_attr_name) == entity_id
            )
            result = await self.session.execute(query)
            db_entity = result.scalars().first()
            
            if not db_entity:
                raise EntityNotFoundError(
                    f"{self.model_type.__name__} not found with ID: {entity_id}"
                )
            
            # Update fields
            db_entity = self._update_db_entity(db_entity, entity)
            
            # Flush changes
            await self.session.flush()
            
            # Return updated entity as domain model
            domain_entity = self._to_domain(db_entity)
            assert domain_entity is not None, "Updated entity should not be None"
            return domain_entity
        except EntityNotFoundError:
            raise
        except Exception as e:
            # Get id safely for error message
            entity_id = getattr(entity, 'id', getattr(entity, 'user_id', 'unknown'))
            self._handle_db_error(e, f"Error updating entity with ID {entity_id}")
            raise  # Never reached, just to satisfy typechecker
    
    async def delete(self, entity_id: str) -> bool:
        """
        Delete entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            True if entity was deleted, False otherwise
        """
        try:
            # Determine ID field name based on entity type
            id_attr_name = "id"
            if hasattr(self.db_model_type, "user_id"):
                id_attr_name = "user_id"
                
            # Get entity
            query = select(self.db_model_type).where(
                getattr(self.db_model_type, id_attr_name) == entity_id
            )
            result = await self.session.execute(query)
            db_entity = result.scalars().first()
            
            if not db_entity:
                return False
            
            # Delete entity
            await self.session.delete(db_entity)
            await self.session.flush()
            
            return True
        except Exception as e:
            self._handle_db_error(e, f"Error deleting entity with ID {entity_id}")
            raise  # Never reached, just to satisfy typechecker
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities with optional filtering.
        
        Args:
            filters: Optional filters as field-value pairs
            
        Returns:
            Count of entities
        """
        try:
            # Build query
            query = select(func.count()).select_from(self.db_model_type)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.db_model_type, field):
                        query = query.where(getattr(self.db_model_type, field) == value)
            
            # Execute query
            result = await self.session.execute(query)
            count = result.scalar() or 0
            return count
        except Exception as e:
            self._handle_db_error(e, "Error counting entities")
            raise  # Never reached, just to satisfy typechecker
    
    def _to_domain(self, db_entity: Optional[DB]) -> Optional[T]:
        """
        Convert database entity to domain entity.
        
        Args:
            db_entity: Database entity
            
        Returns:
            Domain entity
        """
        raise NotImplementedError("Subclasses must implement _to_domain")
    
    def _to_db(self, entity: T) -> DB:
        """
        Convert domain entity to database entity.
        
        Args:
            entity: Domain entity
            
        Returns:
            Database entity
        """
        raise NotImplementedError("Subclasses must implement _to_db")
    
    def _update_db_entity(self, db_entity: DB, entity: T) -> DB:
        """
        Update database entity from domain entity.
        
        Args:
            db_entity: Database entity to update
            entity: Domain entity with new values
            
        Returns:
            Updated database entity
        """
        raise NotImplementedError("Subclasses must implement _update_db_entity")
    
    def _handle_db_error(self, error: Exception, message: str) -> None:
        """
        Handle database error.
        
        Args:
            error: Exception that occurred
            message: Error message
            
        Raises:
            DatabaseError: Wrapped database error
        """
        # Log the error
        import logging
        logging.error(f"{message}: {str(error)}")
        
        # Wrap and raise
        raise DatabaseError(f"{message}: {str(error)}") from error