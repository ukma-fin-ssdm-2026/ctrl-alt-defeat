import { describe, expect, it } from 'vitest';
import { buildCatalogParams } from './catalogParams';

describe('catalog request parameters', () => {
  it('maps the menu categories to the API categories', () => {
    expect(buildCatalogParams({ selectedCategory: 'Фільми' })).toEqual({ category: 'Movie' });
    expect(buildCatalogParams({ selectedCategory: 'TV Shows' })).toEqual({ category: 'Series' });
    expect(buildCatalogParams({ selectedCategory: 'Мультфільми' })).toEqual({ category: 'Cartoons' });
    expect(buildCatalogParams({ selectedCategory: 'Other' })).toEqual({ category: 'Other' });
  });

  it('adds genre, year and sorting', () => {
    expect(buildCatalogParams({ filterGenre: 'Драма', filterYear: 2024, sortKey: 'rating_desc' })).toEqual({
      genre: 'Драма',
      year: 2024,
      sort_by: 'rating',
      order: 'desc',
    });
    expect(buildCatalogParams({})).toEqual({});
  });
});
