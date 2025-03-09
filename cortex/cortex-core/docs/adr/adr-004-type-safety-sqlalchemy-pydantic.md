# ADR-004: Type Safety with SQLAlchemy and Pydantic

## Status

Accepted

## Context

The Cortex Core platform uses SQLAlchemy for database ORM and Pydantic for data validation and serialization. These powerful libraries help create a robust system, but integrating them presents several challenges:

1. **SQLAlchemy Column Type Behavior**: SQLAlchemy's Column objects have unique type characteristics:
   - They aren't directly compatible with standard Python types
   - Direct boolean evaluation (`if column:`) raises "Invalid conditional operand" errors
   - Passing them to functions like `json.loads()` causes type errors

2. **JSON Field Handling**: We store structured data in JSON string fields in the database:
   - Converting between JSON strings and Python objects requires explicit handling
   - Column objects need special treatment before JSON operations
   - Type errors occur when attempting to parse JSON directly from Column objects

3. **Type Mismatch in Layer Boundaries**: When domain models cross architectural boundaries:
   - Type errors emerge when Column objects leak into service or API layers
   - Subtle bugs occur when Column objects are compared with Python types
   - Testing becomes challenging when mock types don't match expected types

4. **Pydantic Validation**: When using Pydantic models:
   - Validators need proper type conversion for SQLAlchemy fields
   - Field conversions can be missed during model updates
   - Schema evolution requires careful type handling

These issues have caused numerous production bugs and made the codebase harder to maintain.

## Decision

We will adopt a comprehensive approach to type safety at all layer boundaries, with specific patterns for handling SQLAlchemy Column objects:

1. **Explicit Column Object Conversion**:
   ```python
   # NEVER:
   value = db_model.column
   
   # ALWAYS:
   value = str(db_model.column) if db_model.column is not None else None
   ```

2. **Standard JSON Field Handling Pattern**:
   ```python
   # CORRECT pattern for JSON fields:
   try:
       # Always convert to string first
       json_str = str(db_model.json_field) if db_model.json_field is not None else "{}"
       data = json.loads(json_str)
   except (json.JSONDecodeError, TypeError):
       data = {}  # Default fallback
   ```

3. **Safe Conditional Checks**:
   ```python
   # NEVER:
   if db_model.nullable_field:
       # ...
   
   # ALWAYS:
   if db_model.nullable_field is not None:
       # ...
   ```

4. **Date/Time Handling**:
   ```python
   # CORRECT datetime handling:
   from app.utils.json_helpers import parse_datetime
   
   timestamp = parse_datetime(db_model.timestamp) if db_model.timestamp is not None else datetime.now(timezone.utc)
   ```

5. **Repository Conversion Requirements**:
   - Every repository must have explicit `_to_domain()` methods
   - All conversions between SQLAlchemy and domain models must happen in repositories
   - Type annotations are required for all parameters and return values

Additionally, we will enforce strict architectural boundaries to ensure SQLAlchemy models never leak outside repositories.

## Consequences

### Positive

1. **Improved Type Safety**: Fewer runtime errors related to type mismatches
2. **Easier Debugging**: More explicit and predictable type behavior
3. **Better IDE Support**: Proper type hints enable better editor/IDE integration
4. **Consistent Patterns**: Standard approaches to common challenges
5. **Simplified Testing**: Clearer boundaries between types makes testing more straightforward
6. **Reduced Bugs**: Fewer unexpected type-related failures in production

### Negative

1. **Increased Boilerplate**: More explicit type conversions add code
2. **Learning Curve**: Developers need to understand proper SQLAlchemy Column handling
3. **Verbosity**: Some operations require more code than direct access

## Implementation Examples

### Repository Type Conversion

```python
def _to_domain(self, db_model: UserDB) -> User:
    """Convert database model to domain model with proper type handling"""
    # Parse JSON metadata with proper error handling
    try:
        metadata_str = str(db_model.meta_data) if db_model.meta_data is not None else "{}"
        metadata = json.loads(metadata_str)
    except (json.JSONDecodeError, TypeError):
        metadata = {}
        
    # Handle dates properly
    created_at = parse_datetime(db_model.created_at_utc) if db_model.created_at_utc is not None else datetime.now(timezone.utc)
    updated_at = parse_datetime(db_model.updated_at_utc) if db_model.updated_at_utc is not None else None
    
    # Convert all fields with explicit type casts
    return User(
        id=str(db_model.id),
        email=str(db_model.email),
        name=str(db_model.name) if db_model.name is not None else None,
        created_at=created_at,
        updated_at=updated_at,
        metadata=metadata
    )
```

### Safe JSON Field Handling

```python
class ConversationRepository:
    def _parse_entries(self, db_model: ConversationDB) -> List[Message]:
        """Parse conversation entries with safe type handling"""
        try:
            # Convert Column to string first
            entries_json = str(db_model.entries) if db_model.entries is not None else "[]"
            entries = json.loads(entries_json)
            
            # Convert each entry to a domain model
            return [
                Message(
                    id=str(entry.get("id")),
                    content=str(entry.get("content", "")),
                    role=str(entry.get("role", "user")),
                    created_at=parse_datetime(entry.get("created_at_utc")),
                    metadata=entry.get("metadata", {})
                )
                for entry in entries if isinstance(entry, dict)
            ]
        except (json.JSONDecodeError, TypeError):
            # Return empty list on parsing failure
            logger.warning(f"Failed to parse conversation entries for ID: {db_model.id}")
            return []
```

## Alternatives Considered

### Use SQLModel Instead

We considered using SQLModel, which attempts to unify SQLAlchemy and Pydantic models. Benefits would have been:
- Fewer type conversion issues
- Less boilerplate code
- Simpler model definitions

Drawbacks that led us to reject this approach:
- Still relatively new library with evolving patterns
- Would require significant refactoring of existing code
- Some SQLAlchemy features aren't fully supported
- The clear separation between domain and database layers would be reduced

### Runtime Type Checking

We considered adding more aggressive runtime type checking to catch issues. This would have:
- Caught type errors at runtime before they cause problems
- Provided clearer error messages
- Potentially simplified debugging

We rejected this due to:
- Performance overhead in production
- Additional complexity in the codebase
- Focus on prevention rather than detection is more efficient

### Custom Field Types

We considered creating custom field types that handle type conversions automatically. This would have:
- Reduced boilerplate code
- Encapsulated conversion logic
- Potentially improved DRY principles

We rejected this because:
- It would add a layer of abstraction that could be confusing
- The explicit conversions make the behavior more obvious
- Custom field types add complexity to testing and debugging

## References

- [SQLAlchemy Type Documentation](https://docs.sqlalchemy.org/en/20/core/type_basics.html)
- [Pydantic Data Types](https://docs.pydantic.dev/latest/usage/types/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [SQLAlchemy-Pydantic Integration Challenges](https://sqlalchemyorg/en/20/orm/extensions/pydantic.html)