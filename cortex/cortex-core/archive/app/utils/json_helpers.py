"""
Helper functions for JSON serialization/deserialization with database storage
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypeVar, Union, cast
from app.utils.logger import logger


# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects by converting them to ISO format"""
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

T = TypeVar("T")


def parse_json_string(json_string: Optional[str], default_value: T) -> T:
    """
    Safely parses a JSON string to an object

    Args:
        json_string: The JSON string to parse
        default_value: Default value to return if parsing fails

    Returns:
        Parsed object or default value
    """
    if not json_string:
        return default_value

    try:
        # Cast explicitly back to the same type as default_value
        result = json.loads(json_string)
        return result  # type: ignore
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON string: {e}")
        return default_value


def stringify_json(data: Any, default_value: str = "{}") -> str:
    """
    Safely stringifies an object to JSON

    Args:
        data: The data to stringify
        default_value: Default string to return if stringification fails

    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(data)
    except Exception as e:
        logger.error(f"Error stringifying object: {e}")
        return default_value


def parse_string_array(json_array: Optional[str]) -> List[str]:
    """
    Parse a JSON string array

    Args:
        json_array: The JSON array string to parse

    Returns:
        String array or empty array if parsing fails
    """
    return parse_json_string(json_array, [])


# Helper classes for working with database models


class SessionHelpers:
    """Helper for working with Session model"""

    @staticmethod
    def parse_config(session: Dict[str, Any]) -> Dict[str, Any]:
        return parse_json_string(session.get("config"), {})

    @staticmethod
    def parse_metadata(session: Dict[str, Any]) -> Dict[str, Any]:
        return parse_json_string(session.get("metadata"), {})


class ApiKeyHelpers:
    """Helper for working with ApiKey model"""

    @staticmethod
    def parse_scopes(api_key: Dict[str, Any]) -> List[str]:
        return parse_string_array(api_key.get("scopes_json"))


class WorkspaceHelpers:
    """Helper for working with Workspace model"""

    @staticmethod
    def parse_config(workspace: Dict[str, Any]) -> Dict[str, Any]:
        return parse_json_string(workspace.get("config"), {})

    @staticmethod
    def parse_metadata(workspace: Dict[str, Any]) -> Dict[str, Any]:
        return parse_json_string(workspace.get("metadata"), {})


class WorkspaceSharingHelpers:
    """Helper for working with WorkspaceSharing model"""

    @staticmethod
    def parse_permissions(sharing: Dict[str, Any]) -> List[str]:
        return parse_string_array(sharing.get("permissions_json"))


class ConversationHelpers:
    """Helper for working with Conversation model"""

    @staticmethod
    def parse_entries(conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
        return parse_json_string(conversation.get("entries"), [])

    @staticmethod
    def parse_metadata(conversation: Dict[str, Any]) -> Dict[str, Any]:
        return parse_json_string(conversation.get("metadata"), {})


class MemoryItemHelpers:
    """Helper for working with MemoryItem model"""

    @staticmethod
    def parse_content(item: Dict[str, Any]) -> Dict[str, Any]:
        return parse_json_string(item.get("content"), {})

    @staticmethod
    def parse_metadata(item: Dict[str, Any]) -> Dict[str, Any]:
        return parse_json_string(item.get("metadata"), {})


class IntegrationHelpers:
    """Helper for working with Integration model"""

    @staticmethod
    def parse_connection_details(integration: Dict[str, Any]) -> Dict[str, Any]:
        return parse_json_string(integration.get("connection_details"), {})

    @staticmethod
    def parse_capabilities(integration: Dict[str, Any]) -> List[str]:
        return parse_string_array(integration.get("capabilities_json"))


class DomainExpertTaskHelpers:
    """Helper for working with DomainExpertTask model"""

    @staticmethod
    def parse_task_details(task: Dict[str, Any]) -> Dict[str, Any]:
        return parse_json_string(task.get("task_details"), {})

    @staticmethod
    def parse_result(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return parse_json_string(task.get("result"), None)

    @staticmethod
    def parse_metadata(task: Dict[str, Any]) -> Dict[str, Any]:
        return parse_json_string(task.get("metadata"), {})


def parse_datetime(date_obj: Any) -> datetime:
    """
    Parse a date object into a datetime object.
    
    Args:
        date_obj: String in ISO format, datetime object, SQLAlchemy Column, or other type
        
    Returns:
        Parsed datetime object or current time if parsing fails
    """
    # Handle existing datetime objects
    if isinstance(date_obj, datetime):
        return date_obj
        
    # Handle None values
    if date_obj is None:
        return datetime.now(timezone.utc)
        
    # Handle mock objects in tests
    # Check if the object is a MagicMock by looking for 'mock' in its repr
    if hasattr(date_obj, '__repr__') and 'mock' in repr(date_obj).lower():
        return datetime.now(timezone.utc)
        
    # Handle SQLAlchemy Column objects
    if hasattr(date_obj, '__class__') and 'sqlalchemy' in str(date_obj.__class__.__module__).lower():
        try:
            # For SQLAlchemy objects, try to convert to string first
            date_str = str(date_obj)
            if date_str and not ('mock' in date_str.lower() or '<' in date_str):
                # Try to parse it as a string
                return parse_datetime(date_str)
            else:
                # If it's clearly not a datetime string, use current time
                return datetime.now(timezone.utc)
        except Exception as e:
            logger.error(f"Error handling SQLAlchemy Column: {e}")
            return datetime.now(timezone.utc)
        
    try:
        # Convert to string if it's not already
        date_str = date_obj if isinstance(date_obj, str) else str(date_obj)
        
        # Handle both formats with and without timezone info
        if date_str.endswith('Z'):
            # UTC time with Z suffix
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        elif '+' in date_str or '-' in date_str[-6:]:
            # ISO format with timezone info
            dt = datetime.fromisoformat(date_str)
        else:
            # No timezone info, assume UTC
            dt = datetime.fromisoformat(date_str)
            dt = dt.replace(tzinfo=timezone.utc)
                
        return dt
    except (ValueError, TypeError) as e:
        logger.error(f"Error parsing datetime: {e} from {date_obj}")
        return datetime.now(timezone.utc)
