import { EventSourcePolyfill } from 'event-source-polyfill';
import { ChannelType, ConnectionStatus, SSEEvent } from '@/types';

// Use the polyfill or native EventSource depending on environment
const EventSourceImpl = EventSourcePolyfill || EventSource;

// Type for event callbacks
export type EventCallback = (data: any) => void;

/**
 * SSE Manager for handling Server-Sent Events connections
 * Implements the pattern described in ADR-001
 */
export class SSEManager {
    private baseUrl: string;
    private eventSources: Record<string, EventSource> = {};
    private eventHandlers: Record<string, Record<string, EventCallback[]>> = {};
    private connectionStatus: Record<string, ConnectionStatus> = {};
    private reconnectTimeouts: Record<string, NodeJS.Timeout> = {};
    private reconnectAttempts: Record<string, number> = {};
    private maxReconnectAttempts: number = 5;
    private tokenProvider: () => string | null = () => null;

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
     * @param channel The channel type (global, workspace, conversation)
     * @param resourceId Optional resource ID for workspace or conversation channels
     * @returns The EventSource instance or null if connection failed
     */
    connect(channel: ChannelType, resourceId?: string): EventSource | null {
        const token = this.tokenProvider();
        
        if (!token) {
            console.error('No authentication token available');
            return null;
        }
        
        // For non-global channels, resourceId is required
        if (channel !== 'global' && !resourceId) {
            console.error(`ResourceId is required for channel type: ${channel}`);
            return null;
        }
        
        const connectionKey = this.getConnectionKey(channel, resourceId);
        
        // Close existing connection if any
        this.disconnect(connectionKey);
        
        // Set initial connection status
        this.connectionStatus[connectionKey] = ConnectionStatus.CONNECTING;
        
        // Build the SSE URL based on channel type
        const url = this.buildUrl(channel, resourceId, token);
        
        try {
            // Create new EventSource connection
            const eventSource = new EventSourceImpl(url);
            
            // Set up connection event handlers
            eventSource.onopen = this.handleOpen(connectionKey);
            eventSource.onerror = this.handleError(connectionKey, channel, resourceId);
            
            // Register existing event handlers for this connection
            this.registerEventHandlers(connectionKey, eventSource);
            
            // Store the connection
            this.eventSources[connectionKey] = eventSource;
            
            return eventSource;
        } catch (error) {
            console.error(`Error creating SSE connection to ${channel}:`, error);
            this.connectionStatus[connectionKey] = ConnectionStatus.ERROR;
            this.handleReconnect(connectionKey, channel, resourceId);
            return null;
        }
    }

    /**
     * Disconnect from an SSE channel
     * @param connectionKey The connection key
     */
    disconnect(connectionKey: string): void {
        // Clear any pending reconnect timeout
        if (this.reconnectTimeouts[connectionKey]) {
            clearTimeout(this.reconnectTimeouts[connectionKey]);
            delete this.reconnectTimeouts[connectionKey];
        }
        
        // Close the connection if it exists
        if (this.eventSources[connectionKey]) {
            this.eventSources[connectionKey].close();
            delete this.eventSources[connectionKey];
            this.connectionStatus[connectionKey] = ConnectionStatus.DISCONNECTED;
        }
        
        // Reset reconnect attempts
        delete this.reconnectAttempts[connectionKey];
    }

    /**
     * Disconnect from all SSE channels
     */
    disconnectAll(): void {
        Object.keys(this.eventSources).forEach(key => {
            this.disconnect(key);
        });
    }

    /**
     * Register an event handler for a specific event type
     * @param connectionKey The connection key
     * @param eventType The event type to listen for
     * @param callback The callback function to call when the event is received
     */
    on(connectionKey: string, eventType: string, callback: EventCallback): void {
        // Initialize event handlers for this connection if needed
        if (!this.eventHandlers[connectionKey]) {
            this.eventHandlers[connectionKey] = {};
        }
        
        // Initialize handlers for this event type if needed
        if (!this.eventHandlers[connectionKey][eventType]) {
            this.eventHandlers[connectionKey][eventType] = [];
        }
        
        // Add the callback to the handlers
        this.eventHandlers[connectionKey][eventType].push(callback);
        
        // If connection exists, ensure the event listener is added
        if (this.eventSources[connectionKey]) {
            this.addEventListenerToConnection(
                this.eventSources[connectionKey], 
                eventType, 
                this.createEventListener(connectionKey, eventType)
            );
        }
    }

    /**
     * Remove an event handler for a specific event type
     * @param connectionKey The connection key
     * @param eventType The event type to remove handler for
     * @param callback Optional specific callback to remove, or all if not provided
     */
    off(connectionKey: string, eventType: string, callback?: EventCallback): void {
        if (!this.eventHandlers[connectionKey] || 
            !this.eventHandlers[connectionKey][eventType]) {
            return;
        }
        
        if (callback) {
            // Remove specific callback
            this.eventHandlers[connectionKey][eventType] = 
                this.eventHandlers[connectionKey][eventType].filter(cb => cb !== callback);
        } else {
            // Remove all callbacks for this event type
            this.eventHandlers[connectionKey][eventType] = [];
        }
    }

