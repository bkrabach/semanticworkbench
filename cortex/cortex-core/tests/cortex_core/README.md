# End-to-End Validation Guide

This document provides a guide for manual end-to-end validation of the Cortex Core system.

## Prerequisites

Before starting the validation, ensure:

1. The Cortex Core server is running: `cd cortex-core && python -m app.main`
2. The Memory service is running
3. The Cognition service is running

## Validation Steps

Follow these steps to validate the system end-to-end:

### 1. Authentication

First, obtain a JWT token for testing:

```bash
# Obtain a token (for development purposes)
curl -X POST http://localhost:8000/auth/login \
  -d "username=user@example.com" \
  -d "password=password123"
```

Save the token for use in subsequent requests:

```bash
export TOKEN="<paste your token here>"
```

Verify the token is valid:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/auth/verify
```

You should see a response confirming authentication is successful.

### 2. Workspace and Conversation Setup

Create a workspace:

```bash
curl -X POST http://localhost:8000/config/workspaces \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workspace",
    "description": "For manual testing",
    "metadata": {}
  }'
```

Save the workspace ID from the response:

```bash
export WORKSPACE_ID="<paste workspace ID here>"
```

Create a conversation in the workspace:

```bash
curl -X POST http://localhost:8000/config/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"workspace_id\": \"$WORKSPACE_ID\",
    \"topic\": \"Test Conversation\",
    \"metadata\": {}
  }"
```

Save the conversation ID from the response:

```bash
export CONVERSATION_ID="<paste conversation ID here>"
```

### 3. Connect to SSE Stream

Open a new terminal window to connect to the SSE stream:

```bash
curl -N -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/output/stream?conversation_id=$CONVERSATION_ID"
```

This will establish a long-running connection that will receive events. Keep this terminal open.

### 4. Send Input Message

In your original terminal, send a message to the system:

```bash
curl -X POST http://localhost:8000/input \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"content\": \"Hello, how are you today?\",
    \"conversation_id\": \"$CONVERSATION_ID\",
    \"metadata\": {}
  }"
```

### 5. Observe the Response

Watch the SSE terminal. You should see:

1. The message being sent to the system (input event)
2. The system processing the message
3. A response from the system (output event)

The response should be formatted as an SSE event, like:

```
event: output
data: {"type":"output","user_id":"...","conversation_id":"...","content":"I'm doing well, thank you for asking!","role":"assistant"}
```

### 6. Verify Error Handling

Test error handling by:

1. Sending a request without authentication:
   ```bash
   curl -X POST http://localhost:8000/input \
     -H "Content-Type: application/json" \
     -d "{\"content\": \"This should fail\", \"conversation_id\": \"$CONVERSATION_ID\"}"
   ```
   You should receive a 401 Unauthorized error.

2. Sending a malformed request:
   ```bash
   curl -X POST http://localhost:8000/input \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"content\": \"Missing conversation ID\"}"
   ```
   You should receive a 422 Validation Error.

### 7. Verify Health Endpoint

Check the system health:

```bash
curl http://localhost:8000/health
```

You should see a response with status information for the core service and connected services.

## Troubleshooting

If the validation fails at any step:

1. Check server logs for error messages
2. Verify all services are running
3. Ensure your token is valid
4. Check that conversation and workspace IDs are correct

## Running Automated Tests

To run the automated tests that validate similar functionality:

```bash
cd cortex-core && python -m pytest tests/cortex_core/test_integration.py -v
```

For testing specific components:

```bash
# Test SSE output streaming
python -m pytest tests/cortex_core/test_output.py -v

# Test end-to-end integration
python -m pytest tests/cortex_core/test_integration.py::test_full_message_flow_with_dependency_overrides -v

# Test all components
python -m pytest tests/cortex_core/ -v
```