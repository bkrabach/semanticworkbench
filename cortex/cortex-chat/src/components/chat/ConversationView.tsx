import React from 'react';
import {
    makeStyles,
    tokens,
    shorthands,
    Text,
    Subtitle1,
    Button,
    Popover,
    PopoverTrigger,
    PopoverSurface,
    Divider
} from '@fluentui/react-components';
import { EditRegular, MoreHorizontal20Regular, DeleteRegular, InfoRegular } from '@fluentui/react-icons';
import { Conversation, Message } from '@/types';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';

const useStyles = makeStyles({
    container: {
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        position: 'relative',
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        ...shorthands.padding('0.75rem', '1rem'),
        ...shorthands.borderBottom('1px', 'solid', tokens.colorNeutralStroke2),
        backgroundColor: tokens.colorNeutralBackground1,
        minHeight: '3.5rem',
        // Make header sticky on mobile
        position: 'sticky',
        top: 0,
        zIndex: 10,
    },
    titleContainer: {
        display: 'flex',
        alignItems: 'center',
        ...shorthands.gap('0.5rem'),
        overflow: 'hidden',
        flex: 1,
    },
    title: {
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        fontSize: tokens.fontSizeBase500,
        // Smaller font on mobile
        '@media (max-width: 640px)': {
            fontSize: tokens.fontSizeBase400,
        },
    },
    actionsContainer: {
        display: 'flex',
        ...shorthands.gap('0.25rem'),
        flexShrink: 0,
        // Compact actions on small screens
        '@media (max-width: 640px)': {
            ...shorthands.gap('0.125rem'),
        },
    },
    conversationContent: {
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        ...shorthands.overflow('hidden'),
        position: 'relative',
    },
    messagesContainer: {
        flex: 1,
        minHeight: 0,
        ...shorthands.overflow('hidden'),
        // Add padding at the bottom to ensure messages don't get hidden behind the input area
        paddingBottom: '1rem',
    },
    inputContainer: {
        ...shorthands.padding('0.75rem', '1rem', '1rem'),
        backgroundColor: tokens.colorNeutralBackground1,
        ...shorthands.borderTop('1px', 'solid', tokens.colorNeutralStroke2),
        // Make input sticky on mobile so it's always visible
        position: 'sticky',
        bottom: 0,
        zIndex: 10,
        width: '100%',
        // Smaller padding on mobile
        '@media (max-width: 640px)': {
            ...shorthands.padding('0.5rem', '0.75rem', '0.75rem'),
        },
    },
    infoItem: {
        display: 'flex',
        justifyContent: 'space-between',
        ...shorthands.padding('0.25rem', '0'),
    },
    infoLabel: {
        fontWeight: 'bold',
        marginRight: '0.5rem',
    },
    infoValue: {
        color: tokens.colorNeutralForeground2,
    },
    // Add a compact button style for small screens
    actionButton: {
        '@media (max-width: 640px)': {
            minWidth: 'unset',
            ...shorthands.padding('0.25rem'),
        },
    },
    popoverContent: {
        ...shorthands.padding('0.75rem'),
        width: '280px',
        maxWidth: '100vw',
        // Smaller width on mobile
        '@media (max-width: 640px)': {
            width: '240px',
        },
    },
});

export interface ConversationViewProps {
    conversation: Conversation;
    isLoading?: boolean;
    isTyping?: boolean;
    onSendMessage: (content: string) => void;
    onEditTitle?: (newTitle: string) => void;
    onDeleteConversation?: () => void;
    className?: string;
}

export const ConversationView: React.FC<ConversationViewProps> = ({
    conversation,
    isLoading = false,
    isTyping = false,
    onSendMessage,
    onEditTitle,
    onDeleteConversation,
    className,
}) => {
    const styles = useStyles();

    const handleEditTitle = () => {
        if (!onEditTitle) return;
        
        const newTitle = prompt('Enter new conversation title:', conversation.title);
        if (newTitle && newTitle !== conversation.title) {
            onEditTitle(newTitle);
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className={`${styles.container} ${className || ''}`}>
            <div className={styles.header}>
                <div className={styles.titleContainer}>
                    <Subtitle1 className={styles.title}>
                        {conversation.title}
                    </Subtitle1>
                </div>
                
                <div className={styles.actionsContainer}>
                    {onEditTitle && (
                        <Button
                            className={styles.actionButton}
                            appearance="subtle"
                            icon={<EditRegular />}
                            onClick={handleEditTitle}
                            aria-label="Edit conversation title"
                            size="small"
                        />
                    )}
                    
                    <Popover>
                        <PopoverTrigger disableButtonEnhancement>
                            <Button
                                className={styles.actionButton}
                                appearance="subtle"
                                icon={<InfoRegular />}
                                aria-label="Conversation information"
                                size="small"
                            />
                        </PopoverTrigger>
                        <PopoverSurface>
                            <div className={styles.popoverContent}>
                                <Text weight="semibold" block>Conversation Details</Text>
                                <Divider style={{ margin: '0.5rem 0' }} />
                                
                                <div className={styles.infoItem}>
                                    <Text className={styles.infoLabel}>Created:</Text>
                                    <Text className={styles.infoValue}>
                                        {formatDate(conversation.created_at_utc)}
                                    </Text>
                                </div>
                                
                                <div className={styles.infoItem}>
                                    <Text className={styles.infoLabel}>Modality:</Text>
                                    <Text className={styles.infoValue}>
                                        {conversation.modality}
                                    </Text>
                                </div>
                                
                                <div className={styles.infoItem}>
                                    <Text className={styles.infoLabel}>Messages:</Text>
                                    <Text className={styles.infoValue}>
                                        {conversation.messages?.length || 0}
                                    </Text>
                                </div>
                                
                                {onDeleteConversation && (
                                    <>
                                        <Divider style={{ margin: '0.5rem 0' }} />
                                        <Button
                                            appearance="subtle"
                                            icon={<DeleteRegular />}
                                            onClick={onDeleteConversation}
                                            style={{ marginTop: '0.5rem' }}
                                            size="small"
                                        >
                                            Delete conversation
                                        </Button>
                                    </>
                                )}
                            </div>
                        </PopoverSurface>
                    </Popover>
                </div>
            </div>
            
            <div className={styles.conversationContent}>
                <div className={styles.messagesContainer}>
                    <MessageList
                        messages={conversation.messages || []}
                        isLoading={isLoading}
                        isTyping={isTyping}
                        conversationTitle={conversation.title}
                    />
                </div>
                
                <div className={styles.inputContainer}>
                    <MessageInput 
                        onSendMessage={onSendMessage}
                        isDisabled={isLoading}
                    />
                </div>
            </div>
        </div>
    );
};