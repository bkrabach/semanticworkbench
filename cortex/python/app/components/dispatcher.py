"""
Dispatcher Component

This module implements a dispatcher system that routes messages and events to appropriate
handlers. It serves as a central coordination point for component communication.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from app.components.context_manager import ContextManager
from app.components.session_manager import SessionManager
from app.interfaces.domain_expert_interface import DomainExpertInterface
from app.utils.logger import get_contextual_logger

# Configure logger
logger = get_contextual_logger("components.dispatcher")

# Define handler type - async function that takes message and context
MessageHandler = Callable[[Dict[str, Any], Dict[str, Any]], Any]


class Dispatcher:
    """
    Dispatcher for routing messages and events

    This class manages message routing, handler registration, and coordination
    between different components of the system.
    """

    def __init__(
        self,
        context_manager: ContextManager,
        session_manager: SessionManager,
        domain_expert_interface: DomainExpertInterface,
    ):
        """
        Initialize the dispatcher

        Args:
            context_manager: The context manager instance
            session_manager: The session manager instance
            domain_expert_interface: The domain expert interface
        """
        self.context_manager = context_manager
        self.session_manager = session_manager
        self.domain_expert_interface = domain_expert_interface

        # Message handlers
        self.handlers: Dict[str, List[MessageHandler]] = {}

        # Active processors
        self.active_processors: Set[str] = set()

        logger.info("Dispatcher initialized")

    def register_handler(self, message_type: str, handler: MessageHandler) -> None:
        """
        Register a handler for a specific message type

        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        if message_type not in self.handlers:
            self.handlers[message_type] = []

        self.handlers[message_type].append(handler)
        logger.info(f"Registered handler for message type: {message_type}")

    async def dispatch(
        self,
        message_type: str,
        message: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[uuid.UUID] = None,
        workspace_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Dispatch a message to registered handlers

        Args:
            message_type: Type of message
            message: Message content
            context: Optional context information
            session_id: Optional session ID
            workspace_id: Optional workspace ID

        Returns:
            List of handler responses

        Raises:
            ValueError: If message type has no registered handlers
        """
        try:
            logger.info(f"Dispatching message: {message_type}")

            # Check if there are handlers for this message type
            if message_type not in self.handlers:
                logger.warning(
                    f"No handlers registered for message type: {message_type}"
                )
                return []

            # Initialize context if not provided
            if context is None:
                context = {}

            # Add processing metadata to context
            context.update(
                {
                    "message_type": message_type,
                    "dispatch_time": datetime.utcnow().isoformat(),
                    "dispatcher_id": id(self),
                }
            )

            # Add session info if provided
            if session_id:
                context["session_id"] = session_id

                # Get session info from session manager if available
                try:
                    session_info = await self.session_manager.get_session(session_id)
                    if session_info:
                        context["session_info"] = session_info.dict()
                except Exception as e:
                    logger.warning(f"Failed to get session info: {str(e)}")

            # Add workspace info if provided
            if workspace_id:
                context["workspace_id"] = workspace_id

                # Get context for this workspace if both session and workspace IDs are provided
                if session_id:
                    try:
                        workspace_context = await self.context_manager.get_context(
                            session_id=session_id,
                            workspace_id=workspace_id,
                        )
                        context["workspace_context"] = workspace_context.dict()
                    except Exception as e:
                        logger.warning(f"Failed to get workspace context: {str(e)}")

            # Process with all registered handlers
            results = []
            for handler in self.handlers[message_type]:
                try:
                    result = await handler(message, context)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(
                        f"Handler error for message type {message_type}: {str(e)}",
                        exc_info=True,
                    )

            logger.info(
                f"Message {message_type} processed by {len(self.handlers[message_type])} handlers"
            )
            return results

        except Exception as e:
            logger.error(
                f"Error dispatching message {message_type}: {str(e)}", exc_info=True
            )
            raise

    async def dispatch_with_expert(
        self,
        expert_type: str,
        task_type: str,
        content: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Dispatch a task to an expert via the domain expert interface

        Args:
            expert_type: Type of expert to use
            task_type: Type of task to perform
            content: Task content
            context: Optional context information

        Returns:
            Task ID for tracking

        Raises:
            ValueError: If expert delegation fails
        """
        try:
            logger.info(f"Dispatching task to expert: {expert_type}")

            # Create a task object
            from app.interfaces.domain_expert_interface import Task

            task = Task(
                type=task_type,
                content=content,
                context=context or {},
            )

            # Delegate task to expert
            task_id = await self.domain_expert_interface.delegate_task(
                expert_type=expert_type,
                task=task,
            )

            logger.info(f"Task delegated to expert {expert_type}, task ID: {task_id}")
            return task_id

        except Exception as e:
            logger.error(
                f"Error dispatching to expert {expert_type}: {str(e)}", exc_info=True
            )
            raise ValueError(f"Failed to dispatch to expert: {str(e)}")


# Global instance (will be initialized with required components later)
dispatcher = None


def initialize_dispatcher(
    context_manager: ContextManager,
    session_manager: SessionManager,
    domain_expert_interface: DomainExpertInterface,
) -> Dispatcher:
    """
    Initialize the global dispatcher instance

    Args:
        context_manager: The context manager to use
        session_manager: The session manager to use
        domain_expert_interface: The domain expert interface to use

    Returns:
        The initialized dispatcher
    """
    global dispatcher
    if dispatcher is None:
        dispatcher = Dispatcher(
            context_manager=context_manager,
            session_manager=session_manager,
            domain_expert_interface=domain_expert_interface,
        )
    return dispatcher


# Export public symbols
__all__ = [
    "Dispatcher",
    "MessageHandler",
    "dispatcher",
    "initialize_dispatcher",
]
