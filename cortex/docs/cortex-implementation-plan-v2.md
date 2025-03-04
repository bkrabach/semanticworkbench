# Cortex Platform - Implementation Plan (Modular Frontend)

This document provides a detailed implementation plan for the Cortex Platform, focusing on a modular frontend approach with separate applications for each modality that communicate with a central backend.

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
  │   │   ├── voice.py            # Voice endpoints
  │   │   ├── canvas.py           # Canvas endpoints
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

### 1.2 Frontend Applications (Modular Approach)

#### 1.2.1 Shared Libraries

- **Cortex SDK**

  ```
  cortex-sdk/
  ├── src/
  │   ├── api/                   # API clients
  │   │   ├── index.ts           # Export utilities
  │   │   ├── apiClient.ts       # Base API client
  │   │   ├── chatService.ts     # Chat API client
  │   │   ├── voiceService.ts    # Voice API client
  │   │   └── workspaceService.ts # Workspace API client
  │   ├── types/                 # Shared TypeScript types
  │   │   ├── index.ts           # Export types
  │   │   ├── chat.ts            # Chat-related types
  │   │   ├── voice.ts           # Voice-related types
  │   │   └── workspace.ts       # Workspace-related types
  │   ├── utils/                 # Shared utilities
  │   │   ├── index.ts           # Export utilities
  │   │   ├── formatters.ts      # Text formatting utilities
  │   │   └── storage.ts         # Local storage helpers
  │   └── index.ts               # Main entry point
  ├── package.json               # Dependencies
  ├── tsconfig.json              # TypeScript config
  └── README.md                  # Documentation
  ```

- **Cortex UI Components**
  ```
  cortex-ui-components/
  ├── src/
  │   ├── components/            # UI components
  │   │   ├── index.ts           # Export components
  │   │   ├── buttons/           # Button components
  │   │   ├── inputs/            # Input components
  │   │   ├── layout/            # Layout components
  │   │   └── feedback/          # Notification/feedback components
  │   ├── themes/                # Theming
  │   │   ├── index.ts           # Export themes
  │   │   ├── light.ts           # Light theme
  │   │   └── dark.ts            # Dark theme
  │   ├── hooks/                 # Shared React hooks
  │   └── index.ts               # Main entry point
  ├── package.json               # Dependencies
  ├── tsconfig.json              # TypeScript config
  └── README.md                  # Documentation
  ```

#### 1.2.2 Chat Application (React/TypeScript with Vite)

- **Project Structure**
  ```
  cortex-chat-app/
  ├── src/
  │   ├── components/            # Chat-specific components
  │   │   ├── ChatInterface.tsx  # Main chat interface
  │   │   ├── MessageList.tsx    # Message display
  │   │   ├── MessageInput.tsx   # Input component
  │   │   └── ChatControls.tsx   # Chat controls
  │   ├── hooks/                 # Chat-specific hooks
  │   │   └── useChatSession.ts  # Chat session management
  │   ├── store/                 # State management
  │   │   └── chatStore.ts       # Chat state
  │   ├── App.tsx                # Main application
  │   └── main.tsx               # Entry point
  ├── public/                    # Static assets
  ├── index.html                 # HTML template
  ├── package.json               # Dependencies
  ├── tsconfig.json              # TypeScript config
  ├── vite.config.ts             # Vite configuration
  └── README.md                  # Documentation
  ```

#### 1.2.3 Voice Application (React/TypeScript with Vite)

- **Project Structure**
  ```
  cortex-voice-app/
  ├── src/
  │   ├── components/            # Voice-specific components
  │   │   ├── VoiceInterface.tsx # Main voice interface
  │   │   ├── RecordButton.tsx   # Voice recording
  │   │   ├── AudioVisualizer.tsx # Audio visualization
  │   │   └── TranscriptView.tsx # Transcript display
  │   ├── hooks/                 # Voice-specific hooks
  │   │   ├── useAudioRecording.ts # Recording management
  │   │   └── useSpeechSynthesis.ts # TTS management
  │   ├── services/              # Voice services
  │   │   ├── audioProcessing.ts # Audio processing
  │   │   └── speechRecognition.ts # Speech recognition
  │   ├── store/                 # State management
  │   │   └── voiceStore.ts      # Voice state
  │   ├── App.tsx                # Main application
  │   └── main.tsx               # Entry point
  ├── public/                    # Static assets
  ├── index.html                 # HTML template
  ├── package.json               # Dependencies
  ├── tsconfig.json              # TypeScript config
  ├── vite.config.ts             # Vite configuration
  └── README.md                  # Documentation
  ```

