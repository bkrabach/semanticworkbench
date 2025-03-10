import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { 
    FluentProvider, 
    teamsLightTheme,
    Button,
    Input,
    Label,
    Text,
    Card,
    CardHeader,
    makeStyles,
    tokens,
    Spinner,
    Title1,
    Title2,
    MessageBar,
    MessageBarBody,
    shorthands,
    Divider
} from '@fluentui/react-components';
import { AuthProvider, useAuth } from '@/store/AuthContext';
import { AppLayout } from '@/components/shared/AppLayout';
import { WorkspaceList } from '@/components/workspace/WorkspaceList';
import { ConversationList } from '@/components/workspace/ConversationList';
import { ConversationView } from '@/components/chat/ConversationView';
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
        height: '100vh',
        backgroundColor: tokens.colorNeutralBackground1,
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
        ...shorthands.padding('20px'),
        gap: '16px',
    },
    welcomeMessage: {
        marginBottom: '16px',
    },
    errorMessage: {
        marginBottom: '16px',
    }
});

// Login component using Fluent UI
const Login = () => {
    const { login, error } = useAuth();
    const styles = useStyles();
    
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const target = e.target as typeof e.target & {
            email: { value: string };
            password: { value: string };
        };
        try {
            await login(target.email.value, target.password.value);
        } catch (error) {
            console.error('Login error:', error);
        }
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
                        <Input type="email" id="email" defaultValue="test@example.com" />
                    </div>
                    <div className={styles.formField}>
                        <Label htmlFor="password">Password</Label>
                        <Input type="password" id="password" defaultValue="password" />
                    </div>
                    <Button 
                        type="submit" 
                        appearance="primary"
                        className={styles.submitButton}
                    >
                        Login
                    </Button>
                </form>
            </Card>
        </div>
    );
};

// Dashboard component using Fluent UI
const Dashboard = () => {
    const { user, logout } = useAuth();
    const styles = useStyles();
    
    // Mock data for demonstration
    const mockWorkspaces = [
        { id: '1', name: 'Personal Workspace', created_at_utc: new Date().toISOString() },
        { id: '2', name: 'Team Projects', created_at_utc: new Date().toISOString() }
    ];
    
    const mockConversations = [
        { 
            id: '1', 
            title: 'Getting Started', 
            workspace_id: '1', 
            modality: 'chat', 
            created_at_utc: new Date().toISOString(),
            messages: [
                {
                    id: '1',
                    conversation_id: '1',
                    content: 'Welcome to Cortex Chat! How can I help you today?',
                    role: 'assistant',
                    created_at_utc: new Date().toISOString()
                }
            ]
        },
        { 
            id: '2', 
            title: 'Project Ideas', 
            workspace_id: '1', 
            modality: 'chat', 
            created_at_utc: new Date(Date.now() - 86400000).toISOString() 
        }
    ];
    
    // State for selected items
    const [selectedWorkspaceId, setSelectedWorkspaceId] = React.useState('1');
    const [selectedConversationId, setSelectedConversationId] = React.useState('1');
    const [isTyping, setIsTyping] = React.useState(false);
    
    // Get the selected conversation
    const selectedConversation = mockConversations.find(c => c.id === selectedConversationId) || mockConversations[0];
    
    // Mock functions for demonstration
    const handleSendMessage = (content: string) => {
        console.log('Sending message:', content);
        // Simulate typing indicator
        setIsTyping(true);
        setTimeout(() => {
            setIsTyping(false);
        }, 2000);
    };
    
    const handleSelectWorkspace = (id: string) => {
        setSelectedWorkspaceId(id);
    };
    
    const handleCreateWorkspace = () => {
        console.log('Creating new workspace');
    };
    
    const handleSelectConversation = (id: string) => {
        setSelectedConversationId(id);
    };
    
    const handleCreateConversation = () => {
        console.log('Creating new conversation');
    };
    
    // Create the sidebar content
    const sidebarContent = (
        <>
            <WorkspaceList 
                workspaces={mockWorkspaces}
                selectedWorkspaceId={selectedWorkspaceId}
                onSelectWorkspace={handleSelectWorkspace}
                onCreateWorkspace={handleCreateWorkspace}
            />
            <Divider style={{ margin: '16px 0' }} />
            <ConversationList 
                conversations={mockConversations}
                currentConversationId={selectedConversationId}
                onSelectConversation={handleSelectConversation}
                onCreateConversation={handleCreateConversation}
            />
        </>
    );
    
    return (
        <AppLayout user={user} onLogout={logout} sidebar={sidebarContent}>
            <ConversationView 
                conversation={selectedConversation}
                isTyping={isTyping}
                onSendMessage={handleSendMessage}
            />
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
            <FluentProvider theme={teamsLightTheme}>
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
