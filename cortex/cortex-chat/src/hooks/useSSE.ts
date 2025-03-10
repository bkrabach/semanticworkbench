import { useEffect, useState, useCallback, useRef } from 'react';
import { sseManager } from '@services/index';
import { ChannelType, ConnectionStatus } from '@/types';

type EventHandler = (data: any) => void;

/**
 * Hook for connecting to SSE channels and handling events
 * Optimized for stability and performance
 */
export function useSSE(
    type: ChannelType,
    resourceId: string | undefined,
    eventHandlers: Record<string, EventHandler>,
    enabled: boolean = true
) {
    const [status, setStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED);
    const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
    
    // Use refs to track current values without triggering effect reruns
    const handlerRef = useRef(eventHandlers);
    const resourceIdRef = useRef(resourceId);
    const enabledRef = useRef(enabled);
    const typeRef = useRef(type);
    
    // Keep refs updated without triggering effects
    useEffect(() => {
        handlerRef.current = eventHandlers;
        resourceIdRef.current = resourceId;
        enabledRef.current = enabled;
        typeRef.current = type;
    }, [eventHandlers, resourceId, enabled, type]);
    
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
        if (isOnline && enabledRef.current && status === ConnectionStatus.ERROR && 
            (typeRef.current === 'global' || resourceIdRef.current)) {
            console.log(`[useSSE:${typeRef.current}] Network reconnected, reestablishing connection`);
            sseManager.connectToSSE(typeRef.current, resourceIdRef.current);
        }
    }, [isOnline, status]);
    
    // Create a stable connect function
    const connect = useCallback(() => {
        const currentType = typeRef.current;
        const currentResourceId = resourceIdRef.current;
        const currentEnabled = enabledRef.current;
        const currentHandlers = handlerRef.current;
        
        // Only connect if enabled and we have necessary params
        if (!currentEnabled || (currentType !== 'global' && !currentResourceId)) {
            console.log(`[useSSE:${currentType}] Not connecting - enabled: ${currentEnabled}, resourceId: ${currentResourceId}`);
            return null;
        }

        console.log(`[useSSE:${currentType}] Setting up SSE connection${currentResourceId ? ` for ${currentResourceId}` : ''}`);
        
        // Create the connection
        const eventSource = sseManager.connectToSSE(currentType, currentResourceId);
        
        // If connection failed, early return
        if (!eventSource) {
            console.error(`[useSSE:${currentType}] Failed to create connection`);
            setStatus(ConnectionStatus.ERROR);
            return null;
        }
        
        // Track connection status
        const updateStatus = () => {
            const currentStatus = sseManager.getConnectionStatus(currentType);
            setStatus(currentStatus);
        };
        
        // Initial status
        updateStatus();
        
        // Update status on connection events
        const originalOnOpen = eventSource.onopen;
        eventSource.onopen = (event) => {
            console.log(`[useSSE:${currentType}] Connection opened`);
            updateStatus();
            if (originalOnOpen) originalOnOpen.call(eventSource, event);
        };
        
        const originalOnError = eventSource.onerror;
        eventSource.onerror = (event) => {
            console.log(`[useSSE:${currentType}] Connection error`);
            updateStatus();
            if (originalOnError) originalOnError.call(eventSource, event);
        };
        
        // Register event handlers - always use the current handlers from ref
        Object.entries(currentHandlers).forEach(([eventName, handler]) => {
            console.log(`[useSSE:${currentType}] Registering handler for event: ${eventName}`);
            
            sseManager.addEventListener(currentType, eventName, (data) => {
                // Always use the most up-to-date handler from the ref
                console.log(`[useSSE:${currentType}] Handling ${eventName} event:`, data);
                // This will get the latest handler at the time of the event
                handlerRef.current[eventName](data);
            });
        });
        
        return eventSource;
    }, []); // No dependencies means this function is stable and won't change
    
    // Determine whether we need to connect or disconnect
    const shouldConnect = enabled && (type === 'global' || !!resourceId);
    
    // Main connection effect - only triggered on enabled/disabled or type/resource changes
    useEffect(() => {
        // Skip reconnection if nothing important has changed
        if (!shouldConnect) {
            console.log(`[useSSE:${type}] Connection disabled or missing resource ID`);
            sseManager.closeConnection(type);
            setStatus(ConnectionStatus.DISCONNECTED);
            return;
        }
        
        console.log(`[useSSE:${type}] Initial connection setup for ${resourceId || 'global'}`);
        const eventSource = connect();
        
        // Cleanup on unmount or when dependencies change
        return () => {
            console.log(`[useSSE:${type}] Cleaning up SSE connection`);
            sseManager.closeConnection(type);
        };
    }, [type, shouldConnect, connect]); // Only reconnect when type or connection state changes
    
    // Create a reconnect function that will properly reconnect when called
    const reconnect = useCallback(() => {
        console.log(`[useSSE:${typeRef.current}] Manual reconnection requested`);
        sseManager.closeConnection(typeRef.current);
        return connect();
    }, [connect]);
    
    // Create a disconnect function
    const disconnect = useCallback(() => {
        console.log(`[useSSE:${typeRef.current}] Manual disconnection requested`);
        sseManager.closeConnection(typeRef.current);
        setStatus(ConnectionStatus.DISCONNECTED);
    }, []);
    
    // Return information about the connection and convenience methods
    return {
        status,
        isConnected: status === ConnectionStatus.CONNECTED,
        isOnline,
        reconnect,
        disconnect,
    };
}