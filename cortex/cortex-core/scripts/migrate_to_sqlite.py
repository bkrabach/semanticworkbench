import sys
import os
import asyncio
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import environment variables
from dotenv import load_dotenv
load_dotenv()

async def run_migration():
    """Run the migration from in-memory storage to SQLite."""
    from app.database.connection import init_db
    from app.database.migration import migrate_to_sqlite
    
    # Initialize database first
    logger.info("Initializing database...")
    await init_db()
    
    # Run migration
    logger.info("Starting migration from in-memory storage to SQLite...")
    stats = await migrate_to_sqlite()
    
    # Log results
    logger.info("Migration completed")
    logger.info(f"Migrated {stats['users']} users")
    logger.info(f"Migrated {stats['workspaces']} workspaces")
    logger.info(f"Migrated {stats['conversations']} conversations")
    logger.info(f"Migrated {stats['messages']} messages")
    
    if stats["errors"] > 0:
        logger.warning(f"Encountered {stats['errors']} errors during migration")
    else:
        logger.info("No errors encountered during migration")

if __name__ == "__main__":
    asyncio.run(run_migration())