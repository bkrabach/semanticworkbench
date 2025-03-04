# Cortex Platform - Implementation Plan

This document provides a detailed implementation plan for the Cortex Platform, focusing on practical steps to build a 3-day Proof of Concept (PoC) that demonstrates the key architectural concepts.

## 1. Technical Specifications

### 1.1 Backend Services

#### 1.1.1 Central AI Core (Python/FastAPI)

- **Service Structure**

  ```
  cortex-core/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py                 # FastAPI entry point
  │   ├── config.py               # Configuration handling
  │   ├── api/                    # API endpoints
  │   │   ├── __init__.py
  │   │   ├── chat.py             # Chat endpoints
  │   │   ├── openai_compat.py    # OpenAI-compatible endpoints
  │   │   └── workspaces.py       # Workspace management
  │   ├── core/                   # Core functionality
  │   │   ├── __init__.py
  │   │   ├── ai_manager.py       # LLM integration
  │   │   ├── memory.py           # Memory management
  │   │   ├── cognition.py        # Reasoning & decisions
  │   │   └── task_orchestrator.py # Task management
  │   ├── io/                     # I/O handlers
  │   │   ├── __init__.py
  │   │   ├── chat.py             # Text processing
  │   │   ├── voice.py            # Voice processing
  │   │   └── canvas.py           # Visual input/output
  │   ├── mcp/                    # MCP integration
  │   │   ├── __init__.py
  │   │   ├── client.py           # MCP client
  │   │   └── handler.py          # MCP message handling
  │   └── models/                 # Data models
  │       ├── __init__.py
  │       ├── message.py          # Message structures
  │       ├── workspace.py        # Workspace model
  │       └── user.py             # User information
  ├── tests/                      # Test suite
  ├── requirements.txt            # Dependencies
  └── README.md                   # Documentation
  ```

- **Dependencies**
  ```
  fastapi>=0.100.0
  uvicorn>=0.22.0
  pydantic>=2.0.0
  mcp-sdk>=0.1.0
  langchain>=0.0.200
  openai>=0.27.0
  requests>=2.31.0
  tiktoken>=0.4.0
  ```

#### 1.1.2 Memory System (JAKE)

- Simplified version of JAKE for PoC
- Key-value store with vector embeddings
- Persistence using SQLite for the PoC

#### 1.1.3 Domain Expert Systems

- Implement as separate MCP servers
- Modular design for easy replacement
- Simple API for the PoC, expandable later

### 1.2 Frontend Application

#### 1.2.1 React/TypeScript with Vite

- **Project Structure**

  ```
  cortex-ui/
  ├── src/
  │   ├── components/             # UI components
  │   │   ├── chat/               # Chat interface
  │   │   ├── voice/              # Voice interface
  │   │   ├── canvas/             # Canvas interface
  │   │   ├── dashboard/          # Dashboard components
  │   │   ├── workspace/          # Workspace management
  │   │   └── common/             # Shared components
  │   ├── hooks/                  # Custom React hooks
  │   ├── services/               # API services
  │   │   ├── api.ts              # Base API handling
  │   │   ├── chat.ts             # Chat service
  │   │   ├── voice.ts            # Voice service
  │   │   └── workspace.ts        # Workspace service
  │   ├── store/                  # State management
  │   │   ├── index.ts            # Store configuration
  │   │   ├── chat.ts             # Chat state
  │   │   └── workspace.ts        # Workspace state
  │   ├── types/                  # TypeScript types
  │   ├── utils/                  # Utility functions
  │   ├── App.tsx                 # Main application
  │   └── main.tsx                # Entry point
  ├── public/                     # Static assets
  ├── index.html                  # HTML template
  ├── package.json                # Dependencies
  ├── tsconfig.json               # TypeScript config
  ├── vite.config.ts              # Vite configuration
  └── README.md                   # Documentation
  ```

- **Dependencies**
  ```json
  {
    "dependencies": {
      "react": "^18.2.0",
      "react-dom": "^18.2.0",
      "@fluentui/react": "^8.110.0",
      "axios": "^1.4.0",
      "react-markdown": "^8.0.7",
      "react-router-dom": "^6.14.1",
      "zustand": "^4.3.9"
    },
    "devDependencies": {
      "@types/react": "^18.2.15",
      "@types/react-dom": "^18.2.7",
      "typescript": "^5.1.6",
      "vite": "^4.4.4"
    }
  }
  ```

