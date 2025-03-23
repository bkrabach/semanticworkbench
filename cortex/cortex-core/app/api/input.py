import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from ..core.event_bus import event_bus
from ..core.exceptions import AccessDeniedError, EntityNotFoundError, EventBusException
from ..core.response_handler import response_handler
from ..database.unit_of_work import UnitOfWork
from ..models.api.request import InputRequest
from ..models.api.response import ErrorResponse, InputResponse
from ..utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["input"])


@router.post(
    "/input",
    response_model=InputResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def receive_input(
    request: InputRequest, 
    background_tasks: BackgroundTasks, 
    current_user: dict = Depends(get_current_user)
) -> InputResponse:
    """
    Receive input from a client and process it with ResponseHandler.

    Args:
        request: The input request
        background_tasks: FastAPI background tasks
        current_user: The authenticated user

    Returns:
        Status response
    """
    user_id = current_user["user_id"]
    logger.info(f"Received input from user {user_id}")

    try:
        async with UnitOfWork.for_transaction() as uow:
            # Verify conversation exists
            conversation_repo = uow.repositories.get_conversation_repository()
            conversation = await conversation_repo.get_by_id(request.conversation_id)

            if not conversation:
                raise EntityNotFoundError(
                    message=f"Conversation not found: {request.conversation_id}",
                    entity_type="Conversation",
                    entity_id=request.conversation_id,
                )

            # Check if user is a participant
            workspace_repo = uow.repositories.get_workspace_repository()
            workspace = await workspace_repo.get_by_id(conversation.workspace_id)

            if workspace is None:
                raise EntityNotFoundError(f"Workspace not found with ID: {conversation.workspace_id}")

            if workspace.owner_id != user_id and user_id not in conversation.participant_ids:
                raise AccessDeniedError(
                    message="You do not have access to this conversation",
                    entity_type="Conversation",
                    entity_id=request.conversation_id,
                    user_id=user_id,
                )

            # Create a timestamp
            timestamp = datetime.now().isoformat()

            # Create event with user ID using unified message format
            event = {
                "type": "message",
                "message_type": "user",
                "data": {
                    "content": request.content,
                    "conversation_id": request.conversation_id,
                    "timestamp": timestamp,
                    # Note: message_id will be added by the response handler
                    "sender": {
                        "id": user_id,
                        "name": current_user.get("name", "User"),
                        "role": "user"
                    }
                },
                "timestamp": timestamp,
                "metadata": request.metadata or {},
            }

            # Commit the database transaction
            await uow.commit()

            # Publish event to event bus after successful db commit
            try:
                await event_bus.publish(event)
            except Exception as e:
                logger.error(f"Failed to publish event: {e}")
                raise EventBusException(
                    message="Failed to publish input event", details={"conversation_id": request.conversation_id}
                )

            # Create a background task to handle the response generation
            # This allows us to return a response immediately while processing continues
            background_tasks.add_task(
                response_handler.handle_message,
                user_id=user_id,
                conversation_id=request.conversation_id,
                message_content=request.content,
                metadata=request.metadata,
                streaming=request.streaming,
            )

            # Return response
            return InputResponse(
                status="received",
                data={
                    "content": request.content,
                    "conversation_id": request.conversation_id,
                    "timestamp": timestamp,
                    "metadata": request.metadata,
                },
            )

    except (EntityNotFoundError, AccessDeniedError) as e:
        # These are already properly typed exceptions
        if isinstance(e, EntityNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
            error_code = "resource_not_found"
        else:  # AccessDeniedError
            status_code = status.HTTP_403_FORBIDDEN
            error_code = "permission_denied"

        raise HTTPException(
            status_code=status_code,
            detail={
                "error": {"code": error_code, "message": str(e), "details": e.details if hasattr(e, "details") else {}}
            },
        )

    except EventBusException:
        # Pass through event bus exceptions
        raise

    except Exception as e:
        # Log and convert other exceptions
        logger.error(f"Error processing input: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "internal_error",
                    "message": "An error occurred while processing the input",
                    "details": {"error": str(e)},
                }
            },
        )
