// Single source of genre names for the UI. The catalog stores genres in Ukrainian;
// in the English interface they are translated here (unknown genres are shown as is).
export const GENRE_TRANSLATIONS = {
  'Бойовик': 'Action',
  'Біографія': 'Biography',
  'Детектив': 'Detective',
  'Дитячий': 'Kids',
  'Документальний': 'Documentary',
  'Вестерн': 'Western',
  'Воєнний': 'War',
  'Драма': 'Drama',
  'Жахи': 'Horror',
  'Історія': 'History',
  'Комедія': 'Comedy',
  'Кримінал': 'Crime',
  'Мелодрама': 'Romance',
  'Мильна опера': 'Soap',
  'Музика': 'Music',
  'Новини': 'News',
  'Мультфільм': 'Animation',
  'Пригоди': 'Adventure',
  'Реаліті': 'Reality',
  'Сімейний': 'Family',
  'Телефільм': 'TV Movie',
  'Ток-шоу': 'Talk',
  'Трилер': 'Thriller',
  'Фантастика': 'Sci-Fi',
  'Фентезі': 'Fantasy',
};

export function translateGenre(genre, language = 'UKR') {
  if (!genre) return '';
  if (language === 'UKR') return genre;
  return GENRE_TRANSLATIONS[genre] || genre;
}
