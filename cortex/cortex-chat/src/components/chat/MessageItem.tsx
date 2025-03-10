import React from 'react';
import {
    makeStyles,
    tokens,
    shorthands,
    Text,
    Avatar,
    Card,
    Menu,
    MenuTrigger,
    MenuList,
    MenuItem,
    MenuPopover,
    Button
} from '@fluentui/react-components';
import { MoreHorizontal20Regular, CopyRegular, PersonRegular, Bot24Regular } from '@fluentui/react-icons';
import { Message } from '@/types';

const useStyles = makeStyles({
    container: {
        display: 'flex',
        width: '100%',
        ...shorthands.gap('12px'),
    },
    userMessage: {
        alignItems: 'flex-start',
        justifyContent: 'flex-end',
    },
    assistantMessage: {
        alignItems: 'flex-start',
    },
    systemMessage: {
        alignItems: 'center',
        justifyContent: 'center',
    },
    messageContent: {
        display: 'flex',
        flexDirection: 'column',
        maxWidth: '80%',
    },
    card: {
        ...shorthands.padding('12px', '16px'),
        width: 'fit-content',
        boxShadow: tokens.shadow4,
    },
    userCard: {
        backgroundColor: tokens.colorBrandBackground,
        ...shorthands.borderRadius('16px', '4px', '16px', '16px'),
        alignSelf: 'flex-end',
        color: tokens.colorNeutralForegroundOnBrand,
    },
    assistantCard: {
        backgroundColor: tokens.colorNeutralBackground1,
        ...shorthands.borderRadius('4px', '16px', '16px', '16px'),
    },
    systemCard: {
        backgroundColor: tokens.colorNeutralBackground3,
        ...shorthands.borderRadius('16px'),
        color: tokens.colorNeutralForeground2,
        fontStyle: 'italic',
        maxWidth: '70%',
        margin: '0 auto',
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '4px',
    },
    messageText: {
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        lineHeight: '1.5',
    },
    timestamp: {
        fontSize: tokens.fontSizeBase200,
        color: tokens.colorNeutralForeground3,
        alignSelf: 'flex-end',
        marginTop: '4px',
    },
    codeBlock: {
        backgroundColor: tokens.colorNeutralBackground3,
        ...shorthands.padding('8px'),
        ...shorthands.borderRadius('4px'),
        overflowX: 'auto',
        fontFamily: 'monospace',
        fontSize: '14px',
    },
});

export interface MessageItemProps {
    message: Message;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
    const styles = useStyles();

    // Determine container style based on message role
    const containerStyle = React.useMemo(() => {
        switch (message.role) {
            case 'user':
                return styles.userMessage;
            case 'assistant':
                return styles.assistantMessage;
            case 'system':
                return styles.systemMessage;
            default:
                return '';
        }
    }, [message.role, styles]);

    // Determine card style based on message role
    const cardStyle = React.useMemo(() => {
        switch (message.role) {
            case 'user':
                return styles.userCard;
            case 'assistant':
                return styles.assistantCard;
            case 'system':
                return styles.systemCard;
            default:
                return '';
        }
    }, [message.role, styles]);

    // Format timestamp
    const formattedTime = React.useMemo(() => {
        if (!message.created_at_utc) return '';
        
        const date = new Date(message.created_at_utc);
        return date.toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true 
        });
    }, [message.created_at_utc]);
    
    // Format message content with code blocks
    const formattedContent = React.useMemo(() => {
        if (typeof message.content !== 'string') {
            return JSON.stringify(message.content, null, 2);
        }
        
        // Split by code blocks to render differently
        const parts = message.content.split(/(```[\s\S]*?```)/g);
        
        return parts.map((part, index) => {
            if (part.startsWith('```') && part.endsWith('```')) {
                // This is a code block
                const code = part.slice(3, -3).trim();
                return (
                    <div key={index} className={styles.codeBlock}>
                        {code}
                    </div>
                );
            }
            return <span key={index}>{part}</span>;
        });
    }, [message.content, styles.codeBlock]);

    const copyToClipboard = () => {
        if (typeof message.content === 'string') {
            navigator.clipboard.writeText(message.content);
        } else {
            navigator.clipboard.writeText(JSON.stringify(message.content));
        }
    };

    return (
        <div className={`${styles.container} ${containerStyle}`}>
            {message.role !== 'user' && (
                <Avatar
                    name={message.role === 'assistant' ? 'Assistant' : 'System'}
                    icon={message.role === 'assistant' ? <Bot24Regular /> : undefined}
                    color={message.role === 'assistant' ? 'brand' : 'neutral'}
                    size={32}
                />
            )}
            
            <div className={styles.messageContent}>
                <Card className={`${styles.card} ${cardStyle}`}>
                    <div className={styles.header}>
                        <Text weight="semibold">
                            {message.role === 'user' ? 'You' : message.role === 'assistant' ? 'Assistant' : 'System'}
                        </Text>
                        
                        <Menu>
                            <MenuTrigger disableButtonEnhancement>
                                <Button
                                    appearance="subtle"
                                    icon={<MoreHorizontal20Regular />}
                                    size="small"
                                    aria-label="More options"
                                />
                            </MenuTrigger>
                            <MenuPopover>
                                <MenuList>
                                    <MenuItem 
                                        icon={<CopyRegular />}
                                        onClick={copyToClipboard}
                                    >
                                        Copy message
                                    </MenuItem>
                                </MenuList>
                            </MenuPopover>
                        </Menu>
                    </div>
                    
                    <div className={styles.messageText}>
                        {formattedContent}
                    </div>
                </Card>
                
                <Text className={styles.timestamp}>
                    {formattedTime}
                </Text>
            </div>
            
            {message.role === 'user' && (
                <Avatar
                    name="You"
                    icon={<PersonRegular />}
                    color="colorful"
                    size={32}
                />
            )}
        </div>
    );
};