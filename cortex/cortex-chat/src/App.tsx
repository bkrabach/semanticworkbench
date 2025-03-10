import { ConversationView } from '@/components/chat/ConversationView';
import { AppLayout } from '@/components/shared/AppLayout';
import { ConversationList } from '@/components/workspace/ConversationList';
import { WorkspaceList } from '@/components/workspace/WorkspaceList';
import { useSSE } from '@/hooks/useSSE';
import { apiClient } from '@/services/index';
import { AuthProvider, useAuth } from '@/store/AuthContext';
import { Conversation, Message, Workspace } from '@/types';
import {
    Button,
    Card,
    CardHeader,
    Divider,
    FluentProvider,
    Input,
    Label,
    makeStyles,
    MessageBar,
    MessageBarBody,
    shorthands,
    Spinner,
    teamsLightTheme,
    Text,
    Title1,
    Title2,
    tokens,
} from '@fluentui/react-components';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { Navigate, Route, BrowserRouter as Router, Routes, useNavigate } from 'react-router-dom';
import './App.css';

// Create a client for React Query
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 1000 * 60 * 5, // 5 minutes
            retry: 1,
        },
    },
});

// Define styles using makeStyles
const useStyles = makeStyles({
    container: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        width: '100%',
        height: '100vh',
        backgroundColor: tokens.colorNeutralBackground1,
        overflow: 'hidden',
    },
    loginCard: {
        width: '400px',
        maxWidth: '90%',
        ...shorthands.padding('20px'),
    },
    formField: {
        display: 'flex',
        flexDirection: 'column',
        marginBottom: '16px',
    },
    submitButton: {
        marginTop: '16px',
    },
    dashboardContainer: {
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        gap: '16px',
    },
    welcomeMessage: {
        marginBottom: '16px',
    },
    errorMessage: {
        marginBottom: '16px',
    },
});

