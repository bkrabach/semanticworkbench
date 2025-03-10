/**
 * Formats UTC timestamp to local time
 * @param utcTimestamp The UTC timestamp in ISO format
 * @param options Optional Intl.DateTimeFormatOptions
 * @returns The formatted timestamp
 */
export function formatTimestamp(
    utcTimestamp: string | null | undefined,
    options: Intl.DateTimeFormatOptions = {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
    }
): string {
    if (!utcTimestamp) return '';
    
    try {
        const date = new Date(utcTimestamp);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            return '';
        }
        
        return date.toLocaleTimeString(undefined, options);
    } catch (error) {
        console.error('Error formatting timestamp:', error);
        return '';
    }
}

/**
 * Formats message content with Markdown-like syntax
 * @param content The message content 
 * @returns Formatted message content with HTML elements
 */
export function formatMessageContent(content: string | any): string {
    if (typeof content !== 'string') {
        return JSON.stringify(content, null, 2);
    }
    
    // Convert code blocks
    const formattedContent = content
        .replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>')
        // Convert inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>');
    
    return formattedContent;
}