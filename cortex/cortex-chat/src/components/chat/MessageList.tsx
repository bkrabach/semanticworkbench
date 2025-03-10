import React, { useEffect, useRef } from 'react';
import {
    makeStyles,
    tokens,
    shorthands,
    Text,
    Spinner,
    Card,
    Avatar
} from '@fluentui/react-components';
import { Message } from '@/types';
import { MessageItem } from './MessageItem';

const useStyles = makeStyles({
    container: {
        display: 'flex',
        flexDirection: 'column',
        ...shorthands.gap('16px'),
        overflowY: 'auto',
        height: '100%',
        ...shorthands.padding('16px'),
    },
    emptyState: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: tokens.colorNeutralForeground3,
        textAlign: 'center',
        ...shorthands.padding('20px'),
    },
    loadingState: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
    },
    typingIndicator: {
        display: 'flex',
        alignItems: 'center',
        ...shorthands.gap('8px'),
        ...shorthands.padding('8px', '16px'),
        ...shorthands.borderRadius('4px'),
        backgroundColor: tokens.colorNeutralBackground1,
        marginBottom: '8px',
        alignSelf: 'flex-start',
        maxWidth: '75%',
    },
    dot: {
        width: '8px',
        height: '8px',
        ...shorthands.borderRadius('50%'),
        backgroundColor: tokens.colorNeutralForeground3,
        animation: 'wave 1.3s linear infinite',
    },
    dot2: {
        animationDelay: '-1.1s',
    },
    dot3: {
        animationDelay: '-0.9s',
    },
    '@keyframes wave': {
        '0%, 60%, 100%': {
            transform: 'initial',
        },
        '30%': {
            transform: 'translateY(-5px)',
        },
    },
    welcomeMessage: {
        ...shorthands.padding('16px'),
        backgroundColor: tokens.colorNeutralBackground2,
        ...shorthands.borderRadius('4px'),
        marginBottom: '24px',
    },
});

export interface MessageListProps {
    messages: Message[];
    isLoading?: boolean;
    isTyping?: boolean;
    conversationTitle?: string;
    className?: string;
}

export const MessageList: React.FC<MessageListProps> = ({
    messages,
    isLoading = false,
    isTyping = false,
    conversationTitle,
    className,
}) => {
    const styles = useStyles();
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Scroll to bottom when new messages arrive or typing state changes
    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isTyping]);

    if (isLoading) {
        return (
            <div className={styles.loadingState}>
                <Spinner size="medium" label="Loading messages..." />
            </div>
        );
    }

    if (messages.length === 0) {
        return (
            <div className={styles.emptyState}>
                <Card className={styles.welcomeMessage}>
                    <Text weight="semibold" size={500}>
                        Welcome to {conversationTitle || 'the conversation'}
                    </Text>
                    <Text block>
                        Start chatting to get the conversation going. Your messages will appear here.
                    </Text>
                </Card>
            </div>
        );
    }

    return (
        <div className={`${styles.container} ${className || ''}`}>
            {messages.map((message) => (
                <MessageItem key={message.id} message={message} />
            ))}
            
            {isTyping && (
                <div className={styles.typingIndicator}>
                    <Avatar 
                        size={24} 
                        name="Assistant" 
                        color="colorful" 
                    />
                    <div className={styles.dot}></div>
                    <div className={`${styles.dot} ${styles.dot2}`}></div>
                    <div className={`${styles.dot} ${styles.dot3}`}></div>
                </div>
            )}
            
            <div ref={messagesEndRef} />
        </div>
    );
};