# API Integration Guide

This document details how to integrate with the Cortex Core API, focusing on authentication, data exchange, and real-time communication through Server-Sent Events (SSE).

## API Overview

The Cortex Core API provides:

- Authentication services
- Workspace and conversation management
- Message sending and retrieval
- Real-time updates via SSE
- Multi-modal input/output support

## Authentication

### Authentication Flow

1. **Login**:

   ```javascript
   async function login(email, password) {
     try {
       const response = await apiClient.post("/auth/login", {
         email,
         password,
       });

       const { access_token, user } = response.data;

       // Store token securely
       authManager.setToken(access_token);

       return { token: access_token, user };
     } catch (error) {
       handleAuthError(error);
       throw error;
     }
   }
   ```

2. **Token Management**:

   ```javascript
   // authManager.js
   class AuthManager {
     constructor() {
       this.token = null;
     }

     setToken(token) {
       this.token = token;
       localStorage.setItem("auth_token", token);
     }

     getToken() {
       if (!this.token) {
         this.token = localStorage.getItem("auth_token");
       }
       return this.token;
     }

     clearToken() {
       this.token = null;
       localStorage.removeItem("auth_token");
     }

     isAuthenticated() {
       return !!this.getToken();
     }
   }

   export const authManager = new AuthManager();
   ```

3. **Authenticated Requests**:
   ```javascript
   // Using axios interceptors as shown in DEVELOPMENT.md
   ```

## Working with Workspaces

### Fetching Workspaces

```javascript
async function getWorkspaces() {
  try {
    const response = await apiClient.get("/workspaces");
    return response.data.workspaces;
  } catch (error) {
    console.error("Error fetching workspaces:", error);
    throw error;
  }
}
```

### Creating a Workspace

```javascript
async function createWorkspace(name, config = {}) {
  try {
    const response = await apiClient.post("/workspaces", {
      name,
      config: {
        default_modality: "chat",
        sharingEnabled: false,
        retentionDays: 90,
        ...config,
      },
    });

    return response.data;
  } catch (error) {
    console.error("Error creating workspace:", error);
    throw error;
  }
}
```

## Managing Conversations

### Fetching Conversations

```javascript
async function getConversations(workspaceId) {
  try {
    const response = await apiClient.get(
      `/workspaces/${workspaceId}/conversations`
    );
    return response.data.conversations;
  } catch (error) {
    console.error("Error fetching conversations:", error);
    throw error;
  }
}
```

### Creating a Conversation

```javascript
async function createConversation(workspaceId, title, modality = "chat") {
  try {
    const response = await apiClient.post(
      `/workspaces/${workspaceId}/conversations`,
      {
        title,
        modality,
      }
    );

    return response.data;
  } catch (error) {
    console.error("Error creating conversation:", error);
    throw error;
  }
}
```

### Fetching Conversation Details

```javascript
async function getConversation(conversationId) {
  try {
    const response = await apiClient.get(`/conversations/${conversationId}`);
    return response.data;
  } catch (error) {
    console.error("Error fetching conversation:", error);
    throw error;
  }
}
```

## Working with Messages

### Fetching Messages

```javascript
async function getMessages(conversationId) {
  try {
    const response = await apiClient.get(
      `/conversations/${conversationId}/messages`
    );
    return response.data.messages;
  } catch (error) {
    console.error("Error fetching messages:", error);
    throw error;
  }
}
```

### Sending Messages

```javascript
async function sendMessage(
  conversationId,
  content,
  role = "user",
  metadata = {}
) {
  try {
    const response = await apiClient.post(
      `/conversations/${conversationId}/messages`,
      {
        content,
        role,
        metadata,
      }
    );

    return response.data;
  } catch (error) {
    console.error("Error sending message:", error);
    throw error;
  }
}
```

## Real-time Updates with SSE

### SSE Connection Management

