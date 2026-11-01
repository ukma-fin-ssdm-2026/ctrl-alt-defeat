import { AxiosError } from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { clearStoredAuth, setStoredAuth } from '../auth/currentUser';
import apiClient, { SESSION_EXPIRED_EVENT } from './client';

const reply401 = config =>
  Promise.reject(new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, { status: 401, data: {}, headers: {}, config }));

describe('apiClient (FR-001)', () => {
  let listener;
  const originalAdapter = apiClient.defaults.adapter;

  beforeEach(() => {
    listener = vi.fn();
    window.addEventListener(SESSION_EXPIRED_EVENT, listener);
    apiClient.defaults.adapter = reply401;
  });

  afterEach(() => {
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener);
    apiClient.defaults.adapter = originalAdapter;
    clearStoredAuth();
  });

  it('calls the API on the same origin by default (Vite proxy)', () => {
    // Trace: T-037
    expect(apiClient.defaults.baseURL).toBe('/api/v1');
  });

  it('sends the stored token as a Bearer header', async () => {
    // Trace: T-037
    setStoredAuth('token-123', { user_id: 'u-1' });
    let sentHeader;
    apiClient.defaults.adapter = config => {
      sentHeader = config.headers.Authorization;
      return Promise.resolve({ data: {}, status: 200, statusText: 'OK', headers: {}, config });
    };

    await apiClient.get('/watchlist');

    expect(sentHeader).toBe('Bearer token-123');
  });

  it('reports an expired session when a logged-in request gets 401', async () => {
    // Trace: T-037
    setStoredAuth('expired-token', { user_id: 'u-1' });

    await expect(apiClient.post('/watchlist', {})).rejects.toBeTruthy();

    expect(listener).toHaveBeenCalledTimes(1);
  });

  it.each(['/auth/login', '/auth/me'])('does not treat 401 from %s as an expired session', async url => {
    // Trace: T-037
    setStoredAuth('token', { user_id: 'u-1' });

    await expect(apiClient.post(url, {})).rejects.toBeTruthy();

    expect(listener).not.toHaveBeenCalled();
  });

  it('does not report anything for guests', async () => {
    // Trace: T-037
    await expect(apiClient.get('/watchlist')).rejects.toBeTruthy();

    expect(listener).not.toHaveBeenCalled();
  });
});
