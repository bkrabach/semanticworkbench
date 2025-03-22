"""
Tool implementation module.

This module provides implementations of various tools that can be used by the ResponseHandler.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .response_handler import register_tool
from ..database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


@register_tool("get_conversation_summary")
async def get_conversation_summary(conversation_id: str, user_id: str) -> Dict[str, Any]:
    """
    Generate a summary of the conversation.
    
    Args:
        conversation_id: The ID of the conversation
        user_id: The ID of the user
        
    Returns:
        A dictionary with the conversation summary
    """
    logger.info(f"Getting conversation summary for {conversation_id}")
    
    async with UnitOfWork.for_transaction() as uow:
        message_repo = uow.repositories.get_message_repository()
        messages = await message_repo.get_by_conversation_id(conversation_id, limit=50)
        
        conversation_repo = uow.repositories.get_conversation_repository()
        conversation = await conversation_repo.get_by_id(conversation_id)
        
        if not conversation:
            return {
                "summary": "Conversation not found",
                "message_count": 0,
                "topic": "unknown"
            }
        
        return {
            "summary": f"Conversation with topic: {conversation.topic}",
            "message_count": len(messages),
            "topic": conversation.topic,
            "participant_count": len(conversation.participant_ids)
        }


@register_tool("get_current_time")
async def get_current_time(timezone: Optional[str] = None) -> Dict[str, str]:
    """
    Get the current date and time.
    
    Args:
        timezone: Optional timezone (not implemented)
        
    Returns:
        A dictionary with the current date and time information
    """
    now = datetime.now()
    
    return {
        "iso_format": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "year": now.strftime("%Y"),
        "month": now.strftime("%B"),
        "day": now.strftime("%d"),
        "day_of_week": now.strftime("%A")
    }


@register_tool("get_user_info")
async def get_user_info(user_id: str) -> Dict[str, Any]:
    """
    Get information about a user.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        A dictionary with user information
    """
    logger.info(f"Getting user info for user {user_id}")
    
    async with UnitOfWork.for_transaction() as uow:
        user_repo = uow.repositories.get_user_repository()
        user = await user_repo.get_by_id(user_id)
        
        if not user:
            return {
                "user_id": user_id,
                "name": "Unknown User",
                "status": "not_found"
            }
        
        return {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "status": "active"
        }


@register_tool("list_workspaces")
async def list_workspaces(user_id: str, limit: int = 10) -> Dict[str, Any]:
    """
    List workspaces for a user.
    
    Args:
        user_id: The ID of the user
        limit: Maximum number of workspaces to return
        
    Returns:
        A dictionary with workspace information
    """
    logger.info(f"Listing workspaces for user {user_id}")
    
    async with UnitOfWork.for_transaction() as uow:
        workspace_repo = uow.repositories.get_workspace_repository()
        workspaces = await workspace_repo.get_by_owner_id(user_id, limit=limit)
        
        workspace_list = []
        for workspace in workspaces:
            workspace_list.append({
                "id": workspace.id,
                "name": workspace.name,
                "description": workspace.description,
            })
        
        return {
            "count": len(workspace_list),
            "workspaces": workspace_list
        }