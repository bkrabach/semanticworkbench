import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
    makeStyles,
    tokens,
    Button,
    Menu,
    MenuTrigger,
    MenuPopover,
    MenuList,
    MenuItem,
    MenuDivider,
    Divider,
    Text,
    Input,
    shorthands,
    Badge,
    Avatar
} from '@fluentui/react-components';
import {
    Add20Regular,
    ChevronRight20Regular,
    Settings20Regular,
    Search20Regular
} from '@fluentui/react-icons';
import { useConversations, useCreateConversation } from '../../api/hooks/useConversations';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';
import { Conversation } from '../../api/types';

// Define styles for the sidebar
const useStyles = makeStyles({
    sidebar: {
        display: 'flex',
        flexDirection: 'column',
        width: '280px',
        height: '100%',
        backgroundColor: tokens.colorNeutralBackground2,
        ...shorthands.borderRight('1px', 'solid', tokens.colorNeutralStroke1),
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        ...shorthands.padding(tokens.spacingVerticalS, tokens.spacingHorizontalS),
        ...shorthands.borderBottom('1px', 'solid', tokens.colorNeutralStroke1),
    },
    title: {
        fontWeight: tokens.fontWeightSemibold,
    },
    actionBar: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        ...shorthands.padding(tokens.spacingVerticalS, tokens.spacingHorizontalS),
    },
    searchContainer: {
        ...shorthands.padding(tokens.spacingVerticalXS, tokens.spacingHorizontalS),
        ...shorthands.borderBottom('1px', 'solid', tokens.colorNeutralStroke1),
    },
    conversationList: {
        flexGrow: 1,
        overflowY: 'auto',
        ...shorthands.padding(tokens.spacingVerticalXS, '0px'),
    },
    conversationItem: {
        display: 'flex',
        alignItems: 'center',
        ...shorthands.padding(
            tokens.spacingVerticalS,
            tokens.spacingHorizontalM,
            tokens.spacingVerticalS,
            tokens.spacingHorizontalS
        ),
        cursor: 'pointer',
        ...shorthands.borderRadius(0),
        '&:hover': {
            backgroundColor: tokens.colorNeutralBackground1,
        },
    },
    conversationItemActive: {
        backgroundColor: tokens.colorNeutralBackground1,
        '&:hover': {
            backgroundColor: tokens.colorNeutralBackground1,
        },
        ...shorthands.borderLeft('2px', 'solid', tokens.colorBrandBackground),
        ...shorthands.padding(
            tokens.spacingVerticalS,
            tokens.spacingHorizontalM,
            tokens.spacingVerticalS,
            `calc(${tokens.spacingHorizontalS} - 2px)`
        ),
    },
    conversationTitle: {
        flexGrow: 1,
        marginLeft: tokens.spacingHorizontalS,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
    },
    footer: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        ...shorthands.padding(tokens.spacingVerticalS, tokens.spacingHorizontalS),
        ...shorthands.borderTop('1px', 'solid', tokens.colorNeutralStroke1),
    },
    userInfo: {
        display: 'flex',
        alignItems: 'center',
        gap: tokens.spacingHorizontalS,
    },
    newButton: {
        backgroundColor: tokens.colorBrandBackground,
        color: tokens.colorNeutralForegroundOnBrand,
        '&:hover': {
            backgroundColor: tokens.colorBrandBackgroundHover,
        }
    },
    emptyState: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        ...shorthands.padding(tokens.spacingVerticalL),
        textAlign: 'center',
    },
    loading: {
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100px',
    }
});

/**
 * Sidebar component with workspace selector and conversation list
 */
