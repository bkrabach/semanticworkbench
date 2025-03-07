"""
Domain Expert Manager Component

This module implements the domain expert interface that manages specialized expert
systems, task delegation, and result tracking. It serves as a bridge between the core
application and specialized AI capabilities.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from app.interfaces.domain_expert_interface import (
    DomainExpertInterface,
    ExpertInfo,
    PriorityLevel,
    Task,
    TaskConstraints,
    TaskResult,
    TaskState,
    TaskStatus,
)
from app.utils.logger import get_contextual_logger

# Configure logger
logger = get_contextual_logger("components.domain_expert_manager")


class TaskEntry(BaseModel):
    """Internal task tracking structure"""

    task: Task
    expert_type: str
    status: TaskStatus
    result: Optional[TaskResult] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DomainExpertManager(DomainExpertInterface):
    """
    Domain Expert Manager that implements the domain expert interface

    This class manages task delegation to specialized domain experts,
    tracks task status, and provides results.
    """

    def __init__(self):
        """Initialize the domain expert manager"""
        self.tasks: Dict[str, TaskEntry] = {}
        self.experts: Dict[str, ExpertInfo] = {}

        # Register built-in experts
        self._register_builtin_experts()

        logger.info("Domain expert manager initialized")

    def _register_builtin_experts(self) -> None:
        """Register built-in domain experts"""
        # Add Code Assistant expert
        code_expert = ExpertInfo(
            type="code",
            name="Code Assistant",
            capabilities=["code_generation", "code_review", "debugging"],
            description="Specialized expert for software development tasks",
        )
        self.experts[code_expert.type] = code_expert

        # Add Research Assistant expert
        research_expert = ExpertInfo(
            type="research",
            name="Research Assistant",
            capabilities=["information_retrieval", "synthesis", "summarization"],
            description="Expert for research and information analysis tasks",
        )
        self.experts[research_expert.type] = research_expert

        # Add Text Generation expert
        text_expert = ExpertInfo(
            type="text",
            name="Text Generation Expert",
            capabilities=["content_creation", "editing", "translation"],
            description="Expert for text and content generation tasks",
        )
        self.experts[text_expert.type] = text_expert

        logger.info(f"Registered {len(self.experts)} built-in domain experts")

    async def list_experts(self) -> List[ExpertInfo]:
        """
        List available domain experts

        Returns:
            List of available expert information
        """
        return list(self.experts.values())

    async def delegate_task(self, expert_type: str, task: Task) -> str:
        """
        Delegate a task to a domain expert

        Args:
            expert_type: Type of expert to delegate to
            task: Task to delegate

        Returns:
            Task ID for tracking

        Raises:
            ValueError: If expert type is invalid or unavailable
        """
        try:
            logger.info(f"Delegating task to {expert_type} expert: {task.id}")

            # Check if expert exists
            if expert_type not in self.experts:
                raise ValueError(f"Expert type '{expert_type}' is not available")

            # Ensure task has an ID
            if not task.id:
                task.id = str(uuid.uuid4())

            # Create initial task status
            task_status = TaskStatus(
                task_id=task.id,
                state=TaskState.PENDING,
                progress=0.0,
                message="Task queued",
            )

            # Create task entry
            task_entry = TaskEntry(
                task=task, expert_type=expert_type, status=task_status
            )

            # Store task entry
            self.tasks[task.id] = task_entry

            # Start background task execution
            asyncio.create_task(self._execute_task(task.id))

            logger.info(f"Task {task.id} delegated to {expert_type} expert")
            return task.id

        except Exception as e:
            logger.error(
                f"Failed to delegate task to {expert_type} expert", exc_info=True
            )
            raise ValueError(f"Failed to delegate task: {str(e)}")

    async def check_task_status(self, task_id: str) -> TaskStatus:
        """
        Check the status of a delegated task

        Args:
            task_id: ID of the task to check

        Returns:
            Task status information

        Raises:
            ValueError: If task ID is invalid
        """
        try:
            task_entry = self.tasks.get(task_id)
            if not task_entry:
                raise ValueError(f"Task {task_id} not found")

            return task_entry.status

        except Exception as e:
            logger.error(f"Failed to check task status: {task_id}", exc_info=True)
            raise ValueError(f"Failed to check task status: {str(e)}")

    async def get_task_result(self, task_id: str) -> TaskResult:
        """
        Get the result of a completed task

        Args:
            task_id: ID of the completed task

        Returns:
            Task execution result

        Raises:
            ValueError: If task ID is invalid
            RuntimeError: If task is not completed
        """
        try:
            task_entry = self.tasks.get(task_id)
            if not task_entry:
                raise ValueError(f"Task {task_id} not found")

            if task_entry.status.state not in [TaskState.COMPLETED, TaskState.FAILED]:
                raise RuntimeError(
                    f"Task {task_id} is not completed (current state: {task_entry.status.state})"
                )

            if not task_entry.result:
                # Create a default result if not available (this shouldn't happen in normal operation)
                task_entry.result = TaskResult(
                    task_id=task_id,
                    success=task_entry.status.state == TaskState.COMPLETED,
                    error="No result available"
                    if task_entry.status.state == TaskState.FAILED
                    else None,
                )

            return task_entry.result

        except Exception as e:
            logger.error(f"Failed to get task result: {task_id}", exc_info=True)
            raise ValueError(f"Failed to get task result: {str(e)}")

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if task was cancelled, False otherwise

        Raises:
            ValueError: If task ID is invalid
        """
        try:
            task_entry = self.tasks.get(task_id)
            if not task_entry:
                raise ValueError(f"Task {task_id} not found")

            # Can only cancel pending or running tasks
            if task_entry.status.state not in [TaskState.PENDING, TaskState.RUNNING]:
                return False

            # Update status
            task_entry.status.state = TaskState.CANCELLED
            task_entry.status.message = "Task cancelled by user"
            task_entry.status.updated_at = datetime.utcnow()
            task_entry.updated_at = datetime.utcnow()

            # Create result for cancelled task
            task_entry.result = TaskResult(
                task_id=task_id, success=False, error="Task was cancelled"
            )

            logger.info(f"Task {task_id} cancelled")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel task: {task_id}", exc_info=True)
            raise ValueError(f"Failed to cancel task: {str(e)}")

    async def _execute_task(self, task_id: str) -> None:
        """
        Execute a task in the background

        Args:
            task_id: ID of the task to execute
        """
        try:
            task_entry = self.tasks.get(task_id)
            if not task_entry:
                logger.error(f"Task {task_id} not found for execution")
                return

            # Update status to running
            task_entry.status.state = TaskState.RUNNING
            task_entry.status.message = "Task processing"
            task_entry.status.updated_at = datetime.utcnow()
            task_entry.updated_at = datetime.utcnow()

            logger.info(f"Started execution of task {task_id}")

            # Get expert type and task
            expert_type = task_entry.expert_type
            task = task_entry.task

            # Simulate task execution (in a real system, this would delegate to actual experts)
            # The execution time is based on the task priority
            if task.constraints and task.constraints.priority_level:
                if task.constraints.priority_level == PriorityLevel.HIGH:
                    delay = 2
                elif task.constraints.priority_level == PriorityLevel.LOW:
                    delay = 6
                else:
                    delay = 4
            else:
                delay = 4

            # Report progress
            for i in range(1, 5):
                if task_entry.status.state == TaskState.CANCELLED:
                    logger.info(f"Task {task_id} was cancelled during execution")
                    return

                progress = i * 0.25
                task_entry.status.progress = progress
                task_entry.status.message = (
                    f"Processing ({int(progress * 100)}% complete)"
                )
                task_entry.status.updated_at = datetime.utcnow()
                task_entry.updated_at = datetime.utcnow()

                await asyncio.sleep(delay / 4)  # Split the delay into segments

            # Complete the task
            if task_entry.status.state != TaskState.CANCELLED:
                # Create a simulated result (in a real system, this would be the actual expert output)
                result = {
                    "expert_type": expert_type,
                    "task_type": task.type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "response": f"Processed {task.type} task with {expert_type} expert",
                }

                if task.content:
                    # Include a reference to the content in the result
                    content_preview = str(task.content)
                    if len(content_preview) > 100:
                        content_preview = content_preview[:100] + "..."
                    result["content_summary"] = content_preview

                # Update task status
                task_entry.status.state = TaskState.COMPLETED
                task_entry.status.progress = 1.0
                task_entry.status.message = "Task completed successfully"
                task_entry.status.updated_at = datetime.utcnow()
                task_entry.updated_at = datetime.utcnow()

                # Create task result
                task_entry.result = TaskResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    metrics={
                        "execution_time_seconds": delay,
                        "expert_type": expert_type,
                    },
                )

                logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Error executing task {task_id}", exc_info=True)

            # Update task status on error
            try:
                if task_id in self.tasks:
                    task_entry = self.tasks[task_id]

                    task_entry.status.state = TaskState.FAILED
                    task_entry.status.message = f"Task failed: {str(e)}"
                    task_entry.status.updated_at = datetime.utcnow()
                    task_entry.updated_at = datetime.utcnow()

                    task_entry.result = TaskResult(
                        task_id=task_id, success=False, error=str(e)
                    )

                    logger.info(f"Task {task_id} marked as failed")
            except Exception as inner_e:
                logger.error(
                    f"Failed to update task status for {task_id}", exc_info=True
                )


# Global instance (will be initialized later)
domain_expert_manager = None


def initialize_domain_expert_interface() -> DomainExpertInterface:
    """
    Initialize the global domain expert manager instance

    Returns:
        The initialized domain expert manager
    """
    global domain_expert_manager
    if domain_expert_manager is None:
        domain_expert_manager = DomainExpertManager()
    return domain_expert_manager


# Export public symbols
__all__ = [
    "DomainExpertManager",
    "initialize_domain_expert_interface",
    "domain_expert_manager",
]
