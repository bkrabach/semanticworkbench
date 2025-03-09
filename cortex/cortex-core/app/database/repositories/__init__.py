"""
Repository interfaces and implementations for data access.

This package contains repository interfaces (abstract base classes) and
their implementations, which provide a clean separation between the
database layer and the business logic.
"""

# Import from the original repositories file for backward compatibility during transition
# This is a temporary solution until all imports are updated to use the new module structure
from app.database.repositories.resource_access_repository import (
    ResourceAccessRepository,
    SQLAlchemyResourceAccessRepository,
    get_resource_access_repository
)

# Import from the original repositories.py file for backward compatibility
# This is necessary to avoid circular imports
import sys
import importlib.util
import os

# Get the path to the original repositories.py file
original_path = os.path.join(os.path.dirname(__file__), '..', 'repositories.py')

# Load the original module manually to avoid circular imports
spec = importlib.util.spec_from_file_location('original_repositories', original_path)
original_repositories = importlib.util.module_from_spec(spec)
sys.modules['original_repositories'] = original_repositories
spec.loader.exec_module(original_repositories)

# Import symbols from the original module
from original_repositories import (
    ConversationRepository,
    SQLAlchemyConversationRepository,
    get_conversation_repository,
    UserRepository,
    SQLAlchemyUserRepository,
    get_user_repository,
    WorkspaceRepository,
    SQLAlchemyWorkspaceRepository,
    get_workspace_repository
)