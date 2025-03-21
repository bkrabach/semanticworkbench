# Migration Guide for Cortex Core Phase 2

## Overview

This document provides comprehensive instructions for migrating from Phase 1's in-memory storage to Phase 2's SQLite persistence layer. The migration will preserve all existing data while ensuring minimal disruption to the system's operation. Since this is a pre-production environment, the migration approach prioritizes simplicity and reliability over zero-downtime concerns.

## Table of Contents

1. [Migration Goals and Principles](#migration-goals-and-principles)
2. [Prerequisites](#prerequisites)
3. [Migration Strategy](#migration-strategy)
4. [Schema Creation](#schema-creation)
5. [Data Migration Process](#data-migration-process)
6. [Fallback Strategy](#fallback-strategy)
7. [Testing the Migration](#testing-the-migration)
8. [Verification Steps](#verification-steps)
9. [Post-Migration Tasks](#post-migration-tasks)
10. [Troubleshooting Common Issues](#troubleshooting-common-issues)
11. [Implementation Examples](#implementation-examples)

## Migration Goals and Principles

### Goals

1. **Complete Data Preservation**: Migrate all data from in-memory storage to SQLite
2. **Minimal Disruption**: Simple, one-time migration requiring minimal downtime
3. **Data Integrity**: Ensure data correctness and referential integrity
4. **Simple Fallback**: Provide a straightforward fallback mechanism
5. **Verification**: Robust validation of migration success

### Principles

1. **Simplicity Over Sophistication**: Prefer simpler approaches given the pre-production nature
2. **One-Time Migration**: Design as a one-time process rather than a complex migration framework
3. **Complete Test Coverage**: Test the migration thoroughly before running in actual environments
4. **Explicit ID Preservation**: Maintain existing IDs to ensure continuity of service
5. **Clean Cutover**: Clear separation between old and new storage systems

## Prerequisites

Before beginning the migration, ensure you have:

1. **Complete Backup**: Export all in-memory data to a JSON backup file
2. **Application Code Updated**: All repositories and models must be implemented
3. **SQLite Libraries Installed**: SQLAlchemy and SQLite dependencies installed
4. **Sufficient Disk Space**: At least 100MB free for SQLite database and backup files
5. **Required Permissions**: Write permissions to database directory
6. **No Active Connections**: Ideally, perform migration during a maintenance window

### Required Packages

Ensure these packages are installed:

```bash
pip install sqlalchemy==2.0.0 aiosqlite==0.17.0 pydantic==2.0.0
```

## Migration Strategy

The migration follows a sequential approach:

1. **Initialize Database**: Create SQLite database file and tables
2. **Extract In-Memory Data**: Retrieve all data from in-memory storage
3. **Transform Data**: Convert in-memory models to database models
4. **Load Data**: Insert data into SQLite tables
5. **Verify Migration**: Validate data integrity and completeness
6. **Switch Storage System**: Update application to use SQLite repositories
7. **Backup In-Memory Data**: Maintain in-memory data as fallback

This approach allows for a clean transition with opportunities for validation at each step.

## Schema Creation

The first step is to create the SQLite database schema.

### Database Initialization Script

Create a script to initialize the database schema:

```python
# db_init.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.database.models import Base

async def create_database_schema(database_url: str):
    """
    Create SQLite database schema.

    Args:
        database_url: SQLite database URL (sqlite+aiosqlite:///cortex.db)
    """
    print(f"Creating database schema at {database_url}")

    # Create engine
    engine = create_async_engine(database_url, echo=True)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Close engine
    await engine.dispose()

    print("Database schema created successfully")

if __name__ == "__main__":
    # Get database URL from environment variable or use default
    import os
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///cortex.db")

    # Run the schema creation
    asyncio.run(create_database_schema(database_url))
```

### Schema Verification

After creating the schema, verify that all tables are created correctly:

```python
# db_verify.py
import asyncio
import sqlite3

def verify_schema(database_path: str):
    """
    Verify SQLite database schema.

    Args:
        database_path: Path to SQLite database file
    """
    print(f"Verifying database schema at {database_path}")

    # Connect to database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Print tables
    print("Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")

        # Get table schema
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()

        # Print columns
        for column in columns:
            print(f"    - {column[1]} ({column[2]})")

    # Close connection
    conn.close()

if __name__ == "__main__":
    # Get database path from environment variable or use default
    import os
    database_path = os.getenv("DATABASE_PATH", "cortex.db")

    # Run schema verification
    verify_schema(database_path)
```

## Data Migration Process

The migration process involves extracting data from in-memory storage, transforming it, and loading it into SQLite.

### Migration Script

Create a migration script that handles the entire ETL process:

```python
# migrate.py
import asyncio
import json
import uuid
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.storage import in_memory_storage
from app.database.models import (
    User as DbUser,
    Workspace as DbWorkspace,
    Conversation as DbConversation,
    Message as DbMessage
)

async def migrate_to_sqlite(database_url: str, backup_path: str = None):
    """
    Migrate data from in-memory storage to SQLite.

    Args:
        database_url: SQLite database URL
        backup_path: Optional path to save backup JSON file
    """
    print(f"Starting migration to SQLite at {database_url}")
    migration_start = datetime.now()

    # Create backup of in-memory data
    backup_data = {
        "users": list(in_memory_storage.users.values()),
        "workspaces": list(in_memory_storage.workspaces.values()),
        "conversations": list(in_memory_storage.conversations.values()),
        "messages": list(in_memory_storage.messages.values())
    }

    # Save backup if path provided
    if backup_path:
        with open(backup_path, "w") as f:
            json.dump(backup_data, f, indent=2)
        print(f"Backup saved to {backup_path}")

    # Create engine and session
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Execute migration within a transaction
    async with async_session() as session:
        try:
            # Step 1: Migrate users
            print("Migrating users...")
            for user_data in in_memory_storage.users.values():
                db_user = DbUser(
                    user_id=user_data["user_id"],
                    name=user_data["name"],
                    email=user_data["email"],
                    metadata_json=json.dumps(user_data.get("metadata", {}))
                )
                session.add(db_user)
            await session.flush()
            print(f"Migrated {len(in_memory_storage.users)} users")

            # Step 2: Migrate workspaces
            print("Migrating workspaces...")
            for workspace_data in in_memory_storage.workspaces.values():
                db_workspace = DbWorkspace(
                    id=workspace_data["id"],
                    name=workspace_data["name"],
                    description=workspace_data["description"],
                    owner_id=workspace_data["owner_id"],
                    metadata_json=json.dumps(workspace_data.get("metadata", {}))
                )
                session.add(db_workspace)
            await session.flush()
            print(f"Migrated {len(in_memory_storage.workspaces)} workspaces")

            # Step 3: Migrate conversations
            print("Migrating conversations...")
            for conversation_data in in_memory_storage.conversations.values():
                db_conversation = DbConversation(
                    id=conversation_data["id"],
                    topic=conversation_data["topic"],
                    workspace_id=conversation_data["workspace_id"],
                    participant_ids_json=json.dumps(conversation_data.get("participant_ids", [])),
                    metadata_json=json.dumps(conversation_data.get("metadata", {}))
                )
                session.add(db_conversation)
            await session.flush()
            print(f"Migrated {len(in_memory_storage.conversations)} conversations")

            # Step 4: Migrate messages
            print("Migrating messages...")
            for message_data in in_memory_storage.messages.values():
                db_message = DbMessage(
                    id=message_data["id"],
                    content=message_data["content"],
                    sender_id=message_data["sender_id"],
                    conversation_id=message_data["conversation_id"],
                    timestamp=message_data["timestamp"],
                    metadata_json=json.dumps(message_data.get("metadata", {}))
                )
                session.add(db_message)
            await session.flush()
            print(f"Migrated {len(in_memory_storage.messages)} messages")

            # Commit the transaction
            await session.commit()

            migration_end = datetime.now()
            duration = (migration_end - migration_start).total_seconds()
            print(f"Migration completed successfully in {duration:.2f} seconds")

        except Exception as e:
            # Rollback transaction on error
            await session.rollback()
            print(f"Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    # Get database URL from environment variable or use default
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///cortex.db")

    # Get backup path from environment variable or use default
    backup_path = os.getenv("BACKUP_PATH", "in_memory_backup.json")

    # Run migration
    asyncio.run(migrate_to_sqlite(database_url, backup_path))
```

### Handling JSON Fields

SQLite stores JSON as text, so we need to handle serialization/deserialization properly:

```python
def serialize_json(data):
    """Serialize data to JSON string."""
    if data is None:
        return "{}"
    return json.dumps(data)

def deserialize_json(json_str):
    """Deserialize JSON string to data."""
    if not json_str or json_str == "":
        return {}
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON: {json_str}")
        return {}
```

## Fallback Strategy

In case the migration fails or issues are discovered post-migration, implement a fallback strategy.

### Preserving In-Memory Storage

Modify the application to maintain the in-memory storage as a fallback:

```python
# app/core/storage.py

# Flag to control storage backend
USE_SQLITE_STORAGE = os.getenv("USE_SQLITE_STORAGE", "true").lower() == "true"

# In-memory storage (preserved for fallback)
in_memory_storage = InMemoryStorage()

def get_repository_factory(session=None):
    """
    Get appropriate repository factory based on configuration.

    Args:
        session: Optional database session (required for SQLite)

    Returns:
        Repository factory
    """
    if USE_SQLITE_STORAGE:
        if session is None:
            raise ValueError("Database session required for SQLite storage")
        return SqliteRepositoryFactory(session)
    else:
        return InMemoryRepositoryFactory(in_memory_storage)
```

### Rollback Script

Create a script to roll back to in-memory storage if needed:

```python
# rollback.py
import os

def rollback_to_in_memory():
    """Roll back to in-memory storage."""
    # Create .env file with USE_SQLITE_STORAGE=false
    with open(".env", "w") as f:
        f.write("USE_SQLITE_STORAGE=false\n")

    print("Rolled back to in-memory storage")
    print("Restart the application for changes to take effect")

if __name__ == "__main__":
    rollback_to_in_memory()
```

## Testing the Migration

Before performing the migration in any environment, test it thoroughly.

### Migration Test Script

Create a test script that verifies the migration process:

```python
# test_migration.py
import asyncio
import json
import uuid
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.database.models import Base, User as DbUser, Workspace as DbWorkspace
from app.core.storage import InMemoryStorage
from migrate import migrate_to_sqlite

async def test_migration():
    """Test the migration process with sample data."""
    print("Testing migration process...")

    # Create test database URL
    test_db_url = "sqlite+aiosqlite:///test_migration.db"

    # Create test in-memory storage with sample data
    in_memory_storage = InMemoryStorage()

    # Add test users
    user_id = str(uuid.uuid4())
    in_memory_storage.users[user_id] = {
        "user_id": user_id,
        "name": "Test User",
        "email": "test@example.com",
        "metadata": {"test": True}
    }

    # Add test workspaces
    workspace_id = str(uuid.uuid4())
    in_memory_storage.workspaces[workspace_id] = {
        "id": workspace_id,
        "name": "Test Workspace",
        "description": "Test description",
        "owner_id": user_id,
        "metadata": {"key": "value"}
    }

    # Add test conversations
    conversation_id = str(uuid.uuid4())
    in_memory_storage.conversations[conversation_id] = {
        "id": conversation_id,
        "topic": "Test Conversation",
        "workspace_id": workspace_id,
        "participant_ids": [user_id],
        "metadata": {"key": "value"}
    }

    # Add test messages
    message_id = str(uuid.uuid4())
    in_memory_storage.messages[message_id] = {
        "id": message_id,
        "content": "Test message",
        "sender_id": user_id,
        "conversation_id": conversation_id,
        "timestamp": "2023-01-01T00:00:00",
        "metadata": {"key": "value"}
    }

    # Create test engine
    engine = create_async_engine(test_db_url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Run migration
    from app.core import storage
    storage.in_memory_storage = in_memory_storage
    await migrate_to_sqlite(test_db_url)

    # Verify migration
    async with async_session() as session:
        # Check users
        result = await session.execute(select(DbUser))
        users = result.scalars().all()
        assert len(users) == 1, f"Expected 1 user, found {len(users)}"
        assert users[0].user_id == user_id
        assert users[0].name == "Test User"
        assert users[0].email == "test@example.com"

        # Check workspaces
        result = await session.execute(select(DbWorkspace))
        workspaces = result.scalars().all()
        assert len(workspaces) == 1, f"Expected 1 workspace, found {len(workspaces)}"
        assert workspaces[0].id == workspace_id
        assert workspaces[0].name == "Test Workspace"
        assert workspaces[0].owner_id == user_id

    # Drop test database
    os.remove("test_migration.db")

    print("Migration test passed!")

if __name__ == "__main__":
    asyncio.run(test_migration())
```

## Verification Steps

After migration, perform these verification steps to ensure data integrity.

### Count Verification

Create a script to verify record counts:

```python
# verify_counts.py
import asyncio
import json
import sqlite3
from app.core.storage import in_memory_storage

async def verify_counts(database_path: str):
    """
    Verify record counts between in-memory and SQLite.

    Args:
        database_path: Path to SQLite database file
    """
    print(f"Verifying record counts between in-memory and SQLite at {database_path}")

    # Get in-memory counts
    in_memory_counts = {
        "users": len(in_memory_storage.users),
        "workspaces": len(in_memory_storage.workspaces),
        "conversations": len(in_memory_storage.conversations),
        "messages": len(in_memory_storage.messages)
    }

    print("In-memory record counts:")
    for table, count in in_memory_counts.items():
        print(f"  - {table}: {count}")

    # Get SQLite counts
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    sqlite_counts = {}
    for table in ["users", "workspaces", "conversations", "messages"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        sqlite_counts[table] = count

    conn.close()

    print("SQLite record counts:")
    for table, count in sqlite_counts.items():
        print(f"  - {table}: {count}")

    # Compare counts
    all_match = True
    for table in in_memory_counts:
        if in_memory_counts[table] != sqlite_counts[table]:
            print(f"Count mismatch for {table}: in-memory={in_memory_counts[table]}, sqlite={sqlite_counts[table]}")
            all_match = False

    if all_match:
        print("All record counts match!")
    else:
        print("Record count mismatch found")

if __name__ == "__main__":
    # Get database path from environment variable or use default
    import os
    database_path = os.getenv("DATABASE_PATH", "cortex.db")

    # Run verification
    asyncio.run(verify_counts(database_path))
```

### Data Sampling Verification

Verify a sample of records for each entity type:

```python
# verify_samples.py
import asyncio
import json
import sqlite3
import random
from app.core.storage import in_memory_storage

async def verify_samples(database_path: str, sample_size: int = 5):
    """
    Verify sample records between in-memory and SQLite.

    Args:
        database_path: Path to SQLite database file
        sample_size: Number of records to sample from each table
    """
    print(f"Verifying sample records between in-memory and SQLite at {database_path}")

    # Connect to SQLite
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Verify users
    print(f"Verifying {sample_size} random users...")
    if in_memory_storage.users:
        user_ids = random.sample(list(in_memory_storage.users.keys()), min(sample_size, len(in_memory_storage.users)))

        for user_id in user_ids:
            in_memory_user = in_memory_storage.users[user_id]

            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            sqlite_user = cursor.fetchone()

            if not sqlite_user:
                print(f"User {user_id} not found in SQLite")
                continue

            # Compare fields
            assert in_memory_user["user_id"] == sqlite_user["user_id"], f"User ID mismatch for {user_id}"
            assert in_memory_user["name"] == sqlite_user["name"], f"Name mismatch for user {user_id}"
            assert in_memory_user["email"] == sqlite_user["email"], f"Email mismatch for user {user_id}"

            # Compare metadata
            in_memory_metadata = in_memory_user.get("metadata", {})
            sqlite_metadata = json.loads(sqlite_user["metadata_json"] or "{}")
            assert in_memory_metadata == sqlite_metadata, f"Metadata mismatch for user {user_id}"

            print(f"User {user_id} verified ✓")

    # Verify workspaces
    print(f"Verifying {sample_size} random workspaces...")
    if in_memory_storage.workspaces:
        workspace_ids = random.sample(list(in_memory_storage.workspaces.keys()), min(sample_size, len(in_memory_storage.workspaces)))

        for workspace_id in workspace_ids:
            in_memory_workspace = in_memory_storage.workspaces[workspace_id]

            cursor.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,))
            sqlite_workspace = cursor.fetchone()

            if not sqlite_workspace:
                print(f"Workspace {workspace_id} not found in SQLite")
                continue

            # Compare fields
            assert in_memory_workspace["id"] == sqlite_workspace["id"], f"ID mismatch for workspace {workspace_id}"
            assert in_memory_workspace["name"] == sqlite_workspace["name"], f"Name mismatch for workspace {workspace_id}"
            assert in_memory_workspace["description"] == sqlite_workspace["description"], f"Description mismatch for workspace {workspace_id}"
            assert in_memory_workspace["owner_id"] == sqlite_workspace["owner_id"], f"Owner ID mismatch for workspace {workspace_id}"

            # Compare metadata
            in_memory_metadata = in_memory_workspace.get("metadata", {})
            sqlite_metadata = json.loads(sqlite_workspace["metadata_json"] or "{}")
            assert in_memory_metadata == sqlite_metadata, f"Metadata mismatch for workspace {workspace_id}"

            print(f"Workspace {workspace_id} verified ✓")

    # Continue with conversations and messages...
    # Similar verification logic for other entity types

    conn.close()
    print("Sample verification completed!")

if __name__ == "__main__":
    # Get database path from environment variable or use default
    import os
    database_path = os.getenv("DATABASE_PATH", "cortex.db")

    # Run verification
    asyncio.run(verify_samples(database_path))
```

## Post-Migration Tasks

After successful migration, perform these tasks to complete the transition.

### Update Configuration

Create or update `.env` file to use SQLite storage:

```
# .env
USE_SQLITE_STORAGE=true
DATABASE_URL=sqlite+aiosqlite:///cortex.db
```

### Archive In-Memory Backup

Archive the in-memory backup for future reference:

```bash
mkdir -p backups
cp in_memory_backup.json backups/in_memory_backup_$(date +%Y%m%d%H%M%S).json
```

### Verify Application Functionality

After migration, verify key application functionality:

1. **Authentication Flow**: Verify login and token validation
2. **Input/Output Flow**: Verify input processing and output streaming
3. **Configuration API**: Verify workspace and conversation management
4. **Existing Data Access**: Verify access to migrated data

## Troubleshooting Common Issues

### Foreign Key Constraints

If foreign key constraint errors occur during migration:

```python
# Enable foreign keys
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

### SQLite Locking Issues

If SQLite database locking issues occur:

```python
# Configure SQLite for better concurrency
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()
```

### JSON Parsing Errors

If JSON parsing errors occur during migration:

```python
def safe_json_loads(json_str, default=None):
    """Safely load JSON string."""
    if not json_str or json_str == "":
        return default or {}
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON: {json_str}")
        return default or {}
```

### ID Conflicts

If ID conflicts occur during migration:

```python
async def check_id_conflicts(session):
    """Check for ID conflicts."""
    # Check for duplicate user IDs
    result = await session.execute("""
        SELECT user_id, COUNT(*) AS count
        FROM users
        GROUP BY user_id
        HAVING count > 1
    """)
    duplicate_users = result.fetchall()
    if duplicate_users:
        print(f"Found {len(duplicate_users)} duplicate user IDs")
        for user_id, count in duplicate_users:
            print(f"  - User ID: {user_id}, Count: {count}")

    # Similar checks for other entity types
```

## Implementation Examples

### Complete Migration Script

Here's a complete migration script that handles all aspects of the migration process:

```python
#!/usr/bin/env python
"""
Migration script for Cortex Core Phase 2.

This script migrates data from in-memory storage to SQLite database.
"""

import asyncio
import json
import uuid
import os
import sys
import sqlite3
import time
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import event

from app.database.models import Base, User as DbUser, Workspace as DbWorkspace, Conversation as DbConversation, Message as DbMessage
from app.core.storage import in_memory_storage

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///cortex.db")
BACKUP_PATH = os.getenv("BACKUP_PATH", "in_memory_backup.json")
VERIFY_MIGRATION = os.getenv("VERIFY_MIGRATION", "true").lower() == "true"
SAMPLE_SIZE = int(os.getenv("SAMPLE_SIZE", "5"))

async def create_database_schema(engine):
    """
    Create database schema.

    Args:
        engine: SQLAlchemy engine
    """
    print("Creating database schema...")

    # Create tables
    async with engine.begin() as conn:
        # Enable foreign keys
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

        await conn.run_sync(Base.metadata.create_all)

    print("Database schema created successfully")

def create_backup():
    """Create backup of in-memory data."""
    print(f"Creating backup at {BACKUP_PATH}...")

    # Create backup data
    backup_data = {
        "users": list(in_memory_storage.users.values()),
        "workspaces": list(in_memory_storage.workspaces.values()),
        "conversations": list(in_memory_storage.conversations.values()),
        "messages": list(in_memory_storage.messages.values())
    }

    # Save backup
    with open(BACKUP_PATH, "w") as f:
        json.dump(backup_data, f, indent=2)

    print(f"Backup created with {len(in_memory_storage.users)} users, "
          f"{len(in_memory_storage.workspaces)} workspaces, "
          f"{len(in_memory_storage.conversations)} conversations, "
          f"{len(in_memory_storage.messages)} messages")

    return backup_data

async def migrate_data(session):
    """
    Migrate data from in-memory storage to SQLite.

    Args:
        session: SQLAlchemy session
    """
    print("Starting data migration...")
    start_time = time.time()

    # Step 1: Migrate users
    print("Migrating users...")
    for user_id, user_data in in_memory_storage.users.items():
        db_user = DbUser(
            user_id=user_data["user_id"],
            name=user_data["name"],
            email=user_data["email"],
            metadata_json=json.dumps(user_data.get("metadata", {}))
        )
        session.add(db_user)
    await session.flush()
    print(f"Migrated {len(in_memory_storage.users)} users")

    # Step 2: Migrate workspaces
    print("Migrating workspaces...")
    for workspace_id, workspace_data in in_memory_storage.workspaces.items():
        db_workspace = DbWorkspace(
            id=workspace_data["id"],
            name=workspace_data["name"],
            description=workspace_data["description"],
            owner_id=workspace_data["owner_id"],
            metadata_json=json.dumps(workspace_data.get("metadata", {}))
        )
        session.add(db_workspace)
    await session.flush()
    print(f"Migrated {len(in_memory_storage.workspaces)} workspaces")

    # Step 3: Migrate conversations
    print("Migrating conversations...")
    for conversation_id, conversation_data in in_memory_storage.conversations.items():
        db_conversation = DbConversation(
            id=conversation_data["id"],
            topic=conversation_data["topic"],
            workspace_id=conversation_data["workspace_id"],
            participant_ids_json=json.dumps(conversation_data.get("participant_ids", [])),
            metadata_json=json.dumps(conversation_data.get("metadata", {}))
        )
        session.add(db_conversation)
    await session.flush()
    print(f"Migrated {len(in_memory_storage.conversations)} conversations")

    # Step 4: Migrate messages
    print("Migrating messages...")
    for message_id, message_data in in_memory_storage.messages.items():
        db_message = DbMessage(
            id=message_data["id"],
            content=message_data["content"],
            sender_id=message_data["sender_id"],
            conversation_id=message_data["conversation_id"],
            timestamp=message_data["timestamp"],
            metadata_json=json.dumps(message_data.get("metadata", {}))
        )
        session.add(db_message)
    await session.flush()
    print(f"Migrated {len(in_memory_storage.messages)} messages")

    # Commit the transaction
    await session.commit()

    elapsed_time = time.time() - start_time
    print(f"Data migration completed in {elapsed_time:.2f} seconds")

async def verify_migration(engine, sample_size=5):
    """
    Verify migration success.

    Args:
        engine: SQLAlchemy engine
        sample_size: Number of records to sample for verification
    """
    print("Verifying migration...")

    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Step 1: Verify record counts
        print("Verifying record counts...")

        # Count users
        result = await session.execute(select(DbUser))
        db_users = result.scalars().all()
        if len(db_users) != len(in_memory_storage.users):
            print(f"User count mismatch: SQLite={len(db_users)}, in-memory={len(in_memory_storage.users)}")
            return False

        # Count workspaces
        result = await session.execute(select(DbWorkspace))
        db_workspaces = result.scalars().all()
        if len(db_workspaces) != len(in_memory_storage.workspaces):
            print(f"Workspace count mismatch: SQLite={len(db_workspaces)}, in-memory={len(in_memory_storage.workspaces)}")
            return False

        # Count conversations
        result = await session.execute(select(DbConversation))
        db_conversations = result.scalars().all()
        if len(db_conversations) != len(in_memory_storage.conversations):
            print(f"Conversation count mismatch: SQLite={len(db_conversations)}, in-memory={len(in_memory_storage.conversations)}")
            return False

        # Count messages
        result = await session.execute(select(DbMessage))
        db_messages = result.scalars().all()
        if len(db_messages) != len(in_memory_storage.messages):
            print(f"Message count mismatch: SQLite={len(db_messages)}, in-memory={len(in_memory_storage.messages)}")
            return False

        print("Record counts verified ✓")

        # Step 2: Verify sample records
        print(f"Verifying {sample_size} random records of each type...")

        # Verify users
        if in_memory_storage.users:
            import random
            user_ids = random.sample(list(in_memory_storage.users.keys()), min(sample_size, len(in_memory_storage.users)))

            for user_id in user_ids:
                in_memory_user = in_memory_storage.users[user_id]

                result = await session.execute(select(DbUser).where(DbUser.user_id == user_id))
                db_user = result.scalars().first()

                if not db_user:
                    print(f"User {user_id} not found in SQLite")
                    return False

                # Verify fields
                assert db_user.user_id == in_memory_user["user_id"], f"User ID mismatch: {db_user.user_id} != {in_memory_user['user_id']}"
                assert db_user.name == in_memory_user["name"], f"Name mismatch: {db_user.name} != {in_memory_user['name']}"
                assert db_user.email == in_memory_user["email"], f"Email mismatch: {db_user.email} != {in_memory_user['email']}"

                # Verify metadata
                db_metadata = json.loads(db_user.metadata_json or "{}")
                in_memory_metadata = in_memory_user.get("metadata", {})
                assert db_metadata == in_memory_metadata, f"Metadata mismatch: {db_metadata} != {in_memory_metadata}"

            print("User samples verified ✓")

        # Verify workspaces
        if in_memory_storage.workspaces:
            import random
            workspace_ids = random.sample(list(in_memory_storage.workspaces.keys()), min(sample_size, len(in_memory_storage.workspaces)))

            for workspace_id in workspace_ids:
                in_memory_workspace = in_memory_storage.workspaces[workspace_id]

                result = await session.execute(select(DbWorkspace).where(DbWorkspace.id == workspace_id))
                db_workspace = result.scalars().first()

                if not db_workspace:
                    print(f"Workspace {workspace_id} not found in SQLite")
                    return False

                # Verify fields
                assert db_workspace.id == in_memory_workspace["id"], f"ID mismatch: {db_workspace.id} != {in_memory_workspace['id']}"
                assert db_workspace.name == in_memory_workspace["name"], f"Name mismatch: {db_workspace.name} != {in_memory_workspace['name']}"
                assert db_workspace.description == in_memory_workspace["description"], f"Description mismatch"
                assert db_workspace.owner_id == in_memory_workspace["owner_id"], f"Owner ID mismatch"

                # Verify metadata
                db_metadata = json.loads(db_workspace.metadata_json or "{}")
                in_memory_metadata = in_memory_workspace.get("metadata", {})
                assert db_metadata == in_memory_metadata, f"Metadata mismatch: {db_metadata} != {in_memory_metadata}"

            print("Workspace samples verified ✓")

        # Continue with conversation and message verification...

    print("Migration verification successful ✓")
    return True

async def main():
    """Main migration function."""
    print(f"Starting migration to SQLite at {DATABASE_URL}")
    print(f"Backup path: {BACKUP_PATH}")

    try:
        # Step 1: Create backup
        backup_data = create_backup()

        # Step 2: Create engine
        engine = create_async_engine(DATABASE_URL, echo=False)

        # Step 3: Create database schema
        await create_database_schema(engine)

        # Step 4: Create session
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        # Step 5: Migrate data
        async with async_session() as session:
            try:
                await migrate_data(session)
            except Exception as e:
                await session.rollback()
                print(f"Migration failed: {str(e)}")
                return False

        # Step 6: Verify migration
        if VERIFY_MIGRATION:
            success = await verify_migration(engine, SAMPLE_SIZE)
            if not success:
                print("Migration verification failed")
                return False

        # Step 7: Update configuration
        with open(".env", "w") as f:
            f.write(f"USE_SQLITE_STORAGE=true\n")
            f.write(f"DATABASE_URL={DATABASE_URL}\n")

        print("Migration completed successfully")
        print("The application is now configured to use SQLite storage")
        return True

    except Exception as e:
        print(f"Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
```

### Migration Wrapper Script

Create a wrapper script for easy execution with command line options:

```bash
#!/bin/bash
# migrate.sh - Migration wrapper script

# Default values
DATABASE_URL="sqlite+aiosqlite:///cortex.db"
BACKUP_PATH="in_memory_backup.json"
VERIFY="true"
SAMPLE_SIZE=5

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --database-url)
            DATABASE_URL="$2"
            shift
            shift
            ;;
        --backup-path)
            BACKUP_PATH="$2"
            shift
            shift
            ;;
        --no-verify)
            VERIFY="false"
            shift
            ;;
        --sample-size)
            SAMPLE_SIZE="$2"
            shift
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: migrate.sh [--database-url URL] [--backup-path PATH] [--no-verify] [--sample-size N]"
            exit 1
            ;;
    esac
done

# Export environment variables
export DATABASE_URL="$DATABASE_URL"
export BACKUP_PATH="$BACKUP_PATH"
export VERIFY_MIGRATION="$VERIFY"
export SAMPLE_SIZE="$SAMPLE_SIZE"

# Run migration script
echo "Running migration with the following settings:"
echo "- Database URL: $DATABASE_URL"
echo "- Backup path: $BACKUP_PATH"
echo "- Verify migration: $VERIFY"
echo "- Sample size: $SAMPLE_SIZE"
echo

python migrate.py

# Check exit code
if [ $? -eq 0 ]; then
    echo "Migration completed successfully"
    echo "Backup stored at: $BACKUP_PATH"
    echo
    echo "Remember to restart the application for changes to take effect"
else
    echo "Migration failed, no changes made to configuration"
    echo "Check the error messages above for details"
fi
```

This migration guide provides a comprehensive approach to migrating from in-memory storage to SQLite. By following these steps, you can ensure a smooth transition with minimal disruption to the system's operation.
