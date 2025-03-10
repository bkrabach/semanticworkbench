import { ChannelType, ConnectionStatus } from '@/types';

// Type for event callbacks
export type EventCallback = (data: any) => void;

/**
 * SSE Manager for handling Server-Sent Events connections
 * Matches web-client.html patterns exactly
 */
export class SSEManager {
    private baseUrl: string;
    private eventSources: Record<string, EventSource> = {};
    private reconnectAttempts: Record<string, number> = {};
    private tokenProvider: () => string | null = () => null;
    private MAX_RECONNECT_ATTEMPTS = 5;
    private hasConnected: Record<string, boolean> = {};

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
        if (
            type !== 'global' &&
            (!resourceId || resourceId === 'undefined' || resourceId === 'null')
        ) {
            console.error(`[SSE:${type}] Cannot connect: Invalid resource ID ${resourceId}`);
            return null;
        }

        // Check if we already have a connection to this channel
        if (this.eventSources[type]) {
            const existingConnection = this.eventSources[type];

            // If the connection is open or connecting, don't create a new one
            if (
                existingConnection.readyState === EventSource.OPEN ||
                existingConnection.readyState === EventSource.CONNECTING
            ) {
                console.log(
                    `[SSE:${type}] Reusing existing connection in state ${existingConnection.readyState}`
                );
                return existingConnection;
            }

            // Close the existing connection if it's in a bad state
            console.log(
                `[SSE:${type}] Closing stale connection in state ${existingConnection.readyState}`
            );
            this.closeConnection(type);
        }

        // Build the SSE URL based on channel type
        const url = this.buildSseUrl(type, resourceId);

