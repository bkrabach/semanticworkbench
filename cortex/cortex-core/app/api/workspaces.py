"""
Workspace API endpoints for the Cortex application.

This module handles workspace CRUD operations and workspace membership management.
"""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.exceptions import PermissionDeniedError, ResourceNotFoundError
from app.models.api.request.workspace import WorkspaceCreate, WorkspaceUpdate, WorkspaceMemberUpdate
from app.models.api.response.user import UserInfo
from app.models.api.response.workspace import WorkspaceInfo, WorkspaceWithUsers
from app.services.workspace_service import WorkspaceService

router = APIRouter(tags=["workspaces"])


async def get_workspace_service() -> WorkspaceService:
    """
    Dependency to get a WorkspaceService instance.
    
    Returns:
        A WorkspaceService instance
    """
    db = await get_db()
    return WorkspaceService(db=db)


@router.post("/workspaces", response_model=WorkspaceInfo, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceInfo:
    """
    Create a new workspace.
    
    Args:
        workspace_data: The workspace creation data
        current_user: The current authenticated user
        workspace_service: The workspace service instance
        
    Returns:
        The newly created workspace
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        workspace = await workspace_service.create_workspace(
            workspace_data=workspace_data,
            user_id=current_user.id,
        )
        return workspace
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/workspaces", response_model=List[WorkspaceInfo])
async def list_workspaces(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    skip: int = 0,
    limit: int = 100,
) -> List[WorkspaceInfo]:
    """
    List all workspaces accessible to the current user.
    
    Args:
        current_user: The current authenticated user
        workspace_service: The workspace service instance
        skip: Number of results to skip
        limit: Maximum number of results to return
        
    Returns:
        List of workspaces
    """
    workspaces = await workspace_service.get_user_workspaces(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return workspaces


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceWithUsers)
async def get_workspace(
    workspace_id: str,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceWithUsers:
    """
    Get a specific workspace by ID.
    
    Args:
        workspace_id: The workspace ID
        current_user: The current authenticated user
        workspace_service: The workspace service instance
        
    Returns:
        The workspace with its members
        
    Raises:
        HTTPException: If workspace not found or user lacks permission
    """
    try:
        workspace = await workspace_service.get_workspace_with_users(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
        return workspace
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this workspace",
        )


@router.put("/workspaces/{workspace_id}", response_model=WorkspaceInfo)
async def update_workspace(
    workspace_id: str,
    workspace_data: WorkspaceUpdate,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceInfo:
    """
    Update a workspace.
    
    Args:
        workspace_id: The workspace ID
        workspace_data: The workspace update data
        current_user: The current authenticated user
        workspace_service: The workspace service instance
        
    Returns:
        The updated workspace
        
    Raises:
        HTTPException: If update fails
    """
    try:
        workspace = await workspace_service.update_workspace(
            workspace_id=workspace_id,
            workspace_data=workspace_data,
            user_id=current_user.id,
        )
        return workspace
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this workspace",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> None:
    """
    Delete a workspace.
    
    Args:
        workspace_id: The workspace ID
        current_user: The current authenticated user
        workspace_service: The workspace service instance
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        await workspace_service.delete_workspace(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this workspace",
        )


@router.post("/workspaces/{workspace_id}/members", response_model=WorkspaceWithUsers)
async def add_workspace_member(
    workspace_id: str,
    member_data: WorkspaceMemberUpdate,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceWithUsers:
    """
    Add a user to a workspace.
    
    Args:
        workspace_id: The workspace ID
        member_data: The member update data containing user_id and role
        current_user: The current authenticated user
        workspace_service: The workspace service instance
        
    Returns:
        The updated workspace with its members
        
    Raises:
        HTTPException: If the operation fails
    """
    try:
        workspace = await workspace_service.add_user_to_workspace(
            workspace_id=workspace_id,
            user_id=member_data.user_id,
            role=member_data.role,
            current_user_id=current_user.id,
        )
        return workspace
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace or user not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage this workspace's members",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/workspaces/{workspace_id}/members/{user_id}", response_model=WorkspaceWithUsers)
async def update_workspace_member(
    workspace_id: str,
    user_id: str,
    member_data: WorkspaceMemberUpdate,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceWithUsers:
    """
    Update a workspace member's role.
    
    Args:
        workspace_id: The workspace ID
        user_id: The user ID of the member to update
        member_data: The member update data containing role
        current_user: The current authenticated user
        workspace_service: The workspace service instance
        
    Returns:
        The updated workspace with its members
        
    Raises:
        HTTPException: If the operation fails
    """
    # Ensure the user_id in the URL matches the one in the request body
    if user_id != member_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID in URL must match user ID in request body",
        )
    
    try:
        workspace = await workspace_service.update_user_role(
            workspace_id=workspace_id,
            user_id=user_id,
            role=member_data.role,
            current_user_id=current_user.id,
        )
        return workspace
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace or user not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this member's role",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/workspaces/{workspace_id}/members/{user_id}", response_model=WorkspaceWithUsers)
async def remove_workspace_member(
    workspace_id: str,
    user_id: str,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceWithUsers:
    """
    Remove a user from a workspace.
    
    Args:
        workspace_id: The workspace ID
        user_id: The user ID to remove
        current_user: The current authenticated user
        workspace_service: The workspace service instance
        
    Returns:
        The updated workspace with its members
        
    Raises:
        HTTPException: If the operation fails
    """
    try:
        workspace = await workspace_service.remove_user_from_workspace(
            workspace_id=workspace_id,
            user_id=user_id,
            current_user_id=current_user.id,
        )
        return workspace
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace or user not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to remove this member",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )