# LLM Integration in Cortex Core

This document provides information about the LLM (Large Language Model) integration in Cortex Core, explaining how the system communicates with language models.

## Overview

Cortex Core integrates with various LLM providers through [LiteLLM](https://github.com/BerriAI/litellm), a unified interface for multiple LLM providers. This integration allows the CortexRouter to generate real responses to user messages by forwarding them to language models.

## Architecture

The LLM integration follows the service layer pattern used throughout Cortex Core:

```
┌───────────────────┐           ┌───────────────┐           ┌────────────────┐
│   CortexRouter    │           │  LLM Service  │           │     LiteLLM    │
│                   │──────────▶│               │──────────▶│                │
│ (Message Routing) │           │ (LLM Access)  │           │ (Provider API) │
└───────────────────┘           └───────────────┘           └────────────────┘
```

1. **CortexRouter**: Receives input messages, determines when to call the LLM, and manages the message flow
2. **LLM Service**: Provides a clean interface to language models, handling prompts and responses
3. **LiteLLM**: Abstracts away differences between model providers, offering a unified API

## Configuration

LLM integration is configured through environment variables:

- `LLM_DEFAULT_MODEL`: The default model to use (e.g., "openai/gpt-3.5-turbo", "anthropic/claude-3-sonnet")
- `LLM_USE_MOCK`: Set to "true" to run in mock mode (no actual API calls)
- `LLM_TIMEOUT`: Timeout in seconds for LLM API calls

### Provider API Keys

LiteLLM looks for environment variables for provider API keys:

- `OPENAI_API_KEY`: For OpenAI models
- `ANTHROPIC_API_KEY`: For Anthropic models
- Various other provider-specific keys (see LiteLLM documentation)

## Usage in CortexRouter

When the CortexRouter receives a message with ActionType.RESPOND, it:

1. Shows a typing indicator to the client
2. Calls the LLM service with the message content
3. Receives the LLM's response
4. Saves the response to the database
5. Sends the response to the client
6. Turns off the typing indicator

## Error Handling

The integration includes comprehensive error handling:

- If the LLM service fails, a graceful error message is returned
- If LiteLLM is not installed, the service operates in mock mode
- Timeouts prevent hanging on slow API responses
- All errors are properly logged for debugging

## Mock Mode

For development, testing, or environments without API keys, the LLM service can run in mock mode:

- No actual API calls are made
- Responses are echoes of the input with a prefix
- Artificial delays simulate real API latency

## Supported Features

The LLM service provides:

- **Standard Completions**: Regular request/response pattern
- **Streaming Completions**: Real-time streaming of tokens as they're generated
- **System Prompts**: Setting context for the LLM via system messages
- **Temperature Control**: Adjusting the randomness of responses
- **Token Limits**: Setting maximum response lengths

## Supported Providers

Through LiteLLM, the integration supports a wide range of providers:

- OpenAI (GPT-3.5, GPT-4, etc.)
- Anthropic (Claude models)
- Google (Gemini)
- Azure OpenAI
- And many others

See the [LiteLLM documentation](https://docs.litellm.ai/docs/) for a full list of supported providers.

## Future Enhancements

Planned improvements to the LLM integration:

- Tool usage/function calling
- Conversational memory/context
- Prompt templating system
- Cost tracking and optimization
- Advanced routing based on message content