### 1.3 MCP Servers

#### 1.3.1 VS Code MCP Server (TypeScript)

- Provides code context, file operations
- Integrates with existing VS Code extension capabilities

#### 1.3.2 Browser MCP Server (Python)

- Implements Playwright for web automation
- Provides web content analysis

## 2. Day-by-Day Implementation Plan

### 2.1 Day 1: Core Framework & Basic UI

#### 2.1.1 Backend Setup (2 hours)

- Initialize FastAPI project
- Configure basic routes and middleware
- Set up project structure
- Implement simple LLM integration with OpenAI

```python
# app/main.py
from fastapi import FastAPI
from app.api import chat, openai_compat, workspaces

app = FastAPI(title="Cortex AI Platform")

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(openai_compat.router, prefix="/v1", tags=["openai-compat"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["workspaces"])

@app.get("/")
async def root():
    return {"message": "Welcome to Cortex AI Platform"}
```

```python
# app/api/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.ai_manager import process_message

router = APIRouter()

class ChatMessage(BaseModel):
    content: str
    workspace_id: str = "default"

class ChatResponse(BaseModel):
    response: str

@router.post("/send", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    try:
        response = await process_message(message.content, message.workspace_id)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### 2.1.2 Frontend Setup (2 hours)

- Initialize React/TS with Vite
- Configure project structure
- Set up Fluent UI components
- Create basic state management

```typescript
// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { initializeIcons } from "@fluentui/react";
import App from "./App";
import "./index.css";

// Initialize Fluent UI icons
initializeIcons();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

```typescript
// src/App.tsx
import { useState } from "react";
import { Stack, ThemeProvider, createTheme } from "@fluentui/react";
import ChatInterface from "./components/chat/ChatInterface";
import Sidebar from "./components/common/Sidebar";
import "./App.css";

const theme = createTheme({
  palette: {
    themePrimary: "#0078d4",
  },
});

function App() {
  const [currentWorkspace, setCurrentWorkspace] = useState("default");

  return (
    <ThemeProvider theme={theme}>
      <Stack horizontal className="app-container">
        <Sidebar
          currentWorkspace={currentWorkspace}
          onWorkspaceChange={setCurrentWorkspace}
        />
        <ChatInterface workspaceId={currentWorkspace} />
      </Stack>
    </ThemeProvider>
  );
}

export default App;
```

#### 2.1.3 Core AI Integration (2 hours)

- Implement basic memory management
- Set up conversation handling
- Create simple AI prompt templates

```python
# app/core/ai_manager.py
from openai import AsyncOpenAI
from app.core.memory import MemoryManager
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
memory_manager = MemoryManager()

async def process_message(content: str, workspace_id: str) -> str:
    # Get conversation history from memory
    history = memory_manager.get_conversation_history(workspace_id)

    # Prepare the messages for the API call
    messages = [
        {"role": "system", "content": "You are Cortex, an intelligent AI assistant."},
        *history,
        {"role": "user", "content": content}
    ]

    # Call the OpenAI API
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=0.7,
    )

    # Extract the response content
    response_content = response.choices[0].message.content

    # Save the exchange to memory
    memory_manager.add_interaction(workspace_id,
                                   {"role": "user", "content": content},
                                   {"role": "assistant", "content": response_content})

    return response_content
```

#### 2.1.4 Chat Interface (2 hours)

- Build the chat message components
- Implement chat input and message display
- Add basic styling

