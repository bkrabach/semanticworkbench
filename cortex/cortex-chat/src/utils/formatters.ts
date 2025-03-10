/**
 * Formats message content with Markdown-like syntax
 * Exactly matches web-client.html implementation
 * @param content The message content 
 * @returns Formatted message content with HTML elements
 */
export function formatMessageContent(content: string | object): string {
    if (typeof content !== 'string') {
        return JSON.stringify(content, null, 2);
    }
    
    // Convert code blocks - exact match with web-client.html
    const formattedContent = content
        .replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>');
    
    return formattedContent;
}

/**
 * Formats UTC timestamp to local time
 * Exactly matches web-client.html implementation
 * @param utcTimestamp The UTC timestamp in ISO format
 * @returns The formatted timestamp
 */
export function formatUTCToLocalTime(utcTimestamp: string | null | undefined): string {
    if (!utcTimestamp) return '';
    
    try {
        const date = new Date(utcTimestamp);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            return '';
        }
        
        return date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    } catch (error) {
        console.error('Error formatting timestamp:', error);
        return '';
    }
}

// Legacy function for backward compatibility
export const formatTimestamp = formatUTCToLocalTime;