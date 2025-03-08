"""
Database connection utility for Cortex Core
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.utils.logger import logger
from contextlib import contextmanager
from typing import Generator
import json

# Create SQLAlchemy engine
engine = create_engine(
    settings.database.url,
    connect_args={"check_same_thread": False}
    if settings.database.url.startswith("sqlite")
    else {},
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models
from app.database.models import Base


# Database access class
class Database:
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal

    @contextmanager
    def get_db(self) -> Generator:
        """Get database session"""
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            db.close()

    async def connect(self):
        """Connect to database"""
        try:
            logger.info("Connecting to database...")
            # For SQLite, create tables if they don't exist
            if settings.database.url.startswith("sqlite"):
                Base.metadata.create_all(bind=self.engine)
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def disconnect(self):
        """Disconnect from database"""
        try:
            logger.info("Disconnecting from database...")
            # No explicit disconnect needed for SQLAlchemy
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Failed to disconnect from database: {e}")
            raise

    # JSON helper methods
    def parse_json_string(self, json_string, default=None):
        """Parse JSON string to Python object"""
        if not json_string:
            return default or {}

        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            logger.error(f"Error parsing JSON string: {json_string}")
            return default or {}

    def stringify_json(self, data, default="{}"):
        """Convert Python object to JSON string"""
        try:
            return json.dumps(data)
        except Exception as e:
            logger.error(f"Error stringifying object: {e}")
            return default


# Create database instance
db = Database()


# Helper function to get DB session (dependency injection for FastAPI)
async def get_db():
    """FastAPI dependency for database session"""
    with db.get_db() as session:
        yield session
