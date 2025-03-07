# Cortex Core Quick Start Guide

This guide provides a minimal working example to get started with the Cortex Core API. Follow these steps to quickly build a basic client that can interact with the Cortex Core platform.

## Prerequisites

- Basic knowledge of JavaScript/HTML
- A running Cortex Core server instance
- A valid authentication token

## HTML Structure

Create a simple HTML file with the following structure:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Cortex Core Client Example</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
      }
      .chat-container {
        border: 1px solid #ddd;
        border-radius: 8px;
        height: 400px;
        overflow-y: auto;
        padding: 10px;
        margin-bottom: 10px;
      }
      .message {
        margin-bottom: 10px;
        padding: 8px 12px;
        border-radius: 18px;
        max-width: 70%;
        word-wrap: break-word;
      }
      .user-message {
        background-color: #e3f2fd;
        margin-left: auto;
        border-bottom-right-radius: 4px;
      }
      .assistant-message {
        background-color: #f1f1f1;
        margin-right: auto;
        border-bottom-left-radius: 4px;
      }
      .message-container {
        display: flex;
        margin-bottom: 8px;
      }
      .message-input {
        flex-grow: 1;
        padding: 8px;
        border: 1px solid #ddd;
        border-radius: 4px;
      }
      .send-button {
        margin-left: 8px;
        padding: 8px 16px;
        background-color: #2196f3;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
      }
      .connection-status {
        margin-bottom: 10px;
        font-size: 14px;
      }
      .status-connected {
        color: green;
      }
      .status-disconnected {
        color: red;
      }
      .typing-indicator {
        display: none;
        font-style: italic;
        color: #666;
        margin-bottom: 8px;
      }
    </style>
  </head>
  <body>
    <h1>Cortex Core Chat</h1>

    <div class="connection-status status-disconnected" id="connectionStatus">
      Disconnected
    </div>

    <div class="chat-container" id="chatContainer"></div>

    <div class="typing-indicator" id="typingIndicator">AI is typing...</div>

    <div class="message-container">
      <input
        type="text"
        class="message-input"
        id="messageInput"
        placeholder="Type your message..."
      />
      <button class="send-button" id="sendButton">Send</button>
    </div>

    <script src="app.js"></script>
  </body>
</html>
```

## JavaScript Implementation

Create a file named `app.js` with the following code:

```javascript
// Configuration
const API_BASE_URL = "http://localhost:8000";
const API_TOKEN = "your-auth-token-here"; // Replace with your actual token

// DOM Elements
const chatContainer = document.getElementById("chatContainer");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const connectionStatus = document.getElementById("connectionStatus");
const typingIndicator = document.getElementById("typingIndicator");

// State
let currentConversation = null;
let eventSource = null;

// Initialize the app
async function initialize() {
  try {
    // Validate the session token
    const sessionResponse = await validateSession();

    if (sessionResponse.valid) {
      updateConnectionStatus("Valid session, creating conversation...");

      // Create a new conversation
      const conversationResponse = await createConversation();
      currentConversation = conversationResponse.conversation;

      // Connect to SSE for real-time updates
      connectToSSE(currentConversation.id);

      // Enable the UI
      messageInput.disabled = false;
      sendButton.disabled = false;

      // Add event listeners
      messageInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          handleSendMessage();
        }
      });

      sendButton.addEventListener("click", handleSendMessage);

      updateConnectionStatus("Connected", true);
    } else {
      updateConnectionStatus("Invalid session token");
    }
  } catch (error) {
    console.error("Initialization error:", error);
    updateConnectionStatus(`Error: ${error.message}`);
  }
}

// API Functions
async function validateSession() {
  const response = await fetch(`${API_BASE_URL}/api/validate-session`, {
    headers: {
      Authorization: `Bearer ${API_TOKEN}`,
    },
  });

  return response.json();
}

async function createConversation() {
  const response = await fetch(`${API_BASE_URL}/api/conversations`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${API_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title: "Quick Start Conversation",
    }),
  });

  return response.json();
}

async function sendMessage(content) {
  const response = await fetch(
    `${API_BASE_URL}/api/conversations/${currentConversation.id}/messages`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${API_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        content,
        role: "user",
      }),
    }
  );

  return response.json();
}

