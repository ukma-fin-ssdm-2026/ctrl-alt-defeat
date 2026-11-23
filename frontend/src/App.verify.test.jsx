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
    if (url === '/auth/session') return Promise.resolve({ data: { user: null } });
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

    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith('/auth/session'));
    expect(apiClient.get).not.toHaveBeenCalledWith('/auth/me');
    expect(apiClient.get).not.toHaveBeenCalledWith('/auth/verify', expect.anything());
  });
});

describe('App session on startup (issue #276)', () => {
  afterEach(() => vi.clearAllMocks());

  it('restores the signed-in user from /auth/session', async () => {
    apiClient.get.mockImplementation((url) => {
      if (url === '/auth/session') {
        return Promise.resolve({ data: { user: { user_id: 'u1', nickname: 'cinephile', role: 'user' } } });
      }
      return Promise.resolve({ data: { items: [], enabled: false, accounts: [] } });
    });

    render(<App />);

    expect(await screen.findByRole('button', { name: 'Мій профіль' })).toBeInTheDocument();
    expect(screen.queryByText('Увійти')).not.toBeInTheDocument();
  });

  it('shows the login button for a guest', async () => {
    mockApi(() => Promise.resolve({ data: {} }));

    render(<App />);

    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith('/auth/session'));
    expect((await screen.findAllByRole('button', { name: 'Увійти' })).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: 'Мій профіль' })).not.toBeInTheDocument();
  });
});

describe('App TMDB attribution', () => {
  afterEach(() => vi.clearAllMocks());

  it('credits TMDB with its logo and the required notice', async () => {
    mockApi(() => Promise.resolve({ data: {} }));
    render(<App />);

    const logo = await screen.findByAltText('The Movie Database (TMDB)');
    expect(logo).toHaveAttribute('src', '/tmdb-logo.svg');
    expect(logo.closest('a')).toHaveAttribute('href', 'https://www.themoviedb.org');
    expect(screen.getByText(/This product uses the TMDB API but is not endorsed or certified by TMDB\./)).toBeInTheDocument();
  });
});
