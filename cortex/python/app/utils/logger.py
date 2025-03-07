"""
Logging Utilities

This module provides logging utilities for structured logging with context
tracking, rotating file handlers, and performance measurements.
"""

import asyncio
import functools
import logging
import os
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from app.config import settings

# Type variables for decorators
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")

# Context variables for tracking request context
_request_id = None
_user_id = None
_context_extra = {}


def configure_logging():
    """
    Configure global logging settings

    This function sets up formatters, handlers, and logger levels.
    It's called automatically when this module is imported.
    """
    # Define formatters
    simple_formatter = logging.Formatter(settings.log_format)

    json_format = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"'
    json_format += ', "request_id": "%(request_id)s", "user_id": "%(user_id)s"'
    json_format += ', "path": "%(pathname)s", "lineno": %(lineno)d'

    # Add any extra context fields
    json_format += ', "extra": %(extra)s}'

    json_formatter = logging.Formatter(json_format)

    # Create console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(
        json_formatter
        if settings.environment.value != "development"
        else simple_formatter
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.value)
    root_logger.addHandler(console)

    # Create file handlers if enabled
    if settings.enable_file_logging:
        log_dir = Path(settings.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create application log file handler
        app_log_file = log_dir / f"cortex-{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = TimedRotatingFileHandler(
            filename=app_log_file,
            when="midnight",
            backupCount=30,
        )
        file_handler.setFormatter(json_formatter)
        file_handler.setLevel(settings.log_level.value)

        # Create error log file handler
        error_log_file = (
            log_dir / f"cortex-error-{datetime.now().strftime('%Y-%m-%d')}.log"
        )
        error_file_handler = TimedRotatingFileHandler(
            filename=error_log_file,
            when="midnight",
            backupCount=30,
        )
        error_file_handler.setFormatter(json_formatter)
        error_file_handler.setLevel(logging.ERROR)

        # Create request log file handler
        request_log_file = (
            log_dir / f"cortex-requests-{datetime.now().strftime('%Y-%m-%d')}.log"
        )
        request_file_handler = TimedRotatingFileHandler(
            filename=request_log_file,
            when="midnight",
            backupCount=30,
        )
        request_file_handler.setFormatter(json_formatter)

        # Add handlers to root logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(error_file_handler)

        # Create and configure request logger
        request_logger = logging.getLogger("request")
        request_logger.propagate = False
        request_logger.addHandler(console)
        request_logger.addHandler(request_file_handler)

    # Set specific loggers to different levels if needed
    if settings.is_development:
        # Set third-party loggers to less verbose levels in development
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("aiosqlite").setLevel(logging.WARNING)

        # But allow our app loggers to be debug level
        logging.getLogger("app").setLevel(logging.DEBUG)


class ContextAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds context information to log records

    This adapter injects request_id, user_id, and other context
    variables into log records.
    """

    def process(self, msg, kwargs):
        """
        Process log record to add context

        Args:
            msg: Log message
            kwargs: Keyword arguments for logging

        Returns:
            Tuple of (message, kwargs) with added context
        """
        # Initialize extra dict if not present
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        # Add request and user IDs
        kwargs["extra"]["request_id"] = _request_id or "unknown"
        kwargs["extra"]["user_id"] = _user_id or "unknown"

        # Add any additional context
        kwargs["extra"]["extra"] = _context_extra or {}

        # Add additional context keys at the top level too
        for key, value in _context_extra.items():
            kwargs["extra"][key] = value

        return msg, kwargs


def get_contextual_logger(name: str) -> logging.Logger:
    """
    Get a logger with context adapter

    Args:
        name: Logger name

    Returns:
        Logger with context adapter
    """
    logger = logging.getLogger(name)
    return ContextAdapter(logger, {})


def set_request_context(
    request_id: Optional[str] = None, user_id: Optional[str] = None
) -> None:
    """
    Set context for the current request

    Args:
        request_id: Optional request ID (generated if not provided)
        user_id: Optional user ID
    """
    global _request_id, _user_id
    _request_id = request_id or str(uuid.uuid4())
    _user_id = user_id


def set_context_value(key: str, value: Any) -> None:
    """
    Set a value in the logging context

    Args:
        key: Context key
        value: Context value
    """
    global _context_extra
    _context_extra[key] = value


def clear_context() -> None:
    """Clear all context values"""
    global _request_id, _user_id, _context_extra
    _request_id = None
    _user_id = None
    _context_extra = {}


@contextmanager
def log_context(
    logger: Optional[logging.Logger] = None,
    level: int = logging.DEBUG,
    **context_values,
):
    """
    Context manager for temporarily setting logging context

    Args:
        logger: Optional logger to log to
        level: Log level
        context_values: Context values to set
    """
    # Save original context
    original_context = _context_extra.copy()

    # Set new context values
    for key, value in context_values.items():
        set_context_value(key, value)

    try:
        if logger:
            logger.log(level, f"Entering context: {context_values}")

        yield

    finally:
        if logger:
            logger.log(level, f"Exiting context: {context_values}")

        # Restore original context
        global _context_extra
        _context_extra = original_context


def log_execution_time(func: F) -> F:
    """
    Decorator to log function execution time

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_contextual_logger(func.__module__)
        start_time = time.time()

        logger.debug(f"Executing {func.__name__}")

        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(
                f"{func.__name__} failed after {execution_time:.3f}s: {str(e)}"
            )
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_contextual_logger(func.__module__)
        start_time = time.time()

        logger.debug(f"Executing {func.__name__}")

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(
                f"{func.__name__} failed after {execution_time:.3f}s: {str(e)}"
            )
            raise

    # Return the appropriate wrapper based on whether the function is async or not
    if asyncio.iscoroutinefunction(func):
        return cast(F, async_wrapper)
    else:
        return cast(F, sync_wrapper)
