"""
Memory API Routes

This module provides endpoints for creating, reading, updating, and deleting
memory items, as well as searching and querying the memory store.
"""

import uuid
from typing import Dict, List, Optional, Any, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.security_manager import get_current_active_user
from app.components.whiteboard_memory import whiteboard_memory
from app.database.connection import get_db_session
from app.database.models import User, MemoryItemType
from app.schemas.base import (
    BaseResponse,
    CreatedResponse,
    PaginatedResponse,
    PaginationParams,
    MemoryItemCreate,
    MemoryItemRead,
    MemoryItemUpdate,
)
from app.utils.logger import logger

# Create router
router = APIRouter(
    prefix="/memory",
    tags=["memory"],
)


@router.post(
    "/items",
    response_model=CreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create memory item",
    description="Create a new memory item in the specified workspace",
)
async def create_memory_item(
    item_data: MemoryItemCreate,
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new memory item

    Creates a new memory item in the specified workspace with the current user
    as the owner.
    """
    try:
        # Convert string type to enum
        try:
            item_type = MemoryItemType(item_data.type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid memory item type: {item_data.type}. Valid types are: {', '.join([t.value for t in MemoryItemType])}",
            )

        # Create memory item
        item = await whiteboard_memory.create_item(
            workspace_id=workspace_id,
            owner_id=current_user.id,
            item_type=item_type,
            content=item_data.content,
            metadata=item_data.metadata,
            parent_id=item_data.parent_id,
            ttl=None,  # Can add TTL parameter to request if needed
        )

        logger.info(
            f"Created memory item {item['id']} of type {item['type']} in workspace {workspace_id}"
        )

        return CreatedResponse(
            id=uuid.UUID(item["id"]) if isinstance(item["id"], str) else item["id"],
            message="Memory item created successfully",
        )

    except Exception as e:
        logger.error(f"Error creating memory item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating memory item: {str(e)}",
        )


@router.get(
    "/items/{item_id}",
    response_model=MemoryItemRead,
    summary="Get memory item",
    description="Get a specific memory item by ID",
)
async def get_memory_item(
    item_id: uuid.UUID = Path(..., description="Memory item ID"),
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a memory item

    Retrieves a specific memory item by ID from the specified workspace.
    """
    item = await whiteboard_memory.get_item(
        workspace_id=workspace_id,
        item_id=item_id,
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory item {item_id} not found",
        )

    # Convert from whiteboard memory dict to Pydantic model
    return MemoryItemRead(
        id=uuid.UUID(item["id"]) if isinstance(item["id"], str) else item["id"],
        type=item["type"],
        content=item["content"],
        metadata=item["metadata"],
        workspace_id=uuid.UUID(item["workspace_id"])
        if isinstance(item["workspace_id"], str)
        else item["workspace_id"],
        owner_id=uuid.UUID(item["owner_id"])
        if isinstance(item["owner_id"], str)
        else item["owner_id"],
        parent_id=uuid.UUID(item["parent_id"])
        if item.get("parent_id") and not isinstance(item["parent_id"], type(None))
        else None,
        created_at=item["created_at"],
        updated_at=item["updated_at"],
        expires_at=item.get("expires_at"),
    )


@router.put(
    "/items/{item_id}",
    response_model=MemoryItemRead,
    summary="Update memory item",
    description="Update a specific memory item by ID",
)
async def update_memory_item(
    item_update: MemoryItemUpdate,
    item_id: uuid.UUID = Path(..., description="Memory item ID"),
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a memory item

    Updates a specific memory item by ID in the specified workspace.
    """
    # Check if item exists
    existing_item = await whiteboard_memory.get_item(
        workspace_id=workspace_id,
        item_id=item_id,
    )

    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory item {item_id} not found",
        )

    # Check ownership or admin status
    item_owner_id = existing_item["owner_id"]
    if isinstance(item_owner_id, str):
        item_owner_id = uuid.UUID(item_owner_id)

    if item_owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this memory item",
        )

    # Update item
    updated_item = await whiteboard_memory.update_item(
        workspace_id=workspace_id,
        item_id=item_id,
        content=item_update.content,
        metadata=item_update.metadata,
        ttl=None,  # Can add TTL parameter to request if needed
    )

    if not updated_item:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update memory item",
        )

    logger.info(f"Updated memory item {item_id} in workspace {workspace_id}")

    # Convert from whiteboard memory dict to Pydantic model
    return MemoryItemRead(
        id=uuid.UUID(updated_item["id"])
        if isinstance(updated_item["id"], str)
        else updated_item["id"],
        type=updated_item["type"],
        content=updated_item["content"],
        metadata=updated_item["metadata"],
        workspace_id=uuid.UUID(updated_item["workspace_id"])
        if isinstance(updated_item["workspace_id"], str)
        else updated_item["workspace_id"],
        owner_id=uuid.UUID(updated_item["owner_id"])
        if isinstance(updated_item["owner_id"], str)
        else updated_item["owner_id"],
        parent_id=uuid.UUID(updated_item["parent_id"])
        if updated_item.get("parent_id")
        and not isinstance(updated_item["parent_id"], type(None))
        else None,
        created_at=updated_item["created_at"],
        updated_at=updated_item["updated_at"],
        expires_at=updated_item.get("expires_at"),
    )


@router.delete(
    "/items/{item_id}",
    response_model=BaseResponse,
    summary="Delete memory item",
    description="Delete a specific memory item by ID",
)
async def delete_memory_item(
    item_id: uuid.UUID = Path(..., description="Memory item ID"),
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a memory item

    Deletes a specific memory item by ID from the specified workspace.
    """
    # Check if item exists
    existing_item = await whiteboard_memory.get_item(
        workspace_id=workspace_id,
        item_id=item_id,
    )

    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory item {item_id} not found",
        )

    # Check ownership or admin status
    item_owner_id = existing_item["owner_id"]
    if isinstance(item_owner_id, str):
        item_owner_id = uuid.UUID(item_owner_id)

    if item_owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this memory item",
        )

    # Delete item
    success = await whiteboard_memory.delete_item(
        workspace_id=workspace_id,
        item_id=item_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete memory item",
        )

    logger.info(f"Deleted memory item {item_id} from workspace {workspace_id}")

    return BaseResponse(message=f"Memory item {item_id} deleted successfully")