        try {
            console.log(`[SSE:${type}] Connecting to ${url}`);

            // Create new EventSource connection
            const eventSource = new EventSource(url);

            // Reset connection state for this channel
            this.hasConnected[type] = false;
            this.reconnectAttempts[type] = 0;

            // Set up event handlers
            this.setupEventHandlers(eventSource, type, resourceId);

            // Store connection
            this.eventSources[type] = eventSource;

            return eventSource;
        } catch (error) {
            console.error(`[SSE:${type}] Error creating connection:`, error);
            // Only attempt reconnect if we don't already have a reconnect in progress
            if (!(type in this.reconnectAttempts) || this.reconnectAttempts[type] === 0) {
                this.reconnect(type, resourceId);
            }
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

            // Clear event listeners for this channel
            if (this.eventListeners[type]) {
                console.log(`[SSE:${type}] Clearing event listeners`);
                delete this.eventListeners[type];
            }

            // Reset connection attempts
            this.reconnectAttempts[type] = 0;
            this.hasConnected[type] = false;
        }
    }

    /**
     * Close all SSE connections
     */
    closeAllConnections(): void {
        Object.keys(this.eventSources).forEach((key) => {
            const eventSource = this.eventSources[key as ChannelType];
            if (eventSource) {
                console.log(`[SSE:${key}] Closing connection`);
                eventSource.close();
            }
        });
        this.eventSources = {};
        this.reconnectAttempts = {};
        this.hasConnected = {};
        this.eventListeners = {};
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

    // Store callbacks by channel and event name to prevent duplicates
    private eventListeners: Record<string, Record<string, EventCallback[]>> = {};

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

        // Initialize listener store for this channel if needed
        if (!this.eventListeners[type]) {
            this.eventListeners[type] = {};
        }

        // Initialize listener array for this event if needed
        if (!this.eventListeners[type][eventName]) {
            this.eventListeners[type][eventName] = [];

            // Only add the actual DOM event listener once per event name
            console.log(`[SSE:${type}] Adding DOM event listener for '${eventName}'`);

            eventSource.addEventListener(eventName, (event: MessageEvent) => {
                try {
                    console.log(`[SSE:${type}] Received '${eventName}' event:`, event.data);
                    const data = JSON.parse(event.data);

                    // Call all registered callbacks for this event
                    const listeners = this.eventListeners[type][eventName] || [];
                    listeners.forEach((cb) => {
                        try {
                            cb(data);
                        } catch (cbError) {
                            console.error(`[SSE:${type}] Error in ${eventName} callback:`, cbError);
                        }
                    });
                } catch (error) {
                    console.error(`[SSE:${type}] Error handling '${eventName}' event:`, error);
                }
            });
        }

        // Check if this exact callback is already registered
        const existingCallbacks = this.eventListeners[type][eventName];
        if (!existingCallbacks.includes(callback)) {
            console.log(`[SSE:${type}] Registering callback for '${eventName}'`);
            existingCallbacks.push(callback);
        } else {
            console.log(`[SSE:${type}] Callback for '${eventName}' already registered, skipping`);
        }
    }

    // Private helper methods

    /**
     * Build the SSE URL based on channel type and resource ID
     */
    private buildSseUrl(type: ChannelType, resourceId?: string): string {
        const token = this.tokenProvider();
        let url: URL;

        // Determine the URL based on the type - exact match with web-client.html
        switch (type) {
            case 'global':
                url = new URL(`${this.baseUrl}/v1/global/global`);
                break;
            case 'workspace':
                url = new URL(`${this.baseUrl}/v1/workspace/${resourceId}`);
                break;
            case 'conversation':
                url = new URL(`${this.baseUrl}/v1/conversation/${resourceId}`);
                break;
            default:
                url = new URL(`${this.baseUrl}/v1`);
                console.error('Invalid SSE type:', type);
        }

        // Add token to URL exactly as web-client does
        if (token) {
            url.searchParams.append('token', token);
        }

        return url.toString();
    }

    /**
     * Set up all event handlers for an SSE connection
     */
    private setupEventHandlers(
        eventSource: EventSource,
        type: ChannelType,
        resourceId?: string
    ): void {
        // Connection opened
        eventSource.onopen = () => {
            console.log(`[SSE:${type}] Connection established`);
            this.hasConnected[type] = true;
            this.reconnectAttempts[type] = 0; // Reset reconnect attempts after successful connection
        };

        // Connection error - exact matching of web-client.html behavior
        eventSource.onerror = (error) => {
            console.error(`[SSE:${type}] Connection error:`, error);

            // If we never established a connection and have exceeded max attempts, give up
            if (
                !this.hasConnected[type] &&
                (this.reconnectAttempts[type] || 0) >= this.MAX_RECONNECT_ATTEMPTS
            ) {
                console.error(
                    `[SSE:${type}] Failed to connect after ${this.MAX_RECONNECT_ATTEMPTS} attempts, giving up`
                );

                // Clean up the resource
                if (this.eventSources[type] === eventSource) {
                    this.closeConnection(type);
                }
                return;
            }

            // Check if service is unavailable or connection was rejected
            const isServiceUnavailable =
                // @ts-ignore - EventSource error has target property
                error.target && error.target.readyState === EventSource.CONNECTING;

            // Determine if we should reconnect - follows web-client.html logic exactly
            const shouldReconnect =
                !isServiceUnavailable &&
                (this.reconnectAttempts[type] || 0) < this.MAX_RECONNECT_ATTEMPTS;

            if (shouldReconnect) {
                this.reconnect(type, resourceId);
            }
        };

        // Common events
        eventSource.addEventListener('connect', (event) => {
            console.log(
                `[SSE:${type}] Connect event received:`,
                event.data ? JSON.parse(event.data) : {}
            );
        });

        eventSource.addEventListener('heartbeat', (event) => {
            console.log(
                `[SSE:${type}] Heartbeat received:`,
                event.data ? JSON.parse(event.data) : {}
            );
        });
    }

    /**
     * Handle reconnection with exponential backoff
     */
    private reconnect(type: ChannelType, resourceId?: string): void {
        // Get current attempt count
        const attempts = this.reconnectAttempts[type] || 0;

        // Increment attempt counter
        this.reconnectAttempts[type] = attempts + 1;

        // Calculate backoff delay with exponential backoff (matching web-client.html exactly)
        const delay = Math.min(1000 * this.reconnectAttempts[type], 5000);

        console.log(
            `[SSE:${type}] Reconnecting in ${delay / 1000} seconds... (attempt ${this.reconnectAttempts[type]}/${this.MAX_RECONNECT_ATTEMPTS})`
        );

        // Set timeout for reconnection - matching web-client.html pattern
        setTimeout(() => {
            // Only close current connection right before creating a new one
            if (this.eventSources[type]) {
                this.eventSources[type].close();
            }
            this.connectToSSE(type, resourceId);
        }, delay);
    }
}
