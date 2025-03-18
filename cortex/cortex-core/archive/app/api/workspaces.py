"""
Workspace API endpoints for the Cortex Core application.

This module implements workspace-related API endpoints using the domain-driven architecture.
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.domain.user import User
from app.models.api.request.workspace import WorkspaceCreate, WorkspaceUpdate
from app.models.api.response.workspace import WorkspaceResponse, WorkspaceListResponse
from app.database.repositories.workspace_repository import get_workspace_repository
from app.services.workspace_service import get_workspace_service, WorkspaceService
from app.api.auth import get_current_user
from app.components.event_system import get_event_system
from app.services.sse_service import get_sse_service

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> WorkspaceService:
    """Get workspace service with dependencies"""
    # Create repository inside function to avoid FastAPI dependency issues
    repo = get_workspace_repository(db)
    
    # We need to cast the event_system to the concrete type expected by the service
    from app.components.event_system import EventSystem
    event_system = get_event_system()
    
    # Cast to the concrete type for type checking
    return get_workspace_service(
        db, 
        repo, 
        event_system if isinstance(event_system, EventSystem) else None
    )


@router.get("/workspaces", response_model=WorkspaceListResponse)
async def list_workspaces(
    user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_service)
) -> WorkspaceListResponse:
    """List workspaces for the current user"""
    # Get workspaces using service
    workspaces = service.get_user_workspaces(user.id)
    
    # Transform domain models to API response models
    workspace_responses = [
        WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            last_active_at=workspace.last_active_at,
            config=workspace.config,
            metadata=workspace.metadata
        )
        for workspace in workspaces
    ]
    
    return WorkspaceListResponse(workspaces=workspace_responses)


@router.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(
    request: WorkspaceCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_service)
) -> WorkspaceResponse:
    """Create a new workspace"""
    # Create workspace using service layer
    workspace = await service.create_workspace(
        user_id=user.id,
        name=request.name,
        description=request.description
    )
    
    # Send additional SSE notification to user
    # This is separate from the event that the service publishes
    background_tasks.add_task(
        get_sse_service().connection_manager.send_event,
        "user",
        user.id,
        "workspace_created",
        {
            "id": workspace.id,
            "name": workspace.name,
            "created_at": workspace.created_at.isoformat()
        }
    )
    
    # Transform domain model to response model
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        last_active_at=workspace.last_active_at,
        config=workspace.config,
        metadata=workspace.metadata
    )


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_service)
) -> WorkspaceResponse:
    """Get a specific workspace by ID"""
    # Get workspace using service
    workspace = service.get_workspace(workspace_id)
    
    # Check if workspace exists
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Check if user has access to this workspace
    if workspace.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied to this workspace")
    
    # Transform domain model to response model
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        last_active_at=workspace.last_active_at,
        config=workspace.config,
        metadata=workspace.metadata
    )


@router.put("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    request: WorkspaceUpdate,
    user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_service)
) -> WorkspaceResponse:
    """Update a workspace"""
    # Check workspace ownership first
    workspace = service.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if workspace.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied to this workspace")
    
    # Update the workspace
    updated_workspace = await service.update_workspace(
        workspace_id=workspace_id,
        name=request.name,
        metadata=request.metadata
    )
    
    if not updated_workspace:
        raise HTTPException(status_code=404, detail="Failed to update workspace")
    
    # Transform domain model to response model
    return WorkspaceResponse(
        id=updated_workspace.id,
        name=updated_workspace.name,
        created_at=updated_workspace.created_at,
        updated_at=updated_workspace.updated_at,
        last_active_at=updated_workspace.last_active_at,
        config=updated_workspace.config,
        metadata=updated_workspace.metadata
    )


@router.delete("/workspaces/{workspace_id}", response_model=dict)
async def delete_workspace(
    workspace_id: str,
    user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_service)
) -> dict:
    """Delete a workspace"""
    # Check workspace ownership first
    workspace = service.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if workspace.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied to this workspace")
    
    # Delete the workspace
    success = await service.delete_workspace(workspace_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete workspace")
    
    return {"success": True, "message": "Workspace deleted successfully"}
