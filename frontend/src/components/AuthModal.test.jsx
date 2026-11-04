import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import AuthModal from './AuthModal';

vi.mock('../api/client', () => ({ default: { post: vi.fn(), get: vi.fn() } }));

const demoResponse = {
  data: {
    enabled: true,
    accounts: [
      { role: 'admin', email: 'admin@demo.test', password: 'admin-pass-from-env' },
      { role: 'user', email: 'user@demo.test', password: 'user-pass-from-env' },
    ],
  },
};

beforeEach(() => {
  vi.mocked(apiClient.get).mockReset();
  vi.mocked(apiClient.get).mockResolvedValue({ data: { enabled: false, accounts: [] } });
});

describe('AuthModal notice (FR-005)', () => {
  it('shows why a guest was asked to log in', () => {
    // Trace: T-001
    render(<AuthModal close={() => {}} onLogin={vi.fn()} notice="Будь ласка, авторизуйтесь для використання цієї функції" />);

    expect(screen.getByRole('status')).toHaveTextContent('Будь ласка, авторизуйтесь для використання цієї функції');
  });

  it('shows no notice by default', () => {
    // Trace: T-001
    render(<AuthModal close={() => {}} onLogin={vi.fn()} />);

    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});

describe('AuthModal demo accounts (SEC-001)', () => {
  it('does not prefill or hardcode any credentials', async () => {
    render(<AuthModal close={() => {}} onLogin={vi.fn()} />);

    expect(await screen.findByPlaceholderText('Email')).toHaveValue('');
    expect(screen.getByPlaceholderText('Пароль')).toHaveValue('');
    expect(apiClient.get).toHaveBeenCalledWith('/auth/demo-accounts');
    expect(screen.queryByText(/Демо доступ/)).not.toBeInTheDocument();
  });

  it('shows the accounts configured on the server and fills the form with one click', async () => {
    vi.mocked(apiClient.get).mockResolvedValue(demoResponse);
    const onLogin = vi.fn().mockResolvedValue({ success: true });
    render(<AuthModal close={() => {}} onLogin={onLogin} />);

    expect(await screen.findByText('admin@demo.test')).toBeInTheDocument();
    expect(screen.getByText('user-pass-from-env')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: 'Підставити' })[1]);
    expect(screen.getByPlaceholderText('Email')).toHaveValue('user@demo.test');
    expect(screen.getByPlaceholderText('Пароль')).toHaveValue('user-pass-from-env');

    fireEvent.click(screen.getByRole('button', { name: 'Увійти' }));
    expect(onLogin).toHaveBeenCalledWith('user@demo.test', 'user-pass-from-env');
  });

  it('keeps working when the hint cannot be loaded', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('Network Error'));
    render(<AuthModal close={() => {}} onLogin={vi.fn()} />);

    expect(await screen.findByRole('button', { name: 'Увійти' })).toBeInTheDocument();
    expect(screen.queryByText(/Демо доступ/)).not.toBeInTheDocument();
  });
});
