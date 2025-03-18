"""Database connection configuration."""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create SQLAlchemy engine and session factory
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Create base class for SQLAlchemy models
Base = declarative_base()


async def init_db() -> None:
    """
    Initialize the database connection.
    
    This function should be called during application startup.
    """
    logger.info("Initializing database connection")
    
    # Verify database connection
    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)
    
    logger.info("Database connection initialized successfully")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session.
    
    Yields:
        AsyncSession: A SQLAlchemy async session
    """
    async with SessionLocal() as session:
        yield session
        
        
async def close_db_connection() -> None:
    """
    Close the database connection.
    
    This function should be called during application shutdown.
    """
    logger.info("Closing database connection")
    await engine.dispose()
    logger.info("Database connection closed")