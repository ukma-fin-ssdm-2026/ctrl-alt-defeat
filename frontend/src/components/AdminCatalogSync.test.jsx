import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import AdminCatalogSync, { POLL_MS } from './AdminCatalogSync';

vi.mock('../api/client', () => ({ default: { get: vi.fn(), post: vi.fn() } }));

const idle = { configured: true, state: 'idle', added: 0, updated: 0, skipped: 0 };

describe('AdminCatalogSync (FR-012)', () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.useRealTimers());

  it('starts the update and shows the result after polling', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: idle })
      .mockResolvedValueOnce({ data: { ...idle, state: 'done', added: 250, updated: 30, placeholders_removed: 28, placeholders_kept: 2, finished_at: '2026-11-06T10:00:00Z' } });
    apiClient.post.mockResolvedValue({ data: { ...idle, state: 'running' } });
    render(<AdminCatalogSync />);

    const button = await screen.findByRole('button', { name: 'Оновити каталог з TMDB' });
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await userEvent.click(button);

    expect(apiClient.post).toHaveBeenCalledWith('/admin/catalog/sync');
    expect(screen.getByRole('button', { name: 'Оновлення…' })).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('Іде оновлення');

    await act(async () => { vi.advanceTimersByTime(POLL_MS); });
    expect(await screen.findByText(/додано 250, оновлено 30, прибрано тестових фільмів 28 \(2 залишено/)).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledTimes(2);
  });

  it('explains a missing TMDB key and disables the button', async () => {
    apiClient.get.mockResolvedValue({ data: { ...idle, configured: false } });
    render(<AdminCatalogSync />);

    expect(await screen.findByText(/додайте TMDB_API_KEY у Render/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Оновити каталог з TMDB' })).toBeDisabled();
  });

  it('shows a failed update', async () => {
    apiClient.get.mockResolvedValue({ data: { ...idle, state: 'failed', error: 'TMDB answered 401' } });
    render(<AdminCatalogSync language="EN" />);

    expect(await screen.findByText(/The update failed: TMDB answered 401/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Update from TMDB' })).toBeEnabled();
  });
});