```typescript
// src/components/chat/ChatInterface.tsx
import { useState, useEffect } from "react";
import {
  Stack,
  TextField,
  PrimaryButton,
  MessageBar,
  MessageBarType,
} from "@fluentui/react";
import ChatMessage from "./ChatMessage";
import { sendChatMessage } from "../../services/chat";
import "./ChatInterface.css";

interface ChatInterfaceProps {
  workspaceId: string;
}

function ChatInterface({ workspaceId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<
    Array<{ role: string; content: string }>
  >([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    // Add user message to UI immediately
    setMessages([...messages, { role: "user", content: input }]);

    // Clear input and set loading state
    setInput("");
    setIsLoading(true);
    setError(null);

    try {
      // Send message to API
      const response = await sendChatMessage(input, workspaceId);

      // Add assistant response
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.response },
      ]);
    } catch (err) {
      setError("Failed to send message. Please try again.");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Stack className="chat-container">
      <Stack className="messages-container">
        {messages.map((msg, index) => (
          <ChatMessage key={index} role={msg.role} content={msg.content} />
        ))}
        {isLoading && <div className="loading-indicator">Thinking...</div>}
        {error && (
          <MessageBar messageBarType={MessageBarType.error}>{error}</MessageBar>
        )}
      </Stack>

      <Stack horizontal className="input-container">
        <TextField
          placeholder="Type your message here..."
          value={input}
          onChange={(_, newValue) => setInput(newValue || "")}
          onKeyDown={(e) =>
            e.key === "Enter" && !e.shiftKey && handleSendMessage()
          }
          multiline
          autoAdjustHeight
          className="chat-input"
        />
        <PrimaryButton
          onClick={handleSendMessage}
          disabled={isLoading || !input.trim()}
          iconProps={{ iconName: "Send" }}
        >
          Send
        </PrimaryButton>
      </Stack>
    </Stack>
  );
}

export default ChatInterface;
```

### 2.2 Day 2: MCP Integration & I/O Enhancements

#### 2.2.1 MCP Protocol Handler (3 hours)

- Implement the MCP client functionality
- Create server connection management
- Set up message routing

```python
# app/mcp/client.py
import asyncio
import json
from typing import Dict, List, Any, Optional
from app.config import settings

class MCPClient:
    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.server_processes: Dict[str, asyncio.subprocess.Process] = {}

    async def initialize_servers(self):
        """Initialize all configured MCP servers"""
        for server_name, config in settings.MCP_SERVERS.items():
            await self.connect_server(server_name, config)

    async def connect_server(self, server_name: str, config: Dict[str, Any]):
        """Connect to an MCP server"""
        try:
            # Start the server process
            process = await asyncio.create_subprocess_exec(
                config["command"],
                *config.get("args", []),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=config.get("env", {})
            )

            self.server_processes[server_name] = process

            # Get server capabilities
            capabilities = await self._get_server_capabilities(server_name)

            self.servers[server_name] = {
                "process": process,
                "capabilities": capabilities
            }

            print(f"Connected to MCP server: {server_name}")
            return True

        except Exception as e:
            print(f"Failed to connect to MCP server {server_name}: {e}")
            return False

    async def _get_server_capabilities(self, server_name: str) -> Dict[str, Any]:
        """Get capabilities from an MCP server"""
        # Send a capabilities request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getCapabilities",
            "params": {}
        }

        response = await self._send_request(server_name, request)
        return response.get("result", {})

    async def call_tool(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on an MCP server"""
        if server_name not in self.servers:
            raise ValueError(f"MCP server '{server_name}' not connected")

        # Check if tool exists
        capabilities = self.servers[server_name]["capabilities"]
        tools = capabilities.get("tools", {})

        if tool_name not in tools:
            raise ValueError(f"Tool '{tool_name}' not available on server '{server_name}'")

        # Prepare the request
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "callTool",
            "params": {
                "name": tool_name,
                "arguments": args
            }
        }

        # Send the request and return the result
        response = await self._send_request(server_name, request)
        return response.get("result", {})

    async def _send_request(self, server_name: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to an MCP server and get the response"""
        process = self.server_processes[server_name]

        # Ensure stdin and stdout are available
        if process.stdin is None or process.stdout is None:
            raise RuntimeError(f"MCP server {server_name} process streams not available")

        # Send the request
        request_str = json.dumps(request) + "\n"
        process.stdin.write(request_str.encode())
        await process.stdin.drain()

        # Read the response
        response_line = await process.stdout.readline()
        response = json.loads(response_line.decode())

        return response

    async def close(self):
        """Close all MCP server connections"""
        for server_name, process in self.server_processes.items():
            if process.returncode is None:  # Process is still running
                process.terminate()
                await process.wait()
            print(f"Disconnected from MCP server: {server_name}")

# Singleton instance
mcp_client = MCPClient()
```