#### 1.2.4 Canvas Application (React/TypeScript with Vite)

- **Project Structure**
  ```
  cortex-canvas-app/
  ├── src/
  │   ├── components/            # Canvas-specific components
  │   │   ├── CanvasInterface.tsx # Main canvas interface
  │   │   ├── DrawingCanvas.tsx  # Drawing area
  │   │   ├── ToolPanel.tsx      # Drawing tools
  │   │   └── CanvasControls.tsx # Canvas controls
  │   ├── hooks/                 # Canvas-specific hooks
  │   │   └── useCanvas.ts       # Canvas state management
  │   ├── services/              # Canvas services
  │   │   └── canvasProcessor.ts # Process canvas data
  │   ├── store/                 # State management
  │   │   └── canvasStore.ts     # Canvas state
  │   ├── App.tsx                # Main application
  │   └── main.tsx               # Entry point
  ├── public/                    # Static assets
  ├── index.html                 # HTML template
  ├── package.json               # Dependencies
  ├── tsconfig.json              # TypeScript config
  ├── vite.config.ts             # Vite configuration
  └── README.md                  # Documentation
  ```

#### 1.2.5 Workspace Manager Application (React/TypeScript with Vite)

- **Project Structure**
  ```
  cortex-workspace-app/
  ├── src/
  │   ├── components/            # Workspace-specific components
  │   │   ├── WorkspaceList.tsx  # Workspace listing
  │   │   ├── WorkspaceDetail.tsx # Workspace details
  │   │   ├── CreateWorkspace.tsx # Creation form
  │   │   └── WorkspaceSettings.tsx # Settings
  │   ├── hooks/                 # Workspace-specific hooks
  │   │   └── useWorkspaces.ts   # Workspace management
  │   ├── store/                 # State management
  │   │   └── workspaceStore.ts  # Workspace state
  │   ├── App.tsx                # Main application
  │   └── main.tsx               # Entry point
  ├── public/                    # Static assets
  ├── index.html                 # HTML template
  ├── package.json               # Dependencies
  ├── tsconfig.json              # TypeScript config
  ├── vite.config.ts             # Vite configuration
  └── README.md                  # Documentation
  ```

#### 1.2.6 Dashboard Application (React/TypeScript with Vite)

- **Project Structure**
  ```
  cortex-dashboard-app/
  ├── src/
  │   ├── components/            # Dashboard-specific components
  │   │   ├── Dashboard.tsx      # Main dashboard
  │   │   ├── Widgets/           # Dashboard widgets
  │   │   ├── Charts/            # Data visualization
  │   │   └── ControlPanel.tsx   # Dashboard controls
  │   ├── hooks/                 # Dashboard-specific hooks
  │   │   └── useDashboardData.ts # Data fetching
  │   ├── store/                 # State management
  │   │   └── dashboardStore.ts  # Dashboard state
  │   ├── App.tsx                # Main application
  │   └── main.tsx               # Entry point
  ├── public/                    # Static assets
  ├── index.html                 # HTML template
  ├── package.json               # Dependencies
  ├── tsconfig.json              # TypeScript config
  ├── vite.config.ts             # Vite configuration
  └── README.md                  # Documentation
  ```

### 1.3 MCP Servers

#### 1.3.1 VS Code MCP Server (TypeScript)

- Provides code context, file operations
- Integrates with existing VS Code extension capabilities

#### 1.3.2 Browser MCP Server (Python)

- Implements Playwright for web automation
- Provides web content analysis

## 2. Day-by-Day Implementation Plan

### 2.1 Day 1: Core Backend & Base Frontend Applications

