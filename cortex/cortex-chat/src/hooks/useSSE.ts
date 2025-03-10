import { useEffect, useState, useCallback } from 'react';
import { sseManager } from '@services/index';
import { ChannelType, ConnectionStatus } from '@/types';

type EventHandler = (data: any) => void;

/**
 * Hook for connecting to SSE channels and handling events
 * Matches web-client.html patterns exactly
 */
export function useSSE(
    type: ChannelType,
    resourceId: string | undefined,
    eventHandlers: Record<string, EventHandler>,
    enabled: boolean = true
) {
    const [status, setStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED);
    const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
    
    // Network status monitoring
    useEffect(() => {
        const handleOnline = () => {
            console.log(`[useSSE] Network status changed to online`);
            setIsOnline(true);
        };
        
        const handleOffline = () => {
            console.log(`[useSSE] Network status changed to offline`);
            setIsOnline(false);
        };
        
        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);
        
        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);
    
    // Reconnect when network comes back online
    useEffect(() => {
        if (isOnline && enabled && status === ConnectionStatus.ERROR && (type === 'global' || resourceId)) {
            console.log(`[useSSE:${type}] Network reconnected, reestablishing connection`);
            sseManager.connectToSSE(type, resourceId);
        }
    }, [isOnline, enabled, status, type, resourceId]);
    
    // Create a memoized connect function
    const connect = useCallback(() => {
        // Only connect if enabled and we have necessary params
        if (!enabled || (type !== 'global' && !resourceId)) {
            console.log(`[useSSE:${type}] Not connecting - enabled: ${enabled}, resourceId: ${resourceId}`);
            return null;
        }

        console.log(`[useSSE:${type}] Setting up SSE connection${resourceId ? ` for ${resourceId}` : ''}`);
        
        // Create the connection
        const eventSource = sseManager.connectToSSE(type, resourceId);
        
        // If connection failed, early return
        if (!eventSource) {
            console.error(`[useSSE:${type}] Failed to create connection`);
            setStatus(ConnectionStatus.ERROR);
            return null;
        }
        
        // Track connection status
        const updateStatus = () => {
            const currentStatus = sseManager.getConnectionStatus(type);
            setStatus(currentStatus);
        };
        
        // Initial status
        updateStatus();
        
        // Update status on connection events
        const originalOnOpen = eventSource.onopen;
        eventSource.onopen = (event) => {
            console.log(`[useSSE:${type}] Connection opened`);
            updateStatus();
            if (originalOnOpen) originalOnOpen.call(eventSource, event);
        };
        
        const originalOnError = eventSource.onerror;
        eventSource.onerror = (event) => {
            console.log(`[useSSE:${type}] Connection error`);
            updateStatus();
            if (originalOnError) originalOnError.call(eventSource, event);
        };
        
        // Register event handlers - direct approach just like web-client.html
        Object.entries(eventHandlers).forEach(([eventName, handler]) => {
            console.log(`[useSSE:${type}] Registering handler for event: ${eventName}`);
            
            sseManager.addEventListener(type, eventName, (data) => {
                console.log(`[useSSE:${type}] Handling ${eventName} event:`, data);
                handler(data);
            });
        });
        
        return eventSource;
    }, [type, resourceId, eventHandlers, enabled]);
    
    // Main connection effect
    useEffect(() => {
        const eventSource = connect();
        
        // Cleanup on unmount or when dependencies change
        return () => {
            console.log(`[useSSE:${type}] Cleaning up SSE connection`);
            sseManager.closeConnection(type);
        };
    }, [type, resourceId, eventHandlers, enabled, connect]);
    
    // Create a reconnect function that will properly reconnect when called
    const reconnect = useCallback(() => {
        console.log(`[useSSE:${type}] Manual reconnection requested`);
        sseManager.closeConnection(type);
        return connect();
    }, [type, connect]);
    
    // Create a disconnect function
    const disconnect = useCallback(() => {
        console.log(`[useSSE:${type}] Manual disconnection requested`);
        sseManager.closeConnection(type);
        setStatus(ConnectionStatus.DISCONNECTED);
    }, [type]);
    
    // Return information about the connection and convenience methods
    return {
        status,
        isConnected: status === ConnectionStatus.CONNECTED,
        isOnline,
        reconnect,
        disconnect,
    };
}