#### 2.2.2 Voice Input/Output (2 hours)

- Implement basic speech-to-text
- Add text-to-speech capabilities
- Integrate with chat interface

```python
# app/io/voice.py
import base64
import tempfile
import os
from typing import Optional
import requests
from app.config import settings

class VoiceProcessor:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY

    async def speech_to_text(self, audio_data: bytes) -> Optional[str]:
        """Convert speech audio to text using OpenAI Whisper API"""
        try:
            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            # Call OpenAI API
            with open(temp_file_path, "rb") as audio_file:
                response = requests.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.openai_api_key}"},
                    files={"file": audio_file},
                    data={"model": "whisper-1"}
                )

            # Clean up temp file
            os.unlink(temp_file_path)

            # Process response
            if response.status_code == 200:
                return response.json().get("text")
            else:
                print(f"Error in speech-to-text: {response.text}")
                return None

        except Exception as e:
            print(f"Speech-to-text error: {e}")
            return None

    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech using OpenAI TTS API"""
        try:
            response = requests.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": "alloy"
                }
            )

            if response.status_code == 200:
                return response.content
            else:
                print(f"Error in text-to-speech: {response.text}")
                return None

        except Exception as e:
            print(f"Text-to-speech error: {e}")
            return None

# Add API endpoints for voice
```

#### 2.2.3 First Domain Expert System (3 hours)

- Create a basic Code Assistant domain expert
- Implement VS Code MCP server connector
- Test basic functionality

```typescript
// TypeScript MCP Server for VS Code integration
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import * as fs from "fs/promises";
import * as path from "path";
import * as vscode from "vscode"; // This would be part of a VS Code extension

const server = new McpServer({
  name: "Cortex Code Assistant",
  version: "0.1.0",
});

// Tool to list files in workspace
server.tool(
  "list-files",
  { folderPath: z.string().optional() },
  async ({ folderPath }) => {
    try {
      const workspaceFolders = vscode.workspace.workspaceFolders;

      if (!workspaceFolders) {
        return {
          content: [{ type: "text", text: "No workspace folders open" }],
          isError: true,
        };
      }

      let targetPath: string;

      if (folderPath) {
        targetPath = path.isAbsolute(folderPath)
          ? folderPath
          : path.join(workspaceFolders[0].uri.fsPath, folderPath);
      } else {
        targetPath = workspaceFolders[0].uri.fsPath;
      }

      const files = await fs.readdir(targetPath);

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(files, null, 2),
          },
        ],
      };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error: ${err.message}` }],
        isError: true,
      };
    }
  }
);

// Tool to read file contents
server.tool("read-file", { filePath: z.string() }, async ({ filePath }) => {
  try {
    const workspaceFolders = vscode.workspace.workspaceFolders;

    if (!workspaceFolders) {
      return {
        content: [{ type: "text", text: "No workspace folders open" }],
        isError: true,
      };
    }

    const targetPath = path.isAbsolute(filePath)
      ? filePath
      : path.join(workspaceFolders[0].uri.fsPath, filePath);

    const content = await fs.readFile(targetPath, "utf-8");

    return {
      content: [{ type: "text", text: content }],
    };
  } catch (err) {
    return {
      content: [{ type: "text", text: `Error: ${err.message}` }],
      isError: true,
    };
  }
});