@router.get(
    "/items",
    response_model=PaginatedResponse[MemoryItemRead],
    summary="List memory items",
    description="List memory items in a workspace with optional filtering",
)
async def list_memory_items(
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    pagination: PaginationParams = Depends(),
    item_types: Optional[List[str]] = Query(None, description="Filter by item types"),
    owner_id: Optional[uuid.UUID] = Query(None, description="Filter by owner ID"),
    parent_id: Optional[uuid.UUID] = Query(None, description="Filter by parent ID"),
    current_user: User = Depends(get_current_active_user),
):
    """
    List memory items

    Lists memory items in the specified workspace with optional filtering.
    """
    try:
        # Convert string types to enums if provided
        enum_types = None
        if item_types:
            try:
                enum_types = [MemoryItemType(t) for t in item_types]
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid memory item type: {str(e)}. Valid types are: {', '.join([t.value for t in MemoryItemType])}",
                )

        # Count total items for pagination
        total_items = await whiteboard_memory.count_items(
            workspace_id=workspace_id,
            item_types=enum_types,
            owner_id=owner_id,
            parent_id=parent_id,
        )

        # Get items with pagination
        items = await whiteboard_memory.list_items(
            workspace_id=workspace_id,
            item_types=enum_types,
            owner_id=owner_id,
            parent_id=parent_id,
            limit=pagination.page_size,
            offset=pagination.skip,
        )

        # Calculate total pages
        total_pages = (total_items + pagination.page_size - 1) // pagination.page_size

        # Convert items to Pydantic models
        item_models = []
        for item in items:
            item_models.append(
                MemoryItemRead(
                    id=uuid.UUID(item["id"])
                    if isinstance(item["id"], str)
                    else item["id"],
                    type=item["type"],
                    content=item["content"],
                    metadata=item["metadata"],
                    workspace_id=uuid.UUID(item["workspace_id"])
                    if isinstance(item["workspace_id"], str)
                    else item["workspace_id"],
                    owner_id=uuid.UUID(item["owner_id"])
                    if isinstance(item["owner_id"], str)
                    else item["owner_id"],
                    parent_id=uuid.UUID(item["parent_id"])
                    if item.get("parent_id")
                    and not isinstance(item["parent_id"], type(None))
                    else None,
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                    expires_at=item.get("expires_at"),
                )
            )

        # Create paginated response
        return PaginatedResponse(
            data=item_models,
            page_info={
                "page": pagination.page,
                "page_size": pagination.page_size,
                "total_pages": total_pages,
                "total_items": total_items,
                "has_next": pagination.page < total_pages,
                "has_prev": pagination.page > 1,
            },
            message=f"Retrieved {len(item_models)} of {total_items} memory items",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing memory items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing memory items: {str(e)}",
        )


