import React from 'react';
import {
    makeStyles,
    tokens,
    shorthands,
    Text,
    Card,
    CardHeader,
    Avatar
} from '@fluentui/react-components';
import { Message } from '../../api/types';
import MarkdownRenderer from '../common/MarkdownRenderer';
import ToolResultView from '../common/ToolResultView';
import StreamingIndicator from './StreamingIndicator';

// Define styles for the message list
const useStyles = makeStyles({
    messageList: {
        display: 'flex',
        flexDirection: 'column',
        ...shorthands.gap(tokens.spacingVerticalM),
    },
    messageContainer: {
        display: 'flex',
        ...shorthands.gap(tokens.spacingHorizontalM),
        alignItems: 'flex-start',
    },
    userMessage: {
        backgroundColor: tokens.colorBrandBackground,
        color: tokens.colorNeutralForegroundOnBrand,
        alignSelf: 'flex-end',
        maxWidth: '80%',
    },
    assistantMessage: {
        backgroundColor: tokens.colorNeutralBackground2,
        alignSelf: 'flex-start',
        maxWidth: '80%',
    },
    systemMessage: {
        backgroundColor: tokens.colorNeutralBackground3,
        alignSelf: 'center',
        maxWidth: '90%',
        fontSize: tokens.fontSizeBase200,
    },
    messageContent: {
        ...shorthands.padding(tokens.spacingVerticalS, tokens.spacingHorizontalM),
    },
    messageHeader: {
        ...shorthands.padding(
            tokens.spacingVerticalXS,
            tokens.spacingHorizontalM,
            '0px',
            tokens.spacingHorizontalM
        ),
        fontSize: tokens.fontSizeBase200,
    },
    toolResultsContainer: {
        marginTop: tokens.spacingVerticalS,
    },
    timestamp: {
        fontSize: tokens.fontSizeBase100,
        color: tokens.colorNeutralForeground3,
    }
});

interface MessageListProps {
    messages: Message[];
    isStreaming?: boolean;
}

// Define valid avatar color type
type MessageAvatarColor = 'brand' | 'colorful' | 'neutral';

// Get avatar details based on message role
const getAvatarDetails = (role?: string): { name: string; color: MessageAvatarColor } => {
    switch (role) {
        case 'assistant':
            return { name: 'AI', color: 'brand' };
        case 'user':
            return { name: 'You', color: 'colorful' };
        case 'system':
        default:
            return { name: 'System', color: 'neutral' };
    }
};

// Get message style based on role
const getMessageStyle = (styles: ReturnType<typeof useStyles>, role?: string) => {
    switch (role) {
        case 'assistant':
            return styles.assistantMessage;
        case 'user':
            return styles.userMessage;
        case 'system':
            return styles.systemMessage;
        default:
            return styles.assistantMessage;
    }
};

// Format timestamp
const formatTime = (dateString?: string) => {
    if (!dateString) return '';

    const date = new Date(dateString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

/**
 * Component to display a list of messages
 */
const MessageList: React.FC<MessageListProps> = ({ messages, isStreaming = false }) => {
    const styles = useStyles();

    if (!messages || messages.length === 0) {
        return (
            <div className={styles.messageList}>
                <Card className={styles.systemMessage}>
                    <CardHeader header={<Text>No messages yet</Text>} />
                </Card>
            </div>
        );
    }

    return (
        <div className={styles.messageList}>
            {messages.map((message) => {
                const avatarDetails = getAvatarDetails(message.role);
                const messageStyle = getMessageStyle(styles, message.role);

                return (
                    <div key={message.id} className={styles.messageContainer}>
                        {message.role === 'assistant' && (
                            <Avatar name={avatarDetails.name} color={avatarDetails.color} />
                        )}

                        <Card className={messageStyle}>
                            <div className={styles.messageHeader}>
                                <Text weight="semibold">{avatarDetails.name}</Text>
                                <Text className={styles.timestamp}>{formatTime(message.createdAt)}</Text>
                            </div>

                            <div className={styles.messageContent}>
                                {/* Render message content as markdown */}
                                <MarkdownRenderer content={message.content} />

                                {/* Show tool executions if any */}
                                {message.toolExecutions && message.toolExecutions.length > 0 && (
                                    <div className={styles.toolResultsContainer}>
                                        {message.toolExecutions.map((tool) => (
                                            <ToolResultView key={tool.id} toolExecution={tool} />
                                        ))}
                                    </div>
                                )}
                            </div>
                        </Card>

                        {message.role === 'user' && (
                            <Avatar name={avatarDetails.name} color={avatarDetails.color} />
                        )}
                    </div>
                );
            })}

            {/* Streaming indicator shown when messages are being streamed */}
            {isStreaming && (
                <div className={styles.messageContainer}>
                    <Avatar name="AI" color="brand" />
                    <Card className={styles.assistantMessage}>
                        <div className={styles.messageHeader}>
                            <Text weight="semibold">AI</Text>
                        </div>
                        <div className={styles.messageContent}>
                            <StreamingIndicator />
                        </div>
                    </Card>
                </div>
            )}
        </div>
    );
};

export default MessageList;