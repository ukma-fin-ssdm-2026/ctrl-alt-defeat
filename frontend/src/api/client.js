import axios from 'axios';
import { getStoredToken, getStoredUser } from '../auth/currentUser';

export const SESSION_EXPIRED_EVENT = 'auth:session-expired';

// Same-origin by default: the Vite dev/preview server proxies /api to the backend (vite.config.js),
// so the HttpOnly session cookie is kept after a page reload and any frontend port works.
// Set VITE_API_URL to call a backend on another origin.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Requests that answer 401 by design and must not be treated as an expired session
const AUTH_ENDPOINTS = ['/auth/login', '/auth/me', '/auth/register', '/auth/logout'];

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || '';
    const isAuthEndpoint = AUTH_ENDPOINTS.some(path => url.startsWith(path));
    if (error.response?.status === 401 && !isAuthEndpoint && getStoredUser()) {
      // The UI thinks the user is logged in, but the server no longer accepts the session
      window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
    }
    return Promise.reject(error);
  }
);

export default apiClient;
