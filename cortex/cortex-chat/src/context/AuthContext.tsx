import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { AuthResponse } from '../api/types';
import {
    getToken,
    clearToken,
    authenticateWithToken,
    validateToken
} from '../api/client';

interface AuthContextType {
    isAuthenticated: boolean;
    isLoading: boolean;
    error: Error | null;
    login: (token: string) => Promise<AuthResponse>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
    children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<Error | null>(null);

    // Check for existing token and validate it on mount
    useEffect(() => {
        const checkAuth = async () => {
            const token = getToken();
            if (!token) {
                setIsLoading(false);
                return;
            }

            try {
                const isValid = await validateToken();
                setIsAuthenticated(isValid);
            } catch (err) {
                setError(err instanceof Error ? err : new Error('Authentication error'));
                clearToken();
            } finally {
                setIsLoading(false);
            }
        };

        checkAuth();
    }, []);

    // Login function that accepts a raw token string
    const login = async (tokenString: string): Promise<AuthResponse> => {
        setIsLoading(true);
        setError(null);

        try {
            const response = await authenticateWithToken(tokenString);
            setIsAuthenticated(true);
            return response;
        } catch (err) {
            const error = err instanceof Error
                ? err
                : new Error('Authentication failed');

            setError(error);
            throw error;
        } finally {
            setIsLoading(false);
        }
    };

    // Logout function
    const logout = () => {
        clearToken();
        setIsAuthenticated(false);
        setError(null);
    };

    const value = {
        isAuthenticated,
        isLoading,
        error,
        login,
        logout,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

// Custom hook to use the auth context
export function useAuth(): AuthContextType {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}