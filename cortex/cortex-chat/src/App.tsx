import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FluentProvider, teamsLightTheme } from '@fluentui/react-components';
import { AuthProvider, useAuth } from '@/store/AuthContext';
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

// Placeholder components (to be replaced with actual components later)
const Login = () => {
    const { login, error } = useAuth();
    
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
        <div>
            <h1>Login</h1>
            {error && <p style={{ color: 'red' }}>{error}</p>}
            <form onSubmit={handleSubmit}>
                <div>
                    <label htmlFor="email">Email:</label>
                    <input type="email" id="email" defaultValue="test@example.com" />
                </div>
                <div>
                    <label htmlFor="password">Password:</label>
                    <input type="password" id="password" defaultValue="password" />
                </div>
                <button type="submit">Login</button>
            </form>
        </div>
    );
};

const Dashboard = () => {
    const { user, logout } = useAuth();
    
    return (
        <div>
            <h1>Dashboard</h1>
            <p>Welcome, {user?.name || user?.email}</p>
            <button onClick={logout}>Logout</button>
        </div>
    );
};

// Protected route component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
    const { isAuthenticated, isLoading } = useAuth();
    
    if (isLoading) {
        return <div>Loading...</div>;
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
