import { describe, expect, it } from 'vitest';
import { SORT_OPTIONS, getSortParams, sortMovies } from './sortMovies';

const movies = [
  { id: 1, title: 'Drama Old', rating: 9.3, year: 1994, runtime: 142 },
  { id: 2, title: 'SciFi New', rating: 8.8, year: 2024, runtime: 166 },
  { id: 3, title: 'Drama New', rating: 8.5, year: 2019, runtime: 132 },
  { id: 4, title: 'Unknown Runtime', rating: 7.0, year: 2026, runtime: null },
  { id: 5, title: 'SciFi Mid', rating: 8.8, year: 2016, runtime: 51 },
];

const ids = list => list.map(movie => movie.id);

describe('getSortParams (FR-010)', () => {
  it('maps a sort key to backend query params', () => {
    expect(getSortParams('rating_desc')).toEqual({ sort_by: 'rating', order: 'desc' });
    expect(getSortParams('release_date_asc')).toEqual({ sort_by: 'release_date', order: 'asc' });
    expect(getSortParams('runtime_desc')).toEqual({ sort_by: 'runtime', order: 'desc' });
  });

  it('returns no params for default or unknown keys', () => {
    expect(getSortParams('')).toEqual({});
    expect(getSortParams('popularity')).toEqual({});
  });

  it('every non-default option has a backend field and both labels', () => {
    SORT_OPTIONS.filter(option => option.key).forEach(option => {
      expect(['rating', 'release_date', 'runtime']).toContain(option.field);
      expect(option.labelUkr).toBeTruthy();
      expect(option.labelEn).toBeTruthy();
    });
  });
});

describe('sortMovies (FR-010)', () => {
  it('sorts by rating, highest first, ties by id', () => {
    expect(ids(sortMovies(movies, 'rating_desc'))).toEqual([1, 2, 5, 3, 4]);
  });

  it('sorts by release date in both directions', () => {
    expect(ids(sortMovies(movies, 'release_date_desc'))).toEqual([4, 2, 3, 5, 1]);
    expect(ids(sortMovies(movies, 'release_date_asc'))).toEqual([1, 5, 3, 2, 4]);
  });

  it('puts movies without runtime last in both directions', () => {
    expect(ids(sortMovies(movies, 'runtime_desc'))).toEqual([2, 1, 3, 5, 4]);
    expect(ids(sortMovies(movies, 'runtime_asc'))).toEqual([5, 3, 1, 2, 4]);
  });

  it('puts missing values last even when they come first in the input', () => {
    const list = [
      { id: 1, runtime: null, rating: undefined },
      { id: 2, runtime: 100, rating: 7 },
      { id: 3, runtime: 50, rating: 9 },
    ];
    expect(ids(sortMovies(list, 'runtime_desc'))).toEqual([2, 3, 1]);
    expect(ids(sortMovies(list, 'runtime_asc'))).toEqual([3, 2, 1]);
    expect(ids(sortMovies(list, 'rating_desc'))).toEqual([3, 2, 1]);
  });

  it('keeps the original order for the default option', () => {
    expect(ids(sortMovies(movies, ''))).toEqual([1, 2, 3, 4, 5]);
  });

  it('does not mutate the input array', () => {
    const copy = [...movies];
    sortMovies(movies, 'rating_desc');
    expect(movies).toEqual(copy);
  });

  it('handles empty input', () => {
    expect(sortMovies(undefined, 'rating_desc')).toEqual([]);
  });
});
