# Cortex Core Client Documentation

This documentation provides developers with the necessary information to build client applications that interface with the Cortex Core API. Whether you're building a web application, mobile app, or command-line tool, these resources will help you implement a robust client that communicates effectively with the Cortex Core platform.

## Documentation Overview

This documentation set contains the following resources:

1. [Quick Start Guide](#quick-start-guide)
2. [Client Integration Guide](#CLIENT_INTEGRATION_GUIDE)
3. [API Reference](#api-reference)
4. [Examples](#examples)

## Quick Start Guide

The [Quick Start Guide](CLIENT_QUICKSTART.md) provides a minimal working example to get you started quickly. It includes:

- A simple HTML/JavaScript client implementation
- Basic authentication setup
- Sending messages and receiving responses
- Real-time updates using Server-Sent Events (SSE)

This guide is perfect for developers who want to quickly get a functional client up and running to better understand how the Cortex Core API works.

## Client Integration Guide

The [Client Integration Guide](CLIENT_INTEGRATION_GUIDE.md) offers comprehensive documentation for building robust client applications. It covers:

- Authentication and session management
- Conversation operations (creating, listing, retrieving, deleting)
- Message handling (sending, receiving, streaming)
- Real-time updates with Server-Sent Events (SSE)
- Error handling strategies
- Complete JavaScript and Python client implementations

This guide is ideal for developers building production-ready applications that need to make full use of the Cortex Core API capabilities.

## API Reference

The [API Reference](CLIENT_API_REFERENCE.md) provides a concise technical reference for:

- All API endpoints with request/response formats
- Data models and schemas
- Authentication requirements
- SSE event types and data formats
- Implementation notes and best practices

This reference is designed for developers who need quick access to specific API details while implementing their clients.

## Examples

The documentation includes several complete example implementations:

### JavaScript/TypeScript Client

A complete JavaScript/TypeScript client implementation can be found in the [Client Integration Guide](CLIENT_INTEGRATION_GUIDE.md#client-implementation-examples). This example includes:

- Authentication and session management
- Conversation and message operations
- Real-time updates with SSE
- Error handling

### Python Client

A complete Python client implementation can be found in the [Client Integration Guide](CLIENT_INTEGRATION_GUIDE.md#client-implementation-examples). This example includes:

- Authentication and session management
- Conversation and message operations
- Real-time updates with SSE in a background thread
- Error handling

### HTML/JavaScript Web Client

A simple but complete web client implementation can be found in the [Quick Start Guide](CLIENT_QUICKSTART.md). This example includes:

- A chat interface
- Authentication setup
- Sending and receiving messages
- Real-time updates with SSE

## Key Concepts

### Authentication

Cortex Core uses bearer token authentication. All API requests must include an `Authorization` header with a valid bearer token:

```
Authorization: Bearer <your-token>
```

### Conversations and Messages

The API revolves around two main resources:

1. **Conversations**: Represent a chat session with a history of messages.
2. **Messages**: Individual exchanges within a conversation, with different roles (user, assistant, system, tool).

### Real-time Updates with SSE

Server-Sent Events (SSE) are used for real-time updates, particularly for receiving AI responses. When you send a user message, the API returns immediately with acknowledgment, but the AI's response comes through the SSE connection.

### Message Streaming

AI responses are often streamed word-by-word for a better user experience. This is handled through SSE events:

1. A `message_created` event with `is_complete: false` marks the start of streaming
2. Multiple `message_updated` events provide incremental updates
3. A final `message_updated` event with `is_complete: true` marks the completion

## Best Practices

1. **Always listen for SSE events** when interacting with conversations.
2. **Handle partial messages** during streaming for a better user experience.
3. **Implement reconnection logic** if the SSE connection is lost.
4. **Validate tokens periodically** to ensure the session is still valid.
5. **Properly handle errors** from all API endpoints.

## Development Workflow

A typical development workflow with the Cortex Core API looks like:

1. Authenticate and obtain a valid session token
2. Create a new conversation or list existing conversations
3. Connect to the SSE endpoint for the selected conversation
4. Send user messages and receive AI responses via SSE
5. Update the UI to display the conversation
6. Implement error handling and reconnection logic

## Support and Feedback

For questions, issues, or feedback regarding this documentation or the Cortex Core API, please contact your system administrator or technical support team.

---

This documentation is designed to help you build robust, efficient clients that make the most of the Cortex Core platform's capabilities. Whether you're building a simple chat interface or a complex application with advanced features, these resources provide the information you need to succeed.
