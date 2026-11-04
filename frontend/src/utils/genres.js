// Single source of genre names for the UI. The catalog stores genres in Ukrainian;
// in the English interface they are translated here (unknown genres are shown as is).
export const GENRE_TRANSLATIONS = {
  'Бойовик': 'Action',
  'Біографія': 'Biography',
  'Детектив': 'Detective',
  'Документальний': 'Documentary',
  'Драма': 'Drama',
  'Жахи': 'Horror',
  'Історія': 'History',
  'Комедія': 'Comedy',
  'Кримінал': 'Crime',
  'Мелодрама': 'Romance',
  'Музика': 'Music',
  'Мультфільм': 'Animation',
  'Пригоди': 'Adventure',
  'Сімейний': 'Family',
  'Трилер': 'Thriller',
  'Фантастика': 'Sci-Fi',
};

export function translateGenre(genre, language = 'UKR') {
  if (!genre) return '';
  if (language === 'UKR') return genre;
  return GENRE_TRANSLATIONS[genre] || genre;
}