    /**
     * Get the current connection status
     * @param connectionKey The connection key
     * @returns The connection status
     */
    getConnectionStatus(connectionKey: string): ConnectionStatus {
        return this.connectionStatus[connectionKey] || ConnectionStatus.DISCONNECTED;
    }

    // Private helper methods

    /**
     * Build the SSE URL based on channel type and resource ID
     */
    private buildUrl(channel: ChannelType, resourceId?: string, token?: string): string {
        let url = `${this.baseUrl}/v1`;
        
        switch (channel) {
            case 'global':
                url += `/global`;
                break;
            case 'workspace':
                url += `/workspace/${resourceId}`;
                break;
            case 'conversation':
                url += `/conversation/${resourceId}`;
                break;
            default:
                throw new Error(`Invalid channel type: ${channel}`);
        }
        
        // Add token if available
        if (token) {
            url += `?token=${encodeURIComponent(token)}`;
        }
        
        return url;
    }

    /**
     * Get a unique key for a connection based on channel and resource ID
     */
    private getConnectionKey(channel: ChannelType, resourceId?: string): string {
        return resourceId ? `${channel}_${resourceId}` : channel;
    }

    /**
     * Create an event handler for the 'open' event
     */
    private handleOpen(connectionKey: string) {
        return () => {
            console.log(`SSE connection opened: ${connectionKey}`);
            this.connectionStatus[connectionKey] = ConnectionStatus.CONNECTED;
            this.reconnectAttempts[connectionKey] = 0;
            
            // Trigger handlers for the 'open' event
            this.triggerEvent(connectionKey, 'open', { connectionKey });
        };
    }

    /**
     * Create an event handler for the 'error' event
     */
    private handleError(connectionKey: string, channel: ChannelType, resourceId?: string) {
        return (error: Event) => {
            console.error(`SSE connection error: ${connectionKey}`, error);
            
            // Trigger handlers for the 'error' event
            this.triggerEvent(connectionKey, 'error', { connectionKey, error });
            
            // Attempt to reconnect
            this.handleReconnect(connectionKey, channel, resourceId);
        };
    }

    /**
     * Handle reconnection attempts
     */
    private handleReconnect(connectionKey: string, channel: ChannelType, resourceId?: string): void {
        // Check if we've exceeded max reconnect attempts
        const attempts = this.reconnectAttempts[connectionKey] || 0;
        
        if (attempts >= this.maxReconnectAttempts) {
            console.error(`Max reconnect attempts reached for ${connectionKey}`);
            this.connectionStatus[connectionKey] = ConnectionStatus.ERROR;
            this.triggerEvent(connectionKey, 'reconnect_failed', { 
                connectionKey, 
                attempts 
            });
            return;
        }
        
        // Increment reconnect attempts
        this.reconnectAttempts[connectionKey] = attempts + 1;
        
        // Set connection status to reconnecting
        this.connectionStatus[connectionKey] = ConnectionStatus.RECONNECTING;
        
        // Trigger reconnecting event
        this.triggerEvent(connectionKey, 'reconnecting', { 
            connectionKey, 
            attempt: this.reconnectAttempts[connectionKey] 
        });
        
        // Calculate backoff delay (with exponential backoff)
        const delay = Math.min(1000 * Math.pow(2, attempts), 30000);
        
        // Set timeout for reconnection
        this.reconnectTimeouts[connectionKey] = setTimeout(() => {
            console.log(`Attempting to reconnect to ${connectionKey} (attempt ${attempts + 1})`);
            this.connect(channel, resourceId);
        }, delay);
    }

    /**
     * Register existing event handlers for a new connection
     */
    private registerEventHandlers(connectionKey: string, eventSource: EventSource): void {
        if (this.eventHandlers[connectionKey]) {
            Object.keys(this.eventHandlers[connectionKey]).forEach(eventType => {
                this.addEventListenerToConnection(
                    eventSource, 
                    eventType, 
                    this.createEventListener(connectionKey, eventType)
                );
            });
        }
    }

    /**
     * Add an event listener to a connection
     */
    private addEventListenerToConnection(
        eventSource: EventSource, 
        eventType: string, 
        listener: (event: MessageEvent) => void
    ): void {
        eventSource.addEventListener(eventType, listener);
    }

    /**
     * Create an event listener function for a specific event type
     */
    private createEventListener(connectionKey: string, eventType: string): (event: MessageEvent) => void {
        return (event: MessageEvent) => {
            try {
                // Parse event data
                const data = JSON.parse(event.data);
                
                // Trigger handlers for this event type
                this.triggerEvent(connectionKey, eventType, data);
            } catch (error) {
                console.error(`Error parsing SSE data for ${eventType}:`, error);
            }
        };
    }

    /**
     * Trigger all handlers for a specific event type
     */
    private triggerEvent(connectionKey: string, eventType: string, data: any): void {
        // Check if we have handlers for this connection and event type
        if (!this.eventHandlers[connectionKey] || 
            !this.eventHandlers[connectionKey][eventType]) {
            return;
        }
        
        // Call each handler with the event data
        this.eventHandlers[connectionKey][eventType].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`Error in SSE event handler for ${eventType}:`, error);
            }
        });
    }
}