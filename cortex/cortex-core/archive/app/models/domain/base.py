"""Base domain models for the Cortex application."""
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class BaseModelWithTimestamps(BaseModel):
    """Base model with created_at and updated_at timestamps."""
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class BaseModelWithMetadata(BaseModelWithTimestamps):
    """Base model with metadata field."""
    
    metadata: Dict[str, Any] = Field(default_factory=dict)