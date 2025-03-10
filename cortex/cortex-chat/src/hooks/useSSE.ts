import { useEffect, useState } from 'react';
import { sseManager } from '@services/index';
import { ChannelType, ConnectionStatus } from '@/types';

type EventHandler = (data: any) => void;

/**
 * Hook for connecting to SSE channels and handling events
 * Simplified to match web-client.html patterns exactly
 */
export function useSSE(
    type: ChannelType,
    resourceId: string | undefined,
    eventHandlers: Record<string, EventHandler>,
    enabled: boolean = true
) {
    const [status, setStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED);
    
    useEffect(() => {
        // Only connect if enabled and we have necessary params
        if (!enabled || (type !== 'global' && !resourceId)) {
            console.log(`[useSSE:${type}] Not connecting - enabled: ${enabled}, resourceId: ${resourceId}`);
            return;
        }

        console.log(`[useSSE:${type}] Setting up SSE connection${resourceId ? ` for ${resourceId}` : ''}`);
        
        // Create the connection
        const eventSource = sseManager.connectToSSE(type, resourceId);
        
        // If connection failed, early return
        if (!eventSource) {
            console.error(`[useSSE:${type}] Failed to create connection`);
            setStatus(ConnectionStatus.ERROR);
            return;
        }
        
        // Track connection status
        const updateStatus = () => {
            const currentStatus = sseManager.getConnectionStatus(type);
            setStatus(currentStatus);
        };
        
        // Initial status
        updateStatus();
        
        // Update status on connection events
        eventSource.onopen = () => {
            console.log(`[useSSE:${type}] Connection opened`);
            updateStatus();
        };
        
        eventSource.onerror = () => {
            console.log(`[useSSE:${type}] Connection error`);
            updateStatus();
        };
        
        // Register event handlers - direct approach just like web-client.html
        Object.entries(eventHandlers).forEach(([eventName, handler]) => {
            console.log(`[useSSE:${type}] Registering handler for event: ${eventName}`);
            
            sseManager.addEventListener(type, eventName, (data) => {
                console.log(`[useSSE:${type}] Handling ${eventName} event:`, data);
                handler(data);
            });
        });
        
        // Cleanup on unmount
        return () => {
            console.log(`[useSSE:${type}] Cleaning up SSE connection`);
            sseManager.closeConnection(type);
        };
    }, [type, resourceId, eventHandlers, enabled]);
    
    // Return information about the connection and convenience methods
    return {
        status,
        isConnected: status === ConnectionStatus.CONNECTED,
        reconnect: () => sseManager.connectToSSE(type, resourceId),
        disconnect: () => sseManager.closeConnection(type),
    };
}