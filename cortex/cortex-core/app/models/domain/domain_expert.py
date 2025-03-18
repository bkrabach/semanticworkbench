"""Domain expert models for the Cortex application."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl

from app.models.domain.base import BaseModelWithMetadata


class DomainExpertCreate(BaseModel):
    """Model for creating a new domain expert."""
    
    name: str
    endpoint_url: HttpUrl
    auth_token: Optional[str] = None
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DomainExpertInfo(BaseModelWithMetadata):
    """Model for domain expert information."""
    
    id: UUID = Field(default_factory=uuid4)
    name: str
    endpoint_url: HttpUrl
    is_active: bool = True
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    last_connected_at: Optional[datetime] = None


class DomainExpertUpdate(BaseModel):
    """Model for updating a domain expert."""
    
    name: Optional[str] = None
    endpoint_url: Optional[HttpUrl] = None
    auth_token: Optional[str] = None
    is_active: Optional[bool] = None
    capabilities: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolParameter(BaseModel):
    """Model for a tool parameter."""
    
    name: str
    description: Optional[str] = None
    type: str
    required: bool = False
    default: Optional[Any] = None


class ToolInfo(BaseModelWithMetadata):
    """Model for domain expert tool information."""
    
    id: UUID = Field(default_factory=uuid4)
    expert_id: UUID
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]


class ToolExecutionRequest(BaseModel):
    """Model for executing a tool."""
    
    expert_id: UUID
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResponse(BaseModel):
    """Model for tool execution response."""
    
    expert_name: str
    tool_name: str
    result: Dict[str, Any]
    execution_time: float
    metadata: Dict[str, Any] = Field(default_factory=dict)