@router.get(
    "/search",
    response_model=List[MemoryItemRead],
    summary="Search memory items",
    description="Search for memory items in a workspace",
)
async def search_memory_items(
    query: str = Query(..., description="Search query"),
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    item_types: Optional[List[str]] = Query(None, description="Filter by item types"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Search memory items

    Searches for memory items in the specified workspace that match the query.
    """
    try:
        # Convert string types to enums if provided
        enum_types = None
        if item_types:
            try:
                enum_types = [MemoryItemType(t) for t in item_types]
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid memory item type: {str(e)}. Valid types are: {', '.join([t.value for t in MemoryItemType])}",
                )

        # Search for items
        items = await whiteboard_memory.search(
            workspace_id=workspace_id,
            query=query,
            item_types=enum_types,
            limit=limit,
        )

        # Convert items to Pydantic models
        item_models = []
        for item in items:
            item_models.append(
                MemoryItemRead(
                    id=uuid.UUID(item["id"])
                    if isinstance(item["id"], str)
                    else item["id"],
                    type=item["type"],
                    content=item["content"],
                    metadata=item["metadata"],
                    workspace_id=uuid.UUID(item["workspace_id"])
                    if isinstance(item["workspace_id"], str)
                    else item["workspace_id"],
                    owner_id=uuid.UUID(item["owner_id"])
                    if isinstance(item["owner_id"], str)
                    else item["owner_id"],
                    parent_id=uuid.UUID(item["parent_id"])
                    if item.get("parent_id")
                    and not isinstance(item["parent_id"], type(None))
                    else None,
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                    expires_at=item.get("expires_at"),
                )
            )

        return item_models

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching memory items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching memory items: {str(e)}",
        )


@router.get(
    "/items/{item_id}/children",
    response_model=List[MemoryItemRead],
    summary="Get child memory items",
    description="Get child memory items for a parent item",
)
async def get_child_items(
    item_id: uuid.UUID = Path(..., description="Parent memory item ID"),
    workspace_id: uuid.UUID = Query(..., description="Workspace ID"),
    item_types: Optional[List[str]] = Query(None, description="Filter by item types"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get child memory items

    Retrieves child memory items for a specific parent item.
    """
    try:
        # Check if parent item exists
        parent_item = await whiteboard_memory.get_item(
            workspace_id=workspace_id,
            item_id=item_id,
        )

        if not parent_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent memory item {item_id} not found",
            )

        # Convert string types to enums if provided
        enum_types = None
        if item_types:
            try:
                enum_types = [MemoryItemType(t) for t in item_types]
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid memory item type: {str(e)}. Valid types are: {', '.join([t.value for t in MemoryItemType])}",
                )

        # Get child items
        items = await whiteboard_memory.get_child_items(
            workspace_id=workspace_id,
            parent_id=item_id,
            item_types=enum_types,
        )

        # Convert items to Pydantic models
        item_models = []
        for item in items:
            item_models.append(
                MemoryItemRead(
                    id=uuid.UUID(item["id"])
                    if isinstance(item["id"], str)
                    else item["id"],
                    type=item["type"],
                    content=item["content"],
                    metadata=item["metadata"],
                    workspace_id=uuid.UUID(item["workspace_id"])
                    if isinstance(item["workspace_id"], str)
                    else item["workspace_id"],
                    owner_id=uuid.UUID(item["owner_id"])
                    if isinstance(item["owner_id"], str)
                    else item["owner_id"],
                    parent_id=uuid.UUID(item["parent_id"])
                    if item.get("parent_id")
                    and not isinstance(item["parent_id"], type(None))
                    else None,
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                    expires_at=item.get("expires_at"),
                )
            )

        return item_models

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting child memory items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting child memory items: {str(e)}",
        )
