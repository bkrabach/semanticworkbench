from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, field_serializer, Field
import uuid
from datetime import datetime, timezone
import json
from pydantic.json import pydantic_encoder
from app.database.connection import get_db
from app.database.models import User, Workspace
from app.api.auth import get_current_user
from app.utils.logger import logger
from app.api.sse import send_event_to_user
from app.utils.json_helpers import DateTimeEncoder

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
    created_at_utc: datetime
    last_active_at_utc: datetime
    config: Dict[str, Any] = Field(default_factory=dict)
    meta_data: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "from_attributes": True,
        "json_encoders": {
            datetime: lambda dt: dt.isoformat()
        }
    }


@router.get("/workspaces", response_model=Dict[str, List[WorkspaceResponse]])
async def list_workspaces(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List workspaces for the current user"""
    workspaces = db.query(Workspace).filter(
        Workspace.user_id == user.id
    ).order_by(
        Workspace.last_active_at_utc.desc()
    ).all()
    
    # Process each workspace to handle the JSON fields
    processed_workspaces = []
    for workspace in workspaces:
        # Parse JSON strings to dictionaries safely
        config_str = "{}"
        meta_data_str = "{}"
        
        if workspace.config is not None:
            config_str = str(workspace.config)
            if not config_str:
                config_str = "{}"
                
        if workspace.meta_data is not None:
            meta_data_str = str(workspace.meta_data)
            if not meta_data_str:
                meta_data_str = "{}"
        
        try:
            config = json.loads(config_str)
        except json.JSONDecodeError:
            config = {}
            
        try:
            meta_data = json.loads(meta_data_str)
        except json.JSONDecodeError:
            meta_data = {}
            
        workspace_dict = {
            "id": str(workspace.id),
            "name": str(workspace.name),
            "created_at_utc": workspace.created_at_utc,
            "last_active_at_utc": workspace.last_active_at_utc,
            "config": config,
            "meta_data": meta_data
        }
        processed_workspaces.append(WorkspaceResponse.model_validate(workspace_dict))
    
    return {"workspaces": processed_workspaces}


@router.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(
    workspace: WorkspaceCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new workspace"""
    now = datetime.now(timezone.utc)
    config = workspace.config or {}

    # Convert config to JSON string
    config_json = json.dumps(config)

    new_workspace = Workspace(
        id=str(uuid.uuid4()),
        user_id=str(user.id),
        name=workspace.name,
        created_at_utc=now,
        last_active_at_utc=now,
        config=config_json,
        meta_data="{}"
    )

    db.add(new_workspace)
    db.commit()
    db.refresh(new_workspace)

    # Send event to user
    background_tasks.add_task(
        send_event_to_user,
        str(user.id),
        "workspace_created",
        {
            "id": str(new_workspace.id),
            "name": str(new_workspace.name),
            "created_at_utc": new_workspace.created_at_utc.isoformat()
        }
    )

    # Parse JSON strings and return validated model
    config_str = "{}"
    meta_data_str = "{}"
    
    if new_workspace.config is not None:
        config_str = str(new_workspace.config)
        if not config_str:
            config_str = "{}"
            
    if new_workspace.meta_data is not None:
        meta_data_str = str(new_workspace.meta_data)
        if not meta_data_str:
            meta_data_str = "{}"
    
    try:
        config = json.loads(config_str)
    except json.JSONDecodeError:
        config = {}
        
    try:
        meta_data = json.loads(meta_data_str)
    except json.JSONDecodeError:
        meta_data = {}
    
    return WorkspaceResponse.model_validate({
        "id": str(new_workspace.id),
        "name": str(new_workspace.name),
        "created_at_utc": new_workspace.created_at_utc,
        "last_active_at_utc": new_workspace.last_active_at_utc,
        "config": config,
        "meta_data": meta_data
    })
