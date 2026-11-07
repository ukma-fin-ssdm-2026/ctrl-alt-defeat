import apiClient from './client';

// The API returns at most 100 titles per request (GET /movies, limit <= 100)
export const CATALOG_PAGE_SIZE = 100;
const MAX_PAGES = 20;

// Every title matching the filters, page by page (no filters = whole catalog: header search, user lists, home page)
export async function fetchWholeCatalog(params = {}) {
  const items = [];
  for (let page = 0; page < MAX_PAGES; page += 1) {
    const response = await apiClient.get('/movies', { params: { ...params, skip: items.length, limit: CATALOG_PAGE_SIZE } });
    const pageItems = response.data.items || [];
    items.push(...pageItems);
    if (!response.data.has_more || pageItems.length === 0) break;
  }
  return items;
}
