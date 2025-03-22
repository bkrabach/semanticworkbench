import re
import uuid
from typing import Optional


def is_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID.

    Args:
        value: The string to check

    Returns:
        True if valid UUID, False otherwise
    """
    try:
        uuid_obj = uuid.UUID(value)
        return str(uuid_obj) == value
    except (ValueError, AttributeError):
        return False


def is_valid_email(email: str) -> bool:
    """
    Validate an email address.

    Args:
        email: The email address to validate

    Returns:
        True if valid email, False otherwise
    """
    # Simple pattern matching for email validation
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_pagination(limit: Optional[int] = None, offset: Optional[int] = None) -> tuple[int, int]:
    """
    Validate and sanitize pagination parameters.

    Args:
        limit: The maximum number of items to return
        offset: The number of items to skip

    Returns:
        Tuple of (sanitized_limit, sanitized_offset)
    """
    # Default values
    default_limit = 100
    default_offset = 0

    # Maximum allowed limit
    max_limit = 1000

    # Sanitize limit
    if limit is None:
        limit = default_limit
    else:
        limit = max(1, min(limit, max_limit))

    # Sanitize offset
    if offset is None:
        offset = default_offset
    else:
        offset = max(0, offset)

    return limit, offset
