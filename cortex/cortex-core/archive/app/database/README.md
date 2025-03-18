# Database Layer Architecture

## Repository Pattern

This project uses the Repository Pattern to abstract database access away from the API layer. This provides several benefits:

1. **Separation of Concerns**: API endpoints focus on HTTP interaction, while repositories handle data operations
2. **Testability**: Repositories can be mocked for testing API endpoints without complex DB mocking
3. **Flexibility**: Allows for easier DB backend changes in the future
4. **Consistency**: Provides consistent data access patterns across the codebase

## Components

### Models (`models.py`)
- SQLAlchemy ORM models representing database tables
- Focus on structure and relationships, not business logic

### Repositories (`repositories.py`)
- Abstract interfaces for data access operations
- Concrete implementations that handle the actual data operations
- Methods map to business operations rather than raw SQL/ORM operations

### Connection (`connection.py`)
- Database connection and session management
- Dependency injection for FastAPI

## Usage Example

In an API endpoint:

```python
@router.get("/items/{item_id}")
async def get_item(
    item_id: str,
    repository: ItemRepository = Depends(get_repository)
):
    item = repository.get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
```

This pattern keeps API endpoints clean and focused on HTTP concerns, while repositories handle the data access details.

## Testing

When testing API endpoints, mock the repository interface instead of mocking database sessions or individual queries:

```python
# Create a mock repository
mock_repo = MagicMock(spec=ItemRepository)
mock_repo.get_item_by_id.return_value = Item(id="123", name="Test Item")

# Patch the get_repository dependency
with patch('app.api.items.get_repository', return_value=mock_repo):
    response = client.get("/items/123")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Item"
```

This makes tests more stable and less brittle to implementation details.