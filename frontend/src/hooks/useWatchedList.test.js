import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import useWatchedList from './useWatchedList';

vi.mock('../api/client', () => ({
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

const user = { user_id: 'u-1' };
const dune = { id: 1, content_id: '11111111-1111-4111-8111-111111111111', title: 'Dune' };
const shrek = { id: 3, content_id: '33333333-3333-4333-8333-333333333333', title: 'Shrek' };
const mockOnly = { id: 99, title: 'Mock movie without content id' };
const watchedDune = { id: 'w-1', content_id: dune.content_id, title: 'Dune' };

const setup = async (props = {}) => {
  const hook = renderHook(p => useWatchedList(p), { initialProps: { user, catalog: [dune, shrek, mockOnly], ...props } });
  const activeUser = 'user' in props ? props.user : user;
  if (activeUser) await waitFor(() => expect(apiClient.get).toHaveBeenCalled());
  return hook;
};

describe('useWatchedList (FR-006)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    apiClient.get.mockResolvedValue({ data: { items: [watchedDune], total: 1 } });
    apiClient.post.mockResolvedValue({ data: { id: 'w-2', content_id: shrek.content_id, title: 'Shrek' } });
    apiClient.delete.mockResolvedValue({});
  });

  it('loads the watched list after login', async () => {
    // Trace: T-011
    const { result } = await setup();

    await waitFor(() => expect(result.current.watchedMovies).toEqual([watchedDune]));
    expect(apiClient.get).toHaveBeenCalledWith('/users/me/watched');
    expect(result.current.isWatched(dune)).toBe(true);
    expect(result.current.isWatched(1)).toBe(true);
    expect(result.current.isWatched(shrek)).toBe(false);
  });

  it('marks a title as watched instantly and keeps the server version', async () => {
    // Trace: T-011
    const { result } = await setup();
    await waitFor(() => expect(result.current.watchedMovies).toHaveLength(1));

    await act(() => result.current.toggleWatched(shrek));

    expect(apiClient.post).toHaveBeenCalledWith('/users/me/watched', { content_id: shrek.content_id });
    expect(result.current.watchedMovies.map(m => m.id)).toEqual(['w-2', 'w-1']);
    expect(result.current.isWatched(shrek)).toBe(true);
  });

  it('removes a watched title', async () => {
    // Trace: T-012
    const { result } = await setup();
    await waitFor(() => expect(result.current.watchedMovies).toHaveLength(1));

    await act(() => result.current.toggleWatched(1));

    expect(apiClient.delete).toHaveBeenCalledWith('/users/me/watched', { params: { content_id: dune.content_id } });
    expect(result.current.watchedMovies).toEqual([]);
  });

  it('rolls back and shows an error instead of failing silently', async () => {
    // Trace: T-011
    apiClient.post.mockRejectedValue({ response: { status: 500 } });
    const { result } = await setup();
    await waitFor(() => expect(result.current.watchedMovies).toHaveLength(1));

    await act(() => result.current.toggleWatched(shrek));

    expect(result.current.watchedMovies).toEqual([watchedDune]);
    expect(result.current.error).toBe('FAILED');
  });

  it('reports titles that are not in the backend catalog', async () => {
    // Trace: T-011
    const { result } = await setup();

    await act(() => result.current.toggleWatched(99));

    expect(result.current.error).toBe('UNAVAILABLE');
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('asks a guest to log in', async () => {
    // Trace: T-011
    const onAuthRequired = vi.fn();
    const { result } = await setup({ user: null, onAuthRequired });

    await act(() => result.current.toggleWatched(dune));

    expect(onAuthRequired).toHaveBeenCalledTimes(1);
    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it('clears the list on logout', async () => {
    // Trace: T-012
    const { result, rerender } = await setup();
    await waitFor(() => expect(result.current.watchedMovies).toHaveLength(1));

    rerender({ user: null, catalog: [] });

    expect(result.current.watchedMovies).toEqual([]);
  });
});