#### 2.1.1 Backend Setup (3 hours)

- Initialize FastAPI project
- Configure basic routes and middleware
- Set up project structure
- Implement simple LLM integration with OpenAI

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, voice, canvas, openai_compat, workspaces

app = FastAPI(title="Cortex AI Platform")

# Configure CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(canvas.router, prefix="/api/canvas", tags=["canvas"])
app.include_router(openai_compat.router, prefix="/v1", tags=["openai-compat"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["workspaces"])

@app.get("/")
async def root():
    return {"message": "Welcome to Cortex AI Platform"}
```

#### 2.1.2 Shared Libraries (2 hours)

- Initialize Cortex SDK project
- Implement API client foundations
- Set up basic TypeScript types

```typescript
// cortex-sdk/src/api/apiClient.ts
import axios, { AxiosInstance, AxiosRequestConfig } from "axios";

export class ApiClient {
  private axiosInstance: AxiosInstance;

  constructor(baseURL: string = "http://localhost:8000") {
    this.axiosInstance = axios.create({
      baseURL,
      timeout: 30000, // 30 seconds
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Add request interceptor for authentication if needed
    this.axiosInstance.interceptors.request.use(
      (config) => {
        // Get token from storage and add to headers
        const token = localStorage.getItem("auth_token");
        if (token) {
          config.headers["Authorization"] = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.axiosInstance.get<T>(url, config);
    return response.data;
  }

  async post<T>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.axiosInstance.post<T>(url, data, config);
    return response.data;
  }

  async put<T>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.axiosInstance.put<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.axiosInstance.delete<T>(url, config);
    return response.data;
  }
}

export default new ApiClient();
```

#### 2.1.3 Chat Application (3 hours)

- Initialize Chat application with Vite
- Implement basic chat interface
- Connect to backend API

```typescript
// cortex-chat-app/src/components/ChatInterface.tsx
import { useState, useEffect } from "react";
import { chatService } from "cortex-sdk";
import { Button, TextField, Stack } from "cortex-ui-components";
import MessageList from "./MessageList";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    // Add user message to UI
    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      // Send to API
      const response = await chatService.sendMessage(input);

      // Add assistant response
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.response },
      ]);
    } catch (error) {
      console.error("Error sending message:", error);
      // Show error notification
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Stack className="chat-container">
      <MessageList messages={messages} isLoading={isLoading} />

      <Stack horizontal className="input-container">
        <TextField
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          disabled={isLoading}
          multiline
          autoFocus
        />
        <Button
          onClick={sendMessage}
          disabled={!input.trim() || isLoading}
          icon="send"
          primary
        >
          Send
        </Button>
      </Stack>
    </Stack>
  );
}
```

### 2.2 Day 2: MCP Integration & Additional Frontend Apps

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
        # Implementation as in previous plan
        # ...

    async def call_tool(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on an MCP server"""
        # Implementation as in previous plan
        # ...

    async def _send_request(self, server_name: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to an MCP server and get the response"""
        # Implementation as in previous plan
        # ...

    async def close(self):
        """Close all MCP server connections"""
        # Implementation as in previous plan
        # ...

# Singleton instance
mcp_client = MCPClient()
```

#### 2.2.2 Voice Application (3 hours)

- Initialize Voice application with Vite
- Implement basic voice recording and playback
- Connect to backend API

```typescript
// cortex-voice-app/src/components/VoiceInterface.tsx
import { useState, useRef } from "react";
import { voiceService } from "cortex-sdk";
import { Button, Stack, Text } from "cortex-ui-components";
import RecordButton from "./RecordButton";
import AudioVisualizer from "./AudioVisualizer";
import TranscriptView from "./TranscriptView";

export default function VoiceInterface() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = handleAudioStop;

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Error starting recording:", error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleAudioStop = async () => {
    const audioBlob = new Blob(audioChunksRef.current, { type: "audio/mp3" });
    setIsProcessing(true);

    try {
      // Send to API for transcription and response
      const result = await voiceService.processAudio(audioBlob);
      setTranscript(result.transcript);
      setResponse(result.response);

      // Play audio response if available
      if (result.audioResponse && audioRef.current) {
        const audioUrl = URL.createObjectURL(result.audioResponse);
        audioRef.current.src = audioUrl;
        audioRef.current.play();
      }
    } catch (error) {
      console.error("Error processing audio:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Stack className="voice-container">
      <AudioVisualizer isRecording={isRecording} />

      <RecordButton
        isRecording={isRecording}
        isProcessing={isProcessing}
        onStartRecording={startRecording}
        onStopRecording={stopRecording}
      />

      {transcript && (
        <TranscriptView transcript={transcript} response={response} />
      )}

      <audio ref={audioRef} style={{ display: "none" }} />
    </Stack>
  );
}
```

