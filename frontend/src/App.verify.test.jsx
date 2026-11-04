import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import apiClient from './api/client';
import App from './App';

vi.mock('./api/client', () => ({
  SESSION_EXPIRED_EVENT: 'auth:session-expired',
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

const mockApi = (verify) => {
  apiClient.get.mockImplementation((url) => {
    if (url === '/auth/verify') return verify();
    if (url === '/auth/me') return Promise.reject({ response: { status: 401 } });
    return Promise.resolve({ data: { items: [], enabled: false, accounts: [] } });
  });
};

describe('App email confirmation link (FR-001)', () => {
  afterEach(() => {
    vi.clearAllMocks();
    window.history.replaceState(null, '', '/');
  });

  it('confirms the email from /verify-email and opens the login window', async () => {
    mockApi(() => Promise.resolve({ data: { status: 'active' } }));
    window.history.replaceState(null, '', '/verify-email?token=abc123');

    render(<App />);

    expect(await screen.findByText('Пошту підтверджено! Тепер ви можете увійти.')).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledWith('/auth/verify', { params: { token: 'abc123' } });
    await waitFor(() => expect(window.location.pathname).toBe('/'));
  });

  it('explains an invalid or used link', async () => {
    mockApi(() => Promise.reject({ response: { status: 400 } }));
    window.history.replaceState(null, '', '/verify-email?token=used');

    render(<App />);

    expect(await screen.findByText(/Посилання недійсне або вже використане/)).toBeInTheDocument();
  });

  it('does nothing on other pages', async () => {
    mockApi(() => Promise.resolve({ data: {} }));

    render(<App />);

    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith('/auth/me'));
    expect(apiClient.get).not.toHaveBeenCalledWith('/auth/verify', expect.anything());
  });
});
