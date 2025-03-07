# Cortex Core PoC

This repository contains a minimal viable implementation of the Cortex Core—the central orchestrator of an adaptive AI ecosystem. The core is designed to handle sessions, maintain unified context, perform basic adaptive reasoning, and delegate specialized tasks (e.g., via stub domain expert entities) while exposing standard interfaces (REST API, SSE notifications).

## Directory Structure

```
.
├── api_server.py          # FastAPI REST API endpoint for processing input
├── cortex_core.py         # Core implementation (session, workspace, context, cognition, dispatcher, etc.)
├── client.py              # Example client to send requests and subscribe to notifications
├── notification_queue.py  # Global asynchronous queue for notifications
├── sse_server.py          # SSE server to stream notifications to clients
├── test_core.py           # Pytest unit tests for the Cortex Core
└── README.md              # This file
```

## Features

- **Session & Workspace Management:**  
  Track user sessions and conversation logs.
- **Unified Context (Whiteboard Model):**  
  Simple in‑memory storage for context updates.
- **Adaptive Reasoning:**  
  A basic cognition component that routes code-related inputs to a stub domain expert.
- **Dispatcher & Domain Expert Stub:**  
  Delegates specialized tasks (e.g., code assistance) to a stub domain expert.
- **Integration Hub (Output):**  
  Currently, outputs are printed and can later be extended to support REST, SSE, etc.
- **Security:**  
  Basic token-based authentication.

- **REST API & SSE Endpoint:**  
  Expose endpoints for processing input and streaming notifications.

## Setup & Installation

### Requirements

- Python 3.8+
- Dependencies (install via pip):

```bash
pip install fastapi uvicorn httpx litellm python-dotenv sse-starlette sseclient pydantic pytest
```

### Optional (for testing and development)

- [pytest](https://docs.pytest.org/)

## Running the Project

### 1. Start the API Server

Run the Cortex Core API (exposes the `/process` endpoint):

```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

### 2. Start the SSE Notification Server

In a separate terminal, start the SSE server to stream notifications:

```bash
uvicorn sse_server:app --host 0.0.0.0 --port 8001
```

### 3. Run the Example Client

The `client.py` script demonstrates sending an input request to the API server and subscribing to notifications from the SSE server.

```bash
python client.py
```

### 4. Run the Tests

To execute the unit tests for the Cortex Core:

```bash
pytest test_core.py
```

## Project Overview

The Cortex Core is designed with modularity in mind so that each component (e.g., session management, context handling, cognition, domain experts) can be extended or replaced independently. The PoC currently supports text-based interactions but is structured to easily integrate additional modalities (voice, canvas, native app extensions) and more advanced memory or cognition systems later on.

### Future Enhancements

- Expand input/output modalities (voice, canvas, etc.).
- Replace the whiteboard memory with a robust unified memory system (e.g., JAKE).
- Integrate real domain expert entities and extend the guided conversation protocol.
- Enhance security and authentication mechanisms.
- Extend the integration hub to support multiple transport protocols (REST, SSE, WebRTC).

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests with improvements or new features.

---

This README provides the foundation for setting up and testing the Cortex Core PoC. Let me know if you'd like to add any additional documentation or move on to another file!
