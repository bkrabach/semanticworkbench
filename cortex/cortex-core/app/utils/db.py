import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def serialize_json(obj: Optional[Dict[str, Any]]) -> str:
    """
    Serialize an object to JSON, handling None values.

    Args:
        obj: The object to serialize

    Returns:
        JSON string representation
    """
    if obj is None:
        return "{}"

    try:
        return json.dumps(obj)
    except Exception as e:
        logger.error(f"Error serializing JSON: {str(e)}")
        return "{}"


def deserialize_json(json_str: Optional[str]) -> Dict[str, Any]:
    """
    Deserialize a JSON string to an object, handling None values, SQLAlchemy columns, and errors.

    Args:
        json_str: The JSON string to deserialize (can be SQLAlchemy Column)

    Returns:
        Deserialized object or empty dict on error
    """
    if not json_str:
        return {}

    try:
        # Convert SQLAlchemy Column object to string if needed
        json_string = str(json_str)

        result = json.loads(json_string)
        if isinstance(result, dict):
            return result
        logger.error(f"Expected JSON object but got {type(result)}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error deserializing JSON: {str(e)}")
        return {}
    except TypeError as e:
        logger.error(f"Type error deserializing JSON: {str(e)}")
        return {}


def serialize_json_list(obj_list: Optional[List[Any]]) -> str:
    """
    Serialize a list to JSON, handling None values.

    Args:
        obj_list: The list to serialize

    Returns:
        JSON string representation
    """
    if obj_list is None:
        return "[]"

    try:
        return json.dumps(obj_list)
    except Exception as e:
        logger.error(f"Error serializing JSON list: {str(e)}")
        return "[]"


def deserialize_json_list(json_str: Optional[str]) -> List[Any]:
    """
    Deserialize a JSON string to a list, handling None values, SQLAlchemy columns, and errors.

    Args:
        json_str: The JSON string to deserialize (can be SQLAlchemy Column)

    Returns:
        Deserialized list or empty list on error
    """
    if not json_str:
        return []

    try:
        # Convert SQLAlchemy Column object to string if needed
        json_string = str(json_str)

        result = json.loads(json_string)
        if not isinstance(result, list):
            logger.warning(f"Expected JSON list but got {type(result)}")
            return []
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Error deserializing JSON list: {str(e)}")
        return []
    except TypeError as e:
        logger.error(f"Type error deserializing JSON list: {str(e)}")
        return []
