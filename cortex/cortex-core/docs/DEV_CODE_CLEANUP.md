# Development Code Cleanup Plan

This document outlines the steps to properly separate development-only code from production code in the Cortex Core application.

## Current Issues

1. **Development Code in Main Module**: The `ensure_test_users_exist` function in main.py is only needed for development.

2. **Mixed Concerns**: Production and development functionality are mixed in the same files.

3. **Conditional Environment Checks**: Code uses environment variables to conditionally include development features.

4. **Lack of Clear Separation**: There's no clear boundary between development and production code.

## Implementation Plan

### 1. Create a Development Module

Create a new module specifically for development functionality:

```python
# app/dev/development.py

"""
Development utilities for Cortex Core.

This module contains functions and utilities that are only used in development
environments and should never be included in production.
"""

import logging
import os
from typing import List

from ..database.unit_of_work import UnitOfWork
from ..models.domain import User, Workspace

logger = logging.getLogger(__name__)


async def ensure_test_users_exist() -> None:
    """
    Ensure test users exist in the database.
    
    This function creates default test users and workspaces in development
    environments. It should not be used in production.
    """
    logger.info("Ensuring test users exist...")
    
    test_users = [
        {
            "user_id": "user1",
            "name": "Test User 1",
            "email": "user@example.com",
            "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "password"
        },
        {
            "user_id": "user2",
            "name": "Test User 2",
            "email": "user2@example.com",
            "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "password"
        }
    ]
    
    test_workspaces = [
        {
            "name": "Default Workspace",
            "description": "Default workspace for testing",
            "owner_id": "user1"
        },
        {
            "name": "Shared Workspace",
            "description": "Shared workspace for collaboration testing",
            "owner_id": "user1"
        }
    ]
    
    async with UnitOfWork.for_transaction() as uow:
        user_repo = uow.repositories.get_user_repository()
        
        # Create test users if they don't exist
        for user_data in test_users:
            user_id = user_data["user_id"]
            user = await user_repo.get_by_id(user_id)
            
            if not user:
                logger.info(f"Creating test user: {user_id}")
                user = User(**user_data)
                await user_repo.create(user)
            else:
                logger.info(f"Test user already exists: {user_id}")
        
        # Create test workspaces if they don't exist
        workspace_repo = uow.repositories.get_workspace_repository()
        
        for workspace_data in test_workspaces:
            owner_id = workspace_data["owner_id"]
            name = workspace_data["name"]
            
            # Check if workspace exists
            workspaces = await workspace_repo.list_by_owner(owner_id)
            workspace_exists = any(w.name == name for w in workspaces)
            
            if not workspace_exists:
                logger.info(f"Creating test workspace: {name}")
                workspace = Workspace(
                    name=name,
                    description=workspace_data["description"],
                    owner_id=owner_id,
                    participant_ids=[]
                )
                await workspace_repo.create(workspace)
                
                if "Shared" in name:
                    # Add second user as participant if it's the shared workspace
                    workspace.participant_ids = ["user2"]
                    await workspace_repo.update(workspace)
            else:
                logger.info(f"Test workspace already exists: {name}")
                
        # Commit all changes
        await uow.commit()
        
    logger.info("Test users and workspaces setup complete")


async def create_test_data() -> None:
    """
    Create additional test data for development purposes.
    
    This function populates the database with sample conversations and messages
    for testing. It should not be used in production.
    """
    logger.info("Creating additional test data...")
    
    # Test data creation implementation here...
    
    logger.info("Test data creation complete")
```

### 2. Create a Development Configuration Module

```python
# app/dev/config.py

"""
Development-specific configuration for Cortex Core.

This module contains development-specific configuration and should not be
included in production builds.
"""

import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# Development configuration
DEV_CONFIG: Dict[str, Any] = {
    "create_test_users": True,
    "create_test_data": True,
    "debug_logging": True,
    "allow_cors": True,
    "mock_llm": os.getenv("USE_MOCK_LLM", "true").lower() == "true"
}

def get_dev_config() -> Dict[str, Any]:
    """
    Get development configuration.
    
    Returns:
        Dictionary of development configuration options
    """
    if DEV_MODE:
        logger.info("Running in development mode with development configuration")
        return DEV_CONFIG
    else:
        logger.info("Development mode disabled")
        return {}
```

### 3. Update Main Module to Use Development Code Conditionally

```python
# app/main.py

import logging
import os
from typing import List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .api.auth import router as auth_router
from .api.cognition import router as cognition_router
from .api.input import router as input_router
from .api.output import router as output_router
from .database.connection import init_db
from .database.migration import run_migrations

# Import development utilities conditionally
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
if DEV_MODE:
    from .dev.development import ensure_test_users_exist, create_test_data
    from .dev.config import get_dev_config
    dev_config = get_dev_config()
else:
    dev_config = {}

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Cortex Core API",
    description="Core API for Cortex platform",
    version="0.1.0",
)

# Configure CORS
if DEV_MODE and dev_config.get("allow_cors", False):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(auth_router)
app.include_router(cognition_router)
app.include_router(input_router)
app.include_router(output_router)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize services on application startup."""
    logger.info("Starting Cortex Core API")
    
    # Initialize database
    await init_db()
    
    # Run database migrations
    run_migrations()
    
    # Create test users in development mode
    if DEV_MODE and dev_config.get("create_test_users", False):
        await ensure_test_users_exist()
        
    # Create additional test data in development mode
    if DEV_MODE and dev_config.get("create_test_data", False):
        await create_test_data()
        
    logger.info("Cortex Core API startup complete")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on application shutdown."""
    logger.info("Shutting down Cortex Core API")


@app.get("/")
async def root() -> dict:
    """Root endpoint for API health check."""
    return {"message": "Welcome to Cortex Core API", "status": "healthy"}
```

### 4. Create Environment Configuration Files

Create separate environment configuration files for development and production:

`.dev.env`:
```
DEV_MODE=true
USE_MOCK_LLM=true
DB_URL=sqlite:///cortex.db
```

`.prod.env`:
```
DEV_MODE=false
USE_MOCK_LLM=false
DB_URL=sqlite:///cortex.db
# This would be replaced with real production DB in actual deployment
```

## Required Changes

1. Move `ensure_test_users_exist` from main.py to the development module
2. Create a development configuration system
3. Add conditional imports in main.py based on environment
4. Move other development-only features to the development module
5. Add clear logging about development mode status

## Testing Updates

1. Add tests for development module functionality
2. Update main application tests to work with or without development mode
3. Add environment variable control in test fixtures

## Benefits

1. **Clear Separation**: Development and production code are clearly separated
2. **Reduced Risk**: Less chance of development features leaking into production
3. **Improved Organization**: Code is organized by its purpose and lifecycle
4. **Better Configuration**: Environment-specific configuration is better managed
5. **Simplified Main Module**: The main.py file becomes simpler and more focused