import { describe, expect, it } from 'vitest';
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
    // Every genre the backend creates (src/api/services/genres.py: TMDB movie and TV genres, extra genres)
    const catalogGenres = [
      'Бойовик', 'Пригоди', 'Мультфільм', 'Комедія', 'Кримінал', 'Документальний', 'Драма', 'Сімейний',
      'Фентезі', 'Історія', 'Жахи', 'Музика', 'Детектив', 'Мелодрама', 'Фантастика', 'Телефільм', 'Трилер',
      'Воєнний', 'Вестерн', 'Біографія', 'Дитячий', 'Новини', 'Реаліті', 'Мильна опера', 'Ток-шоу',
    ];
    const missing = catalogGenres.filter(genre => !GENRE_TRANSLATIONS[genre]);
    expect(missing).toEqual([]);
  });
});