```javascript
class SSEClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.connections = {};
    this.listeners = {};
    this.tokenProvider = () => null;
  }

  setTokenProvider(provider) {
    this.tokenProvider = provider;
  }

  connect(channel, resourceId = null) {
    const token = this.tokenProvider();

    if (!token) {
      console.error("No authentication token available");
      return null;
    }

    const connectionKey = resourceId ? `${channel}_${resourceId}` : channel;

    // Close existing connection if any
    this.disconnect(connectionKey);

    // Build SSE URL
    let url;
    switch (channel) {
      case "global":
        url = `${this.baseUrl}/v1/global?token=${token}`;
        break;
      case "workspace":
        url = `${this.baseUrl}/v1/workspace/${resourceId}?token=${token}`;
        break;
      case "conversation":
        url = `${this.baseUrl}/v1/conversation/${resourceId}?token=${token}`;
        break;
      default:
        console.error("Invalid SSE channel type:", channel);
        return null;
    }

    try {
      // Create new EventSource
      const eventSource = new EventSource(url);

      // Set up event handlers
      this.setupEventHandlers(eventSource, connectionKey);

      // Store connection
      this.connections[connectionKey] = eventSource;

      return eventSource;
    } catch (error) {
      console.error("Error creating SSE connection:", error);
      return null;
    }
  }

  disconnect(connectionKey) {
    if (this.connections[connectionKey]) {
      this.connections[connectionKey].close();
      delete this.connections[connectionKey];
    }
  }

  disconnectAll() {
    Object.keys(this.connections).forEach((key) => {
      this.disconnect(key);
    });
  }

  on(connectionKey, eventType, callback) {
    if (!this.listeners[connectionKey]) {
      this.listeners[connectionKey] = {};
    }

    if (!this.listeners[connectionKey][eventType]) {
      this.listeners[connectionKey][eventType] = [];
    }

    this.listeners[connectionKey][eventType].push(callback);

    // If connection exists, add event listener
    if (this.connections[connectionKey]) {
      this.addEventListenerToConnection(connectionKey, eventType);
    }
  }

  off(connectionKey, eventType, callback = null) {
    if (
      !this.listeners[connectionKey] ||
      !this.listeners[connectionKey][eventType]
    ) {
      return;
    }

    if (callback) {
      this.listeners[connectionKey][eventType] = this.listeners[connectionKey][
        eventType
      ].filter((cb) => cb !== callback);
    } else {
      this.listeners[connectionKey][eventType] = [];
    }
  }

  setupEventHandlers(eventSource, connectionKey) {
    // Add standard handlers
    eventSource.onopen = () => {
      console.log(`SSE connection opened: ${connectionKey}`);
      this.triggerEvent(connectionKey, "open", { connectionKey });
    };

    eventSource.onerror = (error) => {
      console.error(`SSE connection error: ${connectionKey}`, error);
      this.triggerEvent(connectionKey, "error", { connectionKey, error });
    };

    // Add handlers for all registered event types
    if (this.listeners[connectionKey]) {
      Object.keys(this.listeners[connectionKey]).forEach((eventType) => {
        this.addEventListenerToConnection(connectionKey, eventType);
      });
    }
  }

  addEventListenerToConnection(connectionKey, eventType) {
    if (!this.connections[connectionKey]) return;

    this.connections[connectionKey].addEventListener(eventType, (event) => {
      try {
        const data = JSON.parse(event.data);
        this.triggerEvent(connectionKey, eventType, data);
      } catch (error) {
        console.error(`Error parsing SSE data for ${eventType}:`, error);
      }
    });
  }

  triggerEvent(connectionKey, eventType, data) {
    if (
      !this.listeners[connectionKey] ||
      !this.listeners[connectionKey][eventType]
    ) {
      return;
    }

    this.listeners[connectionKey][eventType].forEach((callback) => {
      try {
        callback(data);
      } catch (error) {
        console.error(`Error in SSE event handler for ${eventType}:`, error);
      }
    });
  }
}

// Usage
const sseClient = new SSEClient("https://api.example.com");
sseClient.setTokenProvider(() => authManager.getToken());

// Global events
const globalConnection = sseClient.connect("global");
sseClient.on("global", "notification", (data) => {
  console.log("Global notification received:", data);
});

// Workspace events
const workspaceId = "123";
sseClient.connect("workspace", workspaceId);
sseClient.on(`workspace_${workspaceId}`, "conversation_created", (data) => {
  console.log("New conversation created:", data);
});

// Conversation events
const conversationId = "456";
sseClient.connect("conversation", conversationId);
sseClient.on(`conversation_${conversationId}`, "message_received", (data) => {
  console.log("New message received:", data);
});
sseClient.on(`conversation_${conversationId}`, "typing_indicator", (data) => {
  console.log("Typing indicator:", data.isTyping);
});

// Clean up when done
sseClient.disconnectAll();
```

### SSE Event Types

#### Global Events

- `notification`: System-wide notifications
- `system_update`: Platform status updates

#### Workspace Events

- `conversation_created`: New conversation created
- `conversation_deleted`: Conversation deleted
- `workspace_update`: Workspace settings changed

#### Conversation Events

- `message_received`: New message received
- `typing_indicator`: User typing indicator
- `status_update`: Conversation status changes

## Error Handling

### API Error Structure

API errors follow a consistent structure:

```javascript
{
  "error": {
    "code": "authentication_failed",
    "message": "Invalid credentials provided",
    "details": {
      // Additional error context
    }
  }
}
```

### Error Handling Strategy