#### 2.2.3 Workspace Application (2 hours)

- Initialize Workspace application with Vite
- Implement basic workspace management
- Connect to backend API

```typescript
// cortex-workspace-app/src/components/WorkspaceList.tsx
import { useState, useEffect } from 'react';
import { workspaceService } from 'cortex-sdk';
import { Stack, List, Button, Text } from 'cortex-ui-components';

interface Workspace {
  id: string;
  name: string;
  description: string;
  created_at: string;
}

export default function WorkspaceList() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkspaces = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await workspaceService.getWorkspaces();
      setWorkspaces(data);
    } catch (error) {
      console.error('Error fetching workspaces:', error);
      setError('Failed to load workspaces');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  return (
    <Stack className="workspace-list-container">
      <Stack horizontal horizontalAlign="space-between">
        <Text variant="xxLarge">Workspaces</Text>
        <Button
          primary
          icon="add"
          onClick={() => /* Navigate to create workspace */}
        >
          New Workspace
        </Button>
      </Stack>

      {isLoading ? (
        <div>Loading workspaces...</div>
      ) : error ? (
        <div className="error-message">{error}</div>
      ) : (
        <List
          items={workspaces}
          onRenderItem={(workspace) => (
            <div className="workspace-item" key={workspace.id}>
              <Text variant="large">{workspace.name}</Text>
              <Text>{workspace.description}</Text>
              <Text variant="small">
                Created: {new Date(workspace.created_at).toLocaleDateString()}
              </Text>
            </div>
          )}
        />
      )}
    </Stack>
  );
}
```

### 2.3 Day 3: Canvas App & Integration

#### 2.3.1 Canvas Application (3 hours)

- Initialize Canvas application with Vite
- Implement basic drawing functionality
- Connect to backend API

```typescript
// cortex-canvas-app/src/components/DrawingCanvas.tsx
import { useRef, useState, useEffect } from "react";
import { canvasService } from "cortex-sdk";
import { Stack, Button } from "cortex-ui-components";

export default function DrawingCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [context, setContext] = useState<CanvasRenderingContext2D | null>(null);
  const [tool, setTool] = useState<"pen" | "eraser">("pen");
  const [color, setColor] = useState("#000000");
  const [lineWidth, setLineWidth] = useState(5);

  useEffect(() => {
    if (canvasRef.current) {
      const ctx = canvasRef.current.getContext("2d");
      if (ctx) {
        setContext(ctx);

        // Set initial canvas state
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
      }
    }
  }, []);

  useEffect(() => {
    if (context) {
      context.strokeStyle = tool === "eraser" ? "#FFFFFF" : color;
      context.lineWidth = tool === "eraser" ? lineWidth * 2 : lineWidth;
    }
  }, [tool, color, lineWidth, context]);

  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!context) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    context.beginPath();
    context.moveTo(x, y);
    setIsDrawing(true);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing || !context) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    context.lineTo(x, y);
    context.stroke();
  };

  const stopDrawing = () => {
    if (context) {
      context.closePath();
    }
    setIsDrawing(false);
  };

  const clearCanvas = () => {
    if (context && canvasRef.current) {
      context.clearRect(
        0,
        0,
        canvasRef.current.width,
        canvasRef.current.height
      );
    }
  };

  const processCanvas = async () => {
    if (!canvasRef.current) return;

    try {
      // Convert canvas to blob
      const blob = await new Promise<Blob>((resolve) => {
        canvasRef.current?.toBlob((blob) => {
          if (blob) resolve(blob);
        });
      });

      // Send to API
      const response = await canvasService.processCanvas(blob);

      // Handle response
      console.log("Canvas processing response:", response);
    } catch (error) {
      console.error("Error processing canvas:", error);
    }
  };

  return (
    <Stack className="drawing-canvas-container">
      <Stack horizontal className="canvas-controls">
        <Button
          onClick={() => setTool("pen")}
          primary={tool === "pen"}
          icon="edit"
        >
          Pen
        </Button>
        <Button
          onClick={() => setTool("eraser")}
          primary={tool === "eraser"}
          icon="eraser"
        >
          Eraser
        </Button>
        <input
          type="color"
          value={color}
          onChange={(e) => setColor(e.target.value)}
          disabled={tool === "eraser"}
        />
        <Button onClick={clearCanvas} icon="delete">
          Clear
        </Button>
        <Button onClick={processCanvas} primary icon="send">
          Process
        </Button>
      </Stack>

      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        onMouseDown={startDrawing}
        onMouseMove={draw}
        onMouseUp={stopDrawing}
        onMouseLeave={stopDrawing}
        className="drawing-canvas"
      />
    </Stack>
  );
}
```

