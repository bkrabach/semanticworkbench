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
        ...shorthands.gap('0.75rem'),
        // Reduce gap on mobile
        '@media (max-width: 640px)': {
            ...shorthands.gap('0.5rem'),
        },
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
        // Wider message bubbles on mobile
        '@media (max-width: 640px)': {
            maxWidth: '85%',
        },
        '@media (max-width: 480px)': {
            maxWidth: '90%',
        },
    },
    card: {
        ...shorthands.padding('0.75rem', '1rem'),
        width: 'fit-content',
        boxShadow: tokens.shadow4,
        // Less padding on mobile
        '@media (max-width: 640px)': {
            ...shorthands.padding('0.625rem', '0.875rem'),
        },
    },
    userCard: {
        backgroundColor: tokens.colorBrandBackground,
        ...shorthands.borderRadius('1rem', '0.25rem', '1rem', '1rem'),
        alignSelf: 'flex-end',
        color: tokens.colorNeutralForegroundOnBrand,
    },
    assistantCard: {
        backgroundColor: tokens.colorNeutralBackground1,
        ...shorthands.borderRadius('0.25rem', '1rem', '1rem', '1rem'),
    },
    systemCard: {
        backgroundColor: tokens.colorNeutralBackground3,
        ...shorthands.borderRadius('1rem'),
        color: tokens.colorNeutralForeground2,
        fontStyle: 'italic',
        maxWidth: '70%',
        margin: '0 auto',
        // Wider on mobile
        '@media (max-width: 640px)': {
            maxWidth: '80%',
        },
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '0.25rem',
        // Smaller font on mobile
        '@media (max-width: 640px)': {
            '& span': {
                fontSize: tokens.fontSizeBase300,
            },
        },
    },
    messageText: {
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        lineHeight: '1.5',
        // Adjust font size on mobile
        '@media (max-width: 640px)': {
            fontSize: tokens.fontSizeBase300,
            lineHeight: '1.4',
        },
    },
    timestamp: {
        fontSize: tokens.fontSizeBase200,
        color: tokens.colorNeutralForeground3,
        alignSelf: 'flex-end',
        marginTop: '0.25rem',
        // Smaller on mobile
        '@media (max-width: 640px)': {
            fontSize: tokens.fontSizeBase100,
        },
    },
    codeBlock: {
        backgroundColor: tokens.colorNeutralBackground3,
        ...shorthands.padding('0.5rem'),
        ...shorthands.borderRadius('0.25rem'),
        overflowX: 'auto',
        fontFamily: 'monospace',
        fontSize: '0.875rem',
        // Smaller on mobile
        '@media (max-width: 640px)': {
            fontSize: '0.75rem',
            ...shorthands.padding('0.375rem'),
        },
    },
    avatar: {
        flexShrink: 0,
        // Smaller avatars on mobile
        '@media (max-width: 640px)': {
            '& div': {
                width: '1.75rem !important',
                height: '1.75rem !important',
            },
        },
    },
    menuButton: {
        minWidth: 'unset',
        // Even smaller on mobile
        '@media (max-width: 640px)': {
            ...shorthands.padding('0.125rem'),
            height: '1.5rem',
            width: '1.5rem',
        },
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
                <div className={styles.avatar}>
                    <Avatar
                        name={message.role === 'assistant' ? 'Assistant' : 'System'}
                        icon={message.role === 'assistant' ? <Bot24Regular /> : undefined}
                        color={message.role === 'assistant' ? 'brand' : 'neutral'}
                        size={32}
                    />
                </div>
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
                                    className={styles.menuButton}
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
                <div className={styles.avatar}>
                    <Avatar
                        name="You"
                        icon={<PersonRegular />}
                        color="colorful"
                        size={32}
                    />
                </div>
            )}
        </div>
    );
};