"""
Base domain models for the Cortex Core application.

This module defines the base classes for all domain models, including common
functionality like timestamps.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class DomainModel(BaseModel):
    """
    Base class for all domain models.
    
    All domain models inherit from this class to ensure consistent
    structure and behavior across the application.
    """
    id: str


class TimestampedModel(DomainModel):
    """
    Base class for models with timestamps.
    
    Adds created_at and updated_at fields to track when entities are
    created and modified.
    """
    created_at: datetime
    updated_at: Optional[datetime] = None


class AuditableModel(TimestampedModel):
    """
    Base class for models that need auditing.
    
    Adds fields for tracking who created and last modified the entity.
    """
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class MetadataModel(DomainModel):
    """
    Base class for models that have metadata.
    
    Provides a standard way to store additional information that
    doesn't fit the core domain model.
    """
    metadata: Dict[str, Any] = Field(default_factory=dict)