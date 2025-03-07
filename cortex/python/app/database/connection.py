"""
Database Connection Module

This module provides a SQLAlchemy async database connection and session management.
It includes connection pooling, transaction handling, and a FastAPI dependency
for database sessions.
"""

import asyncio
import functools
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Optional, TypeVar, cast

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from app.config import settings
from app.utils.logger import get_contextual_logger, log_context_execution_time

# Configure logger
logger = get_contextual_logger("database.connection")

# Type variable for function decorators
F = TypeVar("F", bound=Callable[..., Any])

# Create engine with appropriate settings
async_engine_args = {
    "echo": settings.sql_echo,
    "pool_size": settings.db_pool_size,
    "max_overflow": settings.db_max_overflow,
    "pool_timeout": settings.db_pool_timeout,
    "pool_recycle": settings.db_pool_recycle,
}

# Use NullPool for SQLite to avoid cross-thread issues
if settings.database_url.startswith("sqlite"):
    # Override pooling for SQLite
    async_engine_args = {
        "echo": settings.sql_echo,
        "poolclass": NullPool,
    }

# Create async engine
async_engine = create_async_engine(
    settings.database_url,
    **async_engine_args,
)

# Create sessionmaker
async_session_factory = async_sessionmaker(
    async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session context manager

    Use as a context manager to get a database session
    that's automatically closed when the context exits.

    Example:
        ```python
        async with get_db() as db:
            result = await db.execute(query)
        ```

    Yields:
        AsyncSession: Database session
    """
    session = async_session_factory()
    try:
        with log_context_execution_time("database_session"):
            yield session
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {str(e)}", exc_info=True)
        raise
    finally:
        await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency for FastAPI

    This dependency injects a database session into route handlers.
    It automatically handles session lifecycle and error handling.

    Example:
        ```python
        @app.get("/items/{item_id}")
        async def get_item(item_id: int, db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Item).where(Item.id == item_id))
            item = result.scalar_one_or_none()
            return item
        ```

    Yields:
        AsyncSession: Database session
    """
    async with get_db() as session:
        yield session


def transactional(func: F) -> F:
    """
    Decorator to wrap a function in a database transaction

    This decorator provides a database session to the decorated function
    and automatically handles commits and rollbacks. If the function
    already has a db parameter, it will reuse it instead of creating a new session.

    Args:
        func: The function to decorate

    Returns:
        Decorated function with transaction handling

    Example:
        ```python
        @transactional
        async def create_user(name: str, db: Optional[AsyncSession] = None) -> User:
            user = User(name=name)
            db.add(user)
            return user
        ```
    """

    @functools.wraps(func)
    async def wrapped_function(*args, **kwargs):
        # Check if db session already provided
        db = kwargs.get("db")
        external_session = db is not None

        if not external_session:
            # Create new session if not provided
            db = async_session_factory()
            kwargs["db"] = db

        try:
            # Execute function
            result = await func(*args, **kwargs)

            # Commit if we created the session
            if not external_session:
                await db.commit()

            return result

        except Exception as e:
            # Rollback if we created the session
            if not external_session:
                await db.rollback()

            # Re-raise the exception
            raise

        finally:
            # Close if we created the session
            if not external_session:
                await db.close()

    return cast(F, wrapped_function)


async def check_database_connection() -> bool:
    """
    Check database connection health

    Returns:
        True if database is accessible, False otherwise
    """
    try:
        # Try to open a session and execute a simple query
        async with get_db() as db:
            await db.execute("SELECT 1")

        return True

    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False


async def init_database() -> None:
    """
    Initialize database connection

    This function tests the database connection and logs the result.
    """
    logger.info(f"Initializing database connection to {settings.database_url}")

    # Check connection
    is_connected = await check_database_connection()

    if is_connected:
        logger.info("Database connection successful")
    else:
        logger.error("Failed to connect to database")


async def close_database() -> None:
    """
    Close database connection pool

    This function should be called when the application is shutting down.
    """
    logger.info("Closing database connection pool")

    # Dispose engine to close all connections
    await async_engine.dispose()


# Export public symbols
__all__ = [
    "get_db",
    "get_db_session",
    "transactional",
    "check_database_connection",
    "init_database",
    "close_database",
]
