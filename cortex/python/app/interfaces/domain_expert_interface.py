"""
Domain Expert Interface

This module defines the abstract interface for domain expert components.
It specifies methods for delegating tasks to specialized expert systems
and monitoring their execution.
"""

import abc
import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, TypeVar

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    """Task execution state enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PriorityLevel(str, Enum):
    """Task priority level enumeration"""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TaskConstraints(BaseModel):
    """Task execution constraints"""

    deadline: Optional[datetime] = None
    max_tokens: Optional[int] = None
    priority_level: PriorityLevel = Field(default=PriorityLevel.NORMAL)
    max_retries: Optional[int] = Field(default=3)


class Task(BaseModel):
    """Task model for expert delegation"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    content: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    constraints: Optional[TaskConstraints] = Field(default_factory=TaskConstraints)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskStatus(BaseModel):
    """Task status information"""

    task_id: str
    state: TaskState
    progress: Optional[float] = None  # 0.0 to 1.0
    message: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskResult(BaseModel):
    """Task execution result"""

    task_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class ExpertInfo(BaseModel):
    """Information about an available domain expert"""

    type: str
    name: str
    capabilities: List[str]
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DomainExpertInterface(abc.ABC):
    """
    Abstract interface for domain expert interactions

    This interface defines the contract for interacting with domain experts,
    delegating tasks, and retrieving results.
    """

    @abc.abstractmethod
    async def list_experts(self) -> List[ExpertInfo]:
        """
        List available domain experts

        Returns:
            List of available expert information
        """
        pass

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
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
        pass


# Export public symbols
__all__ = [
    "TaskState",
    "PriorityLevel",
    "TaskConstraints",
    "Task",
    "TaskStatus",
    "TaskResult",
    "ExpertInfo",
    "DomainExpertInterface",
]
