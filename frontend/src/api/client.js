import axios from 'axios';
import { getStoredToken, getStoredUser } from '../auth/currentUser';

export const SESSION_EXPIRED_EVENT = 'auth:session-expired';

// Reliability (finding 14): no request waits forever. 30 s covers a slow database wake-up and the free
// hosting plan waking up after a quiet period; after that the request fails with ECONNABORTED and the page
// shows "the server is not responding" instead of an endless "Loading...".
export const REQUEST_TIMEOUT_MS = 30000;

// One automatic repeat for reading requests (reliability, finding 14): the first request to a sleeping
// hosting service or a waking database may time out, the second one usually succeeds. Only GET/HEAD are
// repeated: they change nothing, so a repeat cannot create a duplicate review, vote or list entry.
export const RETRY_DELAY_MS = 1000;
const RETRY_METHODS = ['get', 'head'];
const RETRY_STATUSES = [502, 503, 504];
const RETRY_CODES = ['ECONNABORTED', 'ETIMEDOUT', 'ERR_NETWORK', 'ECONNRESET'];

export function shouldRetry(error) {
  const config = error?.config;
  if (!config || config.retried) return false;
  if (!RETRY_METHODS.includes((config.method || 'get').toLowerCase())) return false;
  if (error.response) return RETRY_STATUSES.includes(error.response.status);
  return RETRY_CODES.includes(error.code);
}

const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

// Same-origin by default: the Vite dev/preview server proxies /api to the backend (vite.config.js),
// so the HttpOnly session cookie is kept after a page reload and any frontend port works.
// Set VITE_API_URL to call a backend on another origin.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: REQUEST_TIMEOUT_MS,
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
  async (error) => {
    if (shouldRetry(error)) {
      const { config } = error;
      config.retried = true;
      await wait(config.retryDelayMs ?? RETRY_DELAY_MS);
      return apiClient(config);
    }
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
