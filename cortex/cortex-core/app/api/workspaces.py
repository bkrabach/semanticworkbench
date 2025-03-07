from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import uuid
from datetime import datetime
import json

from app.database.connection import get_db
from app.database.models import User, Workspace
from app.components.security_manager import get_current_user
from app.utils.logger import logger
from app.api.sse import send_event_to_user

router = APIRouter()

# Request and response models


class WorkspaceCreate(BaseModel):
    """Workspace creation model"""
    name: str
    config: Optional[Dict[str, Any]] = None


class WorkspaceUpdate(BaseModel):
    """Workspace update model"""
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class WorkspaceResponse(BaseModel):
    """Workspace response model"""
    id: str
    name: str
    created_at: datetime
    last_active_at: datetime
    config: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None


@router.get("/workspaces", response_model=Dict[str, List[WorkspaceResponse]])
async def list_workspaces(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List workspaces for the current user"""
    workspaces = db.query(Workspace).filter(
        Workspace.user_id == user.id
    ).order_by(
        Workspace.last_active_at.desc()
    ).all()

    return {"workspaces": workspaces}


@router.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(
    workspace: WorkspaceCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new workspace"""
    now = datetime.utcnow()
    config = workspace.config or {}

    # Convert config to JSON string
    config_json = json.dumps(config)

    new_workspace = Workspace(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=workspace.name,
        created_at=now,
        last_active_at=now,
        config=config_json,
        meta_data="{}"
    )

    db.add(new_workspace)
    db.commit()
    db.refresh(new_workspace)

    # Send event to user
    background_tasks.add_task(
        send_event_to_user,
        user.id,
        "workspace_created",
        {
            "id": new_workspace.id,
            "name": new_workspace.name,
            "created_at": new_workspace.created_at.isoformat()
        }
    )

    return new_workspace
