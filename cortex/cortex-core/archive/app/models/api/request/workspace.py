"""
API request models for workspace operations.

This module defines the request models for workspace-related API endpoints.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    """Request model for workspace creation"""
    name: str = Field(..., description="Workspace name")
    description: Optional[str] = Field(None, description="Optional workspace description")
    config: Optional[Dict[str, Any]] = Field(None, description="Optional workspace configuration")


class WorkspaceUpdate(BaseModel):
    """Request model for workspace updates"""
    name: Optional[str] = Field(None, description="Updated workspace name")
    config: Optional[Dict[str, Any]] = Field(None, description="Updated workspace configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated workspace metadata")