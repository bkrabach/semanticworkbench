"""
Workspace domain models for the Cortex Core application.

This module defines the domain models related to workspaces, which
are isolated environments for organizing user content.
"""

from datetime import datetime
from typing import Dict, Any, List
from pydantic import Field

from app.models.domain.base import TimestampedModel, MetadataModel


class Workspace(TimestampedModel, MetadataModel):
    """
    Domain model for a workspace.
    
    Workspaces are isolated environments where users organize their
    conversations and other content.
    """
    user_id: str
    name: str
    last_active_at: datetime
    config: Dict[str, Any] = Field(default_factory=dict)


class WorkspaceSharing(TimestampedModel):
    """
    Domain model for workspace sharing.
    
    Represents access granted to a user for a specific workspace.
    """
    workspace_id: str
    user_id: str
    permissions: List[str] = Field(default_factory=list)