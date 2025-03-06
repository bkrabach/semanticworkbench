import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from cortex_core.models.schemas import (
    User, Conversation, Message, MessageRole, Session as UserSession
)
from cortex_core.core.auth import user_session_manager
from cortex_core.core.conversation import conversation_handler
from cortex_core.core.sse import sse_manager
from cortex_core.db.database import get_db

# Setup logging
logger = logging.getLogger(__name__)

# Setup security
security = HTTPBearer()

# Create router
router = APIRouter()

# Helper functions
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current user from the session token.
    
    Args:
        credentials: The HTTP Authorization header containing the bearer token
        db: Database session
        
    Returns:
        The current user
    
    Raises:
        HTTPException: If the token is invalid or the user is not found
    """
    try:
        token = credentials.credentials
        user = await user_session_manager.validate_session(token, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user
    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

# Authentication and Session Management
@router.post("/validate-session", response_model=Dict[str, Any])
async def validate_session(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Validate a session token from the authentication system.
    
    Args:
        authorization: The Authorization header containing the bearer token
        db: Database session
        
    Returns:
        A dictionary with the validation result and user info
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return {"valid": False, "user": None}
        
        token = authorization.replace("Bearer ", "")
        user = await user_session_manager.validate_session(token, db)
        
        if user:
            return {
                "valid": True,
                "user": {
                    "id": user.id,
                    "name": user.name
                }
            }
        else:
            return {"valid": False, "user": None}
    except Exception as e:
        logger.error(f"Error validating session: {str(e)}")
        return {"valid": False, "user": None, "error": str(e)}

# Conversations
@router.get("/conversations", response_model=Dict[str, Any])
async def list_conversations(
    limit: int = 10,
    offset: int = 0,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all conversations for the current user.
    
    Args:
        limit: Maximum number of conversations to return
        offset: Number of conversations to skip (for pagination)
        sort_by: Field to sort by (created_at, updated_at, title)
        sort_order: Sort order (asc, desc)
        current_user: The current authenticated user
        db: Database session
        
    Returns:
        A dictionary with the list of conversations and total count
    """
    from cortex_core.db.models import Conversation as DBConversation
    from sqlalchemy import desc, asc
    
    try:
        # Validate sort parameters
        if sort_by not in ["created_at", "updated_at", "title"]:
            sort_by = "updated_at"
            
        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "desc"
        
        # Create the base query
        query = db.query(DBConversation).filter(DBConversation.user_id == current_user.id)
        
        # Get total count
        total = query.count()
        
        # Add sorting
        sort_column = getattr(DBConversation, sort_by)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Add pagination
        conversations_db = query.offset(offset).limit(limit).all()
        
        # Convert to Pydantic models
        conversations = []
        for conv in conversations_db:
            conversations.append(Conversation(
                id=conv.id,
                user_id=conv.user_id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                metadata=conv.metadata,
                messages=[]  # Don't include messages in the list view
            ))
        
        return {
            "conversations": conversations,
            "total": total
        }
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing conversations: {str(e)}"
        )

