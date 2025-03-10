# ADR 001: Server-Sent Events (SSE) Implementation

## Status

Accepted

## Context

For real-time updates in the Cortex Chat client, we need a reliable mechanism to receive events from the Cortex Core server. The available options include:

1. **Polling**: Regularly requesting updates from the server
2. **WebSockets**: Bi-directional communication channel
3. **Server-Sent Events (SSE)**: Server-to-client push notifications

The Cortex Core platform has implemented a standardized SSE architecture for real-time event distribution, with a clean unified endpoint pattern. We need to determine the best approach for implementing SSE support in the client, considering factors such as:

- Connection reliability
- Reconnection strategies
- Event handling
- Resource management
- Browser compatibility

## Decision

We will implement a dedicated SSE Manager component with the following features:

1. **Centralized Connection Management**:
   - A single manager class that handles all SSE connections
   - Support for multiple concurrent connections (global, workspace, conversation)
   - Proper connection lifecycle management

2. **Robust Reconnection Strategy**:
   - Exponential backoff for failed connections
   - Connection health monitoring
   - Automatic reconnection for transient failures

3. **Event Routing System**:
   - Type-safe event subscription mechanism
   - Channel-based event filtering
   - Support for multiple event handlers per event type

4. **Clean Resource Management**:
   - Explicit connection cleanup on component unmount
   - Prevention of memory leaks from abandoned connections
   - Proper event listener cleanup

5. **Browser Compatibility**:
   - Core support for all modern browsers
   - Optional polyfill for older browsers that don't support EventSource

## Implementation Details

The SSE Manager will be implemented as a TypeScript class with the following key methods:

```typescript
class SSEManager {
  // Core connection management
  connect(channel: ChannelType, resourceId?: string): EventSource;
  disconnect(connectionKey: string): void;
  disconnectAll(): void;
  
  // Event handling
  on(connectionKey: string, eventType: string, callback: EventCallback): void;
  off(connectionKey: string, eventType: string, callback?: EventCallback): void;
  
  // Connection monitoring
  getConnectionStatus(connectionKey: string): ConnectionStatus;
  setTokenProvider(provider: () => string | null): void;
}
```

The implementation will include the following safeguards:

1. **Token Management**:
   - Secure handling of authentication tokens
   - Proper token refreshing when needed
   - Reconnection with new tokens after expiry

2. **Error Handling**:
   - Graceful handling of network failures
   - Clear error reporting
   - Recovery paths for different error scenarios

3. **Event Processing**:
   - Safe parsing of event data
   - Error boundaries for event handlers
   - Consistent event format normalization

## Alternatives Considered

### Polling

**Pros**:
- Simpler implementation
- Works in all browsers
- No long-lived connections

**Cons**:
- Higher server load
- Higher network usage
- Slower updates
- More complex client-side state management

### WebSockets

**Pros**:
- Bi-directional communication
- Potentially better for high-frequency updates
- Support for binary data

**Cons**:
- More complex server implementation
- More difficult to scale
- May require additional libraries
- Cortex Core already standardized on SSE

## Consequences

**Positive**:
- Real-time updates will improve the user experience
- Standardized approach aligns with Cortex Core's architecture
- Reduced server load compared to polling
- Clean separation of concerns in the client architecture

**Negative**:
- Additional complexity in client implementation
- Need to manage connection lifecycle carefully
- Potential for memory leaks if not implemented properly
- Need to handle network interruptions gracefully

**Neutral**:
- Will require thorough testing, especially for reconnection scenarios
- May need adjustments based on real-world performance

## References

1. [Cortex Core SSE Documentation](../cortex-core/docs/SSE.md)
2. [MDN EventSource Reference](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
3. [SSE vs WebSockets](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#EventSource_versus_WebSockets)