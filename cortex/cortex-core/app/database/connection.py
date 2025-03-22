import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Import aiosqlite directly as recommended by SQLAlchemy for async SQLite
# The import is needed even if not directly referenced in the code
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Use environment variable with default fallback for database URL
# Ensure we're always using the async driver by enforcing the sqlite+aiosqlite:// prefix
db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///cortex.db")
if db_url.startswith("sqlite://"):
    # Convert non-async SQLite URL to async version
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    logger.warning("DATABASE_URL converted to use async driver: %s", db_url)

DATABASE_URL = db_url

# Create engine with minimal configuration
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
)

# Create session factory with minimal configuration
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as an async context manager.

    Yields:
        AsyncSession: An async SQLAlchemy session
    """
    session = async_session_factory()
    try:
        yield session
    finally:
        await session.close()


async def init_db() -> None:
    """Initialize the database by creating all tables."""
    from .models import Base

    async with engine.begin() as conn:
        # Set essential SQLite pragmas
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))

        # Create tables
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized")
