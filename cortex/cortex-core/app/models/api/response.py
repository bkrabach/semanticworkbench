from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Generic

from pydantic import BaseModel, Field, ConfigDict
# No longer need to import GenericModel as it's now part of BaseModel

from ...models import Conversation, Workspace

T = TypeVar('T')


class BaseResponse(BaseModel, Generic[T]):
    """Base response model that all API responses should inherit from."""
    
    status: str = Field("success", description="Status of the operation (success, error, etc.)")
    request_id: Optional[str] = Field(None, description="Unique request identifier for tracing")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Response timestamp")
    data: T = Field(..., description="Response data payload")
    
    # Modern Pydantic v2 way of specifying model configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2023-05-04T12:34:56.789",
                "data": {}
            }
        }
    )


class ResultSegment(BaseModel):
    """Result segment model for streaming responses."""
    
    content: str = Field(..., description="The segment content")
    final: bool = Field(False, description="Whether this is the final segment")


class LoginResponseData(BaseModel):
    """Data model for login response."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    claims: Dict[str, Any] = Field(..., description="User claims")


class LoginResponse(BaseResponse[LoginResponseData]):
    """Login response model."""

    data: LoginResponseData


class InputResponse(BaseResponse[Dict[str, Any]]):
    """Input response model."""
    
    data: Dict[str, Any] = Field(..., description="Echoed input data")


class WorkspaceData(BaseModel):
    """Data model for workspace response."""
    
    workspace: Workspace = Field(..., description="Workspace data")


class WorkspaceResponse(BaseResponse[WorkspaceData]):
    """Workspace response model."""
    
    data: WorkspaceData


class WorkspacesListData(BaseModel):
    """Data model for workspaces list."""
    
    workspaces: List[Workspace] = Field(..., description="List of workspaces")
    total: int = Field(..., description="Total number of workspaces")
    limit: Optional[int] = Field(None, description="Limit used for pagination")
    offset: Optional[int] = Field(None, description="Offset used for pagination")


class WorkspacesListResponse(BaseResponse[WorkspacesListData]):
    """Workspaces list response model."""
    
    data: WorkspacesListData


class ConversationData(BaseModel):
    """Data model for conversation response."""
    
    conversation: Dict[str, Any] = Field(..., description="Conversation data with messages")


class ConversationResponse(BaseResponse[ConversationData]):
    """Conversation response model."""
    
    data: ConversationData


class ConversationsListData(BaseModel):
    """Data model for conversations list."""
    
    conversations: List[Conversation] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")
    limit: Optional[int] = Field(None, description="Limit used for pagination")
    offset: Optional[int] = Field(None, description="Offset used for pagination")


class ConversationsListResponse(BaseResponse[ConversationsListData]):
    """Conversations list response model."""
    
    data: ConversationsListData


class ErrorDetail(BaseModel):
    """Error detail model."""
    
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: ErrorDetail = Field(..., description="Error details")
    request_id: Optional[str] = Field(None, description="Unique request identifier for tracing")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Error timestamp")


class GetContextResponse(BaseResponse[Dict[str, Any]]):
    """Get context response model."""
    
    data: Dict[str, Any] = Field(..., description="Context data")


class AnalyzeConversationResponse(BaseResponse[Dict[str, Any]]):
    """Analyze conversation response model."""
    
    data: Dict[str, Any] = Field(..., description="Analysis results")


class SearchHistoryResponse(BaseResponse[Dict[str, Any]]):
    """Search history response model."""
    
    data: Dict[str, Any] = Field(..., description="Search results")


# Pagination support
class PaginatedResponse(BaseResponse[T]):
    """Paginated response model for list endpoints."""
    
    data: T
    pagination: Dict[str, Any] = Field(
        default_factory=lambda: {
            "limit": None,
            "offset": None, 
            "total": 0,
            "has_more": False
        },
        description="Pagination information"
    )
