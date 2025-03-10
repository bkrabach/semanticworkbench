import { ChannelType, ConnectionStatus, SSEEvent } from '@/types';

// Type for event callbacks
export type EventCallback = (data: any) => void;

/**
 * SSE Manager for handling Server-Sent Events connections
 * Simplified implementation that follows web-client.html patterns exactly
 */
export class SSEManager {
    private baseUrl: string;
    private eventSources: Record<string, EventSource> = {};
    private reconnectAttempts: Record<string, number> = {};
    private tokenProvider: () => string | null = () => null;
    private MAX_RECONNECT_ATTEMPTS = 5;

    /**
     * Create a new SSEManager
     * @param baseUrl The base URL for SSE connections
     */
    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }

    /**
     * Set a function to provide authentication tokens
     * @param provider Function that returns the current auth token
     */
    setTokenProvider(provider: () => string | null): void {
        this.tokenProvider = provider;
    }

    /**
     * Connect to an SSE channel
     * @param type The channel type (global, workspace, conversation)
     * @param resourceId Optional resource ID for workspace or conversation channels
     * @returns The EventSource instance or null if connection failed
     */
    connectToSSE(type: ChannelType, resourceId?: string): EventSource | null {
        const token = this.tokenProvider();
        
        // Verify we have a valid token before connecting
        if (!token) {
            console.error(`[SSE:${type}] Cannot connect: No auth token available`);
            return null;
        }
        
        // For non-global channels, resourceId is required
        if (type !== 'global' && (!resourceId || resourceId === 'undefined' || resourceId === 'null')) {
            console.error(`[SSE:${type}] Cannot connect: Invalid resource ID ${resourceId}`);
            return null;
        }

        // Close existing connection if any
        this.closeConnection(type);
        
        // Build the SSE URL based on channel type
        const url = this.buildSseUrl(type, resourceId);
        
        try {
            console.log(`[SSE:${type}] Connecting to ${url}`);
            
            // Create new EventSource connection - exactly as in web-client.html
            const eventSource = new EventSource(url);
            
            // Set up common event handlers
            this.setupCommonEventHandlers(eventSource, type, resourceId);
            
            // Store connection
            this.eventSources[type] = eventSource;
            
            return eventSource;
        } catch (error) {
            console.error(`[SSE:${type}] Error creating connection:`, error);
            this.reconnect(type, resourceId);
            return null;
        }
    }

    /**
     * Close an SSE connection
     * @param type The channel type to disconnect
     */
    closeConnection(type: ChannelType): void {
        if (this.eventSources[type]) {
            console.log(`[SSE:${type}] Closing connection`);
            this.eventSources[type].close();
            delete this.eventSources[type];
        }
    }

    /**
     * Close all SSE connections
     */
    closeAllConnections(): void {
        Object.keys(this.eventSources).forEach(key => {
            const eventSource = this.eventSources[key as ChannelType];
            if (eventSource) {
                console.log(`[SSE:${key}] Closing connection`);
                eventSource.close();
            }
        });
        this.eventSources = {};
    }

    /**
     * Get the connection status for a channel
     * @param type The channel type
     * @returns ConnectionStatus
     */
    getConnectionStatus(type: ChannelType): ConnectionStatus {
        if (!this.eventSources[type]) {
            return ConnectionStatus.DISCONNECTED;
        }
        
        // Check readyState
        switch (this.eventSources[type].readyState) {
            case EventSource.CONNECTING:
                return ConnectionStatus.CONNECTING;
            case EventSource.OPEN:
                return ConnectionStatus.CONNECTED;
            case EventSource.CLOSED:
                return ConnectionStatus.DISCONNECTED;
            default:
                return ConnectionStatus.DISCONNECTED;
        }
    }

    /**
     * Add an event listener to a connection
     * @param type The channel type
     * @param eventName The event name to listen for
     * @param callback The callback to call when the event is received
     */
    addEventListener(type: ChannelType, eventName: string, callback: EventCallback): void {
        const eventSource = this.eventSources[type];
        if (!eventSource) {
            console.error(`[SSE:${type}] Cannot add event listener: No connection`);
            return;
        }
        
        console.log(`[SSE:${type}] Adding event listener for '${eventName}'`);
        
        eventSource.addEventListener(eventName, (event: MessageEvent) => {
            try {
                console.log(`[SSE:${type}] Received '${eventName}' event:`, event.data);
                const data = JSON.parse(event.data);
                callback(data);
            } catch (error) {
                console.error(`[SSE:${type}] Error handling '${eventName}' event:`, error);
            }
        });
    }

    /**
     * Setup for all SSE channels
     * @param channelType The type of channel
     * @param resourceId Optional resource ID for workspace or conversation
     */
    setupChannel(channelType: ChannelType, resourceId?: string): EventSource | null {
        const eventSource = this.connectToSSE(channelType, resourceId);
        
        if (!eventSource) {
            return null;
        }
        
        // Add channel-specific event listeners based on channel type
        switch (channelType) {
            case 'global':
                this.setupGlobalEvents(eventSource);
                break;
            case 'workspace':
                this.setupWorkspaceEvents(eventSource);
                break;
            case 'conversation':
                this.setupConversationEvents(eventSource);
                break;
        }
        
        return eventSource;
    }

    // Private helper methods

    /**
     * Build the SSE URL based on channel type and resource ID
     */
    private buildSseUrl(type: ChannelType, resourceId?: string): string {
        const token = this.tokenProvider();
        let url = new URL(`${this.baseUrl}/v1`);
        
        if (type === 'global') {
            url = new URL(`${this.baseUrl}/v1/global/global`);
        } else if (type === 'workspace' && resourceId) {
            url = new URL(`${this.baseUrl}/v1/workspace/${resourceId}`);
        } else if (type === 'conversation' && resourceId) {
            url = new URL(`${this.baseUrl}/v1/conversation/${resourceId}`);
        }
        
        // Add token to URL exactly as web-client does
        if (token) {
            url.searchParams.append('token', token);
        }
        
        return url.toString();
    }

    /**
     * Set up common event handlers for all SSE connections
     */
    private setupCommonEventHandlers(
        eventSource: EventSource, 
        type: ChannelType, 
        resourceId?: string
    ): void {
        // Connection opened
        eventSource.onopen = () => {
            console.log(`[SSE:${type}] Connection established`);
            this.reconnectAttempts[type] = 0;
        };
        
        // Connection error
        eventSource.onerror = (error) => {
            console.error(`[SSE:${type}] Connection error:`, error);
            
            // Handle reconnection
            this.reconnect(type, resourceId);
        };
        
        // Common events for all channels
        eventSource.addEventListener('connect', (event) => {
            console.log(`[SSE:${type}] Connect event received:`, event.data);
        });
        
        eventSource.addEventListener('heartbeat', (event) => {
            console.log(`[SSE:${type}] Heartbeat received`);
        });
    }

    /**
     * Set up global channel specific event listeners
     */
    private setupGlobalEvents(eventSource: EventSource): void {
        eventSource.addEventListener('notification', (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('[SSE:global] Notification received:', data);
                // Global notifications can be handled here
            } catch (error) {
                console.error('[SSE:global] Error parsing notification:', error);
            }
        });
        
        eventSource.addEventListener('system_update', (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('[SSE:global] System update received:', data);
                // System updates can be handled here
            } catch (error) {
                console.error('[SSE:global] Error parsing system update:', error);
            }
        });
    }

    /**
     * Set up workspace channel specific event listeners
     */
    private setupWorkspaceEvents(eventSource: EventSource): void {
        // These will be handled by the components that need this data
        // The components will add their own listeners via addEventListener
    }

    /**
     * Set up conversation channel specific event listeners
     */
    private setupConversationEvents(eventSource: EventSource): void {
        // These will be handled by the components that need this data
        // The components will add their own listeners via addEventListener
    }

    /**
     * Handle reconnection with exponential backoff
     */
    private reconnect(type: ChannelType, resourceId?: string): void {
        // Get current attempt count
        const attempts = this.reconnectAttempts[type] || 0;
        
        // Check if we've exceeded max reconnect attempts
        if (attempts >= this.MAX_RECONNECT_ATTEMPTS) {
            console.error(`[SSE:${type}] Max reconnect attempts reached (${this.MAX_RECONNECT_ATTEMPTS})`);
            return;
        }
        
        // Increment attempt counter
        this.reconnectAttempts[type] = attempts + 1;
        
        // Calculate backoff delay with exponential backoff (matching web-client.html exactly)
        const delay = Math.min(1000 * this.reconnectAttempts[type], 5000);
        
        console.log(`[SSE:${type}] Reconnecting in ${delay/1000} seconds... (attempt ${this.reconnectAttempts[type]}/${this.MAX_RECONNECT_ATTEMPTS})`);
        
        // Set timeout for reconnection
        setTimeout(() => {
            this.connectToSSE(type, resourceId);
        }, delay);
    }
}