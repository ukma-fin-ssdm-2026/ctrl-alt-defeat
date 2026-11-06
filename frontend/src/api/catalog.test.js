import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from './client';
import { CATALOG_PAGE_SIZE, fetchWholeCatalog } from './catalog';

vi.mock('./client', () => ({ default: { get: vi.fn() } }));

const titles = (from, count) => Array.from({ length: count }, (_, i) => ({ id: from + i }));

describe('fetchWholeCatalog', () => {
  beforeEach(() => vi.clearAllMocks());

  it('loads every page until the API has no more titles', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: { items: titles(1, 100), has_more: true } })
      .mockResolvedValueOnce({ data: { items: titles(101, 100), has_more: true } })
      .mockResolvedValueOnce({ data: { items: titles(201, 30), has_more: false } });

    const catalog = await fetchWholeCatalog();

    expect(catalog).toHaveLength(230);
    expect(apiClient.get).toHaveBeenNthCalledWith(2, '/movies', { params: { skip: 100, limit: CATALOG_PAGE_SIZE } });
    expect(apiClient.get).toHaveBeenCalledTimes(3);
  });

  it('stops on an empty page and passes errors on', async () => {
    apiClient.get.mockResolvedValueOnce({ data: { items: [], has_more: true } });
    expect(await fetchWholeCatalog()).toEqual([]);

    apiClient.get.mockRejectedValueOnce(new Error('offline'));
    await expect(fetchWholeCatalog()).rejects.toThrow('offline');
  });
});

describe('fetchWholeCatalog with filters', () => {
  beforeEach(() => vi.clearAllMocks());

  it('keeps the filters on every page', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: { items: titles(1, 100), has_more: true } })
      .mockResolvedValueOnce({ data: { items: titles(101, 5), has_more: false } });

    await fetchWholeCatalog({ category: 'Cartoons', sort_by: 'rating', order: 'desc' });

    expect(apiClient.get).toHaveBeenLastCalledWith('/movies', {
      params: { category: 'Cartoons', sort_by: 'rating', order: 'desc', skip: 100, limit: CATALOG_PAGE_SIZE },
    });
  });
});
