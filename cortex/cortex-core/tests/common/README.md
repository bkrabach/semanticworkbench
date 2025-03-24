# Common Test Utilities

This directory contains fixtures, mocks, and utilities used across different test types in the Cortex Core project.

## Structure

- `fixtures/`: Test fixtures that can be reused across different test modules.
- `mocks/`: Mock implementations of external dependencies and interfaces for testing.

## Usage

To use fixtures defined in this directory, import them directly:

```python
from tests.common.fixtures.user_fixtures import create_test_user
```

Alternatively, if they are defined in a conftest.py file, pytest will automatically discover them when tests are run.

The same applies to mock implementations:

```python
from tests.common.mocks.mock_llm import MockLLMClient
```

## Adding New Utilities

When adding new test utilities, follow these guidelines:

1. Place fixtures in the `fixtures/` directory with a descriptive filename.
2. Place mocks in the `mocks/` directory with a descriptive filename.
3. Use a clear naming convention that indicates the purpose of the utility.
4. Document the utility with docstrings describing its purpose and usage.
5. Keep utilities focused on a single responsibility.