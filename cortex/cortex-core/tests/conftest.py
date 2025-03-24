"""
Root conftest.py to make common fixtures available to all tests.

This file imports fixtures from the common fixtures directory to make them
available to all tests without requiring explicit imports.
"""

# Import all fixtures from the common fixtures module
from tests.common.fixtures.pytest_fixtures import (
    test_client,
    async_client,
    mock_event_bus,
    test_token,
    test_db_session,
)

# Any additional test configuration can be added here