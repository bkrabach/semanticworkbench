# Cognition Service

The Cognition Service is a standalone microservice responsible for AI assistant reasoning and response generation. It runs as an independent MCP server using Server-Sent Events (SSE) for communication with the core orchestrator.

## Overview

The Cognition Service offloads LLM processing from the core, delegating all language model interactions to this dedicated service. The design follows Cortex's architectural principles of ruthless simplicity and separation of concerns.

## Key Features

- **Independent SSE Server**: Runs as its own FastMCP server process, exposing an SSE endpoint for the Core to connect
- **Context-Driven Logic**: Processes events from the Core and generates responses using LLMs
- **LLM Interaction Layer**: Uses Pydantic-AI to interface with LLM providers (OpenAI, Anthropic, etc.)
- **Stateless Design**: No persistent state required; each request is processed independently
- **Minimal Implementation**: Direct use of libraries with minimal abstractions

## Architecture

### Components

- **main.py**: Entry point that creates the FastMCP server and exposes MCP tools
- **models.py**: Pydantic models for events and LLM outputs
- **logic.py**: Core logic for handling events and interacting with LLMs
- **config.py**: Configuration settings loaded from environment variables
- **memory_client.py**: Optional MCP client to fetch conversation history

### MCP Tools

The service exposes the following MCP tools:

1. **generate_reply**: Generates an AI assistant reply for a new user message
2. **evaluate_context**: Evaluates context including memory snippets and expert insights
3. **health**: Health check endpoint

## Usage

### Running the Service

Start the Cognition Service with:

```bash
python run_cognition_service.py
```

### Environment Variables

Configure the service using these environment variables:

- `COGNITION_SERVICE_PORT`: Port to run the service on (default: 5000)
- `COGNITION_SERVICE_HOST`: Host to bind to (default: 0.0.0.0)
- `LLM_PROVIDER`: LLM provider to use (default: anthropic)
- `LLM_MODEL_NAME`: Model name to use (default: claude-3-sonnet-20240229)
- `ANTHROPIC_API_KEY`: API key for Anthropic
- `OPENAI_API_KEY`: API key for OpenAI
- `SYSTEM_PROMPT`: System prompt for the LLM
- `MEMORY_SERVICE_URL`: URL of the Memory Service
- `ENABLE_MEMORY`: Enable memory integration (default: false)
- `ENABLE_TOOL_USE`: Enable tool use (default: false)

## Integration with Core

The Core interacts with the Cognition Service using the `CognitionClient` in `app/backend/cognition_client.py`. When a user sends a message, the Core forwards it to the Cognition Service using this client, which then processes the message and returns a response.

### Example Flow

1. User sends a message through the API
2. Core receives the message and publishes a `user_input` event
3. Event handler calls `cognition_client.evaluate_context()`
4. Cognition Service processes the message using an LLM
5. Response is returned to Core
6. Core publishes an `output` event with the response
7. Response is streamed to client via SSE

## Future Enhancements

- Integration with Memory Service to retrieve conversation history
- Tool use implementation for more complex interactions
- Streaming token-by-token replies for a more responsive UI
- Enhanced monitoring and logging for production