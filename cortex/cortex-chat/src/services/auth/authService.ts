import { User } from '@/types';
import { ApiClient } from '@services/api/apiClient';

interface LoginResponse {
    access_token: string;
    user: User;
}

/**
 * Authentication Service for managing user authentication
 */
export class AuthService {
    private apiClient: ApiClient;
    private tokenKey = 'cortex_auth_token';
    private userKey = 'cortex_user';

    /**
     * Create a new AuthService
     * @param apiClient The API client instance
     */
    constructor(apiClient: ApiClient) {
        this.apiClient = apiClient;
        
        // Set the token provider for the API client
        this.apiClient.setTokenProvider(() => this.getToken());
    }

    /**
     * Log in with email and password
     * @param email User's email
     * @param password User's password
     * @returns Promise with user data
     */
    async login(email: string, password: string): Promise<User> {
        try {
            const response = await this.apiClient.post<LoginResponse>('/auth/login', {
                email,
                password,
            });

            const { access_token, user } = response.data;
            
            // Store token and user data
            this.setToken(access_token);
            this.setUser(user);
            
            return user;
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    }

    /**
     * Log out the current user
     */
    logout(): void {
        // Remove token and user data from storage
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.userKey);
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
        const userJson = localStorage.getItem(this.userKey);
        if (!userJson) return null;
        
        try {
            return JSON.parse(userJson);
        } catch (error) {
            console.error('Error parsing user data:', error);
            return null;
        }
    }

    /**
     * Set the authentication token
     * @param token The token to store
     */
    private setToken(token: string): void {
        localStorage.setItem(this.tokenKey, token);
    }

    /**
     * Set the user data
     * @param user The user object to store
     */
    private setUser(user: User): void {
        localStorage.setItem(this.userKey, JSON.stringify(user));
    }
}