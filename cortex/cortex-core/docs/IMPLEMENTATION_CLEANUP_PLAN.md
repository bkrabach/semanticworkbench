# Cortex Core Implementation Cleanup Plan

This document outlines the comprehensive plan for cleaning up the Cortex Core codebase by removing legacy code, simplifying implementations, and improving code organization. The changes focus on making the codebase more maintainable and aligned with the project's implementation philosophy of ruthless simplicity.

## Motivation

The Cortex Core codebase has successfully implemented the Phase 3 requirements with a complete MCP architecture. However, the codebase contains several areas with unnecessary complexity:

1. **Inconsistent LLM provider handling** with direct API dependencies
2. **Fallback implementations** for non-MCP scenarios
3. **Test mock code** mixed with production code
4. **Development code** mixed with production code
5. **Overly complex components** with redundant code paths

These issues make the codebase harder to maintain and understand, contradicting the "ruthless simplicity" philosophy of the project.

## Implementation Approach

We'll take a phased approach to cleanup, focusing on these key areas:

1. **LLM Adapter Improvement**
2. **Tools Implementation Cleanup**
3. **Mock LLM Relocation**
4. **Response Handler Optimization**
5. **Development Code Separation**

Each area has a detailed plan document with specific code changes:

- [LLM Adapter Cleanup](LLM_ADAPTER_CLEANUP.md)
- [Tools Cleanup](TOOLS_CLEANUP.md)
- [Mock LLM Cleanup](MOCK_LLM_CLEANUP.md)
- [Response Handler Cleanup](RESPONSE_HANDLER_CLEANUP.md)
- [Development Code Cleanup](DEV_CODE_CLEANUP.md)

## Implementation Schedule

### Phase 1: LLM Adapter Improvement (Day 1)

1. Refactor to use Pydantic AI abstraction consistently
2. Improve configuration system for provider selection
3. Clean up provider-specific implementation blocks
4. Add validation for required environment variables

### Phase 2: Tools Implementation Cleanup (Day 2)

1. Remove fallback implementations in tools.py
2. Simplify MCP client import and usage
3. Remove unnecessary protocol definitions
4. Update tests to assume MCP is always available

### Phase 3: Mock LLM Relocation (Day 3)

1. Move mock LLM to tests/mocks/ directory
2. Simplify implementation for test scenarios
3. Update all test imports and references
4. Remove development-focused features

### Phase 4: Response Handler Optimization (Day 4)

1. Optimize tool execution method
2. Improve streaming implementation
3. Consolidate message delivery code
4. Split large methods into smaller, focused ones

### Phase 5: Development Code Separation (Day 5)

1. Create dedicated development module
2. Move test user creation to development module
3. Implement environment-specific configuration
4. Clean up main.py to conditionally use development features

## Testing Strategy

Each change will require careful testing to ensure we don't break existing functionality:

1. **Unit Tests**: Update unit tests for each modified component
2. **Integration Tests**: Ensure changes don't break component integration
3. **End-to-End Tests**: Validate complete flows from input to output
4. **Manual Testing**: Use the test client to verify changes work in practice

Special attention should be paid to:

- **Response Handling**: Ensure streaming still works properly
- **Tool Execution**: Verify tools execute correctly through MCP
- **LLM Integration**: Test that all provider integrations work as expected
- **Development Experience**: Check that development mode still provides a good experience

## Code Quality Requirements

All changes must adhere to these quality standards:

1. **Type Safety**: All code must be properly typed with mypy passing
2. **Linting**: Code must pass ruff checks
3. **Documentation**: Update docstrings and comments as needed
4. **Consistency**: Follow project code style guidelines
5. **Simplicity**: Prioritize simple, clear code over clever solutions

## Completion Criteria

The cleanup will be considered complete when:

1. All fallback code is removed
2. Mock LLM is moved to the test directory
3. LLM adapter uses Pydantic AI consistently
4. Development code is properly separated
5. All components pass their tests
6. The codebase is simplified as planned

## Benefits

These changes will provide several benefits:

1. **Reduced Complexity**: Less conditional code means easier maintenance
2. **Improved Organization**: Clear separation between production, development, and test code
3. **Better Configuration**: More explicit provider selection and configuration
4. **Cleaner Abstractions**: Pydantic AI provides a consistent interface to LLMs
5. **Easier Testing**: Better test structures and mock implementations
6. **Better Alignment**: Code aligns with the project's "ruthless simplicity" philosophy

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Comprehensive testing after each change |
| Introducing new bugs | Small, incremental changes with tests |
| Affecting development experience | Dedicated development module with clear separation |
| Test coverage gaps | Review and update tests for complete coverage |
| Pydantic AI integration issues | Request additional documentation as needed |