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
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        ...shorthands.padding('12px', '16px'),
        ...shorthands.borderBottom('1px', 'solid', tokens.colorNeutralStroke2),
        backgroundColor: tokens.colorNeutralBackground1,
    },
    titleContainer: {
        display: 'flex',
        alignItems: 'center',
        ...shorthands.gap('8px'),
        overflow: 'hidden',
    },
    title: {
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
    },
    actionsContainer: {
        display: 'flex',
        ...shorthands.gap('4px'),
    },
    conversationContent: {
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        ...shorthands.overflow('hidden'),
    },
    messagesContainer: {
        flex: 1,
        minHeight: 0,
        ...shorthands.overflow('hidden'),
    },
    inputContainer: {
        ...shorthands.padding('16px'),
        backgroundColor: tokens.colorNeutralBackground1,
    },
    infoItem: {
        display: 'flex',
        justifyContent: 'space-between',
        ...shorthands.padding('4px', '0'),
    },
    infoLabel: {
        fontWeight: 'bold',
        marginRight: '8px',
    },
    infoValue: {
        color: tokens.colorNeutralForeground2,
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
                            appearance="subtle"
                            icon={<EditRegular />}
                            onClick={handleEditTitle}
                            aria-label="Edit conversation title"
                        />
                    )}
                    
                    <Popover>
                        <PopoverTrigger disableButtonEnhancement>
                            <Button
                                appearance="subtle"
                                icon={<InfoRegular />}
                                aria-label="Conversation information"
                            />
                        </PopoverTrigger>
                        <PopoverSurface>
                            <div style={{ padding: '12px', width: '280px' }}>
                                <Text weight="semibold" block>Conversation Details</Text>
                                <Divider style={{ margin: '8px 0' }} />
                                
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
                                        <Divider style={{ margin: '8px 0' }} />
                                        <Button
                                            appearance="subtle"
                                            icon={<DeleteRegular />}
                                            onClick={onDeleteConversation}
                                            style={{ marginTop: '8px' }}
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