const Sidebar: React.FC = () => {
    const styles = useStyles();
    const [searchQuery, setSearchQuery] = useState('');
    const { isAuthenticated } = useAuth();
    const { isDarkMode, themeMode, setThemeMode } = useTheme();

    // Placeholder for API data (to be replaced with actual data)
    const { data: conversations, isLoading } = useConversations();
    const createConversation = useCreateConversation();

    // Filter conversations based on search query
    const filteredConversations = conversations?.filter(conv =>
        conv.title.toLowerCase().includes(searchQuery.toLowerCase())
    ) ?? [];

    // Import useNavigate and useParams from react-router-dom
    const navigate = useNavigate();
    const { conversationId } = useParams<{ conversationId?: string }>();

    // Navigate to the selected conversation
    const handleSelectConversation = (id: string) => {
        navigate(`/conversations/${id}`);
    };

    // Create a new conversation and navigate to it
    const handleCreateConversation = async () => {
        try {
            const newConversation = await createConversation.mutateAsync({
                title: 'New Conversation'
            });
            // Navigate to the new conversation
            navigate(`/conversations/${newConversation.id}`);
        } catch (error) {
            console.error('Failed to create conversation:', error);
        }
    };

    // Toggle theme
    const toggleTheme = () => {
        if (themeMode === 'dark') {
            setThemeMode('light');
        } else if (themeMode === 'light') {
            setThemeMode('system');
        } else {
            setThemeMode('dark');
        }
    };

    if (!isAuthenticated) {
        return null;
    }

    return (
        <nav className={styles.sidebar}>
            <div className={styles.header}>
                <Text className={styles.title} size={500}>Cortex Chat</Text>
                <Menu>
                    <MenuTrigger disableButtonEnhancement>
                        <Button
                            appearance="subtle"
                            icon={<Settings20Regular />}
                            aria-label="Settings"
                        />
                    </MenuTrigger>
                    <MenuPopover>
                        <MenuList>
                            <MenuItem onClick={toggleTheme}>
                                Theme: {isDarkMode ? 'Dark' : 'Light'} ({themeMode})
                            </MenuItem>
                            <MenuDivider />
                            <MenuItem>Settings</MenuItem>
                        </MenuList>
                    </MenuPopover>
                </Menu>
            </div>

            <div className={styles.actionBar}>
                <Button
                    icon={<Add20Regular />}
                    onClick={handleCreateConversation}
                    className={styles.newButton}
                >
                    New Conversation
                </Button>
            </div>

            <div className={styles.searchContainer}>
                <Input
                    placeholder="Search conversations"
                    contentBefore={<Search20Regular />}
                    value={searchQuery}
                    onChange={(_, data) => setSearchQuery(data.value)}
                />
            </div>

            <div className={styles.conversationList}>
                {isLoading ? (
                    <div className={styles.loading}>
                        <Text>Loading...</Text>
                    </div>
                ) : filteredConversations.length === 0 ? (
                    <div className={styles.emptyState}>
                        <Text>No conversations found</Text>
                        {searchQuery ? (
                            <Button
                                appearance="subtle"
                                onClick={() => setSearchQuery('')}
                            >
                                Clear search
                            </Button>
                        ) : (
                            <Button
                                appearance="primary"
                                onClick={handleCreateConversation}
                                icon={<Add20Regular />}
                            >
                                Create your first conversation
                            </Button>
                        )}
                    </div>
                ) : (
                    <>
                        {filteredConversations.map((conversation: Conversation) => {
                            // Determine if this is the active conversation by comparing with the route param
                            const isActive = conversation.id === conversationId;

                            return (
                                <div
                                    key={conversation.id}
                                    className={`${styles.conversationItem} ${isActive ? styles.conversationItemActive : ''}`}
                                    onClick={() => handleSelectConversation(conversation.id)}
                                >
                                    {conversation.isFavorite && (
                                        <Badge appearance="filled" color="danger" shape="rounded" />
                                    )}
                                    <Text className={styles.conversationTitle}>
                                        {conversation.title}
                                    </Text>
                                    <ChevronRight20Regular />
                                </div>
                            );
                        })}
                    </>
                )}
            </div>

            <Divider />

            <div className={styles.footer}>
                <div className={styles.userInfo}>
                    <Avatar name="User" size={28} />
                    <Text>Current User</Text>
                </div>
            </div>
        </nav>
    );
};

export default Sidebar;