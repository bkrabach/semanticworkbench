import React from 'react';
import {
    List,
    ListItem,
    Button,
    makeStyles,
    tokens,
    shorthands,
    Text,
    Subtitle1,
    Divider,
    Menu,
    MenuItem,
    MenuList,
    MenuPopover,
    MenuTrigger,
    Tooltip
} from '@fluentui/react-components';
import { 
    Add20Regular, 
    MoreHorizontal20Regular, 
    Chat20Regular, 
    DeleteRegular, 
    EditRegular 
} from '@fluentui/react-icons';
import { Conversation } from '@/types';

const useStyles = makeStyles({
    container: {
        display: 'flex',
        flexDirection: 'column',
        ...shorthands.gap('8px'),
        width: '100%',
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        ...shorthands.padding('4px', '8px'),
    },
    list: {
        display: 'flex',
        flexDirection: 'column',
        ...shorthands.gap('4px'),
        maxHeight: '400px',
        overflowY: 'auto',
        ...shorthands.padding('4px', '0'),
    },
    listItem: {
        ...shorthands.borderRadius('4px'),
        ':hover': {
            backgroundColor: tokens.colorNeutralBackground1Hover,
        },
        ':focus': {
            outlineWidth: '2px',
            outlineStyle: 'solid',
            outlineColor: tokens.colorBrandStroke1,
        },
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        ...shorthands.padding('10px', '12px'),
        cursor: 'pointer',
    },
    selectedItem: {
        backgroundColor: tokens.colorNeutralBackground1Selected,
        ':hover': {
            backgroundColor: tokens.colorNeutralBackground1Selected,
        },
    },
    itemContent: {
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        flex: 1,
        overflow: 'hidden',
    },
    itemIcon: {
        color: tokens.colorNeutralForeground3,
        flexShrink: 0,
    },
    itemText: {
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
    },
    emptyState: {
        textAlign: 'center',
        color: tokens.colorNeutralForeground3,
        ...shorthands.padding('16px', '8px'),
    },
    timestamp: {
        fontSize: tokens.fontSizeBase200,
        color: tokens.colorNeutralForeground3,
        marginLeft: 'auto',
        flexShrink: 0,
    },
});

export interface ConversationListProps {
    conversations: Conversation[];
    currentConversationId?: string;
    onSelectConversation: (conversationId: string) => void;
    onCreateConversation: () => void;
    onDeleteConversation?: (conversationId: string) => void;
    onRenameConversation?: (conversationId: string, newTitle: string) => void;
    isLoading?: boolean;
}

export const ConversationList: React.FC<ConversationListProps> = ({
    conversations,
    currentConversationId,
    onSelectConversation,
    onCreateConversation,
    onDeleteConversation,
    onRenameConversation,
    isLoading = false,
}) => {
    const styles = useStyles();

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const isToday = date.toDateString() === now.toDateString();
        
        if (isToday) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else {
            return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
        }
    };

    const handleRenameConversation = (conversationId: string) => {
        if (!onRenameConversation) return;
        
        const conversation = conversations.find(c => c.id === conversationId);
        if (!conversation) return;
        
        const newTitle = prompt('Enter new title:', conversation.title);
        if (newTitle && newTitle !== conversation.title) {
            onRenameConversation(conversationId, newTitle);
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <Subtitle1>Conversations</Subtitle1>
                <Tooltip content="New conversation" relationship="label">
                    <Button 
                        appearance="subtle"
                        icon={<Add20Regular />}
                        onClick={onCreateConversation}
                        aria-label="Create new conversation"
                    />
                </Tooltip>
            </div>
            <Divider />
            
            {isLoading ? (
                <div className={styles.emptyState}>
                    <Text>Loading conversations...</Text>
                </div>
            ) : conversations.length === 0 ? (
                <div className={styles.emptyState}>
                    <Text>No conversations found</Text>
                    <Button 
                        appearance="primary"
                        onClick={onCreateConversation}
                        size="small"
                        style={{ marginTop: '8px' }}
                    >
                        Start new conversation
                    </Button>
                </div>
            ) : (
                <List className={styles.list}>
                    {conversations.map((conversation) => (
                        <ListItem
                            key={conversation.id}
                            className={`${styles.listItem} ${currentConversationId === conversation.id ? styles.selectedItem : ''}`}
                            onClick={() => onSelectConversation(conversation.id)}
                        >
                            <div className={styles.itemContent}>
                                <Chat20Regular className={styles.itemIcon} />
                                <Text className={styles.itemText}>{conversation.title}</Text>
                                <Text className={styles.timestamp}>
                                    {formatDate(conversation.created_at_utc)}
                                </Text>
                            </div>
                            
                            {(onDeleteConversation || onRenameConversation) && (
                                <Menu>
                                    <MenuTrigger disableButtonEnhancement>
                                        <Button
                                            appearance="subtle"
                                            icon={<MoreHorizontal20Regular />}
                                            aria-label="More options"
                                            onClick={(e) => e.stopPropagation()}
                                        />
                                    </MenuTrigger>
                                    <MenuPopover>
                                        <MenuList>
                                            {onRenameConversation && (
                                                <MenuItem 
                                                    icon={<EditRegular />}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleRenameConversation(conversation.id);
                                                    }}
                                                >
                                                    Rename
                                                </MenuItem>
                                            )}
                                            {onDeleteConversation && (
                                                <MenuItem 
                                                    icon={<DeleteRegular />}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        onDeleteConversation(conversation.id);
                                                    }}
                                                >
                                                    Delete
                                                </MenuItem>
                                            )}
                                        </MenuList>
                                    </MenuPopover>
                                </Menu>
                            )}
                        </ListItem>
                    ))}
                </List>
            )}
        </div>
    );
};