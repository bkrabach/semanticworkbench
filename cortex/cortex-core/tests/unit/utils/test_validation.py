"""
Unit tests for validation utilities.
"""

import uuid
import pytest

from app.utils.validation import is_valid_uuid, is_valid_email, validate_pagination


def test_is_valid_uuid() -> None:
    """Test the is_valid_uuid function."""
    # Valid UUIDs
    valid_uuid = str(uuid.uuid4())
    assert is_valid_uuid(valid_uuid) is True
    
    # Known valid UUIDs
    assert is_valid_uuid("550e8400-e29b-41d4-a716-446655440000") is True
    assert is_valid_uuid("123e4567-e89b-12d3-a456-426614174000") is True
    
    # Invalid values
    assert is_valid_uuid("not-a-uuid") is False
    assert is_valid_uuid("123") is False
    assert is_valid_uuid("") is False
    assert is_valid_uuid("550e8400-e29b-41d4-a716-44665544000") is False  # Too short
    assert is_valid_uuid("550e8400-e29b-41d4-a716-4466554400000") is False  # Too long
    assert is_valid_uuid("550e8400-e29b-41d4-a716_446655440000") is False  # Wrong format


def test_is_valid_email() -> None:
    """Test the is_valid_email function."""
    # Valid emails
    assert is_valid_email("test@example.com") is True
    assert is_valid_email("user.name+tag@example.co.uk") is True
    # The regex requires at least two chars in TLD
    assert is_valid_email("x@y.zz") is True
    
    # Invalid emails
    assert is_valid_email("not-an-email") is False
    assert is_valid_email("missing-at.com") is False
    assert is_valid_email("missing-domain@") is False
    assert is_valid_email("@missing-user.com") is False
    assert is_valid_email("") is False
    assert is_valid_email("test@example") is False  # Missing TLD


def test_validate_pagination_defaults() -> None:
    """Test validate_pagination with default values."""
    limit, offset = validate_pagination()
    assert limit == 100
    assert offset == 0


def test_validate_pagination_custom_values() -> None:
    """Test validate_pagination with custom values."""
    limit, offset = validate_pagination(limit=50, offset=10)
    assert limit == 50
    assert offset == 10


def test_validate_pagination_sanitizes_values() -> None:
    """Test validate_pagination sanitizes values."""
    # Limit below 1 should become 1
    limit, _ = validate_pagination(limit=0)
    assert limit == 1
    
    # Limit above max (1000) should become 1000
    limit, _ = validate_pagination(limit=2000)
    assert limit == 1000
    
    # Offset below 0 should become 0
    _, offset = validate_pagination(offset=-10)
    assert offset == 0


def test_validate_pagination_mixed_values() -> None:
    """Test validate_pagination with mixed valid and invalid values."""
    # Valid limit, invalid offset
    limit, offset = validate_pagination(limit=50, offset=-10)
    assert limit == 50
    assert offset == 0
    
    # Invalid limit, valid offset
    limit, offset = validate_pagination(limit=2000, offset=10)
    assert limit == 1000
    assert offset == 10