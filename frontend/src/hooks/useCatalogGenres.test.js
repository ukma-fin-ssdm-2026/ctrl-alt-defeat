import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../api/client';
import useCatalogGenres, { FALLBACK_GENRES } from './useCatalogGenres';

vi.mock('../api/client', () => ({ default: { get: vi.fn() } }));

describe('catalog genres (US-012)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('uses the genres that have titles on the server', async () => {
    apiClient.get.mockResolvedValue({
      data: [{ genre_id: 1, name: 'Вестерн', titles_count: 1 }, { genre_id: 2, name: 'Драма', titles_count: 9 }],
    });
    const { result } = renderHook(() => useCatalogGenres());

    expect(result.current).toEqual(FALLBACK_GENRES);
    await waitFor(() => expect(result.current).toEqual(['Вестерн', 'Драма']));
    expect(apiClient.get).toHaveBeenCalledWith('/genres');
  });

  it('keeps the built-in list when the server is unavailable or empty', async () => {
    apiClient.get.mockRejectedValueOnce(new Error('offline'));
    const offline = renderHook(() => useCatalogGenres());
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(1));
    expect(offline.result.current).toEqual(FALLBACK_GENRES);

    apiClient.get.mockResolvedValueOnce({ data: [] });
    const empty = renderHook(() => useCatalogGenres());
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(2));
    expect(empty.result.current).toEqual(FALLBACK_GENRES);
  });
});
