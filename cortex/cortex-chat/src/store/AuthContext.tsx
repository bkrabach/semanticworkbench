import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { AuthState, User } from '@/types';
import { authService } from '@services/index';

// Default auth state
const defaultAuthState: AuthState = {
    user: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
};

// Context for auth state and functions
interface AuthContextType extends AuthState {
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
}

// Create the context
const AuthContext = createContext<AuthContextType>({
    ...defaultAuthState,
    login: async () => {},
    logout: () => {},
});

// Props for the provider component
interface AuthProviderProps {
    children: ReactNode;
}

/**
 * Provider component for authentication state
 */
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    // Auth state
    const [authState, setAuthState] = useState<AuthState>(defaultAuthState);

    // Check authentication on mount
    useEffect(() => {
        const checkAuth = () => {
            try {
                // Check if we have a token and user
                if (authService.isAuthenticated()) {
                    const user = authService.getUser();
                    setAuthState({
                        user,
                        isAuthenticated: true,
                        isLoading: false,
                        error: null,
                    });
                } else {
                    setAuthState({
                        user: null,
                        isAuthenticated: false,
                        isLoading: false,
                        error: null,
                    });
                }
            } catch (error) {
                // Handle any errors during auth check
                setAuthState({
                    user: null,
                    isAuthenticated: false,
                    isLoading: false,
                    error: 'Error checking authentication',
                });
            }
        };

        checkAuth();
    }, []);

    /**
     * Login function
     */
    const login = async (email: string, password: string): Promise<void> => {
        setAuthState(prev => ({
            ...prev,
            isLoading: true,
            error: null,
        }));

        try {
            const user = await authService.login(email, password);
            setAuthState({
                user,
                isAuthenticated: true,
                isLoading: false,
                error: null,
            });
        } catch (error) {
            setAuthState({
                user: null,
                isAuthenticated: false,
                isLoading: false,
                error: 'Login failed',
            });
            throw error;
        }
    };

    /**
     * Logout function
     */
    const logout = (): void => {
        authService.logout();
        setAuthState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
        });
    };

    // Provide auth state and functions
    return (
        <AuthContext.Provider
            value={{
                ...authState,
                login,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

/**
 * Hook for using authentication
 */
export const useAuth = (): AuthContextType => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};