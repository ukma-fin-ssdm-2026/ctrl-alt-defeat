import { describe, expect, it } from 'vitest';
import { mockMovies } from '../data/mockData';
import { GENRE_TRANSLATIONS, translateGenre } from './genres';

describe('translateGenre', () => {
  it('keeps Ukrainian genre names in the Ukrainian interface', () => {
    expect(translateGenre('Драма', 'UKR')).toBe('Драма');
  });

  it('translates genres in the English interface', () => {
    expect(translateGenre('Драма', 'EN')).toBe('Drama');
    expect(translateGenre('Пригоди', 'EN')).toBe('Adventure');
    expect(translateGenre('Кримінал', 'EN')).toBe('Crime');
  });

  it('shows unknown genres as is and handles empty values', () => {
    expect(translateGenre('Аніме', 'EN')).toBe('Аніме');
    expect(translateGenre(undefined, 'EN')).toBe('');
  });

  it('has a translation for every genre used in the catalog', () => {
    const catalogGenres = new Set(mockMovies.flatMap(movie => [movie.genre, ...(movie.genres || [])]).filter(Boolean));
    const missing = [...catalogGenres].filter(genre => !GENRE_TRANSLATIONS[genre]);
    expect(missing).toEqual([]);
  });
});
