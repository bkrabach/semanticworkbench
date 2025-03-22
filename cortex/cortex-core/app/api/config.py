import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query

from ..utils.auth import get_current_user
from ..models.api.request import (
    WorkspaceCreate,
    WorkspaceUpdate,
    ConversationCreate,
    ConversationUpdate,
    PaginationParams
)
from ..models.api.response import (
    WorkspaceResponse,
    WorkspacesListResponse,
    ConversationResponse,
    ConversationsListResponse,
    ErrorResponse
)
from ..models.domain import Workspace, Conversation
from ..database.unit_of_work import UnitOfWork
from ..core.exceptions import (
    EntityNotFoundError,
    AccessDeniedError,
    DuplicateEntityError,
    DatabaseError
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config", tags=["config"])

# Helper for error handling
def handle_repository_error(error: Exception):
    """
    Handle repository exceptions and convert to FastAPI HTTPExceptions.

    Args:
        error: The exception to handle

    Raises:
        HTTPException: FastAPI compatible exception
    """
    if isinstance(error, EntityNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "resource_not_found",
                    "message": str(error),
                    "details": error.details if hasattr(error, "details") else {}
                }
            }
        )
    elif isinstance(error, AccessDeniedError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "permission_denied",
                    "message": str(error),
                    "details": error.details if hasattr(error, "details") else {}
                }
            }
        )
    elif isinstance(error, DuplicateEntityError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "resource_already_exists",
                    "message": str(error),
                    "details": error.details if hasattr(error, "details") else {}
                }
            }
        )
    elif isinstance(error, DatabaseError):
        logger.error(f"Database error: {str(error)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "database_error",
                    "message": "An error occurred while accessing the database",
                    "details": {"original_error": str(error)}
                }
            }
        )
    else:
        logger.error(f"Unexpected error: {str(error)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred",
                    "details": {"original_error": str(error)}
                }
            }
        )

# Workspace endpoints

@router.post("/workspace", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
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

    try:
        # Create workspace
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name=request.name,
            description=request.description,
            owner_id=user_id,
            metadata=request.metadata
        )

        # Store workspace
        async with UnitOfWork.for_transaction() as uow:
            workspace_repo = uow.repositories.get_workspace_repository()
            created_workspace = await workspace_repo.create(workspace)
            await uow.commit()

        logger.info(f"Created workspace {workspace.id} for user {user_id}")

        return WorkspaceResponse(
            status="workspace created",
            workspace=created_workspace
        )
    except Exception as e:
        handle_repository_error(e)

