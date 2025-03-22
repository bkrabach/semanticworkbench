# Response Handler System

The Cortex Core Response Handler is a powerful component that orchestrates the generation of responses using Large Language Models (LLMs) and tool integrations. It processes user inputs, leverages LLMs to generate appropriate responses, and handles multi-step tool usage to provide rich, informative answers.

## Architecture Overview

The Response Handler system comprises several key components:

1. **ResponseHandler**: The central component that orchestrates the end-to-end processing of user inputs. It stores messages, retrieves conversation context, prepares prompts for the LLM, handles tool execution, and streams responses back to clients.

2. **LLMAdapter**: A flexible adapter that provides a unified interface to different LLM providers (OpenAI, Azure OpenAI, Anthropic). It handles message formatting, API calls, and response parsing.

3. **ToolRegistry**: A registry for tools that can be executed by the ResponseHandler based on LLM requests. It provides a registration mechanism and tool discovery.

4. **Tools**: Concrete implementations of various capabilities that the LLM can use, such as retrieving conversation summaries, fetching user information, or getting the current time.

## Key Features

- **Multi-step Tool Call Resolution**: The system can handle multiple rounds of tool usage in a single conversation turn. The LLM can request tool executions, receive the results, and produce a final answer based on those results.

- **Streaming Output**: Responses are streamed to clients in real-time via Server-Sent Events (SSE), providing a responsive user experience.

- **Modular LLM Integration**: The LLM Adapter supports multiple providers and can be extended to support additional ones as needed.

- **Extensible Tool System**: New tools can be easily added by implementing and registering them with the ToolRegistry.

- **Error Handling**: Robust error handling ensures that failures are properly logged and communicated to clients.

- **Mock Support**: A mock LLM implementation is provided for development and testing when real LLM providers are not available.

## Response Handler Workflow

The Response Handler processes messages through the following steps:

1. **Message Storage**: User messages are stored in the database to maintain conversation history.

2. **Context Retrieval**: Relevant conversation history is retrieved to provide context for the LLM.

3. **Prompt Preparation**: A prompt is constructed with system instructions, conversation history, and the user's current message.

4. **LLM Generation**: The prompt is sent to the LLM via the LLMAdapter to generate a response.

5. **Tool Execution (Optional)**: If the LLM requests a tool, the ResponseHandler executes it and provides the result back to the LLM.

6. **Iteration (Optional)**: Steps 4-5 may repeat multiple times for multi-step tool usage.

7. **Response Storage**: The final response is stored in the database.

8. **Response Streaming**: The final response is streamed to the client via SSE.

## Tool System

The tool system allows the LLM to access additional capabilities beyond its pre-trained knowledge. Tools are registered with the ToolRegistry and can be executed by the ResponseHandler based on LLM requests.

### Tool Registration

Tools are registered using the `@register_tool` decorator:

```python
@register_tool("get_current_time")
async def get_current_time(timezone: Optional[str] = None) -> Dict[str, str]:
    """Get the current date and time."""
    now = datetime.now()
    return {
        "iso_format": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        # ...
    }
```

### Tool Execution

When the LLM generates a response with a tool request (e.g., `{"tool": "get_current_time", "input": {}}`), the ResponseHandler executes the tool and provides the result back to the LLM for further processing.

## LLM Adapter

The LLM Adapter provides a unified interface to different LLM providers. It handles:

- Provider-specific API calls
- Message formatting according to each provider's requirements
- Parsing responses to extract tool requests or final answers
- Fallback to a mock implementation when real providers are unavailable

The adapter is configured through environment variables, making it easy to switch between providers without code changes.

## Integration with Event Bus

The Response Handler integrates with the Cortex Core Event Bus to publish events about message processing and response generation. These events can be used by other components to react to message-related activities.

## API Integration

The Response Handler is integrated with the Cortex Core API through:

1. **Input Endpoint**: The `/input` endpoint receives user messages and dispatches them to the ResponseHandler for processing.

2. **SSE Output Endpoint**: The `/output/stream` endpoint streams responses back to clients using Server-Sent Events (SSE).

## Adding New Tools

To add a new tool to the system:

1. Define a new function that implements the tool's functionality.
2. Decorate it with `@register_tool("tool_name")`.
3. Ensure the function is imported at application startup.

## Adding New LLM Providers

To add a new LLM provider:

1. Update the LLMAdapter class to support the new provider.
2. Add the necessary configuration options to the environment variables.
3. Implement the provider-specific message formatting and API calls.

## Configuration

The Response Handler and LLM Adapter are configured through environment variables:

- `LLM_PROVIDER`: The LLM provider to use (openai, azure_openai, anthropic)
- `LLM_TEMPERATURE`: Controls the randomness of LLM outputs
- `LLM_MAX_TOKENS`: Maximum tokens to generate in LLM responses
- `USE_MOCK_LLM`: Whether to use the mock LLM implementation

Provider-specific variables:

- For OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_API_BASE`
- For Azure OpenAI: `AZURE_OPENAI_KEY`, `AZURE_OPENAI_BASE_URL`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`
- For Anthropic: `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`

## Future Enhancements

Potential enhancements to the Response Handler system include:

- Support for more LLM providers
- Advanced prompt engineering techniques
- More sophisticated tool execution patterns
- Enhanced streaming capabilities
- Improved error handling and recovery
- Performance optimizations
- User-specific configuration options