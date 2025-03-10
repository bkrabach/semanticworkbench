/**
 * Application configuration
 * Centralizes important configuration values
 */

// API URL - match what's used in web-client.html
export const API_URL = 'http://127.0.0.1:8000';

// SSE configuration
export const SSE_RECONNECT_ATTEMPTS = 5;
export const SSE_MAX_RECONNECT_DELAY = 5000; // 5 seconds

// Feature flags
export const FEATURES = {
  OPTIMISTIC_UPDATES: true,
  DEBUG_LOGGING: true,
};