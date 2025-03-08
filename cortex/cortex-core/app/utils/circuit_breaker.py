"""
Circuit Breaker pattern implementation for Cortex Core services
"""

import time
from typing import Any, Callable, TypeVar, Awaitable
from enum import Enum
from app.exceptions import ServiceError
from app.utils.logger import logger

T = TypeVar('T')

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Failed state, blocking requests
    HALF_OPEN = "HALF_OPEN" # Testing recovery


class CircuitBreaker:
    """
    Implementation of the Circuit Breaker pattern for service resilience

    The Circuit Breaker pattern prevents cascading failures by protecting
    services from repeated calls to failing operations.

    Usage:
        # Create a circuit breaker
        cb = CircuitBreaker("service_name")

        # Use it to protect an async operation
        try:
            result = await cb.execute(some_async_function, arg1, arg2)
            # Handle success
        except ServiceError:
            # Handle service unavailability
        except Exception as e:
            # Handle other errors
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0
    ):
        """
        Initialize a new circuit breaker

        Args:
            name: Name of the protected service
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Time in seconds before trying to recover
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = CircuitState.CLOSED

    async def execute(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """
        Execute a function with circuit breaker protection

        Args:
            func: Async function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function

        Raises:
            ServiceError: If the circuit is open
            Exception: Any exception raised by the function
        """
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info(f"Circuit {self.name} transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
            else:
                raise ServiceError(
                    detail=f"Service {self.name} is unavailable",
                    code="SERVICE_UNAVAILABLE",
                    status_code=503
                )

        try:
            # Execute the function
            result = await func(*args, **kwargs)

            # Success, reset if in half-open state
            if self.state == CircuitState.HALF_OPEN:
                self.failure_count = 0
                self.state = CircuitState.CLOSED
                logger.info(f"Circuit {self.name} recovered")

            return result

        except Exception as e:
            # Track failure
            self.failure_count += 1
            self.last_failure_time = time.time()

            # Trip the circuit if threshold reached
            if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name} tripped open after {self.failure_count} failures")

            # Re-raise the exception
            raise