// Login component using Fluent UI
const Login = () => {
    const { login, error, isAuthenticated } = useAuth();
    const styles = useStyles();
    const [email, setEmail] = React.useState('test@example.com');
    const [password, setPassword] = React.useState('password');
    const [isLoggingIn, setIsLoggingIn] = React.useState(false);
    const navigate = useNavigate();
    
    // Redirect if already authenticated
    React.useEffect(() => {
        if (isAuthenticated) {
            console.log("User is authenticated, redirecting to dashboard");
            navigate('/');
        }
    }, [isAuthenticated, navigate]);

    const handleLoginClick = async () => {
        if (isLoggingIn) return;
        
        try {
            setIsLoggingIn(true);
            console.log("Login button clicked with:", { email, password });
            // This will trigger the auth flow through multiple layers
            await login(email, password);
            console.log("Login completed successfully");
            // Navigate programmatically after successful login
            navigate('/');
        } catch (error) {
            console.error('Login error in UI layer:', error);
        } finally {
            setIsLoggingIn(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        handleLoginClick();
    };

    return (
        <div className={styles.container}>
            <Card className={styles.loginCard}>
                <CardHeader header={<Title1>Login</Title1>} />
                {error && (
                    <MessageBar intent="error" className={styles.errorMessage}>
                        <MessageBarBody>{error}</MessageBarBody>
                    </MessageBar>
                )}
                <form onSubmit={handleSubmit}>
                    <div className={styles.formField}>
                        <Label htmlFor="email">Email</Label>
                        <Input 
                            type="email" 
                            id="email" 
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                        />
                    </div>
                    <div className={styles.formField}>
                        <Label htmlFor="password">Password</Label>
                        <Input 
                            type="password" 
                            id="password" 
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>
                    <Button 
                        type="submit" 
                        appearance="primary" 
                        className={styles.submitButton}
                        disabled={isLoggingIn}
                    >
                        {isLoggingIn ? 'Logging in...' : 'Login'}
                    </Button>
                </form>
            </Card>
        </div>
    );
};

// Dashboard component using Fluent UI with real API calls
const Dashboard = () => {
    const { user, logout } = useAuth();

    // State for API data with proper type definitions
    const [workspaces, setWorkspaces] = React.useState<Workspace[]>([]);
    const [conversations, setConversations] = React.useState<Conversation[]>([]);
    const [selectedWorkspaceId, setSelectedWorkspaceId] = React.useState<string | null>(null);
    const [selectedConversationId, setSelectedConversationId] = React.useState<string | null>(null);
    const [currentConversation, setCurrentConversation] = React.useState<Conversation | null>(null);
    const [isLoading, setIsLoading] = React.useState(true);
    const [isTyping, setIsTyping] = React.useState(false);
    const [error, setError] = React.useState<string | null>(null);

    // Load workspaces on mount
    React.useEffect(() => {
        fetchWorkspaces();
    }, []);

    // Load conversations when workspace changes
    React.useEffect(() => {
        if (selectedWorkspaceId) {
            fetchConversations(selectedWorkspaceId);
        }
    }, [selectedWorkspaceId]);

    // Load conversation details when conversation changes
    React.useEffect(() => {
        if (selectedConversationId) {
            fetchConversation(selectedConversationId);
        }
    }, [selectedConversationId]);

    // Use the SSE hook for global events
    useSSE(
        'global',
        undefined,
        {
            notification: (data) => {
                console.log('Global notification received:', data);
            },
            system_update: (data) => {
                console.log('System update received:', data);
            },
        },
        true // enabled
    );

    // Connect to workspace SSE - convert null to undefined
    useSSE(
        'workspace',
        selectedWorkspaceId ?? undefined,
        {
            conversation_created: (data) => {
                console.log('New conversation created:', data);
                // Add to conversations if not already present
                setConversations((prev: Conversation[]) => {
                    if (prev.some((c) => c.id === data.id)) return prev;
                    return [...prev, data as Conversation];
                });
            },
            conversation_deleted: (data) => {
                console.log('Conversation deleted:', data);
                // Remove from conversations
                setConversations((prev: Conversation[]) => prev.filter((c) => c.id !== data.id));
                // If current conversation was deleted, clear it
                if (selectedConversationId === data.id) {
                    setSelectedConversationId(null);
                    setCurrentConversation(null);
                }
            },
            workspace_update: (data) => {
                console.log('Workspace updated:', data);
                // Update workspaces
                setWorkspaces((prev: Workspace[]) =>
                    prev.map((w) => (w.id === data.id ? { ...w, ...(data as Workspace) } : w))
                );
            },
        },
        !!selectedWorkspaceId // only enable if we have a workspace ID
    );

    // Connect to conversation SSE - convert null to undefined
    useSSE(
        'conversation',
        selectedConversationId ?? undefined,
        {
            message_received: (data) => {
                console.log('New message received:', data);
                handleNewMessage(data);
            },
            typing_indicator: (data) => {
                console.log('Typing indicator:', data);
                setIsTyping(!!data.isTyping);
            },
            status_update: (data) => {
                console.log('Conversation status update:', data);
                // Update conversation if needed
                setCurrentConversation((prev: Conversation | null) => {
                    if (!prev || prev.id !== data.id) return prev;
                    return { ...prev, ...(data as Partial<Conversation>) };
                });
            },
        },
        !!selectedConversationId // only enable if we have a conversation ID
    );

    // Fetch workspaces
    const fetchWorkspaces = async () => {
        setIsLoading(true);
        setError(null);

        try {
            const response = await apiClient.get<{ workspaces: Workspace[] }>('/workspaces');
            const workspaceList = response.workspaces || [];
            setWorkspaces(workspaceList);

            // Select first workspace if available and we don't have one selected
            if (workspaceList.length > 0 && !selectedWorkspaceId) {
                setSelectedWorkspaceId(workspaceList[0].id);
            }
        } catch (error) {
            console.error('Error fetching workspaces:', error);
            setError('Failed to load workspaces');
        } finally {
            setIsLoading(false);
        }
    };

    // Fetch conversations for a workspace
    const fetchConversations = async (workspaceId: string) => {
        setIsLoading(true);
        setError(null);

        try {
            const response = await apiClient.get<{ conversations: Conversation[] }>(
                `/workspaces/${workspaceId}/conversations`
            );
            const conversationList = response.conversations || [];
            setConversations(conversationList);

            // Select first conversation if available and we don't have one selected
            if (conversationList.length > 0 && !selectedConversationId) {
                setSelectedConversationId(conversationList[0].id);
            }
        } catch (error) {
            console.error('Error fetching conversations:', error);
            setError('Failed to load conversations');
        } finally {
            setIsLoading(false);
        }
    };

    // Fetch conversation details and messages
    const fetchConversation = async (conversationId: string) => {
        setIsLoading(true);
        setError(null);

        try {
            // Get conversation details
            const conversation = await apiClient.get<Conversation>(
                `/conversations/${conversationId}`
            );

            // Get messages for this conversation
            const messagesResponse = await apiClient.get<{ messages: Message[] }>(
                `/conversations/${conversationId}/messages`
            );
            conversation.messages = messagesResponse.messages || [];

            setCurrentConversation(conversation);
        } catch (error) {
            console.error('Error fetching conversation:', error);
            setError('Failed to load conversation');
        } finally {
            setIsLoading(false);
        }
    };

    // Create a new workspace
    const handleCreateWorkspace = async () => {
        const name = prompt('Enter workspace name:');
        if (!name) return;

        setIsLoading(true);
        setError(null);

        try {
            const newWorkspace = await apiClient.post<Workspace>('/workspaces', {
                name,
                config: {
                    default_modality: 'chat',
                    sharingEnabled: false,
                    retentionDays: 90,
                },
            });
            setWorkspaces((prev: Workspace[]) => [...prev, newWorkspace]);
            setSelectedWorkspaceId(newWorkspace.id);
        } catch (error) {
            console.error('Error creating workspace:', error);
            setError('Failed to create workspace');
        } finally {
            setIsLoading(false);
        }
    };

    // Create a new conversation
    const handleCreateConversation = async () => {
        if (!selectedWorkspaceId) {
            alert('Please select a workspace first');
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const newConversation = await apiClient.post<Conversation>(
                `/workspaces/${selectedWorkspaceId}/conversations`,
                {
                    modality: 'chat',
                    title: `Chat ${new Date().toLocaleTimeString()}`,
                }
            );
            setConversations((prev: Conversation[]) => [...prev, newConversation]);
            setSelectedConversationId(newConversation.id);
        } catch (error) {
            console.error('Error creating conversation:', error);
            setError('Failed to create conversation');
        } finally {
            setIsLoading(false);
        }
    };

    // Handle sending a message - exactly matching web-client.html
    const handleSendMessage = async (content: string) => {
        if (!selectedConversationId || !content) return;

        try {
            console.log('Sending message:', content);
            
            // Create temporary message with optimistic UI update
            const tempMessage: Message = {
                id: `temp-${Date.now()}`,
                conversation_id: selectedConversationId,
                content: content,
                role: 'user',
                created_at_utc: new Date().toISOString()
            };
            
            // Add to UI immediately (optimistic update)
            setCurrentConversation((prev: Conversation | null) => {
                if (!prev) return null;
                const messages = [...(prev.messages || []), tempMessage];
                return { ...prev, messages };
            });
            
            // Clear input - already done by the MessageInput component
            
            // Send to server
            await apiClient.post(`/conversations/${selectedConversationId}/messages`, {
                content: content,
                role: 'user'
            });
            
            // Show typing indicator - will be controlled by the server via SSE
            setIsTyping(true);
            
            // The response will come via SSE events
        } catch (error) {
            console.error('Error sending message:', error);
            setError('Failed to send message');
            
            // Remove optimistic message on error
            setCurrentConversation((prev: Conversation | null) => {
                if (!prev) return null;
                
                // Remove any message that starts with temp-
                const messages = prev.messages?.filter(
                    m => !m.id.toString().startsWith('temp-')
                ) || [];
                
                return { ...prev, messages };
            });
            
            setIsTyping(false);
        }
    };

    // Handle selecting a workspace
    const handleSelectWorkspace = (id: string) => {
        setSelectedWorkspaceId(id);
        setSelectedConversationId(null);
        setCurrentConversation(null);
    };

    // Handle selecting a conversation
    const handleSelectConversation = (id: string) => {
        setSelectedConversationId(id);
    };

    // Edit conversation title
    const handleEditConversationTitle = async (conversationId: string, newTitle: string) => {
        if (!newTitle.trim()) return;

        setIsLoading(true);
        setError(null);

        try {
            await apiClient.put(`/conversations/${conversationId}`, {
                title: newTitle.trim(),
            });

            // Update the conversation in state
            if (currentConversation && currentConversation.id === conversationId) {
                setCurrentConversation({
                    ...currentConversation,
                    title: newTitle.trim(),
                });
            }

            // Also update in the conversations list
            setConversations((prev: Conversation[]) =>
                prev.map((c) => (c.id === conversationId ? { ...c, title: newTitle.trim() } : c))
            );
        } catch (error) {
            console.error('Error updating conversation title:', error);
            setError('Failed to update conversation title');
        } finally {
            setIsLoading(false);
        }
    };

    // Delete a conversation
    const handleDeleteConversation = async (conversationId: string) => {
        setIsLoading(true);
        setError(null);

        try {
            await apiClient.delete(`/conversations/${conversationId}`);

            // Remove from conversations list
            setConversations((prev: Conversation[]) => prev.filter((c) => c.id !== conversationId));

            // If this was the current conversation, clear it
            if (selectedConversationId === conversationId) {
                setSelectedConversationId(null);
                setCurrentConversation(null);
            }
        } catch (error) {
            console.error('Error deleting conversation:', error);
            setError('Failed to delete conversation');
        } finally {
            setIsLoading(false);
        }
    };

    // Handle new messages from SSE - exactly matching web-client.html
    const handleNewMessage = (message: Message) => {
        console.log('New message received via SSE:', message);
        
        // Only process if this is for the current conversation
        if (!currentConversation || currentConversation.id !== message.conversation_id) {
            console.log('Message is not for current conversation, ignoring');
            return;
        }

        setCurrentConversation((prev: Conversation | null) => {
            if (!prev) return null;

            // Check if we already have this exact message by ID
            const existingIndex =
                prev.messages?.findIndex((m: Message) => m.id === message.id) ?? -1;
            if (existingIndex !== -1) {
                console.log('Message already exists, ignoring duplicate');
                return prev; // Already have this message
            }

            // For user messages, check if we have a temporary message to replace
            if (message.role === 'user') {
                // Find optimistically added message with temp ID and matching content
                const tempIndex =
                    prev.messages?.findIndex(
                        (m: Message) =>
                            m.role === 'user' &&
                            m.content === message.content &&
                            m.id &&
                            m.id.toString().startsWith('temp-')
                    ) ?? -1;

                if (tempIndex !== -1 && prev.messages) {
                    console.log('Replacing temporary message with server version');
                    // Replace our temp message with the server version
                    const updatedMessages = [...prev.messages];
                    updatedMessages[tempIndex] = message;
                    return { ...prev, messages: updatedMessages };
                }
            }

            // Add the new message
            console.log('Adding new message to conversation');
            const messages = [...(prev.messages || []), message];
            
            // Hide typing indicator if this is an assistant message
            if (message.role === 'assistant') {
                setIsTyping(false);
            }
            
            return { ...prev, messages };
        });
    };

    // Create the sidebar content
    const sidebarContent = (
        <>
            <WorkspaceList
                workspaces={workspaces}
                selectedWorkspaceId={selectedWorkspaceId || ''}
                onSelectWorkspace={handleSelectWorkspace}
                onCreateWorkspace={handleCreateWorkspace}
                isLoading={isLoading}
            />
            <Divider style={{ margin: '16px 0' }} />
            <ConversationList
                conversations={conversations}
                currentConversationId={selectedConversationId || ''}
                onSelectConversation={handleSelectConversation}
                onCreateConversation={handleCreateConversation}
                isLoading={isLoading}
            />
        </>
    );

    return (
        <AppLayout user={user} onLogout={logout} sidebar={sidebarContent}>
            {error && (
                <MessageBar intent="error" style={{ margin: '0 0 16px 0' }}>
                    <MessageBarBody>{error}</MessageBarBody>
                </MessageBar>
            )}

            {currentConversation ? (
                <ConversationView
                    conversation={currentConversation}
                    isLoading={isLoading}
                    isTyping={isTyping}
                    onSendMessage={handleSendMessage}
                    onEditTitle={(newTitle) =>
                        handleEditConversationTitle(currentConversation.id, newTitle)
                    }
                    onDeleteConversation={() => {
                        if (window.confirm('Are you sure you want to delete this conversation?')) {
                            handleDeleteConversation(currentConversation.id);
                        }
                    }}
                />
            ) : selectedWorkspaceId && conversations.length === 0 ? (
                <div
                    style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                        padding: '20px',
                        textAlign: 'center',
                    }}
                >
                    <Title2>No conversations yet</Title2>
                    <Text style={{ margin: '16px 0' }}>
                        Create a new conversation to start chatting
                    </Text>
                    <Button
                        appearance="primary"
                        onClick={handleCreateConversation}
                        disabled={isLoading}
                    >
                        Create Conversation
                    </Button>
                </div>
            ) : (
                <div
                    style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                        padding: '20px',
                        textAlign: 'center',
                    }}
                >
                    <Title2>Welcome to Cortex Chat</Title2>
                    <Text style={{ margin: '16px 0' }}>
                        Select a conversation or create a new one to get started
                    </Text>
                </div>
            )}
        </AppLayout>
    );
};

// Protected route component with Fluent UI
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
    const { isAuthenticated, isLoading } = useAuth();
    const styles = useStyles();

    if (isLoading) {
        return (
            <div className={styles.container}>
                <Spinner size="large" label="Loading..." />
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" />;
    }

    return <>{children}</>;
};

function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <FluentProvider theme={teamsLightTheme} style={{ width: '100%', height: '100vh' }}>
                <AuthProvider>
                    <Router>
                        <Routes>
                            <Route path="/login" element={<Login />} />
                            <Route
                                path="/"
                                element={
                                    <ProtectedRoute>
                                        <Dashboard />
                                    </ProtectedRoute>
                                }
                            />
                            <Route path="*" element={<Navigate to="/" replace />} />
                        </Routes>
                    </Router>
                </AuthProvider>
            </FluentProvider>
        </QueryClientProvider>
    );
}

export default App;
