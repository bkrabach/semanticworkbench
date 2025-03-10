import { User } from '@/types';
import { apiClient } from '@services/api/apiClient';

interface LoginResponse {
    access_token: string;
    user: User;
}

/**
 * Authentication Service for managing user authentication
 * Matches web-client.html pattern exactly
 */
export class AuthService {
    private tokenKey = 'authToken'; // Exact key from web-client.html
    private userIdKey = 'userId'; // Exact key from web-client.html
    private userEmailKey = 'userEmail'; // Exact key from web-client.html

    /**
     * Log in with email and password
     * @param email User's email
     * @param password User's password
     * @returns Promise with user data
     */
    async login(email: string, password: string): Promise<User> {
        try {
            console.log(`[AuthService] Attempting to login with email: ${email}`);
            
            const response = await apiClient.post<LoginResponse>('/auth/login', {
                email,
                password,
            });

            console.log('[AuthService] Login response received:', response);
            
            // The response is directly the data, no need to access .data property
            const { access_token, user } = response;
            
            console.log('[AuthService] Extracted token and user:', { 
                tokenReceived: !!access_token, 
                userId: user?.id,
                userEmail: user?.email
            });
            
            // Store tokens exactly as in web-client.html
            localStorage.setItem(this.tokenKey, access_token);
            localStorage.setItem(this.userIdKey, user.id);
            localStorage.setItem(this.userEmailKey, user.email);
            
            // Double-check localStorage to make sure items were saved
            const savedToken = localStorage.getItem(this.tokenKey);
            console.log('[AuthService] Token saved to localStorage:', { 
                savedSuccessfully: !!savedToken,
                tokenLength: savedToken?.length
            });
            
            console.log('[AuthService] Login successful, user:', user);
            return user;
        } catch (error) {
            console.error('[AuthService] Login failed:', error);
            throw error;
        }
    }

    /**
     * Log out the current user
     */
    logout(): void {
        // Clear state exactly as in web-client.html
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.userIdKey);
        localStorage.removeItem(this.userEmailKey);
    }

    /**
     * Get the current authentication token
     * @returns The token or null if not authenticated
     */
    getToken(): string | null {
        return localStorage.getItem(this.tokenKey);
    }

    /**
     * Check if user is authenticated
     * @returns True if authenticated, false otherwise
     */
    isAuthenticated(): boolean {
        return !!this.getToken();
    }

    /**
     * Get the current user
     * @returns The user object or null if not authenticated
     */
    getUser(): User | null {
        const id = localStorage.getItem(this.userIdKey);
        const email = localStorage.getItem(this.userEmailKey);
        
        if (!id || !email) return null;
        
        return {
            id,
            email
        };
    }

    /**
     * Check session and get auth data
     * Exactly matches web-client.html pattern
     */
    checkSession(): {isAuthenticated: boolean, user: User | null, token: string | null} {
        const token = this.getToken();
        if (token) {
            return {
                isAuthenticated: true,
                user: {
                    id: localStorage.getItem(this.userIdKey) || '',
                    email: localStorage.getItem(this.userEmailKey) || ''
                },
                token
            };
        }
        return { isAuthenticated: false, user: null, token: null };
    }
}