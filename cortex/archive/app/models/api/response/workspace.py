"""
API response models for workspace operations.

This module defines the response models for workspace-related API endpoints.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class WorkspaceResponse(BaseModel):
    """Response model for workspace operations"""
    id: str = Field(..., description="Workspace ID")
    name: str = Field(..., description="Workspace name")
    created_at: datetime = Field(..., description="Workspace creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    last_active_at: datetime = Field(..., description="Last activity time")
    config: Dict[str, Any] = Field(default_factory=dict, description="Workspace configuration")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Workspace metadata")


class WorkspaceListResponse(BaseModel):
    """Response model for listing workspaces"""
    workspaces: List[WorkspaceResponse] = Field(default_factory=list, description="List of workspaces")