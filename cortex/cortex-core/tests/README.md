# Test Organization

This directory contains tests for the Cortex Core application. Tests are organized in a way that reflects both test type and system architecture.

## Directory Structure

```
tests/
├── common/            # Common test utilities and fixtures
│   ├── fixtures/      # Test fixtures for reuse across test types
│   └── mocks/         # Mock implementations for testing
├── unit/              # Unit tests that test individual components in isolation
│   ├── api/           # Tests for API endpoints
│   ├── core/          # Tests for core functionality
│   ├── database/      # Tests for database-related code
│   ├── models/        # Tests for domain models
│   ├── services/      # Tests for service layer
│   └── utils/         # Tests for utility functions
├── integration/       # Integration tests spanning multiple components
├── e2e/               # End-to-end tests that test the entire system flow
└── TEST_COVERAGE_PLAN.md  # Plan for improving test coverage
```

## Test Types

### Unit Tests

Unit tests verify that individual components work correctly in isolation, using mocks for dependencies. These are organized by application module.

### Integration Tests

Integration tests verify that components work correctly together, testing the integration points between modules.

### End-to-End Tests

E2E tests verify that the entire system works correctly from a user's perspective, testing complete user flows.

## Naming Conventions

All test files should:
- Be named with the pattern `test_*.py`
- Use descriptive names that indicate what functionality is being tested
- Match the name of the module under test when applicable (e.g., `test_output.py` for `output.py`)

## Test Fixtures

Common test fixtures are located in `tests/common/fixtures/`. Module-specific fixtures can be defined in the test files or in a `conftest.py` file in the relevant directory.

## Running Tests

Run all tests:
```
python -m pytest
```

Run a specific test file:
```
python -m pytest tests/unit/api/test_output.py
```

Run tests with coverage reporting:
```
python -m pytest --cov=app
```

## Test Implementation Philosophy

Tests should:
1. Be simple and focused on a single aspect of functionality
2. Use descriptive names that make it clear what's being tested
3. Follow the "Arrange-Act-Assert" pattern when applicable
4. Minimize setup code by using fixtures and helper functions
5. Be independent of each other and not rely on side effects