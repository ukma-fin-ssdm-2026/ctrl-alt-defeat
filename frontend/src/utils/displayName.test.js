import { describe, expect, it } from 'vitest';
import { getDisplayName } from './displayName';

describe('getDisplayName', () => {
  it('uses the nickname returned by the backend', () => {
    // Trace: T-037
    expect(getDisplayName({ nickname: 'admin', email: 'admin@gmail.com' })).toBe('admin');
  });

  it('falls back to username, then to the email name', () => {
    // Trace: T-037
    expect(getDisplayName({ username: 'legacy' })).toBe('legacy');
    expect(getDisplayName({ email: 'cinema_fan@example.com' })).toBe('cinema_fan');
  });

  it('returns an empty string for a guest', () => {
    // Trace: T-037
    expect(getDisplayName(null)).toBe('');
  });
});