```javascript
function handleApiError(error) {
  if (!error.response) {
    // Network error
    return {
      type: "network",
      message: "Network error, please check your connection",
    };
  }

  const status = error.response.status;
  const data = error.response.data;

  switch (status) {
    case 400:
      return {
        type: "validation",
        message: data.error?.message || "Invalid request",
        details: data.error?.details,
      };
    case 401:
      return {
        type: "authentication",
        message: "Authentication required",
      };
    case 403:
      return {
        type: "authorization",
        message: "You don't have permission to perform this action",
      };
    case 404:
      return {
        type: "not_found",
        message: "The requested resource was not found",
      };
    case 429:
      return {
        type: "rate_limit",
        message: "Rate limit exceeded, please try again later",
      };
    case 500:
    case 502:
    case 503:
    case 504:
      return {
        type: "server",
        message: "Server error, please try again later",
      };
    default:
      return {
        type: "unknown",
        message: data.error?.message || "An unexpected error occurred",
      };
  }
}
```

## Multi-modal Support

### Chat (Text) Modality

Covered in previous examples.

### Voice Modality

```javascript
async function sendVoiceInput(conversationId, audioBlob) {
  try {
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.wav");

    const response = await fetch(
      `${API_URL}/conversations/${conversationId}/voice`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${authManager.getToken()}`,
        },
        body: formData,
      }
    );

    if (!response.ok) {
      throw new Error(`Voice input failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error sending voice input:", error);
    throw error;
  }
}
```

### Canvas Modality

```javascript
async function sendCanvasInput(conversationId, canvasElement) {
  try {
    // Convert canvas to blob
    const blob = await new Promise((resolve) => {
      canvasElement.toBlob(resolve, "image/png");
    });

    const formData = new FormData();
    formData.append("image", blob, "canvas.png");

    const response = await fetch(
      `${API_URL}/conversations/${conversationId}/canvas`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${authManager.getToken()}`,
        },
        body: formData,
      }
    );

    if (!response.ok) {
      throw new Error(`Canvas input failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error sending canvas input:", error);
    throw error;
  }
}
```

## Performance Considerations

### Request Batching

For operations requiring multiple requests, consider batching:

```javascript
async function batchUpdateConversations(workspaceId, updates) {
  try {
    const response = await apiClient.post(
      `/workspaces/${workspaceId}/conversations/batch`,
      {
        operations: updates,
      }
    );

    return response.data;
  } catch (error) {
    console.error("Error performing batch update:", error);
    throw error;
  }
}
```

### Caching Strategies

Implement appropriate caching for frequently accessed data:

```javascript
// Using a simple cache
class ApiCache {
  constructor(ttl = 60000) {
    // Default TTL: 1 minute
    this.cache = new Map();
    this.ttl = ttl;
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;

    if (Date.now() > item.expiry) {
      this.cache.delete(key);
      return null;
    }

    return item.value;
  }

  set(key, value) {
    const expiry = Date.now() + this.ttl;
    this.cache.set(key, { value, expiry });
  }

  invalidate(key) {
    this.cache.delete(key);
  }

  invalidatePattern(pattern) {
    const regex = new RegExp(pattern);
    for (const key of this.cache.keys()) {
      if (regex.test(key)) {
        this.cache.delete(key);
      }
    }
  }
}

const apiCache = new ApiCache();

// Example usage with the cache
async function getCachedConversations(workspaceId) {
  const cacheKey = `conversations_${workspaceId}`;

  // Try to get from cache first
  const cached = apiCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  // If not in cache, fetch from API
  try {
    const response = await apiClient.get(
      `/workspaces/${workspaceId}/conversations`
    );
    const conversations = response.data.conversations;

    // Cache the result
    apiCache.set(cacheKey, conversations);

    return conversations;
  } catch (error) {
    console.error("Error fetching conversations:", error);
    throw error;
  }
}

// Invalidate cache when creating a new conversation
async function createConversationWithCacheInvalidation(
  workspaceId,
  title,
  modality = "chat"
) {
  try {
    const response = await apiClient.post(
      `/workspaces/${workspaceId}/conversations`,
      {
        title,
        modality,
      }
    );

    // Invalidate the conversations cache for this workspace
    apiCache.invalidate(`conversations_${workspaceId}`);

    return response.data;
  } catch (error) {
    console.error("Error creating conversation:", error);
    throw error;
  }
}
```

## Security Best Practices

- Always use HTTPS for API communication
- Store tokens securely (HttpOnly cookies where possible)
- Implement proper token refresh mechanisms
- Validate all user inputs before sending to API
- Handle errors securely (avoid exposing sensitive information)
- Implement proper logout procedures that clear tokens

## Conclusion

This guide covers the essentials of integrating with the Cortex Core API. For more detailed information about specific endpoints and parameters, refer to the [Cortex Core API Reference](../../cortex-core/docs/API_REFERENCE.md) document.

When implementing your integration, always consider:

- User experience during errors and slow connections
- Proper handling of authentication state
- Efficient management of real-time connections
- Appropriate error reporting for different scenarios
- Performance optimization for your specific use case
