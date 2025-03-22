"""
Tool implementation module.

This module provides implementations of various tools that can be used by the ResponseHandler.
Tools are defined using Pydantic models for input and output schemas to ensure
type safety and proper documentation through the Pydantic AI framework.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from .response_handler import register_tool, tool_registry
from ..database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


# ============== Pydantic Models for Tool Inputs and Outputs ==============

class ConversationSummaryInput(BaseModel):
    """Input parameters for the conversation summary tool."""
    conversation_id: str = Field(..., description="The ID of the conversation to summarize")
    user_id: str = Field(..., description="The ID of the user requesting the summary")


class ConversationSummaryOutput(BaseModel):
    """Output schema for the conversation summary tool."""
    summary: str = Field(..., description="Brief summary of the conversation")
    message_count: int = Field(..., description="Number of messages in the conversation")
    topic: str = Field(..., description="The topic of the conversation")
    participant_count: int = Field(..., description="Number of participants in the conversation")


class TimeInput(BaseModel):
    """Input parameters for the current time tool."""
    timezone: Optional[str] = Field(None, description="Optional timezone (not implemented)")


class TimeOutput(BaseModel):
    """Output schema for the current time tool."""
    iso_format: str = Field(..., description="ISO formatted date and time")
    date: str = Field(..., description="Formatted date (YYYY-MM-DD)")
    time: str = Field(..., description="Formatted time (HH:MM:SS)")
    year: str = Field(..., description="Current year")
    month: str = Field(..., description="Current month name")
    day: str = Field(..., description="Day of month")
    day_of_week: str = Field(..., description="Current day of week")


class UserInfoInput(BaseModel):
    """Input parameters for the user info tool."""
    user_id: str = Field(..., description="The ID of the user to get information about")


class UserInfoOutput(BaseModel):
    """Output schema for the user info tool."""
    user_id: str = Field(..., description="The user's ID")
    name: str = Field(..., description="The user's name")
    email: Optional[str] = Field(None, description="The user's email address")
    status: str = Field(..., description="The user's status")


class WorkspaceListInput(BaseModel):
    """Input parameters for the list workspaces tool."""
    user_id: str = Field(..., description="The ID of the user to list workspaces for")
    limit: int = Field(10, description="Maximum number of workspaces to return")


class WorkspaceItem(BaseModel):
    """Individual workspace information."""
    id: str = Field(..., description="The workspace ID")
    name: str = Field(..., description="The workspace name")
    description: Optional[str] = Field(None, description="The workspace description")


class WorkspaceListOutput(BaseModel):
    """Output schema for the list workspaces tool."""
    count: int = Field(..., description="Number of workspaces returned")
    workspaces: List[WorkspaceItem] = Field(..., description="List of workspace details")


# ============== Tool Implementations ==============

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
        messages = await message_repo.list_by_conversation(conversation_id, limit=50)
        
        conversation_repo = uow.repositories.get_conversation_repository()
        conversation = await conversation_repo.get_by_id(conversation_id)
        
        if not conversation:
            return ConversationSummaryOutput(
                summary="Conversation not found",
                message_count=0,
                topic="unknown",
                participant_count=0
            ).model_dump()
        
        return ConversationSummaryOutput(
            summary=f"Conversation with topic: {conversation.topic}",
            message_count=len(messages),
            topic=conversation.topic,
            participant_count=len(conversation.participant_ids)
        ).model_dump()


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
    
    return TimeOutput(
        iso_format=now.isoformat(),
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S"),
        year=now.strftime("%Y"),
        month=now.strftime("%B"),
        day=now.strftime("%d"),
        day_of_week=now.strftime("%A")
    ).model_dump()


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
            return UserInfoOutput(
                user_id=user_id,
                name="Unknown User",
                email=None,
                status="not_found"
            ).model_dump()
        
        return UserInfoOutput(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            status="active"
        ).model_dump()


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
        workspaces = await workspace_repo.list_by_owner(user_id, limit=limit)
        
        workspace_items = []
        for workspace in workspaces:
            workspace_items.append(WorkspaceItem(
                id=workspace.id,
                name=workspace.name,
                description=workspace.description,
            ))
        
        return WorkspaceListOutput(
            count=len(workspace_items),
            workspaces=workspace_items
        ).model_dump()