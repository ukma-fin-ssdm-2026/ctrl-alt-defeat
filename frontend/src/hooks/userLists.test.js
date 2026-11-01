import { act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import { dune, mockListApi, renderListHook, shrek } from '../test/listFixtures';
import useWatchedList from './useWatchedList';
import useWatchlist from './useWatchlist';

vi.mock('../api/client', () => ({
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

// Behaviour shared by both lists (useUserList core)
describe.each([
  { name: 'watchlist (FR-005)', useHook: useWatchlist, path: '/watchlist', itemsKey: 'watchlistMovies', toggleKey: 'toggleWatchlist' },
  { name: 'watched list (FR-006)', useHook: useWatchedList, path: '/users/me/watched', itemsKey: 'watchedMovies', toggleKey: 'toggleWatched' },
])('$name', ({ useHook, path, itemsKey, toggleKey }) => {
  beforeEach(() => {
    mockListApi();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  it('loads the saved list after login', async () => {
    // Trace: T-004
    const { result } = await renderListHook(useHook);

    await waitFor(() => expect(result.current[itemsKey]).toEqual([dune]));
    expect(apiClient.get).toHaveBeenCalledWith(path);
  });

  it('asks a guest to log in and does not call the API', async () => {
    // Trace: T-001
    const onAuthRequired = vi.fn();
    const { result } = await renderListHook(useHook, { user: null, onAuthRequired });

    await act(() => result.current[toggleKey](dune));

    expect(onAuthRequired).toHaveBeenCalledTimes(1);
    expect(apiClient.get).not.toHaveBeenCalled();
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('rolls back and reports an error when the server refuses', async () => {
    // Trace: T-011
    apiClient.post.mockRejectedValue({ response: { status: 500 } });
    const { result } = await renderListHook(useHook);
    await waitFor(() => expect(result.current[itemsKey]).toHaveLength(1));

    await act(() => result.current[toggleKey](shrek));

    expect(result.current[itemsKey]).toEqual([dune]);
    expect(result.current.error).toBe('FAILED');
  });

  it('reports titles that are not in the backend catalog', async () => {
    // Trace: T-001
    const { result } = await renderListHook(useHook);

    await act(() => result.current[toggleKey](99));

    expect(result.current.error).toBe('UNAVAILABLE');
    expect(apiClient.post).not.toHaveBeenCalled();
    act(() => result.current.clearError());
    expect(result.current.error).toBeNull();
  });

  it('clears the list on logout', async () => {
    // Trace: T-012
    const { result, rerender } = await renderListHook(useHook);
    await waitFor(() => expect(result.current[itemsKey]).toHaveLength(1));

    rerender({ user: null, catalog: [] });

    expect(result.current[itemsKey]).toEqual([]);
  });
});

describe('useWatchlist (FR-005)', () => {
  beforeEach(() => mockListApi());

  it('exposes both numeric and content ids', async () => {
    // Trace: T-004
    const { result } = await renderListHook(useWatchlist);

    await waitFor(() => expect(result.current.watchlistIds).toEqual([1, dune.content_id]));
  });

  it('adds a title instantly and saves it on the server', async () => {
    // Trace: T-001
    const { result } = await renderListHook(useWatchlist);
    await waitFor(() => expect(result.current.watchlistMovies).toHaveLength(1));

    await act(() => result.current.toggleWatchlist(3));

    expect(apiClient.post).toHaveBeenCalledWith('/watchlist', { content_id: shrek.content_id });
    expect(result.current.watchlistMovies.map(m => m.title)).toEqual(['Shrek', 'Dune']);
  });

  it('removes a title that is already in the list', async () => {
    // Trace: T-003
    const { result } = await renderListHook(useWatchlist);
    await waitFor(() => expect(result.current.watchlistMovies).toHaveLength(1));

    await act(() => result.current.toggleWatchlist(dune));

    expect(apiClient.delete).toHaveBeenCalledWith('/watchlist', { params: { content_id: dune.content_id } });
    expect(result.current.watchlistMovies).toEqual([]);
  });

  it('keeps the title when the server reports it is already saved', async () => {
    // Trace: T-002
    apiClient.get.mockResolvedValue({ data: { items: [] } });
    apiClient.post.mockRejectedValue({ response: { status: 409 } });
    const { result } = await renderListHook(useWatchlist);

    await act(() => result.current.toggleWatchlist(1));

    expect(result.current.watchlistMovies).toEqual([dune]);
    expect(result.current.error).toBeNull();
  });
});

const watchedDune = { id: 'w-1', content_id: dune.content_id, title: 'Dune' };

describe('useWatchedList (FR-006)', () => {
  beforeEach(() => mockListApi({ items: [watchedDune], created: { id: 'w-2', content_id: shrek.content_id, title: 'Shrek' } }));

  it('checks the watched state by movie object or numeric id', async () => {
    // Trace: T-011
    const { result } = await renderListHook(useWatchedList);

    await waitFor(() => expect(result.current.isWatched(dune)).toBe(true));
    expect(result.current.isWatched(1)).toBe(true);
    expect(result.current.isWatched(shrek)).toBe(false);
  });

  it('marks a title as watched and keeps the server version', async () => {
    // Trace: T-011
    const { result } = await renderListHook(useWatchedList);
    await waitFor(() => expect(result.current.watchedMovies).toHaveLength(1));

    await act(() => result.current.toggleWatched(shrek));

    expect(apiClient.post).toHaveBeenCalledWith('/users/me/watched', { content_id: shrek.content_id });
    expect(result.current.watchedMovies.map(m => m.id)).toEqual(['w-2', 'w-1']);
  });

  it('removes a watched title via a constant URL', async () => {
    // Trace: T-012
    const { result } = await renderListHook(useWatchedList);
    await waitFor(() => expect(result.current.watchedMovies).toHaveLength(1));

    await act(() => result.current.toggleWatched(1));

    expect(apiClient.delete).toHaveBeenCalledWith('/users/me/watched', { params: { content_id: dune.content_id } });
    expect(result.current.watchedMovies).toEqual([]);
  });

  it('keeps the removal when the server says it was already removed', async () => {
    // Trace: T-012
    apiClient.delete.mockRejectedValue({ response: { status: 404 } });
    const { result } = await renderListHook(useWatchedList);
    await waitFor(() => expect(result.current.watchedMovies).toHaveLength(1));

    await act(() => result.current.toggleWatched(dune));

    expect(result.current.watchedMovies).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});
