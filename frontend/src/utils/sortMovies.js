// Catalog sorting (FR-010). Mirrors the backend rules so the mock fallback behaves the same way:
// unknown values always go last, equal values keep a stable order by id.

export const SORT_OPTIONS = [
  { key: '', labelUkr: 'За замовчуванням', labelEn: 'Default' },
  { key: 'rating_desc', field: 'rating', order: 'desc', labelUkr: 'За рейтингом (спершу найвищий)', labelEn: 'Rating (highest first)' },
  { key: 'release_date_desc', field: 'release_date', order: 'desc', labelUkr: 'За датою виходу (спершу нові)', labelEn: 'Release date (newest first)' },
  { key: 'release_date_asc', field: 'release_date', order: 'asc', labelUkr: 'За датою виходу (спершу старі)', labelEn: 'Release date (oldest first)' },
  { key: 'runtime_desc', field: 'runtime', order: 'desc', labelUkr: 'За тривалістю (спершу довші)', labelEn: 'Runtime (longest first)' },
  { key: 'runtime_asc', field: 'runtime', order: 'asc', labelUkr: 'За тривалістю (спершу коротші)', labelEn: 'Runtime (shortest first)' },
];

// API field -> movie object property
const FIELD_TO_PROP = {
  rating: 'rating',
  release_date: 'year',
  runtime: 'runtime',
};

export function getSortOption(sortKey) {
  return SORT_OPTIONS.find(option => option.key === sortKey && option.field) || null;
}

// Query params for GET /movies, e.g. { sort_by: 'rating', order: 'desc' }
export function getSortParams(sortKey) {
  const option = getSortOption(sortKey);
  return option ? { sort_by: option.field, order: option.order } : {};
}

const isMissing = value => value === null || value === undefined || value === '';

const compareIds = (a, b) => {
  const idA = Number(a.id);
  const idB = Number(b.id);
  if (Number.isFinite(idA) && Number.isFinite(idB)) return idA - idB;
  return String(a.id ?? a.content_id ?? '').localeCompare(String(b.id ?? b.content_id ?? ''));
};

// Returns a new sorted array; the input array is not mutated.
export function sortMovies(movies, sortKey) {
  const list = [...(movies || [])];
  const option = getSortOption(sortKey);
  if (!option) return list;

  const prop = FIELD_TO_PROP[option.field];
  const direction = option.order === 'asc' ? 1 : -1;

  return list.sort((a, b) => {
    const valueA = a[prop];
    const valueB = b[prop];
    const missingA = isMissing(valueA);
    const missingB = isMissing(valueB);
    if (missingA !== missingB) return missingA ? 1 : -1;
    if (!missingA && Number(valueA) !== Number(valueB)) {
      return (Number(valueA) - Number(valueB)) * direction;
    }
    return compareIds(a, b);
  });
}
