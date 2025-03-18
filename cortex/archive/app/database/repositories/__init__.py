"""
Repository interfaces and implementations for data access.

This package contains repository interfaces (abstract base classes) and
their implementations, which provide a clean separation between the
database layer and the business logic.
"""

# Import specific repository implementations
from app.database.repositories.resource_access_repository import (
    ResourceAccessRepository,
    SQLAlchemyResourceAccessRepository,
    get_resource_access_repository
)

# These imports are available for backward compatibility
# but should now be imported directly from their respective modules
from app.database.repositories.conversation_repository import (
    ConversationRepository,
    get_conversation_repository
)

from app.database.repositories.user_repository import (
    UserRepository,
    get_user_repository
)

from app.database.repositories.workspace_repository import (
    WorkspaceRepository,
    get_workspace_repository
)