// Tool to write to a file
server.tool(
  "write-file",
  {
    filePath: z.string(),
    content: z.string(),
  },
  async ({ filePath, content }) => {
    try {
      const workspaceFolders = vscode.workspace.workspaceFolders;

      if (!workspaceFolders) {
        return {
          content: [{ type: "text", text: "No workspace folders open" }],
          isError: true,
        };
      }

      const targetPath = path.isAbsolute(filePath)
        ? filePath
        : path.join(workspaceFolders[0].uri.fsPath, filePath);

      await fs.writeFile(targetPath, content, "utf-8");

      return {
        content: [
          { type: "text", text: `File written successfully: ${filePath}` },
        ],
      };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error: ${err.message}` }],
        isError: true,
      };
    }
  }
);

const transport = new StdioServerTransport();
server.connect(transport);
```

### 2.3 Day 3: Workspaces & Polish

#### 2.3.1 Workspace Implementation (3 hours)

- Create workspace data structures
- Implement persistence layer
- Add workspace management UI

```python
# app/models/workspace.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

class Workspace(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Project X",
                "description": "AI assistant for medical research",
                "created_at": "2025-03-04T12:30:45.123Z",
                "updated_at": "2025-03-04T14:20:30.456Z",
                "metadata": {
                    "tags": ["medical", "research", "assistant"],
                    "collaborators": ["user1", "user2"]
                }
            }
        }
```

```python
# app/api/workspaces.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.models.workspace import Workspace
from app.core.workspace_manager import get_workspaces, create_workspace, get_workspace, update_workspace, delete_workspace

router = APIRouter()

@router.get("/", response_model=List[Workspace])
async def list_workspaces():
    """Get all workspaces"""
    return await get_workspaces()

@router.post("/", response_model=Workspace)
async def add_workspace(workspace: Workspace):
    """Create a new workspace"""
    return await create_workspace(workspace)

@router.get("/{workspace_id}", response_model=Workspace)
async def get_workspace_by_id(workspace_id: str):
    """Get a workspace by ID"""
    workspace = await get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace

@router.put("/{workspace_id}", response_model=Workspace)
async def update_workspace_by_id(workspace_id: str, workspace_update: Workspace):
    """Update a workspace"""
    updated = await update_workspace(workspace_id, workspace_update)
    if not updated:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return updated

@router.delete("/{workspace_id}")
async def delete_workspace_by_id(workspace_id: str):
    """Delete a workspace"""
    success = await delete_workspace(workspace_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"message": "Workspace deleted successfully"}
```

#### 2.3.2 Browser MCP Server (2 hours)

- Set up Playwright-based automation
- Create web content extraction tools
- Test basic functionality

```python
# browser_mcp_server.py (Separate Python process)
from mcp.server.fastmcp import FastMCP
from playwright.sync_api import sync_playwright
import json

mcp = FastMCP("Cortex Browser Assistant")

@mcp.tool()
def visit_webpage(url: str) -> str:
    """Visit a webpage and return its content"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        content = page.content()
        browser.close()
        return content

@mcp.tool()
def take_screenshot(url: str) -> str:
    """Visit a webpage and take a screenshot"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        # Take screenshot and convert to base64
        screenshot_bytes = page.screenshot()
        browser.close()

        import base64
        return base64.b64encode(screenshot_bytes).decode('utf-8')

@mcp.tool()
def extract_text(url: str) -> str:
    """Extract visible text from a webpage"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        # Extract text content
        text = page.evaluate("""() => {
            return document.body.innerText;
        }""")

        browser.close()
        return text

if __name__ == "__main__":
    mcp.run()
```

#### 2.3.3 Documentation & Final Polish (3 hours)

- Complete API documentation
- Add project setup instructions
- Fix critical issues
- Optimization

## 3. Code Examples for Key Components

### 3.1 LLM Integration with OpenAI

```python
# app/core/ai_manager.py (expanded with better prompting)
from openai import AsyncOpenAI
from app.core.memory import MemoryManager
from app.config import settings
import json

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
memory_manager = MemoryManager()

# System prompt template
SYSTEM_PROMPT = """
You are Cortex, an advanced AI assistant with the following capabilities:
- Answering questions and providing information
- Assisting with coding and technical tasks
- Helping with document creation and editing
- Providing recommendations and suggestions

You have access to various tools through a system called MCP (Model Context Protocol).
These tools allow you to interact with the user's environment.

When you respond:
- Be concise and helpful
- Use markdown formatting for clarity when appropriate
- If you need to use a tool, indicate this clearly
"""

async def process_message(content: str, workspace_id: str, tools=None) -> str:
    """Process a user message and generate a response"""
    # Get conversation history from memory
    history = memory_manager.get_conversation_history(workspace_id)

    # Prepare the messages for the API call
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": content}
    ]

    # Add tools information if available
    api_params = {
        "model": "gpt-4",
        "messages": messages,
        "temperature": 0.7,
    }

    if tools:
        api_params["tools"] = tools

    # Call the OpenAI API
    response = await client.chat.completions.create(**api_params)

    # Extract the response content
    response_content = response.choices[0].message.content

    # Process tool calls if present
    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        # Handle tool calls logic here
        pass

    # Save the exchange to memory
    memory_manager.add_interaction(workspace_id,
                                   {"role": "user", "content": content},
                                   {"role": "assistant", "content": response_content})

    return response_content
```

### 3.2 React Component for Workspace Management

```typescript
// src/components/workspace/WorkspaceManager.tsx
import { useState, useEffect } from "react";
import {
  Stack,
  PrimaryButton,
  DetailsList,
  IColumn,
  SelectionMode,
  Dialog,
  DialogType,
  DialogFooter,
  DefaultButton,
  TextField,
  Text,
} from "@fluentui/react";
import {
  createWorkspace,
  getWorkspaces,
  deleteWorkspace,
} from "../../services/workspace";

interface Workspace {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

function WorkspaceManager() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showDialog, setShowDialog] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Define the columns for the table
  const columns: IColumn[] = [
    {
      key: "name",
      name: "Name",
      fieldName: "name",
      minWidth: 100,
      maxWidth: 200,
    },
    {
      key: "description",
      name: "Description",
      fieldName: "description",
      minWidth: 200,
    },
    {
      key: "created",
      name: "Created",
      fieldName: "created_at",
      minWidth: 100,
      onRender: (item: Workspace) => {
        return new Date(item.created_at).toLocaleString();
      },
    },
    {
      key: "actions",
      name: "Actions",
      minWidth: 100,
      onRender: (item: Workspace) => (
        <Stack horizontal tokens={{ childrenGap: 8 }}>
          <DefaultButton
            iconProps={{ iconName: "Delete" }}
            onClick={() => {
              setDeleteId(item.id);
              setShowDeleteDialog(true);
            }}
          >
            Delete
          </DefaultButton>
        </Stack>
      ),
    },
  ];

  // Load workspaces on component mount
  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    setIsLoading(true);
    try {
      const data = await getWorkspaces();
      setWorkspaces(data);
    } catch (error) {
      console.error("Failed to load workspaces:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateWorkspace = async () => {
    if (!newName.trim()) return;

    setIsLoading(true);
    try {
      await createWorkspace({
        name: newName,
        description: newDescription,
      });
      setShowDialog(false);
      setNewName("");
      setNewDescription("");
      loadWorkspaces();
    } catch (error) {
      console.error("Failed to create workspace:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteWorkspace = async () => {
    if (!deleteId) return;

    setIsLoading(true);
    try {
      await deleteWorkspace(deleteId);
      setShowDeleteDialog(false);
      setDeleteId(null);
      loadWorkspaces();
    } catch (error) {
      console.error("Failed to delete workspace:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Stack tokens={{ padding: 20, childrenGap: 20 }}>
      <Stack horizontal horizontalAlign="space-between">
        <Text variant="xxLarge">Workspaces</Text>
        <PrimaryButton
          iconProps={{ iconName: "Add" }}
          onClick={() => setShowDialog(true)}
          disabled={isLoading}
        >
          New Workspace
        </PrimaryButton>
      </Stack>

      <DetailsList
        items={workspaces}
        columns={columns}
        selectionMode={SelectionMode.none}
        isHeaderVisible={true}
      />

      {/* Create Workspace Dialog */}
      <Dialog
        hidden={!showDialog}
        onDismiss={() => setShowDialog(false)}
        dialogContentProps={{
          type: DialogType.normal,
          title: "Create New Workspace",
        }}
      >
        <TextField
          label="Name"
          required
          value={newName}
          onChange={(_, newValue) => setNewName(newValue || "")}
        />
        <TextField
          label="Description"
          multiline
          rows={3}
          value={newDescription}
          onChange={(_, newValue) => setNewDescription(newValue || "")}
        />
        <DialogFooter>
          <PrimaryButton
            onClick={handleCreateWorkspace}
            disabled={!newName.trim() || isLoading}
          >
            Create
          </PrimaryButton>
          <DefaultButton onClick={() => setShowDialog(false)}>
            Cancel
          </DefaultButton>
        </DialogFooter>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        hidden={!showDeleteDialog}
        onDismiss={() => setShowDeleteDialog(false)}
        dialogContentProps={{
          type: DialogType.normal,
          title: "Delete Workspace",
          subText:
            "Are you sure you want to delete this workspace? This action cannot be undone.",
        }}
      >
        <DialogFooter>
          <PrimaryButton onClick={handleDeleteWorkspace} disabled={isLoading}>
            Delete
          </PrimaryButton>
          <DefaultButton onClick={() => setShowDeleteDialog(false)}>
            Cancel
          </DefaultButton>
        </DialogFooter>
      </Dialog>
    </Stack>
  );
}

export default WorkspaceManager;
```

## 4. Deployment Configuration

### 4.1 Local Development

```bash
# Start backend
cd cortex-core
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Start frontend
cd cortex-ui
npm install
npm run dev
```

### 4.2 Azure Deployment (Placeholder)

```yaml
# azure-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cortex-platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: cortex
  template:
    metadata:
      labels:
        app: cortex
    spec:
      containers:
        - name: cortex-api
          image: cortex-api:latest
          ports:
            - containerPort: 8000
          env:
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: cortex-secrets
                  key: openai-api-key
        - name: cortex-ui
          image: cortex-ui:latest
          ports:
            - containerPort: 80
```

### 4.3 GitHub Codespaces

```json
// .devcontainer/devcontainer.json
{
  "name": "Cortex Development",
  "dockerComposeFile": "docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspace",
  "extensions": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode"
  ],
  "forwardPorts": [8000, 3000],
  "postCreateCommand": "bash .devcontainer/post-create.sh",
  "settings": {
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "editor.formatOnSave": true
  }
}
```

## 5. Testing Strategy

### 5.1 Backend Tests

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_chat_endpoint():
    response = client.post(
        "/api/chat/send",
        json={"content": "Hello world", "workspace_id": "default"}
    )
    assert response.status_code == 200
    assert "response" in response.json()

def test_workspace_creation():
    # Create a test workspace
    workspace_data = {
        "name": "Test Workspace",
        "description": "Test description"
    }
    response = client.post("/api/workspaces/", json=workspace_data)
    assert response.status_code == 200

    workspace_id = response.json()["id"]

    # Verify it was created
    response = client.get(f"/api/workspaces/{workspace_id}")
    assert response.status_code == 200
    assert response.json()["name"] == workspace_data["name"]

    # Clean up
    client.delete(f"/api/workspaces/{workspace_id}")
```

### 5.2 Frontend Tests

```typescript
// src/components/chat/__tests__/ChatInterface.test.tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ChatInterface from "../ChatInterface";
import { sendChatMessage } from "../../../services/chat";

// Mock the API service
jest.mock("../../../services/chat");
const mockSendChatMessage = sendChatMessage as jest.MockedFunction<
  typeof sendChatMessage
>;

describe("ChatInterface", () => {
  beforeEach(() => {
    mockSendChatMessage.mockReset();
  });

  it("renders input field and send button", () => {
    render(<ChatInterface workspaceId="test" />);

    expect(
      screen.getByPlaceholderText("Type your message here...")
    ).toBeInTheDocument();
    expect(screen.getByText("Send")).toBeInTheDocument();
  });

  it("sends message when send button is clicked", async () => {
    mockSendChatMessage.mockResolvedValue({ response: "Test response" });

    render(<ChatInterface workspaceId="test" />);

    const input = screen.getByPlaceholderText("Type your message here...");
    fireEvent.change(input, { target: { value: "Hello Cortex" } });

    const sendButton = screen.getByText("Send");
    fireEvent.click(sendButton);

    expect(mockSendChatMessage).toHaveBeenCalledWith("Hello Cortex", "test");

    await waitFor(() => {
      expect(screen.getByText("Hello Cortex")).toBeInTheDocument();
      expect(screen.getByText("Test response")).toBeInTheDocument();
    });
  });

  it("shows error message when API call fails", async () => {
    mockSendChatMessage.mockRejectedValue(new Error("API error"));

    render(<ChatInterface workspaceId="test" />);

    const input = screen.getByPlaceholderText("Type your message here...");
    fireEvent.change(input, { target: { value: "Trigger error" } });

    const sendButton = screen.getByText("Send");
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to send message. Please try again.")
      ).toBeInTheDocument();
    });
  });
});
```
