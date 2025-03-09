"""Workspace repository for accessing workspace data."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import uuid
import json

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database.models import Workspace as WorkspaceDB
from app.models.domain.workspace import Workspace
from app.database.repositories.base import Repository

class WorkspaceRepository(Repository[Workspace, WorkspaceDB]):
    """Repository for workspace data access"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID"""
        workspace_db = self.db.query(WorkspaceDB).filter(WorkspaceDB.id == workspace_id).first()
        if not workspace_db:
            return None
        return self._to_domain(workspace_db)
        
    def get_user_workspaces(self, user_id: str, limit: Optional[int] = None) -> List[Workspace]:
        """Get all workspaces for a user"""
        query = self.db.query(WorkspaceDB).filter(
            WorkspaceDB.user_id == user_id
        ).order_by(desc(WorkspaceDB.created_at_utc))
        
        if limit:
            query = query.limit(limit)
            
        workspaces_db = query.all()
        return [self._to_domain(workspace) for workspace in workspaces_db]
        
    def create_workspace(self, user_id: str, name: str, description: Optional[str] = None) -> Workspace:
        """Create a new workspace"""
        now = datetime.now(timezone.utc)
        
        # Extract metadata if provided
        metadata = {}
        if description:
            metadata["description"] = description
            
        # Convert metadata to JSON
        metadata_json = json.dumps(metadata) if metadata else "{}"
        
        workspace_db = WorkspaceDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            created_at_utc=now,
            updated_at_utc=now,
            meta_data=metadata_json
        )
        
        self.db.add(workspace_db)
        self.db.commit()
        self.db.refresh(workspace_db)
        
        return self._to_domain(workspace_db)
        
    def update_workspace(self, workspace_id: str, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[Workspace]:
        """Update a workspace"""
        workspace_db = self.db.query(WorkspaceDB).filter(WorkspaceDB.id == workspace_id).first()
        if not workspace_db:
            return None
            
        now = datetime.now(timezone.utc)
        workspace_db.updated_at_utc = now
        
        if name:
            workspace_db.name = name
            
        if metadata is not None:
            workspace_db.meta_data = json.dumps(metadata)
            
        self.db.commit()
        self.db.refresh(workspace_db)
        
        return self._to_domain(workspace_db)
        
    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace"""
        workspace_db = self.db.query(WorkspaceDB).filter(WorkspaceDB.id == workspace_id).first()
        if not workspace_db:
            return False
            
        self.db.delete(workspace_db)
        self.db.commit()
        
        return True
        
    def _to_domain(self, db_model: WorkspaceDB) -> Workspace:
        """Convert DB model to domain model"""
        # Parse metadata
        try:
            metadata = json.loads(db_model.meta_data) if db_model.meta_data else {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}
            
        return Workspace(
            id=db_model.id,
            user_id=db_model.user_id,
            name=db_model.name,
            created_at=db_model.created_at_utc,
            updated_at=db_model.updated_at_utc,
            last_active_at=db_model.updated_at_utc,  # Use updated_at as last_active_at
            metadata=metadata,
            config={}  # Default empty config
        )
        
    def _to_db_model(self, domain_model: Workspace) -> WorkspaceDB:
        """Convert domain model to DB model"""
        # This is used for update operations
        metadata_json = json.dumps(domain_model.metadata) if domain_model.metadata else "{}"
        
        return WorkspaceDB(
            id=domain_model.id,
            user_id=domain_model.user_id,
            name=domain_model.name,
            created_at_utc=domain_model.created_at,
            updated_at_utc=domain_model.updated_at or datetime.now(timezone.utc),
            meta_data=metadata_json
        )

# Factory function for dependency injection
def get_workspace_repository(db_session: Session) -> WorkspaceRepository:
    """Get a workspace repository instance"""
    return WorkspaceRepository(db_session)