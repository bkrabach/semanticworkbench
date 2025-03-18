"""Base repository for database operations."""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import Base
from app.exceptions import ResourceNotFoundError


# Generic type for the SQLAlchemy model
ModelType = TypeVar("ModelType", bound=Base)

# Generic type for the Pydantic model for creating a record
CreateSchemaType = TypeVar("CreateSchemaType")

# Generic type for the Pydantic model for updating a record 
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository for database operations."""
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """Initialize the repository.
        
        Args:
            model: The SQLAlchemy model class
            db: The database session
        """
        self.model = model
        self.db = db
    
    async def get(self, id: UUID) -> Optional[ModelType]:
        """Get a record by ID.
        
        Args:
            id: The record ID
            
        Returns:
            The record or None if not found
        """
        query = select(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_or_404(self, id: UUID) -> ModelType:
        """Get a record by ID or raise a 404 exception.
        
        Args:
            id: The record ID
            
        Returns:
            The record
            
        Raises:
            ResourceNotFoundError: If the record is not found
        """
        record = await self.get(id)
        if record is None:
            raise ResourceNotFoundError(f"{self.model.__name__} with ID {id} not found")
        return record
    
    async def get_multi(
        self, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get multiple records.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional dict of field-value pairs to filter by
            
        Returns:
            List of records
        """
        query = select(self.model)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record.
        
        Args:
            obj_in: The create schema model instance
            
        Returns:
            The newly created record
        """
        db_obj = self.model(**obj_in.model_dump(exclude_unset=True))
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """Update a record.
        
        Args:
            db_obj: The database object to update
            obj_in: The update schema model instance or a dict of field-value pairs
            
        Returns:
            The updated record
        """
        update_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, "model_dump") else obj_in
        
        for field, value in update_data.items():
            if hasattr(db_obj, field) and value is not None:
                setattr(db_obj, field, value)
        
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def delete(self, *, id: UUID) -> bool:
        """Delete a record.
        
        Args:
            id: The record ID
            
        Returns:
            True if the record was deleted, False otherwise
        """
        query = delete(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        return result.rowcount > 0
    
    async def count(self, *, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records, optionally filtered.
        
        Args:
            filters: Optional dict of field-value pairs to filter by
            
        Returns:
            The count of records
        """
        query = select(func.count()).select_from(self.model)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)
        
        result = await self.db.execute(query)
        return result.scalar_one()