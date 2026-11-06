import { getSortParams } from './sortMovies';

// Query parameters of the catalog request for the current filters and sorting
export function buildCatalogParams({ selectedCategory, filterGenre, filterYear, sortKey }) {
  const params = {};
  if (selectedCategory) {
    const catLower = selectedCategory.toLowerCase();
    if (catLower === 'фільми' || catLower === 'movie' || catLower === 'movies') {
      params.category = 'Movie';
    } else if (catLower === 'серіали' || catLower === 'series' || catLower === 'tv shows') {
      params.category = 'Series';
    } else if (catLower === 'мультфільми' || catLower === 'cartoons') {
      params.category = 'Cartoons';
    } else {
      params.category = selectedCategory;
    }
  }
  if (filterGenre) params.genre = filterGenre;
  if (filterYear) params.year = filterYear;
  Object.assign(params, getSortParams(sortKey));
  return params;
}
