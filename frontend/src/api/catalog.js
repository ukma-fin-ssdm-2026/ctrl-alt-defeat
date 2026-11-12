import apiClient from './client';

// The API returns at most 100 titles per request (GET /movies, limit <= 100)
export const CATALOG_PAGE_SIZE = 100;
// Up to 3000 titles (the TMDB import keeps 500 movies, 500 series and 500 cartoons)
const MAX_PAGES = 30;
// Pages requested at the same time once the total is known
const PARALLEL_PAGES = 4;

// Identical requests made at the same time (home page and header search on start) share one load
const inFlight = new Map();

const getPage = (params, skip) =>
  apiClient.get('/movies', { params: { ...params, skip, limit: CATALOG_PAGE_SIZE } }).then(response => response.data);

async function loadWholeCatalog(params) {
  const first = await getPage(params, 0);
  const items = [...(first.items || [])];
  if (!first.has_more || items.length === 0) return items;

  // Without the total, the next pages are requested one after another
  if (!Number.isFinite(first.total)) {
    for (let page = 1; page < MAX_PAGES; page += 1) {
      const data = await getPage(params, items.length);
      const pageItems = data.items || [];
      items.push(...pageItems);
      if (!data.has_more || pageItems.length === 0) break;
    }
    return items;
  }

  // With the total, the remaining pages are requested a few at a time
  const pages = Math.min(Math.ceil(first.total / CATALOG_PAGE_SIZE), MAX_PAGES);
  const skips = Array.from({ length: pages - 1 }, (_, i) => (i + 1) * CATALOG_PAGE_SIZE);
  for (let i = 0; i < skips.length; i += PARALLEL_PAGES) {
    const results = await Promise.all(skips.slice(i, i + PARALLEL_PAGES).map(skip => getPage(params, skip)));
    results.forEach(data => items.push(...(data.items || [])));
  }

  // A title added or removed during the load could shift the pages: keep each title once
  const seen = new Set();
  return items.filter(item => {
    const key = item.id ?? item.content_id;
    if (key === undefined || key === null) return true;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

// Every title matching the filters (no filters = whole catalog: header search, user lists, home page)
export function fetchWholeCatalog(params = {}) {
  const key = JSON.stringify(params);
  if (!inFlight.has(key)) {
    const load = loadWholeCatalog(params).finally(() => inFlight.delete(key));
    inFlight.set(key, load);
  }
  return inFlight.get(key);
}
