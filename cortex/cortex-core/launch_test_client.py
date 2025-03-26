#!/usr/bin/env python
"""
Simple HTTP server to host the Cortex test client.
"""
import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
import threading
import tempfile

# Create a temporary HTML file with our test client
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cortex Core Test Client</title>
    <!-- No external dependencies - everything in one file -->
    <script type="text/javascript">
    // Simplified fetch-event-source implementation
    (function() {
        'use strict';
        
        // Create our namespace
        window.fetchEventSource = {
            // Error class for recoverable errors
            FetchError: class FetchError extends Error {
                constructor(message) {
                    super(message);
                    this.name = 'FetchError';
                }
            },

            // Main function to fetch an event source with proper headers
            fetchEventSource: async function(input, options) {
                const { signal, headers: baseHeaders, onopen, onmessage, onclose, onerror } = options;
                
                // If auth header is present, add it to URL for compatibility
                let url = input;
                const authHeader = baseHeaders?.Authorization;
                if (authHeader && authHeader.startsWith('Bearer ')) {
                    const token = authHeader.substring(7);
                    const separator = url.includes('?') ? '&' : '?';
                    url = `${url}${separator}token=${encodeURIComponent(token)}`;
                }
                
                // Use native EventSource since it's simpler and more reliable
                const eventSource = new EventSource(url);
                
                // Set up event handlers
                eventSource.onopen = function() {
                    if (onopen) onopen({ ok: true, status: 200, statusText: 'OK' });
                };
                
                eventSource.onerror = function(e) {
                    console.error('EventSource error', e);
                    if (onerror) {
                        // Let the caller decide if we should retry
                        const shouldRetry = onerror(new Error('EventSource error'));
                        if (!shouldRetry) eventSource.close();
                    }
                };
                
                eventSource.onmessage = function(e) {
                    try {
                        if (onmessage) {
                            onmessage({ 
                                data: e.data, 
                                event: 'message' 
                            });
                        }
                    } catch (err) {
                        console.error('Error processing message', err);
                    }
                };
                
                // Set up handlers for other event types
                ['output', 'system', 'error'].forEach(eventType => {
                    eventSource.addEventListener(eventType, function(e) {
                        try {
                            if (onmessage) {
                                onmessage({ 
                                    data: e.data, 
                                    event: eventType 
                                });
                            }
                        } catch (err) {
                            console.error(`Error processing ${eventType} event`, err);
                        }
                    });
                });
                
                // Set up abort handling
                if (signal) {
                    signal.addEventListener('abort', function() {
                        eventSource.close();
                    });
                }
                
                // Return a cleanup function
                return function cleanup() {
                    eventSource.close();
                    if (onclose) onclose();
                };
            }
        };
    })();
    </script>
    <style>
        :root {
            --primary-color: #1e88e5;
            --secondary-color: #5e35b1;
            --background-color: #f5f7fa;
            --surface-color: #ffffff;
            --error-color: #e53935;
            --success-color: #43a047;
            --text-color: #212121;
            --text-secondary: #757575;
            --border-color: #e0e0e0;
            --highlight-color: rgba(30, 136, 229, 0.1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        body {
            background-color: var(--background-color);
            color: var(--text-color);
            line-height: 1.6;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background-color: var(--primary-color);
            color: white;
            padding: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }

        h1 {
            font-size: 1.5rem;
            font-weight: 500;
        }

        .container {
            flex: 1;
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .tabs {
            display: flex;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 1rem;
        }

        .tab {
            padding: 0.5rem 1rem;
            cursor: pointer;
            transition: background-color 0.2s;
            border: none;
            background: none;
            color: var(--text-color);
            font-size: 1rem;
            border-bottom: 2px solid transparent;
        }

        .tab.active {
            border-bottom: 2px solid var(--primary-color);
            color: var(--primary-color);
            font-weight: 500;
        }

        .tab:hover:not(.active) {
            background-color: rgba(0, 0, 0, 0.05);
        }

        .tab-content {
            display: none;
            flex: 1;
        }

        .tab-content.active {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .card {
            background-color: var(--surface-color);
            padding: 1rem;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .card-title {
            font-size: 1.2rem;
            margin-bottom: 0.5rem;
            color: var(--primary-color);
            font-weight: 500;
        }

        .form-group {
            margin-bottom: 1rem;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: var(--text-secondary);
        }

        input, textarea, select {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 1rem;
        }

        button {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.2s;
            font-size: 1rem;
        }

        button:hover {
            background-color: #1976d2;
        }

        button:disabled {
            background-color: var(--text-secondary);
            cursor: not-allowed;
        }

        .button-secondary {
            background-color: var(--secondary-color);
        }

        .button-secondary:hover {
            background-color: #4527a0;
        }

        .button-group {
            display: flex;
            gap: 0.5rem;
        }

        .status {
            margin-top: 1rem;
            padding: 0.5rem;
            background-color: var(--highlight-color);
            border-radius: 4px;
            font-family: monospace;
        }

        .error {
            background-color: rgba(229, 57, 53, 0.1);
            color: var(--error-color);
        }

        .success {
            background-color: rgba(67, 160, 71, 0.1);
            color: var(--success-color);
        }

        .hidden {
            display: none;
        }

        .flex-row {
            display: flex;
            gap: 1rem;
        }

        .flex-column {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .flex-1 {
            flex: 1;
        }

        .messages-container {
            flex: 1;
            min-height: 300px;
            max-height: 500px;
            overflow-y: auto;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 1rem;
            background-color: white;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .message {
            padding: 0.8rem;
            border-radius: 4px;
            max-width: 80%;
            word-break: break-word;
        }

        .message-user {
            align-self: flex-end;
            background-color: var(--primary-color);
            color: white;
        }

        .message-assistant {
            align-self: flex-start;
            background-color: #f1f1f1;
            color: var(--text-color);
        }

        .message-system {
            align-self: center;
            background-color: rgba(0, 0, 0, 0.05);
            color: var(--text-secondary);
            font-style: italic;
        }

        .message-error {
            align-self: center;
            background-color: rgba(229, 57, 53, 0.1);
            color: var(--error-color);
            font-style: italic;
        }

        .input-container {
            display: flex;
            gap: 0.5rem;
        }

        .input-container textarea {
            flex: 1;
            resize: none;
            height: 80px;
        }

        .badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .badge {
            padding: 0.3rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            background-color: rgba(0, 0, 0, 0.05);
        }

        .badge-primary {
            background-color: var(--primary-color);
            color: white;
        }

        .badge-secondary {
            background-color: var(--secondary-color);
            color: white;
        }

        .badge-success {
            background-color: var(--success-color);
            color: white;
        }

        .badge-error {
            background-color: var(--error-color);
            color: white;
        }

        footer {
            margin-top: auto;
            text-align: center;
            padding: 1rem;
            background-color: var(--primary-color);
            color: white;
            font-size: 0.9rem;
        }

        pre {
            background-color: #f5f5f5;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
            font-family: monospace;
            font-size: 0.9rem;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 0.5rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }

        th {
            font-weight: 500;
            color: var(--text-secondary);
        }

        .loading:after {
            content: '.';
            animation: dots 1.5s steps(5, end) infinite;
        }

        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60% { content: '...'; }
            80%, 100% { content: ''; }
        }

        .system-info {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .system-info-item {
            flex: 1;
            padding: 0.5rem;
            border-radius: 4px;
            background-color: var(--highlight-color);
            text-align: center;
        }

        .system-info-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 0.2rem;
        }

        .system-info-value {
            font-weight: 500;
        }

        .memory-item {
            padding: 0.5rem;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            margin-bottom: 0.5rem;
        }

        .memory-item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }

        .memory-item-content {
            font-family: monospace;
            background-color: #f5f5f5;
            padding: 0.5rem;
            border-radius: 4px;
            white-space: pre-wrap;
        }

        #connectionStatus {
            margin-left: auto;
            padding: 0.3rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
        }

        .connected {
            background-color: rgba(67, 160, 71, 0.8);
            color: white;
        }

        .disconnected {
            background-color: rgba(229, 57, 53, 0.8);
            color: white;
        }
    </style>
</head>
<body>
    <header>
        <h1>Cortex Core Test Client</h1>
        <div id="connectionStatus" class="disconnected">Disconnected</div>
    </header>

    <div class="container">
        <div class="tabs">
            <button class="tab active" data-tab="auth">Authentication</button>
            <button class="tab" data-tab="chat">Chat</button>
            <button class="tab" data-tab="memory">Memory</button>
            <button class="tab" data-tab="cognition">Cognition</button>
            <button class="tab" data-tab="system">System</button>
        </div>

        <!-- Auth Tab -->
        <div id="auth" class="tab-content active">
            <div class="card">
                <div class="card-title">Authentication</div>
                <div class="form-group">
                    <label for="authMode">Authentication Mode</label>
                    <select id="authMode">
                        <option value="dev">Development Mode</option>
                        <option value="auth0">Auth0 Mode</option>
                    </select>
                </div>
                
                <div id="devAuthFields">
                    <div class="form-group">
                        <label for="username">Username</label>
                        <input type="text" id="username" value="user@example.com" />
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" value="password123" />
                    </div>
                    <button id="loginBtn">Login</button>
                </div>
                
                <div id="auth0Fields" class="hidden">
                    <div class="form-group">
                        <label for="auth0Token">Auth0 Token</label>
                        <textarea id="auth0Token" rows="5" placeholder="Paste your Auth0 JWT token here"></textarea>
                    </div>
                    <button id="useAuth0Token">Use Token</button>
                </div>

                <div id="authStatus" class="status hidden"></div>
            </div>

            <div class="card">
                <div class="card-title">User Profile</div>
                <button id="getUserProfile" disabled>Get User Profile</button>
                <pre id="userProfileData" class="hidden"></pre>
            </div>
        </div>

        <!-- Chat Tab -->
        <div id="chat" class="tab-content">
            <div class="card flex-column flex-1">
                <div class="card-title">Chat Interface</div>
                
                <div class="flex-row">
                    <div class="form-group flex-1">
                        <label for="chatWorkspace">Workspace</label>
                        <select id="chatWorkspace">
                            <option value="default">Default Workspace</option>
                        </select>
                    </div>
                    <div class="form-group flex-1">
                        <label for="chatConversation">Conversation</label>
                        <select id="chatConversation">
                            <option value="">Select a conversation</option>
                        </select>
                    </div>
                    <div class="form-group" style="align-self: flex-end;">
                        <button id="createConversation">Create New</button>
                    </div>
                </div>

                <div id="messages" class="messages-container">
                    <div class="message message-system">Please select or create a conversation to start chatting.</div>
                </div>

                <div class="input-container">
                    <textarea 
                        id="userInput" 
                        placeholder="Type your message here..." 
                        disabled
                    ></textarea>
                    <button id="sendMessage" disabled>Send</button>
                </div>
            </div>
        </div>

        <!-- Memory Tab -->
        <div id="memory" class="tab-content">
            <div class="card">
                <div class="card-title">Memory Service</div>
                <div class="form-group">
                    <label for="memoryConversation">Conversation ID</label>
                    <input type="text" id="memoryConversation" placeholder="Enter conversation ID to fetch messages" />
                </div>
                <button id="getMemory">Get Messages</button>
                <div id="memoryStatus" class="status hidden"></div>
                <div id="memoryList" class="hidden"></div>
            </div>
        </div>

        <!-- Cognition Tab -->
        <div id="cognition" class="tab-content">
            <div class="card">
                <div class="card-title">Direct Cognition Test</div>
                <div class="form-group">
                    <label for="directPrompt">Test Prompt</label>
                    <textarea 
                        id="directPrompt" 
                        rows="5" 
                        placeholder="Enter a test prompt to send directly to the cognition service"
                    >What is the Cortex Core system?</textarea>
                </div>
                <div class="form-group">
                    <label for="userId">User ID</label>
                    <input type="text" id="userId" placeholder="Use current user ID" />
                </div>
                <div class="form-group">
                    <label for="directConversationId">Conversation ID</label>
                    <input type="text" id="directConversationId" placeholder="Enter conversation ID or leave blank for new one" />
                </div>
                <button id="testCognition">Test Cognition Service</button>
                <div id="cognitionStatus" class="status hidden"></div>
                <div id="cognitionResponse" class="hidden"></div>
            </div>
        </div>

        <!-- System Tab -->
        <div id="system" class="tab-content">
            <div class="card">
                <div class="card-title">System Status</div>
                <button id="checkHealth">Check Health</button>
                <div id="healthStatus" class="status hidden"></div>
                <div id="systemInfo" class="system-info hidden"></div>
                <pre id="healthData" class="hidden"></pre>
            </div>

            <div class="card">
                <div class="card-title">Service Management</div>
                <div class="form-group">
                    <label for="serviceUrl">Service URL</label>
                    <input type="text" id="serviceUrl" value="http://localhost:8000" />
                </div>
                <div class="button-group">
                    <button id="refreshStatus">Refresh Status</button>
                </div>
                <div id="serviceStatus" class="status hidden"></div>
            </div>
        </div>
    </div>

    <footer>
        Cortex Core Test Client - <a href="https://github.com/cortex" style="color: white;">Project Repository</a>
    </footer>

    <script>
        // Configuration
        let config = {
            baseUrl: 'http://localhost:8000',
            token: null,
            user: null,
            sseController: null,
            conversations: {},
            activeConversation: null,
            serviceStatus: {
                api: false,
                memory: false,
                cognition: false
            }
        };

        // Utility functions
        function $(id) {
            return document.getElementById(id);
        }

        function showStatus(element, message, type = '') {
            element.textContent = message;
            element.className = 'status';
            if (type) element.classList.add(type);
            element.classList.remove('hidden');
        }

        function hideStatus(element) {
            element.classList.add('hidden');
        }

        function updateConnectionStatus(connected) {
            const statusEl = $('connectionStatus');
            if (connected) {
                statusEl.textContent = 'Connected';
                statusEl.className = 'connected';
            } else {
                statusEl.textContent = 'Disconnected';
                statusEl.className = 'disconnected';
            }
        }

        async function fetchWithAuth(url, options = {}) {
            if (!config.token) {
                throw new Error('Authentication token is missing');
            }

            const headers = {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${config.token}`
            };

            return fetch(config.baseUrl + url, {
                ...options,
                headers: {
                    ...headers,
                    ...(options.headers || {})
                }
            });
        }

        async function checkApiHealth() {
            try {
                const response = await fetch(config.baseUrl + '/health/ping');
                return response.ok;
            } catch (error) {
                console.error('API health check failed', error);
                return false;
            }
        }

        // Authentication functions
        async function login(username, password) {
            try {
                const formData = new FormData();
                formData.append('username', username);
                formData.append('password', password);

                const response = await fetch(config.baseUrl + '/auth/login', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error(`Login failed: ${response.status} ${response.statusText}`);
                }

                const data = await response.json();
                config.token = data.access_token;
                
                // Verify token and get user info
                await verifyToken();
                
                return true;
            } catch (error) {
                console.error('Login error', error);
                return false;
            }
        }

        async function verifyToken() {
            try {
                const response = await fetchWithAuth('/auth/verify');
                
                if (!response.ok) {
                    throw new Error(`Token verification failed: ${response.status} ${response.statusText}`);
                }

                const data = await response.json();
                config.user = data.user;
                
                // Update UI elements that depend on authentication
                document.querySelectorAll('.tab').forEach(tab => tab.disabled = false);
                $('getUserProfile').disabled = false;
                
                if ($('userId').value === '') {
                    $('userId').value = config.user.id;
                }
                
                updateConnectionStatus(true);
                
                return true;
            } catch (error) {
                console.error('Token verification error', error);
                config.token = null;
                config.user = null;
                updateConnectionStatus(false);
                return false;
            }
        }

        async function getUserProfile() {
            try {
                const response = await fetchWithAuth('/config/user/profile');
                
                if (!response.ok) {
                    throw new Error(`Failed to get user profile: ${response.status} ${response.statusText}`);
                }

                const data = await response.json();
                return data;
            } catch (error) {
                console.error('Error getting user profile', error);
                throw error;
            }
        }

        // Conversation functions
        async function getWorkspaces() {
            try {
                const response = await fetchWithAuth('/config/workspaces');
                
                if (!response.ok) {
                    // If no workspaces exist, create default workspace
                    if (response.status === 404) {
                        console.log('No workspaces found, creating default workspace');
                        return await createWorkspace('default');
                    }
                    throw new Error(`Failed to get workspaces: ${response.status} ${response.statusText}`);
                }

                const data = await response.json();
                // API returns { workspaces: [...] }
                return data.workspaces || [];
            } catch (error) {
                console.error('Error getting workspaces', error);
                return [];
            }
        }

        async function createWorkspace(name) {
            try {
                const response = await fetchWithAuth('/config/workspaces', {
                    method: 'POST',
                    body: JSON.stringify({
                        name: name,
                        description: `Workspace created by test client on ${new Date().toISOString()}`
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to create workspace: ${response.status} ${response.statusText}`);
                }

                const data = await response.json();
                console.log('Created workspace:', data);
                // API returns { status: "workspace created", workspace: {...} }
                if (data.workspace) {
                    return [data.workspace]; // Return as array to match getWorkspaces format
                }
                return [data]; // Fallback
            } catch (error) {
                console.error('Error creating workspace', error);
                throw error;
            }
        }

        async function getConversations(workspaceId = 'default') {
            try {
                const response = await fetchWithAuth(`/config/conversations?workspace_id=${workspaceId}`);
                
                if (!response.ok) {
                    if (response.status === 404) {
                        // If workspace doesn't exist, we may need to create it
                        const workspaces = await getWorkspaces();
                        if (workspaces.length > 0) {
                            // Try again with the first workspace
                            console.log('Using first available workspace', workspaces[0]);
                            return await getConversations(workspaces[0].id);
                        }
                    }
                    console.warn(`Failed to get conversations: ${response.status} ${response.statusText}`);
                    return [];
                }

                const data = await response.json();
                // API returns { conversations: [...] }
                const conversations = data.conversations || [];
                
                // Update the conversation cache
                config.conversations = conversations.reduce((acc, conv) => {
                    acc[conv.id] = conv;
                    return acc;
                }, {});
                
                return conversations;
            } catch (error) {
                console.error('Error getting conversations', error);
                return [];
            }
        }

        async function createConversation(workspaceId = 'default') {
            try {
                const response = await fetchWithAuth('/config/conversations', {
                    method: 'POST',
                    body: JSON.stringify({
                        workspace_id: workspaceId,
                        topic: `Conversation created on ${new Date().toLocaleString()}`
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to create conversation: ${response.status} ${response.statusText}`);
                }

                const data = await response.json();
                console.log('Create conversation response:', data);
                
                // API returns { status: "conversation created", conversation: {...} }
                if (data.conversation) {
                    // Store in our local cache
                    config.conversations[data.conversation.id] = data.conversation;
                    return data.conversation;
                }
                
                // Fallback
                config.conversations[data.id] = data;
                return data;
            } catch (error) {
                console.error('Error creating conversation', error);
                throw error;
            }
        }

        async function sendMessage(conversationId, content) {
            try {
                const response = await fetchWithAuth('/input/', {
                    method: 'POST',
                    body: JSON.stringify({
                        conversation_id: conversationId,
                        content: content,
                        metadata: { client: 'test-client' }
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to send message: ${response.status} ${response.statusText}`);
                }

                const data = await response.json();
                return data;
            } catch (error) {
                console.error('Error sending message', error);
                throw error;
            }
        }

        // Set up SSE connection with authentication
        async function setupSSEConnection(conversationId) {
            // Clean up existing connection
            if (config.sseController) {
                if (typeof config.sseController === 'function') {
                    config.sseController();
                }
                config.sseController = null;
            }
            
            if (!config.token) {
                console.error('No authentication token available');
                return;
            }
            
            // Build URL with optional conversation ID filter
            let url = `${config.baseUrl}/output/stream`;
            if (conversationId) {
                url += `?conversation_id=${conversationId}`;
            }
            
            try {
                // Create controller for abort handling
                const controller = new AbortController();
                
                // Set up options
                const options = {
                    headers: {
                        'Authorization': `Bearer ${config.token}`
                    },
                    signal: controller.signal,
                    
                    // Handle connection open
                    onopen(response) {
                        console.log('SSE connection opened');
                        updateConnectionStatus(true);
                    },
                    
                    // Handle messages
                    onmessage(event) {
                        console.log('SSE event:', event.event, event.data);
                        try {
                            const data = JSON.parse(event.data);
                            processEvent(data, event.event);
                        } catch (error) {
                            console.error('Error processing SSE event', error);
                        }
                    },
                    
                    // Handle errors with auto-retry
                    onerror(err) {
                        console.error('SSE connection error', err);
                        updateConnectionStatus(false);
                        
                        // Auto reconnect after a delay
                        setTimeout(() => {
                            if (config.sseController === cleanupFunction) {
                                setupSSEConnection(conversationId);
                            }
                        }, 5000);
                        
                        return false; // Don't let library handle retries
                    },
                    
                    // Handle connection close
                    onclose() {
                        console.log('SSE connection closed');
                        updateConnectionStatus(false);
                    }
                };
                
                // Start the connection
                const cleanupFunction = await fetchEventSource.fetchEventSource(url, options);
                config.sseController = cleanupFunction;
                
            } catch (error) {
                console.error('Error in SSE setup', error);
                updateConnectionStatus(false);
                
                // Auto reconnect after a delay
                setTimeout(() => {
                    setupSSEConnection(conversationId);
                }, 5000);
            }
        }

        function processEvent(event, eventType = 'message') {
            // Handle both the old and new event formats
            const type = eventType || event.type || 'message';
            const data = event.data || event;
            
            if ((type === 'output' || type === 'message') && data.role === 'assistant') {
                addMessage({
                    role: 'assistant',
                    content: data.content
                });
            } else if (data.role === 'system' || type === 'system') {
                addMessage({
                    role: 'system',
                    content: data.content || 'System event received',
                    type: data.error ? 'error' : 'system'
                });
            } else if (type === 'error' || data.error) {
                addMessage({
                    role: 'system',
                    content: data.content || data.error || 'Unknown error',
                    type: 'error'
                });
            }
        }

        function addMessage(message) {
            const messagesContainer = $('messages');
            const messageEl = document.createElement('div');
            messageEl.className = `message message-${message.role}`;
            if (message.type) {
                messageEl.classList.add(`message-${message.type}`);
            }
            messageEl.textContent = message.content;
            messagesContainer.appendChild(messageEl);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        async function testCognitionDirectly(userId, conversationId, prompt) {
            try {
                // Direct approach - no need to get cognition URL from system status
                // Using the allowed event types from management API
                const directResponse = await fetchWithAuth('/management/events/publish', {
                    method: 'POST',
                    body: JSON.stringify({
                        event_type: 'system.notification',
                        payload: {
                            type: 'cognition_request',
                            user_id: userId,
                            conversation_id: conversationId || `test-${Date.now()}`,
                            content: prompt
                        }
                    })
                });
                
                if (!directResponse.ok) {
                    throw new Error(`Failed to send cognition request: ${directResponse.status} ${directResponse.statusText}`);
                }
                
                return { 
                    success: true, 
                    message: 'Cognition request sent. Results will appear in the chat or system events.' 
                };
            } catch (error) {
                console.error('Error testing cognition directly', error);
                return { success: false, error: error.message };
            }
        }

        // Memory functions
        async function getMemoryMessages(conversationId) {
            try {
                // Using the allowed event types from management API
                const response = await fetchWithAuth('/management/events/publish', {
                    method: 'POST',
                    body: JSON.stringify({
                        event_type: 'system.notification',
                        payload: {
                            type: 'memory_retrieval',
                            conversation_id: conversationId
                        }
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to get memory messages: ${response.status} ${response.statusText}`);
                }

                return { 
                    success: true, 
                    message: 'Memory retrieval request sent. Results will appear in the system events.' 
                };
            } catch (error) {
                console.error('Error getting memory messages', error);
                return { success: false, error: error.message };
            }
        }

        // System functions
        async function checkSystemHealth() {
            try {
                const response = await fetch(config.baseUrl + '/health');
                
                if (!response.ok) {
                    throw new Error(`Health check failed: ${response.status} ${response.statusText}`);
                }

                const data = await response.json();
                
                // Update service status
                config.serviceStatus.api = data.status === 'online';
                
                // Check dependencies, which may not be present in initial version
                if (data.dependencies) {
                    config.serviceStatus.memory = data.dependencies.memory?.status === 'online';
                    config.serviceStatus.cognition = data.dependencies.cognition?.status === 'online';
                } else {
                    // Fallback to service_status field format
                    if (data.service_status) {
                        config.serviceStatus.memory = data.service_status?.memory === 'healthy';
                        config.serviceStatus.cognition = data.service_status?.cognition === 'healthy';
                    } else {
                        // If no specific service info, assume API is the only thing online
                        config.serviceStatus.memory = false;
                        config.serviceStatus.cognition = false;
                    }
                }
                
                return data;
            } catch (error) {
                console.error('Health check error', error);
                config.serviceStatus = {
                    api: false,
                    memory: false,
                    cognition: false
                };
                throw error;
            }
        }

        async function getSystemStatus() {
            try {
                const response = await fetchWithAuth('/management/system/status');
                
                if (!response.ok) {
                    throw new Error(`Failed to get system status: ${response.status} ${response.statusText}`);
                }

                const data = await response.json();
                return data;
            } catch (error) {
                console.error('Error getting system status', error);
                throw error;
            }
        }

        function populateSystemInfo(data) {
            const container = $('systemInfo');
            container.innerHTML = '';
            container.classList.remove('hidden');
            
            // Create system info items
            const createInfoItem = (label, value, status = null) => {
                const item = document.createElement('div');
                item.className = 'system-info-item';
                if (status) {
                    item.classList.add(status === 'online' || status === 'healthy' ? 'success' : 'error');
                }
                
                const labelEl = document.createElement('div');
                labelEl.className = 'system-info-label';
                labelEl.textContent = label;
                
                const valueEl = document.createElement('div');
                valueEl.className = 'system-info-value';
                valueEl.textContent = value;
                
                item.appendChild(labelEl);
                item.appendChild(valueEl);
                return item;
            };
            
            // Add core system info
            container.appendChild(createInfoItem('API Status', data.status, data.status));
            
            // Add version if available
            if (data.version) {
                container.appendChild(createInfoItem('Version', data.version));
            } else if (data.app_version) {
                container.appendChild(createInfoItem('Version', data.app_version));
            }
            
            // Add environment if available 
            if (data.environment) {
                container.appendChild(createInfoItem('Environment', data.environment));
            }
            
            // Add service info (depends on response format)
            if (data.dependencies) {
                // Format 1: dependencies with status field
                const memoryStatus = data.dependencies.memory?.status || 'offline';
                container.appendChild(createInfoItem('Memory Service', memoryStatus, memoryStatus));
                
                const cognitionStatus = data.dependencies.cognition?.status || 'offline';
                container.appendChild(createInfoItem('Cognition Service', cognitionStatus, cognitionStatus));
            } else if (data.service_status) {
                // Format 2: service_status object with healthy/unhealthy
                const memoryStatus = data.service_status.memory || 'offline';
                container.appendChild(createInfoItem('Memory Service', memoryStatus, memoryStatus));
                
                const cognitionStatus = data.service_status.cognition || 'offline';
                container.appendChild(createInfoItem('Cognition Service', cognitionStatus, cognitionStatus));
            } else {
                // Format 3: No service info available
                container.appendChild(createInfoItem('Memory Service', 'No information', 'offline'));
                container.appendChild(createInfoItem('Cognition Service', 'No information', 'offline'));
            }
            
            // Add additional metrics if available
            if (data.active_users !== undefined) {
                container.appendChild(createInfoItem('Active Users', data.active_users));
            }
            
            if (data.uptime_seconds !== undefined) {
                const uptime = `${Math.floor(data.uptime_seconds / 3600)}h ${Math.floor((data.uptime_seconds % 3600) / 60)}m`;
                container.appendChild(createInfoItem('Uptime', uptime));
            }
        }

        function updateServiceStatus() {
            const serviceStatusEl = $('serviceStatus');
            
            const statusText = [
                `API: ${config.serviceStatus.api ? 'Online' : 'Offline'}`,
                `Memory: ${config.serviceStatus.memory ? 'Online' : 'Offline'}`,
                `Cognition: ${config.serviceStatus.cognition ? 'Online' : 'Offline'}`
            ].join(' | ');
            
            serviceStatusEl.textContent = statusText;
            serviceStatusEl.className = 'status';
            
            if (config.serviceStatus.api) {
                serviceStatusEl.classList.add('success');
            } else {
                serviceStatusEl.classList.add('error');
            }
            
            serviceStatusEl.classList.remove('hidden');
        }

        function updateConversationSelect(conversations) {
            const select = $('chatConversation');
            select.innerHTML = '<option value="">Select a conversation</option>';
            
            conversations.forEach(conversation => {
                const option = document.createElement('option');
                option.value = conversation.id;
                option.textContent = conversation.title || conversation.id;
                select.appendChild(option);
            });
            
            // Enable/disable UI elements based on conversation availability
            $('userInput').disabled = !conversations.length;
            $('sendMessage').disabled = !conversations.length;
        }

        // Tab management
        function setupTabs() {
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    
                    tab.classList.add('active');
                    $(`${tab.dataset.tab}`).classList.add('active');
                });
            });
        }

        // Event listeners
        function setupEventListeners() {
            // Auth tab
            $('authMode').addEventListener('change', () => {
                const mode = $('authMode').value;
                if (mode === 'dev') {
                    $('devAuthFields').classList.remove('hidden');
                    $('auth0Fields').classList.add('hidden');
                } else {
                    $('devAuthFields').classList.add('hidden');
                    $('auth0Fields').classList.remove('hidden');
                }
            });
            
            $('loginBtn').addEventListener('click', async () => {
                const authStatus = $('authStatus');
                showStatus(authStatus, 'Logging in...', '');
                
                const username = $('username').value;
                const password = $('password').value;
                
                const success = await login(username, password);
                
                if (success) {
                    showStatus(authStatus, 'Login successful! Token received.', 'success');
                    setupSSEConnection();
                    
                    // Ensure we have a default workspace
                    try {
                        const workspaces = await getWorkspaces();
                        console.log('Available workspaces:', workspaces);
                        
                        // Then load conversations
                        const conversations = await getConversations(workspaces[0]?.id || 'default');
                        updateConversationSelect(conversations);
                    } catch (error) {
                        console.error('Error setting up initial workspace/conversations:', error);
                    }
                } else {
                    showStatus(authStatus, 'Login failed. Please check credentials.', 'error');
                }
            });
            
            $('useAuth0Token').addEventListener('click', async () => {
                const authStatus = $('authStatus');
                const token = $('auth0Token').value.trim();
                
                if (!token) {
                    showStatus(authStatus, 'Please enter a valid token.', 'error');
                    return;
                }
                
                showStatus(authStatus, 'Verifying token...', '');
                
                config.token = token;
                const success = await verifyToken();
                
                if (success) {
                    showStatus(authStatus, 'Token verified successfully!', 'success');
                    setupSSEConnection();
                    
                    // Load conversations
                    getConversations().then(updateConversationSelect);
                } else {
                    showStatus(authStatus, 'Token verification failed.', 'error');
                }
            });
            
            $('getUserProfile').addEventListener('click', async () => {
                try {
                    const profile = await getUserProfile();
                    $('userProfileData').textContent = JSON.stringify(profile, null, 2);
                    $('userProfileData').classList.remove('hidden');
                } catch (error) {
                    showStatus($('authStatus'), `Error: ${error.message}`, 'error');
                }
            });
            
            // Chat tab
            $('createConversation').addEventListener('click', async () => {
                try {
                    const workspace = $('chatWorkspace').value;
                    const conversation = await createConversation(workspace);
                    
                    // Update select with new conversation
                    getConversations().then(conversations => {
                        updateConversationSelect(conversations);
                        $('chatConversation').value = conversation.id;
                        $('chatConversation').dispatchEvent(new Event('change'));
                    });
                    
                    addMessage({
                        role: 'system',
                        content: `New conversation created: ${conversation.title || conversation.id}`
                    });
                } catch (error) {
                    addMessage({
                        role: 'system',
                        content: `Error creating conversation: ${error.message}`,
                        type: 'error'
                    });
                }
            });
            
            $('chatConversation').addEventListener('change', () => {
                const conversationId = $('chatConversation').value;
                
                if (conversationId) {
                    // Clear messages
                    $('messages').innerHTML = '';
                    
                    // Add system message
                    addMessage({
                        role: 'system',
                        content: `Conversation selected: ${config.conversations[conversationId]?.title || conversationId}`
                    });
                    
                    // Enable input
                    $('userInput').disabled = false;
                    $('sendMessage').disabled = false;
                    
                    // Set active conversation
                    config.activeConversation = conversationId;
                    
                    // Setup SSE for this conversation
                    setupSSEConnection(conversationId);
                } else {
                    $('userInput').disabled = true;
                    $('sendMessage').disabled = true;
                    config.activeConversation = null;
                }
            });
            
            $('sendMessage').addEventListener('click', async () => {
                const content = $('userInput').value.trim();
                const conversationId = config.activeConversation;
                
                if (!content || !conversationId) return;
                
                try {
                    // Add user message to UI
                    addMessage({
                        role: 'user',
                        content: content
                    });
                    
                    // Clear input
                    $('userInput').value = '';
                    
                    // Send message
                    await sendMessage(conversationId, content);
                    
                    // Add temporary system message
                    addMessage({
                        role: 'system',
                        content: 'Message sent, waiting for response...'
                    });
                } catch (error) {
                    addMessage({
                        role: 'system',
                        content: `Error sending message: ${error.message}`,
                        type: 'error'
                    });
                }
            });
            
            // Memory tab
            $('getMemory').addEventListener('click', async () => {
                const conversationId = $('memoryConversation').value.trim();
                
                if (!conversationId) {
                    showStatus($('memoryStatus'), 'Please enter a conversation ID', 'error');
                    return;
                }
                
                try {
                    const result = await getMemoryMessages(conversationId);
                    
                    if (result.success) {
                        showStatus($('memoryStatus'), result.message, 'success');
                    } else {
                        showStatus($('memoryStatus'), `Error: ${result.error}`, 'error');
                    }
                } catch (error) {
                    showStatus($('memoryStatus'), `Error: ${error.message}`, 'error');
                }
            });
            
            // Cognition tab
            $('testCognition').addEventListener('click', async () => {
                const prompt = $('directPrompt').value.trim();
                const userId = $('userId').value.trim() || config.user?.id;
                const conversationId = $('directConversationId').value.trim();
                
                if (!prompt) {
                    showStatus($('cognitionStatus'), 'Please enter a prompt', 'error');
                    return;
                }
                
                if (!userId) {
                    showStatus($('cognitionStatus'), 'Please enter a user ID', 'error');
                    return;
                }
                
                try {
                    showStatus($('cognitionStatus'), 'Sending request to cognition service...', '');
                    
                    const result = await testCognitionDirectly(userId, conversationId, prompt);
                    
                    if (result.success) {
                        showStatus($('cognitionStatus'), result.message, 'success');
                    } else {
                        showStatus($('cognitionStatus'), `Error: ${result.error}`, 'error');
                    }
                } catch (error) {
                    showStatus($('cognitionStatus'), `Error: ${error.message}`, 'error');
                }
            });
            
            // System tab
            $('checkHealth').addEventListener('click', async () => {
                try {
                    showStatus($('healthStatus'), 'Checking health...', '');
                    
                    const data = await checkSystemHealth();
                    showStatus($('healthStatus'), `Health check successful: ${data.status}`, 'success');
                    
                    // Show detailed health data
                    $('healthData').textContent = JSON.stringify(data, null, 2);
                    $('healthData').classList.remove('hidden');
                    
                    // Populate system info
                    populateSystemInfo(data);
                    
                    // Update service status
                    updateServiceStatus();
                } catch (error) {
                    showStatus($('healthStatus'), `Health check failed: ${error.message}`, 'error');
                    $('healthData').classList.add('hidden');
                    $('systemInfo').classList.add('hidden');
                }
            });
            
            $('refreshStatus').addEventListener('click', async () => {
                try {
                    // Update base URL
                    config.baseUrl = $('serviceUrl').value.trim();
                    
                    // Check API health
                    const apiAvailable = await checkApiHealth();
                    
                    if (apiAvailable && config.token) {
                        // Check full system health
                        await checkSystemHealth();
                    } else {
                        config.serviceStatus = {
                            api: apiAvailable,
                            memory: false,
                            cognition: false
                        };
                    }
                    
                    // Update UI
                    updateServiceStatus();
                    updateConnectionStatus(apiAvailable);
                } catch (error) {
                    showStatus($('serviceStatus'), `Error: ${error.message}`, 'error');
                }
            });
            
            // User input keyboard handling
            $('userInput').addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    $('sendMessage').click();
                }
            });
        }

        // Initialization
        async function init() {
            setupTabs();
            setupEventListeners();
            
            // Check if API is available
            try {
                const apiAvailable = await checkApiHealth();
                updateConnectionStatus(apiAvailable);
                
                if (apiAvailable) {
                    showStatus($('authStatus'), 'API is available. Please log in.', 'success');
                } else {
                    showStatus($('authStatus'), 'API is not available. Please check server status.', 'error');
                }
            } catch (error) {
                showStatus($('authStatus'), `Error: ${error.message}`, 'error');
            }
        }

        // Our fetchEventSource implementation is now directly included in the head

        // Start the application
        document.addEventListener('DOMContentLoaded', init);
    </script>
</body>
</html>
"""

def main():
    # Create a temporary HTML file
    temp_dir = tempfile.gettempdir()
    html_file = os.path.join(temp_dir, "cortex_test_client.html")
    
    with open(html_file, 'w') as f:
        f.write(HTML_CONTENT)
    
    # Start a simple HTTP server in a separate thread
    port = 8080
    
    # Use a simple HTTP server that allows directory listing
    class MyHTTPRequestHandler(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            if path == '/':
                return html_file
            return SimpleHTTPRequestHandler.translate_path(self, path)
    
    # Create the HTTP server
    try:
        server = HTTPServer(("localhost", port), MyHTTPRequestHandler)
        
        # Start the server in a separate thread
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        
        print(f"Cortex Test Client is running at http://localhost:{port}")
        
        # Open the client in a web browser
        url = f"http://localhost:{port}"
        webbrowser.open(url)
        
        # Keep the script running
        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("Shutting down server...")
            server.shutdown()
            sys.exit(0)
    except OSError as e:
        if e.errno == 98:
            print(f"Port {port} is already in use. Please close the application using this port and try again.")
            # Try to open the browser anyway
            webbrowser.open(f"http://localhost:{port}")
        else:
            print(f"Error starting server: {e}")
        
if __name__ == "__main__":
    main()