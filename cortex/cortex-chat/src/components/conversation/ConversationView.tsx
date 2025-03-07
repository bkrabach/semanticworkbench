import React, { useEffect, useRef } from 'react';
import {
    makeStyles,
    tokens,
    shorthands,
    Spinner,
    Text
} from '@fluentui/react-components';
import { useParams } from 'react-router-dom';
import { useConversation } from '../../api/hooks/useConversations';
import { useConversationStream } from '../../api/hooks/useSSE';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { useSendMessage } from '../../api/hooks/useMessages';

// Define styles for the conversation view
const useStyles = makeStyles({
    container: {
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        ...shorthands.overflow('hidden'),
    },
    header: {
        ...shorthands.padding(tokens.spacingVerticalS, tokens.spacingHorizontalM),
        ...shorthands.borderBottom('1px', 'solid', tokens.colorNeutralStroke1),
    },
    content: {
        flexGrow: 1,
        display: 'flex',
        flexDirection: 'column',
        ...shorthands.overflow('hidden'),
    },
    messageArea: {
        flexGrow: 1,
        ...shorthands.overflow('auto'),
        ...shorthands.padding(tokens.spacingVerticalM, tokens.spacingHorizontalM),
    },
    inputArea: {
        ...shorthands.padding(
            tokens.spacingVerticalS,
            tokens.spacingHorizontalM,
            tokens.spacingVerticalL,
            tokens.spacingHorizontalM
        ),
        ...shorthands.borderTop('1px', 'solid', tokens.colorNeutralStroke1),
        backgroundColor: tokens.colorNeutralBackground1,
    },
    emptyState: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: tokens.colorNeutralForeground3,
        textAlign: 'center',
        ...shorthands.gap(tokens.spacingVerticalL),
        ...shorthands.padding(tokens.spacingVerticalXL),
    },
    loadingContainer: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
    },
    streamStatus: {
        fontSize: tokens.fontSizeBase200,
        color: tokens.colorNeutralForeground3,
        ...shorthands.padding(tokens.spacingVerticalXS, tokens.spacingHorizontalS),
    }
});

/**
 * Main conversation view component that shows messages and input
 */
const ConversationView: React.FC = () => {
    const styles = useStyles();
    const { conversationId } = useParams<{ conversationId?: string }>();
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Fetch conversation data
    const {
        data: conversation,
        isLoading,
        error
    } = useConversation(conversationId);

    // Setup SSE connection for real-time updates
    const { status: streamStatus } = useConversationStream(conversationId);

    // Send message mutation
    const sendMessage = useSendMessage();

    // Scroll to bottom when new messages arrive
    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [conversation?.messages]);

    // Handle sending a new message
    const handleSendMessage = async (content: string) => {
        if (!conversationId || !content.trim()) return;

        try {
            await sendMessage.mutateAsync({
                conversationId,
                content,
                role: 'user',
            });
        } catch (err) {
            console.error('Failed to send message:', err);
        }
    };

    // If loading, show spinner
    if (isLoading) {
        return (
            <div className={styles.loadingContainer}>
                <Spinner size="medium" label="Loading conversation..." />
            </div>
        );
    }

    // If error, show error message
    if (error) {
        return (
            <div className={styles.emptyState}>
                <Text size={600}>Error loading conversation</Text>
                <Text>{error instanceof Error ? error.message : 'Unknown error'}</Text>
            </div>
        );
    }

    // If no conversation selected or not found
    if (!conversation) {
        return (
            <div className={styles.emptyState}>
                <Text size={600}>No conversation selected</Text>
                <Text>Select a conversation from the sidebar or create a new one</Text>
            </div>
        );
    }

    return (
        <div className={styles.container}>
            <header className={styles.header}>
                <Text size={500} weight="semibold">{conversation.title}</Text>
                <div>
                    <Text className={styles.streamStatus}>
                        Stream: {streamStatus}
                    </Text>
                </div>
            </header>

            <div className={styles.content}>
                <div className={styles.messageArea}>
                    <MessageList
                        messages={conversation.messages}
                        isStreaming={streamStatus === 'connected' && sendMessage.isPending}
                    />
                    <div ref={messagesEndRef} />
                </div>

                <div className={styles.inputArea}>
                    <MessageInput
                        onSendMessage={handleSendMessage}
                        isStreaming={streamStatus === 'connected'}
                        disabled={sendMessage.isPending}
                    />
                </div>
            </div>
        </div>
    );
};

export default ConversationView;