#### 2.3.2 VS Code MCP Server (2 hours)

- Implement VS Code MCP server
- Test integration with core

```typescript
// vs-code-mcp-server/src/index.ts
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

// Implement tools as in previous plan
// ...

const transport = new StdioServerTransport();
server.connect(transport);
```

#### 2.3.3 Integration & Testing (3 hours)

- Set up environment for testing all components together
- Implement cross-app navigation
- Test end-to-end workflows

```typescript
// Example integration test
import { test, expect } from "@playwright/test";

test("Full workflow across multiple apps", async ({ page }) => {
  // 1. Create workspace
  await page.goto("http://localhost:3003"); // Workspace app
  await page.click('text="New Workspace"');
  await page.fill('[placeholder="Workspace name"]', "Test Project");
  await page.fill(
    '[placeholder="Description"]',
    "Test project for integration testing"
  );
  await page.click('text="Create"');

  // 2. Open chat interface
  await page.goto("http://localhost:3000"); // Chat app
  await page.selectOption(
    'select[aria-label="Select Workspace"]',
    "Test Project"
  );

  // 3. Send message
  await page.fill('[placeholder="Type your message..."]', "Hello Cortex!");
  await page.click('text="Send"');

  // Wait for response
  await page.waitForSelector(
    'text="Hello! How can I assist you with the Test Project today?"'
  );

  // 4. Test voice application
  await page.goto("http://localhost:3001"); // Voice app

  // 5. Test canvas application
  await page.goto("http://localhost:3002"); // Canvas app

  // Verify all applications are accessible and functional
  expect(await page.title()).toContain("Cortex Canvas");
});
```

## 3. Frontend Application Dependencies

Each frontend application will have its own package.json with dependencies, but they will share common libraries:

### 3.1 Common Dependencies (Cortex SDK & UI Components)

```json
{
  "dependencies": {
    "axios": "^1.4.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@fluentui/react": "^8.110.0",
    "zustand": "^4.3.9"
  },
  "devDependencies": {
    "@types/react": "^18.2.15",
    "@types/react-dom": "^18.2.7",
    "typescript": "^5.1.6"
  }
}
```

### 3.2 Application-Specific Dependencies

#### Chat Application

```json
{
  "dependencies": {
    "cortex-sdk": "workspace:*",
    "cortex-ui-components": "workspace:*",
    "react-markdown": "^8.0.7"
  }
}
```

#### Voice Application

```json
{
  "dependencies": {
    "cortex-sdk": "workspace:*",
    "cortex-ui-components": "workspace:*",
    "recorder-js": "^1.0.7",
    "wavesurfer.js": "^7.0.0"
  }
}
```

#### Canvas Application

```json
{
  "dependencies": {
    "cortex-sdk": "workspace:*",
    "cortex-ui-components": "workspace:*",
    "fabric.js": "^5.3.0"
  }
}
```