// SSE Functions
function connectToSSE(conversationId) {
  // Close existing connection if any
  if (eventSource) {
    eventSource.close();
  }

  // Create a new SSE connection
  const url = `${API_BASE_URL}/api/sse/conversations/${conversationId}`;

  // Note: In a real application, you might need to use a library that
  // supports custom headers with EventSource, as the native implementation
  // doesn't support this. For simplicity, we're assuming the server allows
  // the token to be passed as a query parameter in this example.
  eventSource = new EventSource(`${url}?token=${API_TOKEN}`);

  // Handle connection open
  eventSource.onopen = () => {
    console.log("SSE connection established");
  };

  // Handle specific events
  eventSource.addEventListener("message_created", handleMessageCreated);
  eventSource.addEventListener("message_updated", handleMessageUpdated);

  // Handle errors
  eventSource.onerror = (error) => {
    console.error("SSE error:", error);
    updateConnectionStatus("Connection error, reconnecting...", false);

    // Attempt to reconnect after a delay
    setTimeout(() => {
      if (currentConversation) {
        connectToSSE(currentConversation.id);
      }
    }, 3000);
  };
}

// Event Handlers
function handleMessageCreated(event) {
  const message = JSON.parse(event.data);

  if (message.role === "assistant") {
    // Show typing indicator for new assistant messages
    typingIndicator.style.display = "block";

    // Only add the message if it doesn't exist yet
    if (!document.getElementById(`message-${message.id}`)) {
      addMessageToUI(message, true);
    }
  }
}

function handleMessageUpdated(event) {
  const message = JSON.parse(event.data);

  if (message.role === "assistant") {
    // Update existing message or add if it doesn't exist
    const existingMessage = document.getElementById(`message-${message.id}`);

    if (existingMessage) {
      existingMessage.textContent = message.content;
    } else {
      addMessageToUI(message);
    }

    // Hide typing indicator if message is complete
    if (message.is_complete) {
      typingIndicator.style.display = "none";
    }
  }
}

async function handleSendMessage() {
  const content = messageInput.value.trim();

  if (content && currentConversation) {
    // Clear input and add message to UI immediately
    messageInput.value = "";

    // Create a temporary message object
    const userMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: content,
    };

    // Add to UI
    addMessageToUI(userMessage);

    try {
      // Send to API
      await sendMessage(content);

      // Show typing indicator
      typingIndicator.style.display = "block";
    } catch (error) {
      console.error("Error sending message:", error);
      alert("Failed to send message. Please try again.");
    }
  }
}

// UI Functions
function addMessageToUI(message, isPartial = false) {
  const messageElement = document.createElement("div");
  messageElement.id = `message-${message.id}`;
  messageElement.className = `message ${message.role}-message`;
  messageElement.textContent = message.content;

  if (isPartial) {
    messageElement.classList.add("partial-message");
  }

  chatContainer.appendChild(messageElement);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function updateConnectionStatus(message, connected = false) {
  connectionStatus.textContent = message;

  if (connected) {
    connectionStatus.className = "connection-status status-connected";
  } else {
    connectionStatus.className = "connection-status status-disconnected";
  }
}

// Start the application
document.addEventListener("DOMContentLoaded", initialize);

// Cleanup on page unload
window.addEventListener("beforeunload", () => {
  if (eventSource) {
    eventSource.close();
  }
});
```

## Running the Example

1. Replace `'your-auth-token-here'` in the JavaScript file with your actual authentication token.
2. Update `API_BASE_URL` if your Cortex Core server is running on a different address.
3. Save both files in the same directory.
4. Open the HTML file in a browser.

## What This Example Demonstrates

- Setting up a basic chat interface
- Authenticating with the Cortex Core API
- Creating a new conversation
- Connecting to the SSE endpoint for real-time updates
- Sending messages to the AI
- Receiving and displaying responses in real-time
- Handling partial message updates (streaming responses)
- Basic error handling and reconnection logic

## Next Steps

After getting this basic example working, you can:

1. Explore the full [Client Integration Guide](CLIENT_INTEGRATION_GUIDE.md) for more advanced features
2. Refer to the [API Reference](CLIENT_API_REFERENCE.md) for detailed endpoint documentation
3. Implement additional features like:
   - Conversation history and management
   - User authentication flow
   - Error handling and retry logic
   - Message formatting and markdown rendering
   - Support for different message types (system messages, tool results)

## Troubleshooting

- **Authentication issues**: Verify your token is valid and correctly formatted in the Authorization header
- **CORS errors**: Ensure your Cortex Core server is configured to allow requests from your client's origin
- **SSE connection failures**: Some environments may require a specialized library for SSE connections with custom headers
- **Streaming not working**: Verify that your server is correctly configured for streaming responses

For more detailed troubleshooting, refer to the full documentation or contact your system administrator.
