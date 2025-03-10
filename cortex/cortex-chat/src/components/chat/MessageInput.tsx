import React, { useState, useRef, useEffect } from 'react';
import {
    makeStyles,
    tokens,
    shorthands,
    Button,
    Textarea,
    Tooltip
} from '@fluentui/react-components';
import { SendRegular, AttachRegular, EmojiRegular } from '@fluentui/react-icons';

const useStyles = makeStyles({
    container: {
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        backgroundColor: tokens.colorNeutralBackground1,
        ...shorthands.borderRadius('0.5rem'),
        ...shorthands.padding('0.5rem'),
        ...shorthands.border('1px', 'solid', tokens.colorNeutralStroke1),
        maxWidth: '100%',
    },
    textareaContainer: {
        position: 'relative',
        width: '100%',
    },
    textarea: {
        width: '100%',
        maxHeight: '12.5rem', // 200px
        resize: 'none',
        ...shorthands.border('none'),
        ':focus': {
            outlineStyle: 'none',
        },
        '::placeholder': {
            color: tokens.colorNeutralForeground3,
        },
        // Adjust height and font size for mobile
        '@media (max-width: 640px)': {
            maxHeight: '9.375rem', // 150px
            fontSize: tokens.fontSizeBase300,
        },
    },
    actionsContainer: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: '0.5rem',
        flexWrap: 'wrap',
        // More compact layout on mobile
        '@media (max-width: 640px)': {
            marginTop: '0.25rem',
        },
    },
    leftActions: {
        display: 'flex',
        ...shorthands.gap('0.25rem'),
        // Hide attachment button on small screens to save space
        '@media (max-width: 480px)': {
            '& > button:first-child': {
                display: 'none',
            },
        },
    },
    rightActions: {
        display: 'flex',
        alignItems: 'center',
        // Reduce spacing on mobile
        '@media (max-width: 640px)': {
            ...shorthands.gap('0.25rem'),
        },
    },
    disabled: {
        backgroundColor: tokens.colorNeutralBackground3,
        cursor: 'not-allowed',
    },
    charCount: {
        fontSize: tokens.fontSizeBase200,
        color: tokens.colorNeutralForeground3,
        marginRight: '0.5rem',
        // Smaller text and reduced margins on mobile
        '@media (max-width: 640px)': {
            fontSize: tokens.fontSizeBase100,
            marginRight: '0.25rem',
        },
    },
    charCountWarning: {
        color: tokens.colorPaletteRedForeground1,
    },
    sendButton: {
        minWidth: '5rem',
        // Smaller button on mobile - icon only
        '@media (max-width: 480px)': {
            minWidth: 'unset',
            width: '2.5rem',
            ...shorthands.padding('0.5rem'),
            '& span': {
                display: 'none',
            },
        },
    },
});

export interface MessageInputProps {
    onSendMessage: (content: string) => void;
    isDisabled?: boolean;
    placeholder?: string;
    maxLength?: number;
    className?: string;
}

export const MessageInput: React.FC<MessageInputProps> = ({
    onSendMessage,
    isDisabled = false,
    placeholder = 'Type your message...',
    maxLength = 2000,
    className,
}) => {
    const styles = useStyles();
    const [message, setMessage] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const handleSubmit = () => {
        const trimmedMessage = message.trim();
        if (trimmedMessage && !isDisabled) {
            onSendMessage(trimmedMessage);
            setMessage('');
            
            // Focus back on textarea after sending
            if (textareaRef.current) {
                textareaRef.current.focus();
            }
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        // Submit on Enter (without Shift)
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    // Auto-resize textarea based on content
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
    }, [message]);

    // Focus textarea on mount
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.focus();
        }
    }, []);

    const isNearLimit = maxLength && message.length > maxLength * 0.8;
    const isAtLimit = maxLength && message.length >= maxLength;

    return (
        <div className={`${styles.container} ${isDisabled ? styles.disabled : ''} ${className || ''}`}>
            <div className={styles.textareaContainer}>
                <Textarea
                    ref={textareaRef}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    className={styles.textarea}
                    disabled={isDisabled}
                    resize="none"
                    maxLength={maxLength}
                    aria-label="Message input"
                />
            </div>
            
            <div className={styles.actionsContainer}>
                <div className={styles.leftActions}>
                    <Tooltip content="Attach files" relationship="label">
                        <Button
                            appearance="subtle"
                            icon={<AttachRegular />}
                            aria-label="Attach files"
                            disabled={isDisabled}
                            size="small"
                        />
                    </Tooltip>
                    <Tooltip content="Add emoji" relationship="label">
                        <Button
                            appearance="subtle"
                            icon={<EmojiRegular />}
                            aria-label="Add emoji"
                            disabled={isDisabled}
                            size="small"
                        />
                    </Tooltip>
                </div>
                
                <div className={styles.rightActions}>
                    {maxLength && (
                        <span className={`${styles.charCount} ${isNearLimit ? styles.charCountWarning : ''}`}>
                            {message.length}/{maxLength}
                        </span>
                    )}
                    
                    <Button
                        className={styles.sendButton}
                        appearance="primary"
                        icon={<SendRegular />}
                        onClick={handleSubmit}
                        disabled={isDisabled || !message.trim() || isAtLimit}
                        aria-label="Send message"
                    >
                        Send
                    </Button>
                </div>
            </div>
        </div>
    );
};