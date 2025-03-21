import logging
from fastapi import APIRouter, Depends

from ..utils.auth import get_current_user
from ..models.api.request import WorkspaceCreate, ConversationCreate
from ..models.api.response import (
    WorkspaceResponse, WorkspacesListResponse,
    ConversationResponse, ConversationsListResponse
)
from ..models.domain import Workspace, Conversation
from ..core.storage import storage
from ..core.exceptions import ResourceNotFoundException, PermissionDeniedException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config", tags=["config"])

# Workspace endpoints

@router.post("/workspace", response_model=WorkspaceResponse)
async def create_workspace(
    request: WorkspaceCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new workspace.

    Args:
        request: The workspace creation request
        current_user: The authenticated user

    Returns:
        The created workspace
    """
    user_id = current_user["user_id"]

    # Create workspace
    workspace = Workspace(
        name=request.name,
        description=request.description,
        owner_id=user_id,
        metadata=request.metadata
    )

    # Store workspace
    workspace_dict = storage.create_workspace(workspace)

    logger.info(f"Created workspace {workspace.id} for user {user_id}")

    return WorkspaceResponse(
        status="workspace created",
        workspace=Workspace(**workspace_dict)
    )

@router.get("/workspace", response_model=WorkspacesListResponse)
async def list_workspaces(current_user: dict = Depends(get_current_user)):
    """
    List workspaces for the current user.

    Args:
        current_user: The authenticated user

    Returns:
        List of workspaces owned by the user
    """
    user_id = current_user["user_id"]

    # Get workspaces for user
    workspace_dicts = storage.list_workspaces(user_id)
    workspaces = [Workspace(**w) for w in workspace_dicts]

    logger.info(f"Listed {len(workspaces)} workspaces for user {user_id}")

    return WorkspacesListResponse(
        workspaces=workspaces,
        total=len(workspaces)
    )

# Conversation endpoints

@router.post("/conversation", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new conversation in a workspace.

    Args:
        request: The conversation creation request
        current_user: The authenticated user

    Returns:
        The created conversation
    """
    user_id = current_user["user_id"]
    workspace_id = request.workspace_id

    # Verify workspace exists and user has access
    workspace = storage.get_workspace(workspace_id)
    if not workspace:
        raise ResourceNotFoundException(
            message="Workspace not found",
            resource_type="workspace",
            resource_id=workspace_id
        )

    if workspace["owner_id"] != user_id:
        raise PermissionDeniedException(
            message="You do not have access to this workspace",
            details={
                "resource_type": "workspace",
                "resource_id": workspace_id,
                "user_id": user_id
            }
        )

    # Create conversation
    # Ensure current user is in participants
    participants = list(request.participant_ids)
    if user_id not in participants:
        participants.append(user_id)

    conversation = Conversation(
        workspace_id=workspace_id,
        topic=request.topic,
        participant_ids=participants,
        metadata=request.metadata
    )

    # Store conversation
    conversation_dict = storage.create_conversation(conversation)

    logger.info(f"Created conversation {conversation.id} in workspace {workspace_id}")

    return ConversationResponse(
        status="conversation created",
        conversation=Conversation(**conversation_dict)
    )

@router.get("/conversation", response_model=ConversationsListResponse)
async def list_conversations(
    workspace_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    List conversations in a workspace.

    Args:
        workspace_id: The workspace ID
        current_user: The authenticated user

    Returns:
        List of conversations in the workspace
    """
    user_id = current_user["user_id"]

    # Verify workspace exists and user has access
    workspace = storage.get_workspace(workspace_id)
    if not workspace:
        raise ResourceNotFoundException(
            message="Workspace not found",
            resource_type="workspace",
            resource_id=workspace_id
        )

    if workspace["owner_id"] != user_id:
        raise PermissionDeniedException(
            message="You do not have access to this workspace",
            details={
                "resource_type": "workspace",
                "resource_id": workspace_id,
                "user_id": user_id
            }
        )

    # Get conversations for workspace
    conversation_dicts = storage.list_conversations(workspace_id)
    conversations = [Conversation(**c) for c in conversation_dicts]

    logger.info(f"Listed {len(conversations)} conversations for workspace {workspace_id}")

    return ConversationsListResponse(
        conversations=conversations,
        total=len(conversations)
    )