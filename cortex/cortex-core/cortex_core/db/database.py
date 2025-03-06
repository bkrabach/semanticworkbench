import logging
from typing import Generator
import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from cortex_core.core.config import get_settings

# Setup logging
logger = logging.getLogger(__name__)
settings = get_settings()

# Create database engine
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Get the base class from models
from cortex_core.db.models import Base

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """
    Initialize the database.
    
    Creates all tables and sets up initial data.
    """
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created")
        
        # Setup initial data
        _setup_initial_data()
        
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def _setup_initial_data() -> None:
    """
    Set up initial data in the database.
    
    Creates demo user if required.
    """
    try:
        # Create a database session
        db = SessionLocal()
        
        try:
            # Import here to avoid circular imports
            from cortex_core.core.auth import auth_manager
            
            # Create demo user if in demo mode
            if settings.DEMO_MODE:
                from cortex_core.models.schemas import User
                import asyncio
                
                # Run async function in a synchronous context
                demo_user = asyncio.run(auth_manager.get_or_create_demo_user(db))
                logger.info(f"Demo user set up: {demo_user.id}")
            
            # Create default MCP servers
            if settings.DEFAULT_MCP_SERVERS:
                from cortex_core.db.models import MCPServer as MCPServerDB
                
                for server_info in settings.DEFAULT_MCP_SERVERS:
                    # Check if server already exists
                    existing = db.query(MCPServerDB).filter(MCPServerDB.name == server_info["name"]).first()
                    
                    if not existing:
                        server = MCPServerDB(
                            name=server_info["name"],
                            url=server_info["url"],
                            status="disconnected"  # Will be connected when MCP client starts
                        )
                        
                        db.add(server)
                        logger.info(f"Added default MCP server: {server_info['name']}")
            
            # Commit all changes
            db.commit()
            
        except Exception as e:
            logger.error(f"Error setting up initial data: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in _setup_initial_data: {str(e)}")
        raise

def get_memory_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for memory database sessions.
    
    This is a separate function to allow future migration to a separate
    database for memory storage if needed.
    
    Yields:
        Session: Database session
    """
    # Currently using the same database
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()