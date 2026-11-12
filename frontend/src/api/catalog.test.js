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

describe('fetchWholeCatalog with a known total', () => {
  beforeEach(() => vi.clearAllMocks());

  it('requests the remaining pages in parallel and keeps every title once', async () => {
    apiClient.get.mockImplementation((url, { params }) => {
      const total = 1530;
      // The page at skip 200 overlaps the previous one (a title was added during the load)
      const from = params.skip === 200 ? 200 : params.skip + 1;
      const count = Math.min(CATALOG_PAGE_SIZE, total - params.skip);
      return Promise.resolve({ data: { items: titles(from, count), total, has_more: params.skip + count < total } });
    });

    const catalog = await fetchWholeCatalog({ category: 'Movie' });

    expect(apiClient.get).toHaveBeenCalledTimes(16);
    const skips = apiClient.get.mock.calls.map(([, { params }]) => params.skip);
    expect(skips).toEqual(Array.from({ length: 16 }, (_, i) => i * 100));
    expect(apiClient.get.mock.calls.every(([, { params }]) => params.category === 'Movie')).toBe(true);
    expect(new Set(catalog.map(item => item.id)).size).toBe(catalog.length);
    expect(catalog).toHaveLength(1529);
  });

  it('shares one load between identical requests made at the same time', async () => {
    apiClient.get.mockResolvedValue({ data: { items: titles(1, 3), total: 3, has_more: false } });

    const [home, header] = await Promise.all([fetchWholeCatalog(), fetchWholeCatalog()]);

    expect(home).toBe(header);
    expect(apiClient.get).toHaveBeenCalledTimes(1);
    // Once finished, the next request loads fresh data
    await fetchWholeCatalog();
    expect(apiClient.get).toHaveBeenCalledTimes(2);
  });
});
