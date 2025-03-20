# Cortex Core Backend Stub Services Documentation

## Overview

This document describes the stub implementations for the backend services that the Cortex Core interacts with via the MCP protocol. It covers two primary stub services:

1. **Memory Service Stub:**

   - Acts as an MCP server that accepts and stores input data.
   - Exposes a tool endpoint (`store_input`) for receiving input events.
   - Provides a resource endpoint (`get_history`) to retrieve stored data by user id.

2. **Cognition Service Stub:**
   - Acts as an MCP server to simulate adaptive reasoning.
   - Exposes an endpoint (`get_context`) that retrieves conversation history.
   - In this stub, it may simply act as a pass-through to the Memory Service, returning the stored history.

These stub services allow the core to simulate full end-to-end behavior in the MVP. They follow predetermined contracts for tools and resources, and their implementations can later be enhanced or replaced with production-grade services.

---

## Memory Service Stub

### Purpose

The Memory Service Stub is designed to:

- Receive user input from the Cortex Core.
- Store the input data (temporarily, in an in-memory store).
- Provide a mechanism to retrieve stored input based on the unique user identifier.

### Interface Contract

The Memory Service Stub exposes two main endpoints:

1. **store_input (Tool):**

   - **Inputs:**
     - `user_id` (string): The unique identifier for the user.
     - `input_data` (object): The input payload provided by the Cortex Core.
   - **Output:**
     - A confirmation object indicating storage success.

2. **get_history (Resource):**
   - **Input:**
     - `user_id` (string): The unique identifier for the user.
   - **Output:**
     - A history object containing the list of stored inputs for that user.

### Sample Code

Below is an example implementation using a hypothetical FastMCP library. In this stub, data is stored in a Python dictionary.

```python
# memory_stub.py
import asyncio
from fastmcp import FastMCP  # Placeholder for the actual FastMCP package
from typing import Dict, List

# In-memory store for input events keyed by unique user id
memory_store: Dict[str, List[dict]] = {}

# Initialize the FastMCP server instance for the Memory Service
mcp = FastMCP("MemoryService")

@mcp.tool()
async def store_input(user_id: str, input_data: dict) -> dict:
    """
    Stores the given input data for the specified user.
    """
    if user_id not in memory_store:
        memory_store[user_id] = []
    memory_store[user_id].append(input_data)
    return {"status": "stored", "user_id": user_id}

@mcp.resource()
async def get_history(user_id: str) -> dict:
    """
    Retrieves the history of stored inputs for the specified user.
    """
    history = memory_store.get(user_id, [])
    return {"history": history, "user_id": user_id}

if __name__ == "__main__":
    import uvicorn
    # Assuming FastMCP provides an ASGI app interface for running the service.
    uvicorn.run("memory_stub:app", host="0.0.0.0", port=9000, reload=True)
```

---

## Cognition Service Stub

### Purpose

The Cognition Service Stub simulates the core's adaptive reasoning component. For the MVP:

- It exposes an endpoint to retrieve context (conversation history).
- It may aggregate data by calling the Memory Service, or simply echo back stored history.
- This stub serves as a placeholder for a more advanced reasoning system.

### Interface Contract

The Cognition Service Stub exposes the following endpoint:

1. **get_context (Tool):**
   - **Inputs:**
     - `user_id` (string): The unique identifier for the user.
   - **Output:**
     - A context object that includes the conversation history for that user.

### Sample Code

Below is an example stub implementation for the Cognition Service.

```python
# cognition_stub.py
import asyncio
from fastmcp import FastMCP  # Placeholder for the actual FastMCP package
from typing import Dict, List

# For simplicity, we simulate context by reusing the memory_store from the Memory Service stub.
# In practice, the Cognition Service could call the Memory Service via its MCP interface.
memory_store: Dict[str, List[dict]] = {}

mcp = FastMCP("CognitionService")

@mcp.tool()
async def get_context(user_id: str) -> dict:
    """
    Retrieves context data for the specified user, simulating adaptive reasoning.
    Here it returns stored history as context.
    """
    history = memory_store.get(user_id, [])
    return {"context": history, "user_id": user_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("cognition_stub:app", host="0.0.0.0", port=9100, reload=True)
```

_Note:_
For integration in the MVP, the Cortex Core will act as an MCP client connecting to these stub services. The stubs here are minimal and meant to simulate responses for initial testing and integration. As the system evolves, these stubs can be enhanced with persistent storage, improved error handling, and more sophisticated reasoning logic.

---

## Summary

This document outlines:

- The purpose and interface contracts for the Memory Service Stub and Cognition Service Stub.
- Sample code implementations using FastMCP.
- A clear definition of the expected inputs and outputs for each service, ensuring that the Cortex Core can integrate with them as an MCP client.

These stub implementations are intended to support end-to-end testing of the Cortex Core MVP and will serve as a foundation on which more advanced services can be built in parallel.
