import { API_URL } from '@/config';

/**
 * Simple API client that matches web-client.html patterns exactly
 */
export const apiClient = {
    /**
     * Get authentication token
     */
    getAuthToken: (): string | null => {
        return localStorage.getItem('authToken');
    },

    /**
     * Make a request to the API
     * @param endpoint The API endpoint
     * @param method The HTTP method
     * @param body Optional request body
     * @returns Promise with response data
     */
    async request<T>(
        endpoint: string,
        method: string = 'GET',
        body?: any
    ): Promise<T> {
        const url = `${API_URL}${endpoint}`;
        const headers: Record<string, string> = {
            'Content-Type': 'application/json'
        };

        // Add authorization token if available
        const token = apiClient.getAuthToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        // Build request options
        const options: RequestInit = {
            method,
            headers,
            body: body ? JSON.stringify(body) : undefined
        };

        // Make the request
        console.log(`Making ${method} request to ${url}`);
        const response = await fetch(url, options);

        // Handle errors
        if (!response.ok) {
            try {
                const errorData = await response.json();
                console.error(`Request failed with status ${response.status}:`, errorData);
                throw new Error(errorData.message || `Request failed with status ${response.status}`);
            } catch (e) {
                console.error(`Request failed with status ${response.status}`);
                throw new Error(`Request failed with status ${response.status}`);
            }
        }

        // For empty responses (e.g. 204 No Content)
        if (response.status === 204) {
            return {} as T;
        }

        // Parse and return the response data
        return response.json();
    },

    /**
     * Make a GET request
     */
    get: <T>(endpoint: string) => apiClient.request<T>(endpoint),

    /**
     * Make a POST request
     */
    post: <T>(endpoint: string, data?: any) => apiClient.request<T>(endpoint, 'POST', data),

    /**
     * Make a PUT request
     */
    put: <T>(endpoint: string, data?: any) => apiClient.request<T>(endpoint, 'PUT', data),

    /**
     * Make a DELETE request
     */
    delete: <T>(endpoint: string) => apiClient.request<T>(endpoint, 'DELETE')
};