@router.get("/workspace", response_model=WorkspacesListResponse, responses={
    401: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def list_workspaces(
    pagination: PaginationParams = Depends(),
    current_user: dict = Depends(get_current_user)
):
    """
    List workspaces for the current user.

    Args:
        pagination: The pagination parameters
        current_user: The authenticated user

    Returns:
        List of workspaces owned by the user
    """
    user_id = current_user["user_id"]

    try:
        async with UnitOfWork.for_transaction() as uow:
            workspace_repo = uow.repositories.get_workspace_repository()

            # Get workspaces for user
            workspaces = await workspace_repo.list_by_owner(
                user_id,
                limit=pagination.limit,
                offset=pagination.offset
            )

            # Get total count
            total = await workspace_repo.count_by_owner(user_id)

        logger.info(f"Listed {len(workspaces)} workspaces for user {user_id}")

        return WorkspacesListResponse(
            workspaces=workspaces,
            total=total
        )
    except Exception as e:
        handle_repository_error(e)

@router.get("/workspace/{workspace_id}", response_model=WorkspaceResponse, responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def get_workspace(
    workspace_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a workspace by ID.

    Args:
        workspace_id: The workspace ID
        current_user: The authenticated user

    Returns:
        The workspace
    """
    user_id = current_user["user_id"]

    try:
        async with UnitOfWork.for_transaction() as uow:
            workspace_repo = uow.repositories.get_workspace_repository()

            # Get workspace with owner check
            workspace = await workspace_repo.get_by_id(workspace_id, owner_id=user_id)

            if not workspace:
                raise EntityNotFoundError(
                    message=f"Workspace not found: {workspace_id}",
                    entity_type="Workspace",
                    entity_id=workspace_id
                )

        logger.info(f"Retrieved workspace {workspace_id} for user {user_id}")

        return WorkspaceResponse(
            status="workspace retrieved",
            workspace=workspace
        )
    except Exception as e:
        handle_repository_error(e)

@router.put("/workspace/{workspace_id}", response_model=WorkspaceResponse, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def update_workspace(
    workspace_id: str,
    request: WorkspaceUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a workspace.

    Args:
        workspace_id: The workspace ID
        request: The workspace update request
        current_user: The authenticated user

    Returns:
        The updated workspace
    """
    user_id = current_user["user_id"]

    try:
        async with UnitOfWork.for_transaction() as uow:
            workspace_repo = uow.repositories.get_workspace_repository()

            # Get workspace with owner check
            workspace = await workspace_repo.get_by_id(workspace_id, owner_id=user_id)

            if not workspace:
                raise EntityNotFoundError(
                    message=f"Workspace not found: {workspace_id}",
                    entity_type="Workspace",
                    entity_id=workspace_id
                )

            # Update fields if provided
            if request.name is not None:
                workspace.name = request.name

            if request.description is not None:
                workspace.description = request.description

            # Update metadata
            if request.metadata:
                workspace.metadata = request.metadata

            # Update workspace
            updated_workspace = await workspace_repo.update(workspace)
            await uow.commit()

        logger.info(f"Updated workspace {workspace_id} for user {user_id}")

        return WorkspaceResponse(
            status="workspace updated",
            workspace=updated_workspace
        )
    except Exception as e:
        handle_repository_error(e)

@router.delete("/workspace/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT, responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def delete_workspace(
    workspace_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a workspace.

    Args:
        workspace_id: The workspace ID
        current_user: The authenticated user
    """
    user_id = current_user["user_id"]

    try:
        async with UnitOfWork.for_transaction() as uow:
            workspace_repo = uow.repositories.get_workspace_repository()

            # Check if workspace exists and user is owner
            workspace = await workspace_repo.get_by_id(workspace_id, owner_id=user_id)

            if not workspace:
                raise EntityNotFoundError(
                    message=f"Workspace not found: {workspace_id}",
                    entity_type="Workspace",
                    entity_id=workspace_id
                )

            # Delete workspace (will cascade to conversations and messages)
            result = await workspace_repo.delete(workspace_id)
            await uow.commit()

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": {
                            "code": "delete_failed",
                            "message": f"Failed to delete workspace {workspace_id}"
                        }
                    }
                )

        logger.info(f"Deleted workspace {workspace_id} for user {user_id}")
    except Exception as e:
        handle_repository_error(e)

# Conversation endpoints

@router.post("/conversation", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
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

    try:
        async with UnitOfWork.for_transaction() as uow:
            workspace_repo = uow.repositories.get_workspace_repository()

            # Verify workspace exists and user has access
            workspace = await workspace_repo.get_by_id(workspace_id, owner_id=user_id)

            if not workspace:
                raise EntityNotFoundError(
                    message=f"Workspace not found: {workspace_id}",
                    entity_type="Workspace",
                    entity_id=workspace_id
                )

            # Create conversation
            # Ensure current user is in participants
            participants = list(request.participant_ids)
            if user_id not in participants:
                participants.append(user_id)

            conversation = Conversation(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                topic=request.topic,
                participant_ids=participants,
                metadata=request.metadata
            )

            # Store conversation
            conversation_repo = uow.repositories.get_conversation_repository()
            created_conversation = await conversation_repo.create(conversation)
            await uow.commit()

        logger.info(f"Created conversation {conversation.id} in workspace {workspace_id}")

        return ConversationResponse(
            status="conversation created",
            conversation=created_conversation
        )
    except Exception as e:
        handle_repository_error(e)

@router.get("/conversation", response_model=ConversationsListResponse, responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def list_conversations(
    workspace_id: str = Query(..., description="The workspace ID"),
    pagination: PaginationParams = Depends(),
    current_user: dict = Depends(get_current_user)
):
    """
    List conversations in a workspace.

    Args:
        workspace_id: The workspace ID
        pagination: The pagination parameters
        current_user: The authenticated user

    Returns:
        List of conversations in the workspace
    """
    user_id = current_user["user_id"]

    try:
        async with UnitOfWork.for_transaction() as uow:
            workspace_repo = uow.repositories.get_workspace_repository()

            # Verify workspace exists and user has access
            workspace = await workspace_repo.get_by_id(workspace_id, owner_id=user_id)

            if not workspace:
                raise EntityNotFoundError(
                    message=f"Workspace not found: {workspace_id}",
                    entity_type="Workspace",
                    entity_id=workspace_id
                )

            # Get conversations for workspace
            conversation_repo = uow.repositories.get_conversation_repository()
            conversations = await conversation_repo.list_by_workspace(
                workspace_id,
                limit=pagination.limit,
                offset=pagination.offset
            )

            # Get total count
            total = await conversation_repo.count_by_workspace(workspace_id)

        logger.info(f"Listed {len(conversations)} conversations for workspace {workspace_id}")

        return ConversationsListResponse(
            conversations=conversations,
            total=total
        )
    except Exception as e:
        handle_repository_error(e)

@router.get("/conversation/{conversation_id}", response_model=ConversationResponse, responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a conversation by ID.

    Args:
        conversation_id: The conversation ID
        current_user: The authenticated user

    Returns:
        The conversation
    """
    user_id = current_user["user_id"]

    try:
        async with UnitOfWork.for_transaction() as uow:
            conversation_repo = uow.repositories.get_conversation_repository()

            # Get conversation
            conversation = await conversation_repo.get_by_id(conversation_id)

            if not conversation:
                raise EntityNotFoundError(
                    message=f"Conversation not found: {conversation_id}",
                    entity_type="Conversation",
                    entity_id=conversation_id
                )

            # Check if user has access (either as workspace owner or participant)
            workspace_repo = uow.repositories.get_workspace_repository()
            workspace = await workspace_repo.get_by_id(conversation.workspace_id)

            if workspace is None:
                raise EntityNotFoundError(
                    message=f"Workspace not found: {conversation.workspace_id}",
                    entity_type="Workspace",
                    entity_id=conversation.workspace_id
                )

            if not workspace or workspace.owner_id != user_id and user_id not in conversation.participant_ids:
                raise AccessDeniedError(
                    message="You do not have access to this conversation",
                    entity_type="Conversation",
                    entity_id=conversation_id,
                    user_id=user_id
                )

        logger.info(f"Retrieved conversation {conversation_id}")

        return ConversationResponse(
            status="conversation retrieved",
            conversation=conversation
        )
    except Exception as e:
        handle_repository_error(e)

@router.put("/conversation/{conversation_id}", response_model=ConversationResponse, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a conversation.

    Args:
        conversation_id: The conversation ID
        request: The conversation update request
        current_user: The authenticated user

    Returns:
        The updated conversation
    """
    user_id = current_user["user_id"]

    try:
        async with UnitOfWork.for_transaction() as uow:
            conversation_repo = uow.repositories.get_conversation_repository()

            # Get conversation
            conversation = await conversation_repo.get_by_id(conversation_id)

            if not conversation:
                raise EntityNotFoundError(
                    message=f"Conversation not found: {conversation_id}",
                    entity_type="Conversation",
                    entity_id=conversation_id
                )

            # Check if user has access (as workspace owner)
            workspace_repo = uow.repositories.get_workspace_repository()
            workspace = await workspace_repo.get_by_id(conversation.workspace_id)

            if workspace is None:
                raise EntityNotFoundError(
                    message=f"Workspace not found: {conversation.workspace_id}",
                    entity_type="Workspace",
                    entity_id=conversation.workspace_id
                )

            if not workspace or workspace.owner_id != user_id:
                raise AccessDeniedError(
                    message="You do not have permission to update this conversation",
                    entity_type="Conversation",
                    entity_id=conversation_id,
                    user_id=user_id
                )

            # Update fields if provided
            if request.topic is not None:
                conversation.topic = request.topic

            if request.participant_ids is not None:
                # Ensure current user is in participants if they're the owner
                # workspace is guaranteed to be non-None at this point
                if user_id not in request.participant_ids and workspace and workspace.owner_id == user_id:
                    request.participant_ids.append(user_id)
                conversation.participant_ids = request.participant_ids

            # Update metadata
            if request.metadata:
                conversation.metadata = request.metadata

            # Update conversation
            updated_conversation = await conversation_repo.update(conversation)
            await uow.commit()

        logger.info(f"Updated conversation {conversation_id}")

        return ConversationResponse(
            status="conversation updated",
            conversation=updated_conversation
        )
    except Exception as e:
        handle_repository_error(e)

@router.delete("/conversation/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a conversation.

    Args:
        conversation_id: The conversation ID
        current_user: The authenticated user
    """
    user_id = current_user["user_id"]

    try:
        async with UnitOfWork.for_transaction() as uow:
            conversation_repo = uow.repositories.get_conversation_repository()

            # Get conversation
            conversation = await conversation_repo.get_by_id(conversation_id)

            if not conversation:
                raise EntityNotFoundError(
                    message=f"Conversation not found: {conversation_id}",
                    entity_type="Conversation",
                    entity_id=conversation_id
                )

            # Check if user has access (as workspace owner)
            workspace_repo = uow.repositories.get_workspace_repository()
            workspace = await workspace_repo.get_by_id(conversation.workspace_id)

            if workspace is None:
                raise EntityNotFoundError(
                    message=f"Workspace not found: {conversation.workspace_id}",
                    entity_type="Workspace",
                    entity_id=conversation.workspace_id
                )

            if not workspace or workspace.owner_id != user_id:
                raise AccessDeniedError(
                    message="You do not have permission to delete this conversation",
                    entity_type="Conversation",
                    entity_id=conversation_id,
                    user_id=user_id
                )

            # Delete conversation (will cascade to messages)
            result = await conversation_repo.delete(conversation_id)
            await uow.commit()

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": {
                            "code": "delete_failed",
                            "message": f"Failed to delete conversation {conversation_id}"
                        }
                    }
                )

        logger.info(f"Deleted conversation {conversation_id}")
    except Exception as e:
        handle_repository_error(e)