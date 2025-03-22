from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ...models.base import BaseModelWithMetadata


class LoginRequest(BaseModel):
    """Login request model."""

    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class InputRequest(BaseModelWithMetadata):
    """Input data from clients."""

    content: str = Field(..., description="Message content")
    conversation_id: str = Field(..., description="Conversation ID")


class WorkspaceCreate(BaseModelWithMetadata):
    """Request to create a workspace."""

    name: str = Field(..., min_length=1, max_length=100, description="Workspace name")
    description: str = Field(..., min_length=1, max_length=500, description="Workspace description")


class WorkspaceUpdate(BaseModelWithMetadata):
    """Request to update a workspace."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Workspace name")
    description: Optional[str] = Field(None, min_length=1, max_length=500, description="Workspace description")


class ConversationCreate(BaseModelWithMetadata):
    """Request to create a conversation."""

    workspace_id: str = Field(..., description="ID of the parent workspace")
    topic: str = Field(..., min_length=1, max_length=200, description="Conversation topic")
    participant_ids: List[str] = Field(default_factory=list, description="List of user IDs")


class ConversationUpdate(BaseModelWithMetadata):
    """Request to update a conversation."""

    topic: Optional[str] = Field(None, min_length=1, max_length=200, description="Conversation topic")
    participant_ids: Optional[List[str]] = Field(None, description="List of user IDs")


class PaginationParams(BaseModel):
    """Pagination parameters."""

    limit: int = Field(100, ge=1, le=1000, description="Maximum number of items to return")
    offset: int = Field(0, ge=0, description="Number of items to skip")


class GetContextRequest(BaseModelWithMetadata):
    """Get context request model."""
    
    query: Optional[str] = Field(None, description="Optional search query to filter context")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Maximum number of items to return")


class AnalyzeConversationRequest(BaseModelWithMetadata):
    """Analyze conversation request model."""
    
    conversation_id: str = Field(..., description="The conversation ID to analyze")
    analysis_type: Optional[str] = Field("summary", description="Type of analysis (summary, topics, sentiment)")


class SearchHistoryRequest(BaseModelWithMetadata):
    """Search history request model."""
    
    query: str = Field(..., min_length=1, description="Search query string")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Maximum number of results to return")
    include_conversations: Optional[bool] = Field(True, description="Whether to include conversation data")
