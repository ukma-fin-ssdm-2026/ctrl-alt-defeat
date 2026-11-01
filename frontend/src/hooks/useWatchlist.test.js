import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import useWatchlist from './useWatchlist';

vi.mock('../api/client', () => ({
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

const user = { user_id: 'u-1', nickname: 'viewer' };
const dune = { id: 1, content_id: '11111111-1111-4111-8111-111111111111', title: 'Dune' };
const shrek = { id: 3, content_id: '33333333-3333-4333-8333-333333333333', title: 'Shrek' };
const mockOnly = { id: 99, title: 'Mock movie without content id' };

const setup = async (props = {}) => {
  const hook = renderHook(p => useWatchlist(p), { initialProps: { user, catalog: [dune, shrek, mockOnly], ...props } });
  const activeUser = 'user' in props ? props.user : user;
  if (activeUser) await waitFor(() => expect(apiClient.get).toHaveBeenCalled());
  return hook;
};

describe('useWatchlist (FR-005)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    apiClient.get.mockResolvedValue({ data: { items: [dune], total: 1 } });
    apiClient.post.mockResolvedValue({ data: shrek });
    apiClient.delete.mockResolvedValue({});
  });

  it('loads the saved watchlist after login', async () => {
    // Trace: T-004
    const { result } = await setup();

    await waitFor(() => expect(result.current.watchlistMovies).toEqual([dune]));
    expect(apiClient.get).toHaveBeenCalledWith('/watchlist');
    expect(result.current.watchlistIds).toContain(1);
    expect(result.current.watchlistIds).toContain(dune.content_id);
  });

  it('adds a title instantly and saves it on the server', async () => {
    // Trace: T-001
    const { result } = await setup();
    await waitFor(() => expect(result.current.watchlistMovies).toHaveLength(1));

    await act(() => result.current.toggleWatchlist(3));

    expect(apiClient.post).toHaveBeenCalledWith('/watchlist', { content_id: shrek.content_id });
    expect(result.current.watchlistMovies.map(m => m.title)).toEqual(['Shrek', 'Dune']);
  });

  it('removes a title that is already in the list', async () => {
    // Trace: T-003
    const { result } = await setup();
    await waitFor(() => expect(result.current.watchlistMovies).toHaveLength(1));

    await act(() => result.current.toggleWatchlist(dune));

    expect(apiClient.delete).toHaveBeenCalledWith('/watchlist', { params: { content_id: dune.content_id } });
    expect(result.current.watchlistMovies).toEqual([]);
  });

  it('keeps the title when the server reports it is already saved', async () => {
    // Trace: T-002
    apiClient.get.mockResolvedValue({ data: { items: [], total: 0 } });
    apiClient.post.mockRejectedValue({ response: { status: 409 } });
    const { result } = await setup();

    await act(() => result.current.toggleWatchlist(1));

    expect(result.current.watchlistMovies).toEqual([dune]);
    expect(result.current.error).toBeNull();
  });

  it('rolls back and reports an error when saving fails', async () => {
    // Trace: T-001
    apiClient.post.mockRejectedValue({ response: { status: 500 } });
    const { result } = await setup();
    await waitFor(() => expect(result.current.watchlistMovies).toHaveLength(1));

    await act(() => result.current.toggleWatchlist(3));

    expect(result.current.watchlistMovies).toEqual([dune]);
    expect(result.current.error).toBe('FAILED');
  });

  it('asks a guest to log in and does not call the API', async () => {
    // Trace: T-001
    const onAuthRequired = vi.fn();
    const { result } = await setup({ user: null, onAuthRequired });

    await act(() => result.current.toggleWatchlist(1));

    expect(onAuthRequired).toHaveBeenCalledTimes(1);
    expect(apiClient.get).not.toHaveBeenCalled();
    expect(apiClient.post).not.toHaveBeenCalled();
    expect(result.current.watchlistMovies).toEqual([]);
  });

  it('refuses titles that are not stored on the backend', async () => {
    // Trace: T-001
    const { result } = await setup();

    await act(() => result.current.toggleWatchlist(99));

    expect(result.current.error).toBe('UNAVAILABLE');
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('clears the list on logout', async () => {
    // Trace: T-004
    const { result, rerender } = await setup();
    await waitFor(() => expect(result.current.watchlistMovies).toHaveLength(1));

    rerender({ user: null, catalog: [dune] });

    expect(result.current.watchlistMovies).toEqual([]);
  });
});
