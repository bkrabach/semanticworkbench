import { ApiClient } from './api/apiClient';
import { AuthService } from './auth/authService';
import { SSEManager } from './sse/sseManager';

// API base URL - in a real app, this would come from an environment variable
const API_URL = 'http://localhost:8000';

// Create service instances
export const apiClient = new ApiClient(API_URL);
export const authService = new AuthService(apiClient);
export const sseManager = new SSEManager(API_URL);

// Set up SSE token provider to use the auth service
sseManager.setTokenProvider(() => authService.getToken());

// Export service classes
export { ApiClient } from './api/apiClient';
export { AuthService } from './auth/authService';
export { SSEManager } from './sse/sseManager';