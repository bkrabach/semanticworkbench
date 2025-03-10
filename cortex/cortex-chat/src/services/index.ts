import { apiClient } from './api/apiClient';
import { AuthService } from './auth/authService';
import { SSEManager } from './sse/sseManager';
import { API_URL } from '@/config';

// Create service instances
export { apiClient } from './api/apiClient';
export const authService = new AuthService();
export const sseManager = new SSEManager(API_URL);

// Set up SSE token provider to use the auth service
sseManager.setTokenProvider(() => authService.getToken());

// Export service classes
export { AuthService } from './auth/authService';
export { SSEManager } from './sse/sseManager';