// Authentication and current user state management (FR-001, US-011)

export const DEFAULT_USER_ID = '3fa85f64-5717-4562-b3fc-2c963f66afa6';
export const CURRENT_USER_ID = DEFAULT_USER_ID;

let inMemoryToken = null;
let inMemoryUser = null;

export function getStoredToken() {
  return inMemoryToken;
}

export function getStoredUser() {
  return inMemoryUser;
}

export function setStoredAuth(token, user) {
  if (token !== undefined && token !== null) {
    inMemoryToken = token;
  }
  if (user !== undefined && user !== null) {
    inMemoryUser = user;
  }
}

export function clearStoredAuth() {
  inMemoryToken = null;
  inMemoryUser = null;
}

export function getCurrentUserId() {
  const user = getStoredUser();
  return user?.user_id || DEFAULT_USER_ID;
}
