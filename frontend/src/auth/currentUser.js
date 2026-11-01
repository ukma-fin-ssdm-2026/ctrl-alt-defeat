// Authentication and current user state management (FR-001, US-011)

export const DEFAULT_USER_ID = '3fa85f64-5717-4562-b3fc-2c963f66afa6';
export const CURRENT_USER_ID = DEFAULT_USER_ID;

export function getStoredToken() {
  try {
    return localStorage.getItem('access_token') || null;
  } catch {
    return null;
  }
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem('auth_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredAuth(token, user) {
  try {
    if (token) localStorage.setItem('access_token', token);
    if (user) localStorage.setItem('auth_user', JSON.stringify(user));
  } catch (e) {
    console.warn('Failed to persist auth data to localStorage:', e);
  }
}

export function clearStoredAuth() {
  try {
    localStorage.removeItem('access_token');
    localStorage.removeItem('auth_user');
  } catch (e) {
    console.warn('Failed to clear auth data from localStorage:', e);
  }
}

export function getCurrentUserId() {
  const user = getStoredUser();
  return user?.user_id || DEFAULT_USER_ID;
}
