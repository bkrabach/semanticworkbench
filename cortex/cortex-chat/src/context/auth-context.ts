import { createContext } from 'react';

export interface AuthContextType {
    isAuthenticated: boolean;
    isLoading: boolean;
    error: Error | null;
    login: (token: string) => Promise<import('../api/types').AuthResponse>;
    logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);