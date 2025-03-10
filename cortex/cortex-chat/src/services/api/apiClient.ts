import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { ApiResponse, ErrorResponse } from '@/types';

/**
 * API Client for making HTTP requests to the Cortex Core API
 */
export class ApiClient {
    private client: AxiosInstance;
    private tokenProvider: () => string | null = () => null;

    /**
     * Create a new ApiClient
     * @param baseURL The base URL for API requests
     * @param config Additional axios configuration
     */
    constructor(baseURL: string, config: AxiosRequestConfig = {}) {
        this.client = axios.create({
            baseURL,
            timeout: 30000, // 30 seconds default timeout
            headers: {
                'Content-Type': 'application/json',
            },
            ...config,
        });

        // Request interceptor for adding auth token
        this.client.interceptors.request.use(
            (config) => {
                const token = this.tokenProvider();
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        // Response interceptor for handling errors
        this.client.interceptors.response.use(
            (response) => response,
            async (error) => {
                // Handle specific error cases
                if (error.response) {
                    // Handle 401 Unauthorized
                    if (error.response.status === 401) {
                        // We'll handle token refresh in the auth service
                        // For now, just return the error
                    }

                    // Format error response
                    const errorResponse: ErrorResponse = {
                        error: {
                            code: error.response.data?.error?.code || 'unknown_error',
                            message: error.response.data?.error?.message || 'An unknown error occurred',
                            details: error.response.data?.error?.details,
                        },
                    };

                    return Promise.reject(errorResponse);
                }

                // Network errors or other issues
                return Promise.reject({
                    error: {
                        code: 'network_error',
                        message: error.message || 'Network error',
                    },
                });
            }
        );
    }

    /**
     * Set a function to provide authentication tokens
     * @param provider Function that returns the current auth token
     */
    setTokenProvider(provider: () => string | null): void {
        this.tokenProvider = provider;
    }

    /**
     * Make a GET request
     * @param url The URL to request
     * @param config Additional axios config
     * @returns Promise with the response data
     */
    async get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
        const response = await this.client.get<T>(url, config);
        return this.formatResponse(response);
    }

    /**
     * Make a POST request
     * @param url The URL to request
     * @param data The data to send
     * @param config Additional axios config
     * @returns Promise with the response data
     */
    async post<T>(
        url: string,
        data?: any,
        config?: AxiosRequestConfig
    ): Promise<ApiResponse<T>> {
        console.log(`Making POST request to ${url} with data:`, data);
        try {
            const response = await this.client.post<T>(url, data, config);
            console.log(`POST response from ${url}:`, response);
            return this.formatResponse(response);
        } catch (error) {
            console.error(`POST request to ${url} failed:`, error);
            throw error;
        }
    }

    /**
     * Make a PUT request
     * @param url The URL to request
     * @param data The data to send
     * @param config Additional axios config
     * @returns Promise with the response data
     */
    async put<T>(
        url: string,
        data?: any,
        config?: AxiosRequestConfig
    ): Promise<ApiResponse<T>> {
        const response = await this.client.put<T>(url, data, config);
        return this.formatResponse(response);
    }

    /**
     * Make a DELETE request
     * @param url The URL to request
     * @param config Additional axios config
     * @returns Promise with the response data
     */
    async delete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
        const response = await this.client.delete<T>(url, config);
        return this.formatResponse(response);
    }

    /**
     * Format the axios response into our ApiResponse type
     */
    private formatResponse<T>(response: AxiosResponse<any>): ApiResponse<T> {
        return {
            data: response.data,
            status: response.status,
            message: response.statusText,
        };
    }
}