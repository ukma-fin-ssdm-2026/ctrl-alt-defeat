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

describe('AuthModal accessibility (S6848)', () => {
  it('switches between login and registration using an accessible button', () => {
    render(<AuthModal close={() => {}} onLogin={vi.fn()} />);

    const signUpButton = screen.getByRole('button', { name: 'Створити' });

    expect(signUpButton).toBeInTheDocument();
    expect(signUpButton).toHaveAttribute('type', 'button');
    expect(signUpButton).not.toHaveAttribute('tabindex', '-1');

    fireEvent.click(signUpButton);

    expect(screen.getByRole('button', { name: 'Увійти' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Увійти' }));

    expect(screen.getByRole('button', { name: 'Створити' })).toBeInTheDocument();
  });
});
describe('AuthModal email confirmation (FR-001)', () => {
  beforeEach(() => {
    vi.mocked(apiClient.post).mockReset();
  });

  const signUp = async () => {
    render(<AuthModal close={() => {}} onLogin={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Створити' }));
    fireEvent.change(screen.getByPlaceholderText("Ваш нікнейм (Ім'я)"), { target: { value: 'newbie' } });
    fireEvent.change(screen.getByPlaceholderText('Email'), { target: { value: 'New@Example.com' } });
    fireEvent.change(screen.getByPlaceholderText('Пароль'), { target: { value: 'Password123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Зареєструватись' }));
  };

  it('tells the user to open the emailed link and offers to send it again', async () => {
    vi.mocked(apiClient.post)
      .mockResolvedValueOnce({ data: { email: 'new@example.com' } })
      .mockResolvedValueOnce({ data: { message: 'sent' } });
    await signUp();

    expect(await screen.findByText(/Ми надіслали лист із посиланням на new@example.com/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /демо в 1 клік/ })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Надіслати лист ще раз/ }));

    expect(await screen.findByText('Лист надіслано ще раз на new@example.com.')).toBeInTheDocument();
    expect(apiClient.post).toHaveBeenLastCalledWith('/auth/resend-verification', { email: 'new@example.com' });
  });

  it('never offers to skip the email, the link comes only by email', async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { email: 'new@example.com' } });
    await signUp();

    expect(await screen.findByText(/Лист може потрапити в «Спам»/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Підтвердити email/ })).not.toBeInTheDocument();
  });

  it('offers a new link when login fails because the email is not confirmed', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { message: 'sent' } });
    const onLogin = vi.fn().mockResolvedValue({ success: false, code: 'EMAIL_NOT_VERIFIED' });
    render(<AuthModal close={() => {}} onLogin={onLogin} />);
    fireEvent.change(await screen.findByPlaceholderText('Email'), { target: { value: 'late@example.com' } });
    fireEvent.change(screen.getByPlaceholderText('Пароль'), { target: { value: 'Password123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Увійти' }));

    fireEvent.click(await screen.findByRole('button', { name: /Надіслати лист ще раз/ }));

    expect(apiClient.post).toHaveBeenCalledWith('/auth/resend-verification', { email: 'late@example.com' });
  });
});

describe('AuthModal login limit', () => {
  it('asks to wait after too many failed attempts', async () => {
    const onLogin = vi.fn().mockResolvedValue({ success: false, code: 'TOO_MANY_ATTEMPTS' });
    render(<AuthModal close={() => {}} onLogin={onLogin} />);

    fireEvent.change(await screen.findByPlaceholderText('Email'), { target: { value: 'user@demo.test' } });
    fireEvent.change(screen.getByPlaceholderText('Пароль'), { target: { value: 'wrong-password' } });
    fireEvent.click(screen.getByRole('button', { name: 'Увійти' }));

    expect(await screen.findByText(/Забагато невдалих спроб входу/)).toBeInTheDocument();
  });
});