@router.post("/conversations", response_model=Dict[str, Any])
async def create_conversation(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new conversation.
    
    Args:
        data: Request data containing the conversation title
        current_user: The current authenticated user
        db: Database session
        
    Returns:
        A dictionary with the created conversation
    """
    try:
        title = data.get("title", "New Conversation")
        
        # Create the conversation
        conversation = await conversation_handler.create_conversation(
            user_id=current_user.id,
            title=title,
            db=db
        )
        
        return {
            "conversation": conversation
        }
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating conversation: {str(e)}"
        )

@router.get("/conversations/{conversation_id}", response_model=Dict[str, Any])
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific conversation.
    
    Args:
        conversation_id: The ID of the conversation to get
        current_user: The current authenticated user
        db: Database session
        
    Returns:
        A dictionary with the conversation details
    """
    try:
        # Get the conversation
        conversation = await conversation_handler.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id,
            db=db
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        return {
            "conversation": conversation
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting conversation: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}", response_model=Dict[str, Any])
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation.
    
    Args:
        conversation_id: The ID of the conversation to delete
        current_user: The current authenticated user
        db: Database session
        
    Returns:
        A dictionary with the success status
    """
    from cortex_core.db.models import Conversation as DBConversation
    
    try:
        # Verify the conversation exists and belongs to the user
        db_conversation = db.query(DBConversation).filter(
            DBConversation.id == conversation_id,
            DBConversation.user_id == current_user.id
        ).first()
        
        if not db_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # Delete the conversation
        db.delete(db_conversation)
        db.commit()
        
        return {
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting conversation: {str(e)}"
        )

# Messages
@router.get("/conversations/{conversation_id}/messages", response_model=Dict[str, Any])
async def list_messages(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
    before_id: Optional[str] = None,
    after_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all messages in a conversation.
    
    Args:
        conversation_id: The ID of the conversation
        limit: Maximum number of messages to return
        offset: Number of messages to skip (for pagination)
        before_id: Return messages before this ID
        after_id: Return messages after this ID
        current_user: The current authenticated user
        db: Database session
        
    Returns:
        A dictionary with the list of messages and total count
    """
    from cortex_core.db.models import Message as DBMessage, Conversation as DBConversation
    from sqlalchemy import desc, asc
    
    try:
        # Verify the conversation exists and belongs to the user
        db_conversation = db.query(DBConversation).filter(
            DBConversation.id == conversation_id,
            DBConversation.user_id == current_user.id
        ).first()
        
        if not db_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # Create the base query
        query = db.query(DBMessage).filter(DBMessage.conversation_id == conversation_id)
        
        # Apply ID filtering if provided
        if before_id:
            # Get the reference message
            ref_message = db.query(DBMessage).filter(DBMessage.id == before_id).first()
            if ref_message:
                query = query.filter(DBMessage.created_at < ref_message.created_at)
        
        if after_id:
            # Get the reference message
            ref_message = db.query(DBMessage).filter(DBMessage.id == after_id).first()
            if ref_message:
                query = query.filter(DBMessage.created_at > ref_message.created_at)
        
        # Get total count
        total = query.count()
        
        # Get messages with pagination
        messages_db = query.order_by(asc(DBMessage.created_at)).offset(offset).limit(limit).all()
        
        # Convert to Pydantic models
        messages = []
        for msg in messages_db:
            messages.append(Message(
                id=msg.id,
                conversation_id=msg.conversation_id,
                role=MessageRole(msg.role),
                content=msg.content,
                created_at=msg.created_at,
                metadata=msg.metadata,
                tool_calls=msg.tool_calls,
                is_complete=msg.is_complete
            ))
        
        return {
            "messages": messages,
            "total": total
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing messages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing messages: {str(e)}"
        )

@router.post("/conversations/{conversation_id}/messages", response_model=Dict[str, Any])
async def create_message(
    conversation_id: str,
    data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a new message to a conversation.
    
    Args:
        conversation_id: The ID of the conversation
        data: Request data containing the message content and role
        background_tasks: FastAPI background tasks
        current_user: The current authenticated user
        db: Database session
        
    Returns:
        A dictionary with the created message
    """
    from cortex_core.db.models import Conversation as DBConversation
    
    try:
        # Verify the conversation exists and belongs to the user
        db_conversation = db.query(DBConversation).filter(
            DBConversation.id == conversation_id,
            DBConversation.user_id == current_user.id
        ).first()
        
        if not db_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # Create the message
        content = data.get("content", "")
        role = data.get("role", "user")
        
        # Validate role
        if role != "user":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only user messages can be created through the API"
            )
        
        # Create message object
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content,
            metadata={
                "user_id": current_user.id
            }
        )
        
        # Process the message in the background
        def process_message():
            try:
                # Get a new database session for the background task
                from cortex_core.db.database import SessionLocal
                db_bg = SessionLocal()
                try:
                    # Process the message with the conversation handler
                    conversation_handler.process_user_message(message, db_bg)
                finally:
                    db_bg.close()
            except Exception as e:
                logger.error(f"Error processing message in background: {str(e)}")
        
        # Add background task
        background_tasks.add_task(process_message)
        
        return {
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating message: {str(e)}"
        )

# Server-Sent Events (SSE)
@router.get("/sse/conversations/{conversation_id}")
async def sse_endpoint(
    request: Request,
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Establish an SSE connection for updates to a specific conversation.
    
    Args:
        request: The FastAPI request
        conversation_id: The ID of the conversation
        current_user: The current authenticated user
        db: Database session
        
    Returns:
        An EventSourceResponse for the SSE stream
    """
    from cortex_core.db.models import Conversation as DBConversation
    
    try:
        # Verify the conversation exists and belongs to the user
        db_conversation = db.query(DBConversation).filter(
            DBConversation.id == conversation_id,
            DBConversation.user_id == current_user.id
        ).first()
        
        if not db_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # Create SSE connection
        connection_data = {
            "user_id": current_user.id,
            "conversation_id": conversation_id
        }
        connection_result = await sse_manager.create_connection(connection_data)
        
        # Return SSE response
        return await sse_manager.sse_endpoint(request, connection_result["connection_id"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error establishing SSE connection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error establishing SSE connection: {str(e)}"
        )