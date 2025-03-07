// Base API client for communicating with cortex-core service

import { ApiError, AuthResponse } from './types';

// Base URL for the cortex-core service
export const API_BASE_URL = 'http://127.0.0.1:8000';

// Endpoints for the API
export const API_ENDPOINTS = {
    conversations: '/api/conversations',
    conversation: (id: string) => `/api/conversations/${id}`,
    messages: (conversationId: string) => `/api/conversations/${conversationId}/messages`,
    message: (conversationId: string, messageId: string) =>
        `/api/conversations/${conversationId}/messages/${messageId}`,
    workspaces: '/api/workspaces',
    workspace: (id: string) => `/api/workspaces/${id}`,
    auth: '/api/auth',
    token: '/api/auth/token',
    sseConversation: (id: string) => `/api/sse/conversations/${id}`,
    mcpServers: '/api/mcp-servers',
};

// Storage keys
const TOKEN_STORAGE_KEY = 'cortex_auth_token';

/**
 * Get the stored authentication token
 */
export function getToken(): string | null {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
}

/**
 * Store the authentication token
 */
export function setToken(token: string): void {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

/**
 * Clear the stored authentication token
 */
export function clearToken(): void {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
}

/**
 * Check if the user is authenticated
 */
export function isAuthenticated(): boolean {
    return getToken() !== null;
}

/**
 * Function to create headers with authentication
 */
function createHeaders(): HeadersInit {
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
    };

    const token = getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
}

/**
 * Handle API errors and transform to ApiError type
 */
async function handleApiResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        let errorData: { message?: string; code?: string; details?: unknown } = {};

        try {
            errorData = await response.json();
        } catch {
            // If the response is not JSON, use the status text
            errorData = {
                message: response.statusText,
                code: response.status.toString(),
            };
        }

        const apiError: ApiError = {
            status: response.status,
            message: errorData.message || `Request failed with status ${response.status}`,
            details: errorData.details,
        };

        throw apiError;
    }

    // For 204 No Content, return an empty object
    if (response.status === 204) {
        return {} as T;
    }

    return await response.json() as T;
}

/**
 * Function to make a GET request
 */
export async function fetchData<T>(url: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${url}`, {
        method: 'GET',
        headers: createHeaders(),
    });

    return handleApiResponse<T>(response);
}

/**
 * Function to make a POST request
 */
export async function postData<T>(url: string, data?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${url}`, {
        method: 'POST',
        headers: createHeaders(),
        body: data ? JSON.stringify(data) : undefined,
    });

    return handleApiResponse<T>(response);
}

/**
 * Function to make a PUT request
 */
export async function putData<T>(url: string, data?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${url}`, {
        method: 'PUT',
        headers: createHeaders(),
        body: data ? JSON.stringify(data) : undefined,
    });

    return handleApiResponse<T>(response);
}

/**
 * Function to make a DELETE request
 */
export async function deleteData<T>(url: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${url}`, {
        method: 'DELETE',
        headers: createHeaders(),
    });

    return handleApiResponse<T>(response);
}

/**
 * Function to authenticate and get a token
 */
export async function authenticateWithToken(token: string): Promise<AuthResponse> {
    // Store token temporarily for this request
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
    };

    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.token}`, {
        method: 'POST',
        headers,
    });

    const data = await handleApiResponse<AuthResponse>(response);

    // Store the token if successful
    setToken(data.token);

    return data;
}

/**
 * Function to validate the current token
 */
export async function validateToken(): Promise<boolean> {
    try {
        await fetchData(API_ENDPOINTS.auth);
        return true;
    } catch {
        clearToken();
        return false;
    }
}