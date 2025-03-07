import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';
import {
    makeStyles,
    tokens,
    shorthands,
    Button,
    Textarea,
    Spinner
} from '@fluentui/react-components';
import { Send24Regular } from '@fluentui/react-icons';

// Define styles for the message input
const useStyles = makeStyles({
    container: {
        display: 'flex',
        flexDirection: 'column',
        ...shorthands.gap(tokens.spacingVerticalS),
    },
    inputArea: {
        display: 'flex',
        alignItems: 'flex-end',
        ...shorthands.gap(tokens.spacingHorizontalS),
    },
    textArea: {
        flexGrow: 1,
        minHeight: '48px',
        maxHeight: '200px',
    },
    sendButton: {
        minWidth: '48px',
        height: '48px',
        ...shorthands.margin(0, 0, tokens.spacingVerticalXS, 0),
    }
});

interface MessageInputProps {
    onSendMessage: (content: string) => void;
    isStreaming?: boolean;
    disabled?: boolean;
}

/**
 * Component for inputting and sending messages
 */
const MessageInput: React.FC<MessageInputProps> = ({
    onSendMessage,
    isStreaming = false,
    disabled = false
}) => {
    const styles = useStyles();
    const [message, setMessage] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Focus the textarea when the component mounts
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.focus();
        }
    }, []);

    // Handle message submission
    const handleSendMessage = () => {
        if (message.trim() && !disabled) {
            onSendMessage(message);
            setMessage('');
        }
    };

    // Handle key presses for sending with Enter (but not with Shift+Enter)
    const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSendMessage();
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.inputArea}>
                <Textarea
                    ref={textareaRef}
                    className={styles.textArea}
                    resize="vertical"
                    placeholder="Type your message here..."
                    value={message}
                    onChange={(_, data) => setMessage(data.value)}
                    onKeyDown={handleKeyDown}
                    disabled={disabled}
                />
                <Button
                    className={styles.sendButton}
                    appearance="primary"
                    icon={disabled ? <Spinner size="tiny" /> : <Send24Regular />}
                    onClick={handleSendMessage}
                    disabled={!message.trim() || disabled}
                    aria-label="Send message"
                />
            </div>
            {isStreaming && (
                <small>
                    The assistant is responding in real-time. Your message will be sent after the current response completes.
                </small>
            )}
        </div>
    );
};

export default MessageInput;