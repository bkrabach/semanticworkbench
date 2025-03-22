"""
Unit tests for database utilities.
"""

import pytest
from app.utils.db import serialize_json, deserialize_json, serialize_json_list, deserialize_json_list


def test_serialize_json():
    """Test serializing dictionaries to JSON."""
    # Test with a regular dictionary
    data = {"name": "Test", "value": 42, "nested": {"key": "value"}}
    serialized = serialize_json(data)
    assert '{"name": "Test"' in serialized
    assert '"value": 42' in serialized
    assert '"nested": {"key": "value"}' in serialized
    
    # Test with None
    assert serialize_json(None) == "{}"
    
    # Test with empty dict
    assert serialize_json({}) == "{}"


def test_deserialize_json():
    """Test deserializing JSON to dictionaries."""
    # Test with a regular JSON string
    json_str = '{"name": "Test", "value": 42, "nested": {"key": "value"}}'
    deserialized = deserialize_json(json_str)
    assert deserialized["name"] == "Test"
    assert deserialized["value"] == 42
    assert deserialized["nested"]["key"] == "value"
    
    # Test with None
    assert deserialize_json(None) == {}
    
    # Test with empty string
    assert deserialize_json("") == {}
    
    # Test with empty JSON object
    assert deserialize_json("{}") == {}
    
    # Test with invalid JSON
    assert deserialize_json("not json") == {}
    
    # Test with non-dict JSON
    assert deserialize_json("123") == {}
    assert deserialize_json('"string"') == {}
    assert deserialize_json("[1, 2, 3]") == {}


def test_serialize_json_list():
    """Test serializing lists to JSON."""
    # Test with a regular list
    data = [1, 2, {"name": "Test"}, [4, 5, 6]]
    serialized = serialize_json_list(data)
    assert '[1, 2, {"name": "Test"}, [4, 5, 6]]' in serialized
    
    # Test with None
    assert serialize_json_list(None) == "[]"
    
    # Test with empty list
    assert serialize_json_list([]) == "[]"


def test_deserialize_json_list():
    """Test deserializing JSON to lists."""
    # Test with a regular JSON array
    json_str = '[1, 2, {"name": "Test"}, [4, 5, 6]]'
    deserialized = deserialize_json_list(json_str)
    assert deserialized[0] == 1
    assert deserialized[1] == 2
    assert deserialized[2]["name"] == "Test"
    assert deserialized[3] == [4, 5, 6]
    
    # Test with None
    assert deserialize_json_list(None) == []
    
    # Test with empty string
    assert deserialize_json_list("") == []
    
    # Test with empty JSON array
    assert deserialize_json_list("[]") == []
    
    # Test with invalid JSON
    assert deserialize_json_list("not json") == []
    
    # Test with non-list JSON
    assert deserialize_json_list("123") == []
    assert deserialize_json_list('"string"') == []
    assert deserialize_json_list('{"key": "value"}') == []


def test_roundtrip_json():
    """Test JSON serialization and deserialization roundtrip."""
    # Dictionary roundtrip
    data = {"name": "Roundtrip", "values": [1, 2, 3], "nested": {"key": "value"}}
    serialized = serialize_json(data)
    deserialized = deserialize_json(serialized)
    assert deserialized == data
    
    # List roundtrip
    list_data = [1, {"name": "Item"}, [4, 5, 6]]
    list_serialized = serialize_json_list(list_data)
    list_deserialized = deserialize_json_list(list_serialized)
    assert list_deserialized == list_data