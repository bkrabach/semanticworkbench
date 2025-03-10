import '@testing-library/jest-dom'

// Mock EventSource for SSE testing
class MockEventSource {
    url: string
    onmessage: ((event: MessageEvent) => void) | null = null
    onerror: ((event: Event) => void) | null = null
    onopen: ((event: Event) => void) | null = null
    readyState: number = 0
    
    constructor(url: string) {
        this.url = url
    }
    
    addEventListener(
        type: string, 
        listener: EventListenerOrEventListenerObject
    ): void {
        // Implementation for adding event listeners
    }
    
    removeEventListener(
        type: string,
        listener: EventListenerOrEventListenerObject
    ): void {
        // Implementation for removing event listeners
    }
    
    close(): void {
        this.readyState = 2 // Closed
    }
}

// Add this to the global object for tests
(global as any).EventSource = MockEventSource