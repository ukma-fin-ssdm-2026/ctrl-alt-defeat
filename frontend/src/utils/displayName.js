// Display name of a user from the backend (FR-001 returns `nickname`; older mock users had `username`)
export function getDisplayName(user) {
  return user?.nickname || user?.username || user?.email?.split('@')[0] || '';
}
