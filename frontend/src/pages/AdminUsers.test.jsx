import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import AdminUsers from './AdminUsers';

vi.mock('../api/client', () => ({ default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() } }));

const viewer = { user_id: 'u-1', nickname: 'spammer', email: 'spam@example.com', role: 'user', status: 'active', ban: null };
const banned = {
  user_id: 'u-2',
  nickname: 'troll',
  email: 'troll@example.com',
  role: 'user',
  status: 'active',
  ban: { ban_type: 'permanent', ends_at: null, reason: 'Образи' },
};
const admin = { user_id: 'u-3', nickname: 'moderator', email: 'admin@example.com', role: 'admin', status: 'active', ban: null };

const list = (items) => ({ data: { items, total: items.length } });

describe('AdminUsers (FR-009, US-006)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.get.mockResolvedValue(list([viewer, banned, admin]));
  });

  it('lists users with their ban status and no ban button for admins', async () => {
    // Trace: T-036
    render(<AdminUsers />);

    expect(await screen.findByText('spammer')).toBeInTheDocument();
    const trollRow = screen.getByText('troll').closest('tr');
    expect(within(trollRow).getByText('Заблоковано назавжди')).toBeInTheDocument();
    expect(within(trollRow).getByText('Образи')).toBeInTheDocument();
    const adminRow = screen.getByText('moderator').closest('tr');
    expect(within(adminRow).queryByRole('button')).not.toBeInTheDocument();
  });

  it('searches users on the server', async () => {
    render(<AdminUsers />);
    await screen.findByText('spammer');

    await userEvent.type(screen.getByLabelText('Пошук користувачів'), 'tro');

    await waitFor(() => expect(apiClient.get).toHaveBeenLastCalledWith('/admin/users', { params: { q: 'tro' } }));
  });

  it('bans a user temporarily with a message and reloads the list', async () => {
    // Trace: T-036
    apiClient.post.mockResolvedValue({ data: { ban_type: 'temporary' } });
    render(<AdminUsers />);

    await userEvent.click(await screen.findByRole('button', { name: 'Заблокувати spammer' }));
    const days = screen.getByLabelText('Термін, днів');
    await userEvent.clear(days);
    await userEvent.type(days, '14');
    await userEvent.type(screen.getByLabelText(/Повідомлення користувачу/), 'Спам у коментарях');
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Заблокувати' }));

    expect(apiClient.post).toHaveBeenCalledWith('/admin/bans', {
      user_id: 'u-1',
      ban_type: 'temporary',
      duration_days: 14,
      reason: 'Спам у коментарях',
    });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(apiClient.get).toHaveBeenCalledTimes(2);
  });

  it('rejects a temporary ban longer than a year without calling the server', async () => {
    render(<AdminUsers />);

    await userEvent.click(await screen.findByRole('button', { name: 'Заблокувати spammer' }));
    const days = screen.getByLabelText('Термін, днів');
    await userEvent.clear(days);
    await userEvent.type(days, '400');
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Заблокувати' }));

    expect(screen.getByRole('alert')).toHaveTextContent('від 1 до 365');
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('lifts a ban', async () => {
    // Trace: T-036
    apiClient.delete.mockResolvedValue({ data: { message: 'Ban lifted' } });
    render(<AdminUsers />);

    await userEvent.click(await screen.findByRole('button', { name: 'Розблокувати troll' }));

    expect(apiClient.delete).toHaveBeenCalledWith('/admin/bans', { params: { user_id: 'u-2' } });
  });

  it('shows the server refusal to ban an administrator', async () => {
    apiClient.post.mockRejectedValue({ response: { data: { error: { code: 'CANNOT_BAN_ADMIN' } } } });
    render(<AdminUsers />);

    await userEvent.click(await screen.findByRole('button', { name: 'Заблокувати spammer' }));
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Заблокувати' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Адміністратора заблокувати не можна.');
  });
});

describe('AdminUsers deletion', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.get.mockResolvedValue(list([viewer, banned, admin]));
  });

  it('deletes a user after confirmation and reloads the list', async () => {
    apiClient.delete.mockResolvedValue({ status: 204 });
    render(<AdminUsers />);

    await userEvent.click(await screen.findByRole('button', { name: 'Видалити spammer' }));
    expect(within(screen.getByRole('dialog')).getByText(/spam@example.com/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Видалити назавжди' }));

    expect(apiClient.delete).toHaveBeenCalledWith('/admin/users', { params: { user_id: 'u-1' } });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(apiClient.get).toHaveBeenCalledTimes(2);
  });

  it('does nothing when cancelled and offers no deletion for admins', async () => {
    render(<AdminUsers />);

    await userEvent.click(await screen.findByRole('button', { name: 'Видалити spammer' }));
    await userEvent.click(screen.getByRole('button', { name: 'Скасувати' }));

    expect(apiClient.delete).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'Видалити moderator' })).not.toBeInTheDocument();
  });

  it('explains that the demo account cannot be deleted', async () => {
    apiClient.delete.mockRejectedValue({ response: { data: { error: { code: 'SEED_ACCOUNT_LOCKED' } } } });
    render(<AdminUsers />);

    await userEvent.click(await screen.findByRole('button', { name: 'Видалити spammer' }));
    await userEvent.click(screen.getByRole('button', { name: 'Видалити назавжди' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Демо-акаунт видалити не можна.');
  });
});
