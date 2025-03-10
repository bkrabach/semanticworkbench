import { useEffect, useRef } from 'react';
import { sseManager } from '@services/index';
import { ChannelType, ConnectionStatus } from '@/types';

type EventHandler = (data: any) => void;

/**
 * Hook for connecting to SSE channels and handling events
 */
export function useSSE(
    channel: ChannelType,
    resourceId: string | undefined,
    eventHandlers: Record<string, EventHandler>,
    enabled: boolean = true
) {
    // Keep track of connection status
    const connectionKey = useRef<string>('');
    
    useEffect(() => {
        // Only connect if enabled and we have necessary params
        if (!enabled || (channel !== 'global' && !resourceId)) {
            return;
        }
        
        // Set connection key for reference
        connectionKey.current = resourceId ? `${channel}_${resourceId}` : channel;
        
        // Connect to SSE channel
        const eventSource = sseManager.connect(channel, resourceId);
        
        // If connection failed, early return
        if (!eventSource) {
            return;
        }
        
        // Register event handlers
        Object.entries(eventHandlers).forEach(([eventType, handler]) => {
            sseManager.on(connectionKey.current, eventType, handler);
        });
        
        // Cleanup on unmount
        return () => {
            sseManager.disconnect(connectionKey.current);
        };
    }, [channel, resourceId, eventHandlers, enabled]);
    
    // Return helpful information about the connection
    return {
        connectionStatus: sseManager.getConnectionStatus(connectionKey.current),
        isConnected: sseManager.getConnectionStatus(connectionKey.current) === ConnectionStatus.CONNECTED,
        reconnect: () => sseManager.connect(channel, resourceId),
        disconnect: () => sseManager.disconnect(connectionKey.current)
    };
}