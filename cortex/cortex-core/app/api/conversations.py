"""
Conversation API endpoints for the Cortex application.

This module handles conversation CRUD operations and message creation.
"""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.exceptions import PermissionDeniedError, ResourceNotFoundError
from app.models.api.request.conversation import ConversationCreate, ConversationUpdate, MessageCreate
from app.models.api.response.conversation import ConversationInfo, MessageInfo
from app.models.api.response.user import UserInfo
from app.services.conversation_service import ConversationService

router = APIRouter(tags=["conversations"])


async def get_conversation_service() -> ConversationService:
    """
    Dependency to get a ConversationService instance.
    
    Returns:
        A ConversationService instance
    """
    db = await get_db()
    return ConversationService(db=db)


@router.post("/workspaces/{workspace_id}/conversations", response_model=ConversationInfo, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    workspace_id: str,
    conversation_data: ConversationCreate,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationInfo:
    """
    Create a new conversation in a workspace.
    
    Args:
        workspace_id: The workspace ID
        conversation_data: The conversation creation data
        current_user: The current authenticated user
        conversation_service: The conversation service instance
        
    Returns:
        The newly created conversation
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        conversation = await conversation_service.create_conversation(
            workspace_id=workspace_id,
            conversation_data=conversation_data,
            user_id=current_user.id,
        )
        return conversation
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create conversations in this workspace",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/workspaces/{workspace_id}/conversations", response_model=List[ConversationInfo])
async def list_conversations(
    workspace_id: str,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
    skip: int = 0,
    limit: int = 100,
) -> List[ConversationInfo]:
    """
    List all conversations in a workspace.
    
    Args:
        workspace_id: The workspace ID
        current_user: The current authenticated user
        conversation_service: The conversation service instance
        skip: Number of results to skip
        limit: Maximum number of results to return
        
    Returns:
        List of conversations
        
    Raises:
        HTTPException: If listing fails
    """
    try:
        conversations = await conversation_service.get_workspace_conversations(
            workspace_id=workspace_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )
        return conversations
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view conversations in this workspace",
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationInfo)
async def get_conversation(
    conversation_id: str,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationInfo:
    """
    Get a specific conversation by ID.
    
    Args:
        conversation_id: The conversation ID
        current_user: The current authenticated user
        conversation_service: The conversation service instance
        
    Returns:
        The conversation
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        conversation = await conversation_service.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
        return conversation
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this conversation",
        )


@router.put("/conversations/{conversation_id}", response_model=ConversationInfo)
async def update_conversation(
    conversation_id: str,
    conversation_data: ConversationUpdate,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationInfo:
    """
    Update a conversation.
    
    Args:
        conversation_id: The conversation ID
        conversation_data: The conversation update data
        current_user: The current authenticated user
        conversation_service: The conversation service instance
        
    Returns:
        The updated conversation
        
    Raises:
        HTTPException: If update fails
    """
    try:
        conversation = await conversation_service.update_conversation(
            conversation_id=conversation_id,
            conversation_data=conversation_data,
            user_id=current_user.id,
        )
        return conversation
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this conversation",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> None:
    """
    Delete a conversation.
    
    Args:
        conversation_id: The conversation ID
        current_user: The current authenticated user
        conversation_service: The conversation service instance
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        await conversation_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this conversation",
        )


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageInfo])
async def list_messages(
    conversation_id: str,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
    skip: int = 0,
    limit: int = 100,
) -> List[MessageInfo]:
    """
    List all messages in a conversation.
    
    Args:
        conversation_id: The conversation ID
        current_user: The current authenticated user
        conversation_service: The conversation service instance
        skip: Number of results to skip
        limit: Maximum number of results to return
        
    Returns:
        List of messages
        
    Raises:
        HTTPException: If listing fails
    """
    try:
        messages = await conversation_service.get_conversation_messages(
            conversation_id=conversation_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )
        return messages
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view messages in this conversation",
        )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageInfo, status_code=status.HTTP_201_CREATED)
async def create_message(
    conversation_id: str,
    message_data: MessageCreate,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> MessageInfo:
    """
    Create a new message in a conversation.
    
    Args:
        conversation_id: The conversation ID
        message_data: The message creation data
        current_user: The current authenticated user
        conversation_service: The conversation service instance
        
    Returns:
        The newly created message
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        message = await conversation_service.create_message(
            conversation_id=conversation_id,
            message_data=message_data,
            user_id=current_user.id,
        )
        return message
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create messages in this conversation",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )