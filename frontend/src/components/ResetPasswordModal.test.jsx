import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import ResetPasswordModal from './ResetPasswordModal';

vi.mock('../api/client', () => ({ default: { post: vi.fn() } }));

const fill = (password, confirm = password) => {
  fireEvent.change(screen.getByPlaceholderText('Новий пароль'), { target: { value: password } });
  fireEvent.change(screen.getByPlaceholderText('Повторіть пароль'), { target: { value: confirm } });
  fireEvent.click(screen.getByRole('button', { name: 'Зберегти пароль' }));
};

describe('ResetPasswordModal', () => {
  beforeEach(() => {
    vi.mocked(apiClient.post).mockReset();
  });

  it('sets the new password with the token from the link', async () => {
    // Trace: T-052
    vi.mocked(apiClient.post).mockResolvedValue({ data: { message: 'ok' } });
    const onDone = vi.fn();
    render(<ResetPasswordModal token="abc" close={() => {}} onDone={onDone} />);

    fill('brand-new-pass');

    await vi.waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(apiClient.post).toHaveBeenCalledWith('/auth/reset-password', { token: 'abc', new_password: 'brand-new-pass' });
  });

  it('checks that both passwords match', () => {
    // Trace: T-052
    render(<ResetPasswordModal token="abc" close={() => {}} />);

    fill('brand-new-pass', 'other-pass-1');

    expect(screen.getByRole('alert')).toHaveTextContent('Паролі не збігаються');
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('explains an expired link', async () => {
    // Trace: T-052
    vi.mocked(apiClient.post).mockRejectedValue({ response: { data: { error: { code: 'RESET_TOKEN_EXPIRED' } } } });
    render(<ResetPasswordModal token="abc" language="EN" close={() => {}} />);

    fireEvent.change(screen.getByPlaceholderText('New password'), { target: { value: 'brand-new-pass' } });
    fireEvent.change(screen.getByPlaceholderText('Repeat the password'), { target: { value: 'brand-new-pass' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save password' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('The link has expired');
  });
});