#### Workspace Application

```json
{
  "dependencies": {
    "cortex-sdk": "workspace:*",
    "cortex-ui-components": "workspace:*",
    "react-router-dom": "^6.14.1"
  }
}
```

## 4. Deployment Configuration

### 4.1 Local Development (using Turborepo)

```json
// package.json (root)
{
  "name": "cortex-platform",
  "private": true,
  "workspaces": [
    "cortex-sdk",
    "cortex-ui-components",
    "cortex-chat-app",
    "cortex-voice-app",
    "cortex-canvas-app",
    "cortex-workspace-app",
    "cortex-dashboard-app"
  ],
  "scripts": {
    "dev": "turbo run dev",
    "build": "turbo run build",
    "test": "turbo run test",
    "lint": "turbo run lint"
  },
  "devDependencies": {
    "turbo": "^1.10.7"
  }
}
```

```json
// turbo.json
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    },
    "test": {
      "dependsOn": ["^build"]
    },
    "lint": {},
    "dev": {
      "cache": false,
      "persistent": true
    }
  }
}
```

### 4.2 Individual App Development

Each application can be started individually for focused development:

```bash
# Start backend
cd cortex-core
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Start chat app
cd cortex-chat-app
npm run dev -- --port 3000

# Start voice app
cd cortex-voice-app
npm run dev -- --port 3001

# Start canvas app
cd cortex-canvas-app
npm run dev -- --port 3002

# Start workspace app
cd cortex-workspace-app
npm run dev -- --port 3003

# Start dashboard app
cd cortex-dashboard-app
npm run dev -- --port 3004
```

### 4.3 Docker Compose for Development

```yaml
# docker-compose.yml
version: "3"
services:
  backend:
    build: ./cortex-core
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./cortex-core:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  sdk:
    build: ./cortex-sdk
    volumes:
      - ./cortex-sdk:/app
    command: npm run dev

  ui-components:
    build: ./cortex-ui-components
    volumes:
      - ./cortex-ui-components:/app
    command: npm run dev

  chat-app:
    build: ./cortex-chat-app
    ports:
      - "3000:3000"
    volumes:
      - ./cortex-chat-app:/app
    command: npm run dev -- --port 3000
    depends_on:
      - backend
      - sdk
      - ui-components

  voice-app:
    build: ./cortex-voice-app
    ports:
      - "3001:3000"
    volumes:
      - ./cortex-voice-app:/app
    command: npm run dev -- --port 3000
    depends_on:
      - backend
      - sdk
      - ui-components

  canvas-app:
    build: ./cortex-canvas-app
    ports:
      - "3002:3000"
    volumes:
      - ./cortex-canvas-app:/app
    command: npm run dev -- --port 3000
    depends_on:
      - backend
      - sdk
      - ui-components

  workspace-app:
    build: ./cortex-workspace-app
    ports:
      - "3003:3000"
    volumes:
      - ./cortex-workspace-app:/app
    command: npm run dev -- --port 3000
    depends_on:
      - backend
      - sdk
      - ui-components

  dashboard-app:
    build: ./cortex-dashboard-app
    ports:
      - "3004:3000"
    volumes:
      - ./cortex-dashboard-app:/app
    command: npm run dev -- --port 3000
    depends_on:
      - backend
      - sdk
      - ui-components
```

## 5. Next Steps Beyond PoC

1. **Application Integration Hub**

   - Develop a central hub that provides navigation between the different applications
   - Implement shared authentication and context passing between apps

2. **Enhanced Real-time Voice**

   - Fully implement real-time voice streaming using OpenAI realtime API
   - Optimize for low-latency conversations

3. **Advanced Domain Experts**

   - Develop more sophisticated domain expert MCP servers
   - Support third-party and community expert systems

4. **Enhanced Memory Management**

   - Implement vector database for semantic search
   - Add structured data storage for complex information

5. **Collaborative Features**

   - Add multi-user support to workspaces
   - Implement real-time collaboration in canvas app

6. **Security & Authentication**
   - Add proper authentication for access control
   - Implement secure storage for sensitive information
   - Add permission management for MCP servers
